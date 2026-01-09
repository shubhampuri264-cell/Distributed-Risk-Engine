# Distributed Risk Engine

A high-performance risk engine capable of:
- Pulling market data (Yahoo Finance, Crypto)
- Running Monte Carlo simulations using Ray
- Computing VaR, CVaR, and Stress Tests
- Exposing results via CLI, API, and Dashboard

## Structure
- `data/`: Storage for DuckDB and logs
- `src/`: Source code including Core Engine, CLI, and API
- `tests/`: Unit and integration tests

## getting Started

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run CLI:
   ```bash
   python -m risk_engine.cli --help
   ```
