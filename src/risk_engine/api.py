from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from risk_engine.core import data_loader, simulator, risk_metrics
import numpy as np

app = FastAPI(title="Distributed Risk Engine API")

class IngestRequest(BaseModel):
    tickers: List[str]
    start_date: str
    end_date: str

class SimulateRequest(BaseModel):
    ticker: str
    initial_price: float = 100.0
    days: int = 252
    paths: int = 10000
    volatility: float = 0.20
    drift: float = 0.05

class RiskResponse(BaseModel):
    ticker: str
    var_95: float
    cvar_95: float
    var_99: float
    cvar_99: float
    mean_price: float

@app.post("/ingest")
def ingest_data(req: IngestRequest):
    try:
        df = data_loader.fetch_market_data(req.tickers, req.start_date, req.end_date)
        if not df.empty:
            data_loader.save_to_duckdb(df)
            return {"status": "success", "rows": len(df)}
        else:
            return {"status": "warning", "message": "No data found"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/simulate", response_model=RiskResponse)
def run_simulation(req: SimulateRequest):
    try:
        sim = simulator.MonteCarloSimulator(n_paths=req.paths, time_horizon=req.days)
        results = sim.simulate(S0=req.initial_price, mu=req.drift, sigma=req.volatility)
        
        var_95 = risk_metrics.calculate_var(results, req.initial_price, 0.95)
        cvar_95 = risk_metrics.calculate_cvar(results, req.initial_price, 0.95)
        var_99 = risk_metrics.calculate_var(results, req.initial_price, 0.99)
        cvar_99 = risk_metrics.calculate_cvar(results, req.initial_price, 0.99)
        
        return RiskResponse(
            ticker=req.ticker,
            var_95=var_95,
            cvar_95=cvar_95,
            var_99=var_99,
            cvar_99=cvar_99,
            mean_price=float(results.mean())
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health():
    return {"status": "ok"}
