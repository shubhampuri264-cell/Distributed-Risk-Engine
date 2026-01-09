import numpy as np

def calculate_var(final_prices: np.ndarray, initial_price: float, confidence_level: float = 0.95) -> float:
    """
    Calculates Value at Risk (VaR).
    VaR is the maximum loss not exceeded with a given confidence level.
    """
    # Calculate PnL
    pnl = final_prices - initial_price
    
    # Sort PnL
    # We want the lower tail.
    # If confidence is 0.95, we look at the 5th percentile worst outcome.
    percentile = (1 - confidence_level) * 100
    var = np.percentile(pnl, percentile)
    
    # VaR is typically expressed as a positive number (loss amount)
    # But np.percentile returns the negative PnL.
    # So if var is -100, it means we lose 100.
    # Let's return the absolute loss if it's negative, or 0 if we gained money at that percentile (unlikely for high conf)
    
    return -var if var < 0 else 0.0

def calculate_cvar(final_prices: np.ndarray, initial_price: float, confidence_level: float = 0.95) -> float:
    """
    Calculates Conditional Value at Risk (CVaR) / Expected Shortfall.
    CVaR is the average loss of the scenarios that exceed VaR.
    """
    pnl = final_prices - initial_price
    percentile = (1 - confidence_level) * 100
    var_threshold = np.percentile(pnl, percentile)
    
    # Filter scenarios worse than VaR
    tail_losses = pnl[pnl <= var_threshold]
    
    if len(tail_losses) == 0:
        return 0.0
        
    cvar = tail_losses.mean()
    
    return -cvar if cvar < 0 else 0.0

if __name__ == "__main__":
    # Test
    initial = 100
    outcomes = np.random.normal(105, 10, 10000) # Mean 105 (gain), std 10
    var_95 = calculate_var(outcomes, initial, 0.95)
    cvar_95 = calculate_cvar(outcomes, initial, 0.95)
    print(f"VaR 95%: {var_95:.2f}")
    print(f"CVaR 95%: {cvar_95:.2f}")
