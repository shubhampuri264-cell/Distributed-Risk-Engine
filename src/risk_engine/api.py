from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
from jose import JWTError, jwt
from risk_engine.core import data_loader, simulator, risk_metrics
import numpy as np
import hashlib
import json
import fakeredis
import os

# Security Config
SECRET_KEY = os.getenv("RISK_ENGINE_SECRET", "super-secret-admin-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASS", "admin123")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

app = FastAPI(title="Distributed Risk Engine API")

# --- CORS Config ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# --- Security Functions ---
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    return username

@app.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    if form_data.username == ADMIN_USER and form_data.password == ADMIN_PASS:
        access_token = create_access_token(data={"sub": form_data.username})
        return {"access_token": access_token, "token_type": "bearer"}
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password",
        headers={"WWW-Authenticate": "Bearer"},
    )

# --- Classes ---
class IngestRequest(BaseModel):
    tickers: List[str]
    start_date: str
    end_date: str

class StressRequest(BaseModel):
    ticker: str
    initial_price: float = 100.0
    scenario_type: str  # "price_shock" or "vol_shock"
    shock_value: float  # e.g., 0.20 for 20% drop, or 0.50 for 50% vol

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
    paths: Optional[List[List[float]]] = None

@app.post("/ingest")
def ingest_data(req: IngestRequest, current_user: str = Depends(get_current_user)):
    try:
        df = data_loader.fetch_market_data(req.tickers, req.start_date, req.end_date)
        if not df.empty:
            data_loader.save_to_duckdb(df)
            # Create preview (first 10 rows, convert dates to string for JSON)
            preview = df.head(10).copy()
            if 'Date' in preview.columns:
                preview['Date'] = preview['Date'].astype(str)
            
            return {
                "status": "success", 
                "rows": len(df), 
                "preview": preview.to_dict(orient='records')
            }
        else:
            return {"status": "warning", "message": "No data found", "preview": []}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

import hashlib
import json
import fakeredis

# Initialize fake redis (in-memory)
cache = fakeredis.FakeStrictRedis()

def get_cache_key(req: SimulateRequest) -> str:
    """Generates a specialized hash key for the simulation request."""
    # Create a string representation of the parameters
    params = f"{req.ticker}-{req.initial_price}-{req.days}-{req.paths}-{req.volatility}-{req.drift}"
    return hashlib.md5(params.encode()).hexdigest()

@app.post("/simulate", response_model=RiskResponse)
def run_simulation(req: SimulateRequest, current_user: str = Depends(get_current_user)):
    try:
        # Check Cache
        cache_key = get_cache_key(req)
        # cached_result = cache.get(cache_key) # Disable cache for dev
        cached_result = None
        
        if cached_result:
            print("Cache Hit!")
            return RiskResponse(**json.loads(cached_result))
            
        # Run Simulation if miss
        print("Cache Miss - Running Simulation...")
        sim = simulator.MonteCarloSimulator(n_paths=req.paths, time_horizon=req.days)
        results = sim.simulate(S0=req.initial_price, mu=req.drift, sigma=req.volatility)
        
        # Results is now (n_paths, days+1) matrix
        # For metrics, we need the final prices (last column)
        final_prices = results[:, -1]
        
        var_95 = risk_metrics.calculate_var(final_prices, req.initial_price, 0.95)
        cvar_95 = risk_metrics.calculate_cvar(final_prices, req.initial_price, 0.95)
        var_99 = risk_metrics.calculate_var(final_prices, req.initial_price, 0.99)
        cvar_99 = risk_metrics.calculate_cvar(final_prices, req.initial_price, 0.99)
        
        # Prepare visualization data: take first 50 paths
        vis_paths = []
        try:
             # Take top 50 paths (rows) and convert to list of lists
             # results is numpy array [n_paths, days]
             vis_paths = results[:50].tolist()
        except Exception as e:
            print(f"Vis Data Error: {e}")

        response = RiskResponse(
            ticker=req.ticker,
            var_95=var_95,
            cvar_95=cvar_95,
            var_99=var_99,
            cvar_99=cvar_99,
            mean_price=float(final_prices.mean()),
            paths=vis_paths
        )
        
        # Save to Cache (1 hour expiry)
        cache.setex(cache_key, 3600, response.json())
        
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/data/{ticker}")
def get_market_data(ticker: str):
    """
    Fetch stored market data for a specific ticker from DuckDB.
    """
    try:
        df = data_loader.load_data_from_db(ticker)
        if df.empty:
            return {"status": "warning", "message": f"No data found for {ticker}", "data": []}
        
        # Convert to list of dicts for JSON response
        # df.to_dict(orient='records') handles Date objects gracefully usually, but let's be safe
        records = df.to_dict(orient='records')
        return {"status": "success", "data": records}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/stress-test")
def run_stress_test(req: StressRequest, current_user: str = Depends(get_current_user)):
    try:
        if req.scenario_type == "price_shock":
            loss = risk_metrics.calculate_stress_impact(req.initial_price, req.shock_value)
            return {
                "ticker": req.ticker,
                "scenario": "Price Shock",
                "shock_pct": req.shock_value,
                "estimated_loss": loss,
                "new_price": req.initial_price - loss
            }
            
        elif req.scenario_type == "vol_shock":
            # 1. Run Baseline Simulation (Normal Vol = 0.20 default or we should ask user? Let's assume 0.20 base)
            # Ideally we'd pass base_vol in request, but for now let's use 0.20 as "Normal"
            base_vol = 0.20
            sim_base = simulator.MonteCarloSimulator(n_paths=5000, time_horizon=252)
            res_base = sim_base.simulate(S0=req.initial_price, mu=0.05, sigma=base_vol)
            var_base = risk_metrics.calculate_var(res_base[:, -1], req.initial_price, 0.99)
            
            # 2. Run Stressed Simulation
            sim_stress = simulator.MonteCarloSimulator(n_paths=5000, time_horizon=252) 
            res_stress = sim_stress.simulate(S0=req.initial_price, mu=0.05, sigma=req.shock_value)
            final_prices = res_stress[:, -1]
            
            var_99 = risk_metrics.calculate_var(final_prices, req.initial_price, 0.99)
            
            return {
                "ticker": req.ticker,
                "scenario": "Volatility Shock",
                "new_volatility": req.shock_value,
                "normal_var_99": var_base,
                "new_var_99": var_99,
                "mean_price": float(final_prices.mean())
            }
        else:
            raise HTTPException(status_code=400, detail="Unknown scenario type. Use 'price_shock' or 'vol_shock'.")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health():
    return {"status": "ok"}
