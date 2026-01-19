# Distributed Risk Engine

A high-performance, distributed market risk engine built with Python, Ray, DuckDB, and FastAPI.

## Features
-   **Distributed Monte Carlo Simulations**: Parallelized via Ray.
-   **Multi-Source Data**: Ingests Stocks (Yahoo Finance) and Crypto (Binance).
-   **Persistent Storage**: Efficiently stores market data in DuckDB.
-   **Enterprise Security**: JWT Authentication and Login Protection.
-   **High Performance**: Redis Caching for instant results.
-   **Dockerized**: One-click deployment.

## Quick Start (Docker)
The easiest way to run the project is with Docker.

1.  **Start the Stack**:
    ```bash
    docker-compose up --build
    ```
2.  **Access the Dashboard**:
    -   Go to [http://localhost:8501](http://localhost:8501)
    -   Login with:
        -   **Username**: `admin`
        -   **Password**: `admin123`

## CLI Usage
If you prefer the command line, you can verify the system manually.

**Note:** You must activate your virtual environment if running locally, or execute inside the docker container.

```bash
# 1. Login
python -m risk_engine.cli login
# Enter 'admin' and 'admin123'

# 2. Ingest Data (Required first step!)
python -m risk_engine.cli ingest --ticker AAPL --start 2023-01-01 --end 2023-12-31

# 3. Ingest Crypto
python -m risk_engine.cli ingest --ticker BTC/USDT --start 2023-01-01 --end 2023-12-31

# 4. Run Simulation
python -m risk_engine.cli simulate --ticker AAPL --paths 10000

# 5. Stress Test
python -m risk_engine.cli stress-test --ticker AAPL --type price_shock --shock 0.30
```

## Architecture
-   **API**: FastAPI (Port 8000)
-   **Dashboard**: Streamlit (Port 8501)
-   **Database**: DuckDB (Local file) + Redis (Cache)
-   **Compute**: Ray Cluster (Local)