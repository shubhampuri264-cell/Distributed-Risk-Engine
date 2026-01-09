import numpy as np
import ray
import pandas as pd
from typing import List

# Initialize Ray if not already initialized
if not ray.is_initialized():
    ray.init(ignore_reinit_error=True)

@ray.remote
def simulate_chunk(S0: float, mu: float, sigma: float, T: int, dt: float, n_paths: int) -> np.ndarray:
    """
    Simulates a chunk of paths using Geometric Brownian Motion.
    Returns the final prices for this chunk.
    """
    # Number of steps
    N = int(T / dt)
    
    # Generate random shocks
    # Shape: (n_paths, N)
    shocks = np.random.normal(0, np.sqrt(dt), size=(n_paths, N))
    
    # Calculate paths
    # We only need the final price for VaR usually, but let's return the whole path if needed?
    # For distributed scale, returning whole paths is heavy. Let's return final prices for now.
    # If we need the path for plotting, we can return a subset.
    
    # Vectorized calculation of final price:
    # S_T = S_0 * exp( (mu - 0.5*sigma^2)*T + sigma * sum(dW) )
    
    drift = (mu - 0.5 * sigma**2) * T
    diffusion = sigma * np.sum(shocks, axis=1)
    
    ST = S0 * np.exp(drift + diffusion)
    return ST

class MonteCarloSimulator:
    def __init__(self, n_paths: int = 10000, time_horizon: int = 252):
        self.n_paths = n_paths
        self.time_horizon = time_horizon # Days
        self.dt = 1/252 # Daily steps

    def simulate(self, S0: float, mu: float, sigma: float) -> np.ndarray:
        """
        Runs the simulation in parallel using Ray.
        """
        # Determine number of cores/chunks
        n_cores = int(ray.available_resources().get("CPU", 1))
        paths_per_chunk = self.n_paths // n_cores
        remainder = self.n_paths % n_cores
        
        futures = []
        for i in range(n_cores):
            count = paths_per_chunk + (1 if i < remainder else 0)
            if count > 0:
                future = simulate_chunk.remote(S0, mu, sigma, self.time_horizon/252, self.dt, count)
                futures.append(future)
        
        results = ray.get(futures)
        return np.concatenate(results)

if __name__ == "__main__":
    sim = MonteCarloSimulator(n_paths=100000)
    results = sim.simulate(S0=100, mu=0.05, sigma=0.2)
    print(f"Simulated {len(results)} paths.")
    print(f"Mean final price: {results.mean():.2f}")
