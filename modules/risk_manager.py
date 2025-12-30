import numpy as np
import time

class RiskManager:
    """
    The Fortress (Safety Core)
    Implements risk management protocols from World-Class Quants:
    - Edward Thorp (Kelly Criterion)
    - Ray Dalio (Volatility Sizing)
    - The Turtles (ATR Stops)
    - Nassim Taleb (Anti-Fragile Circuit Breaker)
    - FTMO / Prop Firm Compliance (Daily Limits)
    """
    
    def __init__(self, config):
        # --- Safety Limits ---
        self.max_drawdown_limit = config.get('max_drawdown_limit', 0.15)
        self.stop_loss_atr_multiplier = config.get('stop_loss_atr_multiplier', 3.0)
        self.kelly_fraction = config.get('kelly_fraction', 0.5)
        
        # --- FTMO / Prop Firm Parameters ---
        self.ftmo_mode = config.get('ftmo_mode', False)
        self.daily_loss_limit_pct = config.get('daily_loss_limit_pct', 0.02)
        self.daily_profit_target_pct = config.get('daily_profit_target_pct', 0.01)
        self.max_drawdown_ftmo_pct = config.get('max_drawdown_ftmo_pct', 0.05)
        self.max_holding_hours = config.get('max_holding_hours', 24)
        
        # Override Max Drawdown if FTMO mode is active
        if self.ftmo_mode:
            print(f"[RiskManager] FTMO MODE ACTIVE. Tightening Drawdown to {self.max_drawdown_ftmo_pct*100}%")
            self.max_drawdown_limit = self.max_drawdown_ftmo_pct
        
        # --- State Tracking ---
        self.peak_balance = 0.0
        self.current_drawdown = 0.0
        self.circuit_breaker_active = False
        
        # Daily Limit Tracking
        self.daily_start_balance = 0.0
        self.is_new_day = True
        self.daily_trading_halted = False
        
        print(f"[RiskManager] Initialized.")
        print(f"   - Max Drawdown Limit: {self.max_drawdown_limit*100}%")
        print(f"   - ATR Stop Multiplier: {self.stop_loss_atr_multiplier}x")
        print(f"   - Kelly Fraction: {self.kelly_fraction}x")

    def reset_daily_stats(self, current_balance):
        """Call this at 00:00 UTC (or start of backtest day)"""
        self.daily_start_balance = current_balance
        self.daily_trading_halted = False
        print(f"[RiskManager] DAILY RESET. Start Balance: ${self.daily_start_balance:.2f}")

    def check_daily_status(self, current_balance):
        """
        Checks if Daily Loss Limit or Daily Profit Target is hit.
        Returns:
            allowed (bool): True if trading is allowed
            reason (str): Reason for halt (if any)
        """
        if not self.ftmo_mode:
            return True, "Normal"

        if self.daily_start_balance == 0:
            self.daily_start_balance = current_balance # First run init

        daily_pnl = current_balance - self.daily_start_balance
        daily_pnl_pct = daily_pnl / self.daily_start_balance

        # 1. Check Daily Loss Limit
        if daily_pnl_pct <= -self.daily_loss_limit_pct:
            if not self.daily_trading_halted:
                print(f"[RISK HALT] Daily Loss Limit Hit ({daily_pnl_pct*100:.2f}%). HALTING TRADES.")
                self.daily_trading_halted = True
            return False, "DAILY_LOSS_LIMIT"

        # 2. Check Daily Profit Target (Optional: Lock Profit)
        if daily_pnl_pct >= self.daily_profit_target_pct:
            if not self.daily_trading_halted:
                print(f"[RISK HALT] Daily Profit Target Hit ({daily_pnl_pct*100:.2f}%). HALTING TO PRESERVE GAINS.")
                self.daily_trading_halted = True
            return False, "DAILY_PROFIT_TARGET"

        return True, "OK"

    def check_timeout_rule(self, position_open_time_epoch, current_time_epoch):
        """
        Returns True if position should be closed due to timeout.
        """
        if not self.ftmo_mode:
            return False
            
        duration_hours = (current_time_epoch - position_open_time_epoch) / 3600
        if duration_hours >= self.max_holding_hours:
            return True
        return False

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
        Calculates safe position size using Sniper Logic ($300 Account).
        Hard Cap Risk: $6 per trade.
        """
        # 0. Check if trading allowed first
        allowed, reason = self.check_daily_status(account_balance)
        if not allowed:
            return 0.0

        # 1. Hard Risk Limit ($6 or dynamic based on FTMO)
        # In FTMO mode, we risk 0.35% of equity (per spec)
        if self.ftmo_mode:
            risk_per_trade_usd = account_balance * 0.0035 # 0.35%
        else:
            risk_per_trade_usd = 6.0 
        
        # 2. Stop Loss Distance (Volatility Based)
        # Use 2.5x ATR for tighter stops on M15
        stop_loss_distance = current_volatility_atr * 2.5
        
        if stop_loss_distance == 0:
            return 0.0
        
        # 3. Position Size Calculation
        # Size = Risk / Stop Distance
        safe_units = risk_per_trade_usd / stop_loss_distance
        
        # 4. Circuit Breaker Penalty
        if self.circuit_breaker_active:
            print(f"[DEFENSE] Circuit Breaker Active: Halving position size.")
            safe_units *= 0.5
            
        return safe_units

    def check_trade_allowed(self, signal_type: str, price: float) -> bool:
        """
        Final Gatekeeper before executing any trade.
        """
        # 1. Hard Kill Switch (Max Drawdown)
        if self.current_drawdown >= self.max_drawdown_limit:
            print(f"[KILL SWITCH] Max Drawdown ({self.current_drawdown*100:.2f}%) Exceeded. Trade REJECTED.")
            return False
            
        # 2. Daily Limit Switch
        if self.daily_trading_halted:
             print(f"[KILL SWITCH] Daily Limit Halted. Trade REJECTED.")
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
