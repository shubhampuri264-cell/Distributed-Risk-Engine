import click
import requests
import pandas as pd
import json

API_URL = "http://127.0.0.1:8000"

@click.group()
def cli():
    """Distributed Risk Engine CLI - API Client"""
    pass

@cli.command()
@click.option('--ticker', multiple=True, required=True, help='Ticker symbol(s) (e.g. AAPL)')
@click.option('--start', required=True, help='Start date (YYYY-MM-DD)')
@click.option('--end', required=True, help='End date (YYYY-MM-DD)')
def ingest(ticker, start, end):
    """Ingest market data via API."""
    payload = {
        "tickers": list(ticker),
        "start_date": start,
        "end_date": end
    }
    try:
        response = requests.post(f"{API_URL}/ingest", json=payload)
        response.raise_for_status()
        data = response.json()
        if data.get("status") == "success":
            click.echo(f"Success: {data.get('rows')} rows loaded.")
        else:
            click.echo(f"Warning: {data.get('message')}")
    except requests.exceptions.ConnectionError:
        click.echo("Error: Could not connect to API. Is it running?")
    except Exception as e:
        click.echo(f"Error: {e}")

@cli.command()
@click.option('--ticker', required=True, help='Ticker symbol to simulate')
@click.option('--initial', default=100.0, help='Initial price')
@click.option('--days', default=252, help='Time horizon in days')
@click.option('--paths', default=10000, help='Number of Monte Carlo paths')
@click.option('--vol', default=0.20, help='Annualized volatility')
@click.option('--drift', default=0.05, help='Annualized drift')
def simulate(ticker, initial, days, paths, vol, drift):
    """Run Monte Carlo simulation via API."""
    payload = {
        "ticker": ticker,
        "initial_price": initial,
        "days": days,
        "paths": paths,
        "volatility": vol,
        "drift": drift
    }
    try:
        click.echo(f"Requesting simulation for {ticker}...")
        response = requests.post(f"{API_URL}/simulate", json=payload)
        response.raise_for_status()
        res = response.json()
        
        click.echo(f"Simulation Complete")
        click.echo(f"Mean Final Price: {res['mean_price']:.2f}")
        click.echo(f"VaR (95%): {res['var_95']:.2f}")
        click.echo(f"CVaR (95%): {res['cvar_95']:.2f}")
        click.echo(f"VaR (99%): {res['var_99']:.2f}")
    except requests.exceptions.ConnectionError:
        click.echo("Error: Could not connect to API. Is it running?")
    except Exception as e:
        click.echo(f"Error: {e}")

@cli.command()
@click.option('--ticker', required=True)
@click.option('--scenario', type=click.Choice(['dotcom', '2008', 'covid']), required=True)
def stress_test(ticker, scenario):
    """Run stress test scenarios (Local logic for now, move to API later)."""
    # Note: Ideally this should also be an API call, but we kept it simple in phase 1
    click.echo(f"Running {scenario} stress test for {ticker}...")
    drops = {'dotcom': 0.45, '2008': 0.50, 'covid': 0.30}
    drop_pct = drops[scenario]
    initial = 100 
    loss = initial * drop_pct
    click.echo(f"Scenario {scenario} implies a {drop_pct*100}% drop.")
    click.echo(f"Estimated Impact on 100 unit position: -{loss:.2f}")

if __name__ == '__main__':
    cli()
