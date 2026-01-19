import click
import requests
import json
import os
from pathlib import Path

API_URL = "http://127.0.0.1:8000"
TOKEN_FILE = Path.home() / ".risk_engine_token"

def save_token(token):
    with open(TOKEN_FILE, "w") as f:
        f.write(token)

def load_token():
    if not TOKEN_FILE.exists():
        return None
    with open(TOKEN_FILE, "r") as f:
        return f.read().strip()

def get_auth_headers():
    token = load_token()
    if not token:
        raise click.ClickException("Not logged in. Run 'python -m risk_engine.cli login' first.")
    return {"Authorization": f"Bearer {token}"}

@click.group()
def cli():
    """Distributed Risk Engine CLI - API Client"""
    pass

@cli.command()
@click.option('--username', prompt=True)
@click.option('--password', prompt=True, hide_input=True)
def login(username, password):
    """Log in to the API and save credentials."""
    try:
        response = requests.post(f"{API_URL}/token", data={"username": username, "password": password})
        if response.status_code == 200:
            token = response.json()["access_token"]
            save_token(token)
            click.echo("Logged in successfully!")
        else:
            click.echo("Login failed: Invalid credentials.")
    except Exception as e:
        click.echo(f"Connection Error: {e}")

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
        response = requests.post(f"{API_URL}/ingest", json=payload, headers=get_auth_headers())
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success":
                click.echo(f"Success: {data.get('rows')} rows loaded.")
            else:
                click.echo(f"Warning: {data.get('message')}")
        else:
             click.echo(f"API Error: {response.text}")
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
        response = requests.post(f"{API_URL}/simulate", json=payload, headers=get_auth_headers())
        res = response.json()
        
        if response.status_code == 200:
            click.echo(f"Simulation Complete")
            click.echo(f"Mean Final Price: {res['mean_price']:.2f}")
            click.echo(f"VaR (95%): {res['var_95']:.2f}")
            click.echo(f"CVaR (95%): {res['cvar_95']:.2f}")
            click.echo(f"VaR (99%): {res['var_99']:.2f}")
            click.echo(f"CVaR (99%): {res['cvar_99']:.2f}")
        else:
            click.echo(f"Error: {res}")
    except Exception as e:
        click.echo(f"Error: {e}")

@cli.command()
@click.option('--ticker', required=True)
@click.option('--type', 'scenario_type', type=click.Choice(['price_shock', 'vol_shock']), required=True)
@click.option('--shock', type=float, required=True, help="Magnitude (e.g. 0.20)")
def stress_test(ticker, scenario_type, shock):
    """Run stress test scenarios via API."""
    initial = 100.0
    payload = {
        "ticker": ticker,
        "initial_price": initial,
        "scenario_type": scenario_type,
        "shock_value": shock
    }
    try:
        click.echo(f"Running {scenario_type} ({shock})...")
        response = requests.post(f"{API_URL}/stress-test", json=payload, headers=get_auth_headers())
        res = response.json()
        
        if response.status_code == 200:
            click.echo("Stress Test Complete:")
            if scenario_type == "price_shock":
                click.echo(f"Estimated Loss: -{res['estimated_loss']:.2f}")
                click.echo(f"New Value: {res['new_price']:.2f}")
            else:
                 click.echo(f"New VaR (99%): {res['new_var_99']:.2f}")
                 click.echo(f"Mean Price: {res['mean_price']:.2f}")
        else:
             click.echo(f"Error: {response.text}")
    except Exception as e:
        click.echo(f"Error: {e}")

if __name__ == '__main__':
    cli()
