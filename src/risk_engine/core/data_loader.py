import yfinance as yf
import duckdb
import pandas as pd
import ccxt
from typing import List, Optional
import os
from datetime import datetime

DB_PATH = os.path.join(os.getcwd(), 'data', 'market_data.duckdb')

def get_db_connection():
    """Establishes connection to DuckDB."""
    con = duckdb.connect(DB_PATH)
    con.execute("""
        CREATE TABLE IF NOT EXISTS market_prices (
            Date DATE,
            Ticker VARCHAR,
            Open DOUBLE,
            High DOUBLE,
            Low DOUBLE,
            Close DOUBLE,
            Volume BIGINT,
            PRIMARY KEY (Date, Ticker)
        )
    """)
    return con

def fetch_crypto_data(ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    Fetches historical data from Binance via CCXT.
    Ticker format expected: 'BTC/USDT'
    """
    print(f"Fetching crypto data for {ticker} from Binance...")
    exchange = ccxt.binance()
    
    # Convert dates to timestamp (ms)
    start_ts = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp() * 1000)
    end_ts = int(datetime.strptime(end_date, "%Y-%m-%d").timestamp() * 1000)
    
    # CCXT fetch_ohlcv fetches limited candles (usually 500 or 1000). 
    # For a full range, we need a loop. For simplicity in this demo, we fetch the max allowed or loop once.
    # Risk Engine usually needs daily data. '1d' timeframe.
    
    all_ohlcv = []
    current_ts = start_ts
    
    try:
        while current_ts < end_ts:
            ohlcv = exchange.fetch_ohlcv(ticker, timeframe='1d', since=current_ts, limit=1000)
            if not ohlcv:
                break
            all_ohlcv.extend(ohlcv)
            current_ts = ohlcv[-1][0] + 86400000 # move to next day
            
            # small break to avoid rate limits if we were looping a lot.
            if len(ohlcv) < 1000:
                break
                
            if len(all_ohlcv) > 5000: # Cap at ~13 years for safety
                break
                
    except Exception as e:
        print(f"Error fetching {ticker} from Binance: {e}")
        return pd.DataFrame()

    if not all_ohlcv:
        return pd.DataFrame()

    # Convert to DataFrame
    df = pd.DataFrame(all_ohlcv, columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
    df['Date'] = pd.to_datetime(df['Timestamp'], unit='ms').dt.date
    df['Ticker'] = ticker
    
    # Filter by date (fetch_ohlcv 'since' is inclusive, but we might have gone past end)
    # We'll just return the relevant columns
    final_df = df[['Date', 'Ticker', 'Open', 'High', 'Low', 'Close', 'Volume']]
    return final_df

def fetch_market_data(tickers: List[str], start_date: str, end_date: str) -> pd.DataFrame:
    """
    Fetches historical market data. Routes to Binance for tickers with '/', otherwise Yahoo.
    """
    all_data = []
    
    yahoo_tickers = []
    crypto_tickers = []
    
    for t in tickers:
        if '/' in t:
            crypto_tickers.append(t)
        else:
            yahoo_tickers.append(t)
            
    # Process Yahoo Tickers
    if yahoo_tickers:
        print(f"Fetching Yahoo data for {yahoo_tickers}...")
        try:
            data = yf.download(yahoo_tickers, start=start_date, end=end_date, group_by='ticker', auto_adjust=True)
            
            if len(yahoo_tickers) == 1:
                ticker = yahoo_tickers[0]
                df = data.copy()
                # yfinance 0.2+ returns different structures. Data might not be MultiIndex if 1 ticker.
                if isinstance(df.columns, pd.MultiIndex):
                     df.columns = df.columns.droplevel(0) # Drop ticker level if exists
                
                df['Ticker'] = ticker
                df = df.reset_index()
                all_data.append(df)
            else:
                # Multi-ticker
                for ticker in yahoo_tickers:
                    try:
                        # Accessing MultiIndex columns: data[ticker] isn't always reliable with new pandas
                        # Use cross-section if possible, or simple column access
                        if ticker in data.columns.levels[0]:
                             df = data.xs(ticker, level=0, axis=1).copy()
                             df['Ticker'] = ticker
                             df = df.reset_index()
                             all_data.append(df)
                    except Exception as ex:
                        print(f"Skipping {ticker}: {ex}")
        except Exception as e:
            print(f"Error fetching Yahoo data: {e}")
            # If Yahoo fails physically (network), we just log it. Don't crash ingestion of others.

    # Process Crypto Tickers
    for t in crypto_tickers:
        df = fetch_crypto_data(t, start_date, end_date)
        if not df.empty:
            all_data.append(df)

    if not all_data:
        return pd.DataFrame()
        
    final_df = pd.concat(all_data)
    
    # Ensure Date is date object
    if pd.api.types.is_datetime64_any_dtype(final_df['Date']):
        final_df['Date'] = final_df['Date'].dt.date
        
    return final_df

def save_to_duckdb(df: pd.DataFrame):
    """
    Saves the DataFrame to DuckDB.
    """
    if df.empty:
        print("No data to save.")
        return

    con = get_db_connection()
    
    # We use 'INSERT OR IGNORE' or similar logic. DuckDB's insert from dataframe is clean.
    # But we want to avoid duplicates.
    # Simplest way: Create temp table, insert new records.
    
    con.register('df_view', df)
    
    # Check what columns we have
    # For simplicity, let's select specific columns
    try:
        con.execute("""
            INSERT INTO market_prices 
            SELECT Date, Ticker, Open, High, Low, Close, Volume 
            FROM df_view
            ON CONFLICT (Date, Ticker) DO UPDATE SET
                Open=EXCLUDED.Open,
                High=EXCLUDED.High,
                Low=EXCLUDED.Low,
                Close=EXCLUDED.Close,
                Volume=EXCLUDED.Volume
        """)
        print(f"Saved/Updated {len(df)} rows in DuckDB.")
    except Exception as e:
        print(f"Error saving to DB: {e}")
    finally:
        con.close()

def load_data_from_db(ticker: str) -> pd.DataFrame:
    """Loads data for a specific ticker from DuckDB."""
    con = duckdb.connect(DB_PATH, read_only=True)
    df = con.execute("SELECT * FROM market_prices WHERE Ticker = ? ORDER BY Date", [ticker]).fetchdf()
    con.close()
    return df

if __name__ == "__main__":
    # Test
    tickers = ["AAPL", "MSFT"]
    df = fetch_market_data(tickers, "2023-01-01", "2023-12-31")
    save_to_duckdb(df)
    print("Data loaded for AAPL:")
    print(load_data_from_db("AAPL").head())
