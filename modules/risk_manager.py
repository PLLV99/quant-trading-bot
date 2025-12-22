import numpy as np

class RiskManager:
    """
    The Fortress (Safety Core)
    Implements risk management protocols from World-Class Quants:
    - Edward Thorp (Kelly Criterion)
    - Ray Dalio (Volatility Sizing)
    - The Turtles (ATR Stops)
    - Nassim Taleb (Anti-Fragile Circuit Breaker)
    """
    
    def __init__(self, config):
        # --- Safety Limits ---
        self.max_drawdown_limit = config.get('max_drawdown_limit', 0.15)  # 15% Hard Stop
        self.stop_loss_atr_multiplier = config.get('stop_loss_atr_multiplier', 3.0)  # Turtle Rule
        self.kelly_fraction = config.get('kelly_fraction', 0.5)  # Thorp's "Half Kelly"
        
        # --- State Tracking ---
        self.peak_balance = 0.0
        self.current_drawdown = 0.0
        self.circuit_breaker_active = False  # If True, cut leverage by 50%
        
        print(f"[RiskManager] Initialized with Anti-Fragile Protocols.")
        print(f"   - Max Drawdown Limit: {self.max_drawdown_limit*100}%")
        print(f"   - ATR Stop Multiplier: {self.stop_loss_atr_multiplier}x")
        print(f"   - Kelly Fraction: {self.kelly_fraction}x")

    def update_account_status(self, current_balance: float):
        """
        Updates drawdown status and triggers 'Smart Circuit Breaker' if needed.
        (Taleb's Logic: Bend, don't break)
        """
        if current_balance > self.peak_balance:
            self.peak_balance = current_balance
            
        if self.peak_balance > 0:
            drawdown = (self.peak_balance - current_balance) / self.peak_balance
            self.current_drawdown = drawdown
            
            # Anti-Fragile Circuit Breaker logic
            if self.current_drawdown > (self.max_drawdown_limit * 0.8): 
                # If approaching limit (e.g. 12%), activate defensive mode
                if not self.circuit_breaker_active:
                    print(f"[RISK ALERT] Drawdown {drawdown*100:.2f}% detected. Activating CIRCUIT BREAKER.")
                    self.circuit_breaker_active = True
            elif self.current_drawdown < (self.max_drawdown_limit * 0.5):
                # Recovery confirmed, deactivate defensive mode
                if self.circuit_breaker_active:
                    print(f"[RISK RESTORE] Drawdown recovered to {drawdown*100:.2f}%. Deactivating Circuit Breaker.")
                    self.circuit_breaker_active = False
        
        return self.current_drawdown

    def calculate_position_size(self, account_balance: float, current_volatility_atr: float, price: float) -> float:
        """
        Calculates safe position size using Dalio's Volatility Sizing & Thorp's Kelly.
        """
        # 1. Base Size (e.g. 5% of equity per grid level) - Placeholder, usually dynamic
        base_risk_per_trade = 0.02 # Risking 2% per trade
        
        # 2. Turtle/Dalio Adjustment: Size is INVERSE to Volatility
        # If ATR is high (volatile), we must trade smaller to keep dollar-risk constant.
        # Implied Stop Distance = 3 * ATR
        risk_per_share = current_volatility_atr * self.stop_loss_atr_multiplier
        
        if risk_per_share == 0:
            return 0.0
        
        # Dollar Risk Budget = Account * 2%
        dollar_risk_budget = account_balance * base_risk_per_trade
        
        # Position Size (Units) = Dollar Risk / Risk Per Share
        safe_units = dollar_risk_budget / risk_per_share
        
        # 3. Circuit Breaker Penalty
        if self.circuit_breaker_active:
            print(f"[DEFENSE] Circuit Breaker Active: Halving position size.")
            safe_units *= 0.5
            
        return safe_units

    def check_trade_allowed(self, signal_type: str, price: float) -> bool:
        """
        Final Gatekeeper before executing any trade.
        """
        # 1. Hard Kill Switch
        if self.current_drawdown >= self.max_drawdown_limit:
            print(f"[KILL SWITCH] Max Drawdown ({self.current_drawdown*100:.2f}%) Exceeded. Trade REJECTED.")
            return False
            
        return True

    def get_adaptive_stop_loss(self, entry_price: float, atr: float, side: str) -> float:
        """
        Returns the Turtle 3x ATR Stop Price.
        """
        distance = atr * self.stop_loss_atr_multiplier
        
        if side == 'buy':
            stop_price = entry_price - distance
        else:
            stop_price = entry_price + distance
            
        return stop_price
