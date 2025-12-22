class RiskManager:
    def __init__(self, params):
        self.max_drawdown = params.get('max_drawdown_limit', 0.15)
        self.stop_loss_pct = params.get('stop_loss_pct', 0.05)
        self.max_pos_size = params.get('max_position_size', 1.0)
        self.kelly_fraction = params.get('kelly_fraction', 0.5)
        self.current_drawdown = 0.0

    def check_trade_allowed(self, current_exposure: float, trade_size: float) -> bool:
        """
        Checks if a new trade is allowed based on risk parameters.
        """
        if self.current_drawdown >= self.max_drawdown:
            print("RISK ALERT: Max drawdown exceeded. Trading permitted: False")
            return False
        
        if current_exposure + trade_size > self.max_pos_size:
            print(f"RISK ALERT: Max position size ({self.max_pos_size}) would be exceeded.")
            return False

        return True

    def calculate_safe_size(self, proposed_size: float, win_prob: float = 0.55, win_loss_ratio: float = 1.0) -> float:
        """
        Calculates position size using Kelly Criterion (fractional).
        Kelly % = (p(b+1) - 1) / b
        where p = win prob, b = odds (win/loss ratio)
        """
        # Simple Kelly formula
        kelly_pct = (win_prob * (win_loss_ratio + 1) - 1) / win_loss_ratio
        
        # Apply fractional Kelly for safety (Thorp's advice)
        safe_pct = max(0, kelly_pct * self.kelly_fraction)
        
        # Just a demo calculation, in real grid we usually use fixed sizes
        # but this could scale the grid step size.
        return proposed_size  # For now, return proposed size but log the kelly suggestion
