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
        
        # --- NEW: Enhanced Risk Engine Parameters (Option A) ---
        # 1. Martingale Detection
        self.martingale_detection_enabled = config.get('martingale_detection_enabled', True)
        self.lot_history = []  # Track last N position sizes
        self.martingale_detected = False
        
        # 2. Floating Loss Tracking
        self.floating_loss_limit_pct = config.get('floating_loss_limit_pct', 0.03)  # 3%
        self.floating_loss = 0.0
        self.floating_loss_cb_active = False
        
        # 3. Losing Streak Circuit Breaker (Equity Curve CB)
        self.losing_streak_threshold = config.get('losing_streak_threshold', 3)
        self.losing_streak_reduction = 0.5  # Reduce risk by 50%
        self.trade_results = []  # List of True (win) / False (loss)
        self.losing_streak_count = 0
        
        # 4. Volatility Scaling
        self.volatility_scaling_enabled = config.get('volatility_scaling_enabled', True)
        self.normal_atr = config.get('normal_atr', None)  # Baseline ATR for comparison
        
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
        
        print(f"[RiskManager] Initialized with Enhanced Safety Features.")
        print(f"   - Max Drawdown Limit: {self.max_drawdown_limit*100}%")
        print(f"   - ATR Stop Multiplier: {self.stop_loss_atr_multiplier}x")
        print(f"   - Kelly Fraction: {self.kelly_fraction}x")
        print(f"   - Martingale Detection: {self.martingale_detection_enabled}")
        print(f"   - Floating Loss Limit: {self.floating_loss_limit_pct*100}%")
        print(f"   - Losing Streak Threshold: {self.losing_streak_threshold}")

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

        # IMPORTANT: Once halted, stay halted until daily reset (sticky flag)
        if self.daily_trading_halted:
            return False, "DAILY_LIMIT_HALTED"

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
        Calculates safe position size using Sniper Logic.
        ENHANCED with Option A features: Volatility Scaling, Losing Streak, Martingale Detection.
        """
        # 0. Check if trading allowed first
        allowed, reason = self.check_daily_status(account_balance)
        if not allowed:
            return 0.0

        # 1. Hard Risk Limit ($6 or dynamic based on FTMO)
        # In FTMO mode, we risk 0.35% of equity (per spec)
        if self.ftmo_mode:
            risk_per_trade_usd = account_balance * 0.0035  # 0.35%
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
        
        # 4. Circuit Breaker Penalty (Existing)
        if self.circuit_breaker_active:
            print(f"[DEFENSE] Circuit Breaker Active: Halving position size.")
            safe_units *= 0.5
        
        # ============================================================
        # NEW: Enhanced Risk Engine Modifiers (Option A)
        # ============================================================
        
        # 5. Volatility Scaling - adjust size based on current vs normal ATR
        volatility_mult = self.get_volatility_multiplier(current_volatility_atr)
        safe_units *= volatility_mult
        
        # 6. Losing Streak Reduction - reduce risk after consecutive losses
        streak_mult = self.get_losing_streak_multiplier()
        if streak_mult < 1.0:
            print(f"[DEFENSE] Losing streak active: Reducing size to {streak_mult*100:.0f}%")
        safe_units *= streak_mult
        
        # 7. Floating Loss Check - halt if floating loss too high
        if self.floating_loss_cb_active:
            print(f"[DEFENSE] Floating loss CB active: Blocking new trades.")
            return 0.0
        
        # 8. Martingale Detection - detect dangerous pattern
        if self.martingale_detection_enabled:
            is_martingale = self.detect_martingale(safe_units)
            if is_martingale:
                print(f"[RISK HALT] Martingale detected. Resetting to minimum safe lot.")
                self.lot_history = []  # Reset history
                safe_units = 0.01  # Minimum safe lot
            
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

    # ============================================================
    # NEW: Enhanced Risk Engine Methods (Option A)
    # ============================================================
    
    def detect_martingale(self, new_lot_size: float) -> bool:
        """
        Detects if position sizes are increasing after losses (Martingale pattern).
        WARNING: This pattern leads to account blowups!
        
        Returns:
            True if dangerous Martingale pattern detected (3+ consecutive increasing lots)
        """
        if not self.martingale_detection_enabled:
            return False
            
        self.lot_history.append(new_lot_size)
        if len(self.lot_history) > 5:
            self.lot_history.pop(0)  # Keep last 5 trades only
        
        # Check for 3+ consecutive increases
        if len(self.lot_history) >= 3:
            last_3 = self.lot_history[-3:]
            # All 3 are different and each is larger than previous
            if last_3[0] < last_3[1] < last_3[2]:
                if not self.martingale_detected:
                    print(f"[RISK ALERT] ⚠️ MARTINGALE PATTERN DETECTED: {[round(x, 4) for x in last_3]}")
                    print(f"[RISK ALERT] Resetting lot history to prevent blowup.")
                self.martingale_detected = True
                return True
        
        self.martingale_detected = False
        return False
    
    def update_floating_loss(self, unrealized_pnl: float, account_balance: float) -> bool:
        """
        Updates floating (unrealized) loss and triggers CB if limit exceeded.
        
        Args:
            unrealized_pnl: Current unrealized P&L (negative = loss)
            account_balance: Current account balance
            
        Returns:
            True if floating loss circuit breaker should activate
        """
        self.floating_loss = unrealized_pnl
        
        if account_balance > 0:
            floating_pct = abs(unrealized_pnl) / account_balance
            
            if unrealized_pnl < 0 and floating_pct > self.floating_loss_limit_pct:
                if not self.floating_loss_cb_active:
                    print(f"[RISK ALERT] ⚠️ Floating Loss {floating_pct*100:.2f}% exceeds limit ({self.floating_loss_limit_pct*100}%)")
                    self.floating_loss_cb_active = True
                return True
        
        # Reset CB if in profit
        if unrealized_pnl >= 0:
            if self.floating_loss_cb_active:
                print(f"[RISK RESTORE] Floating loss recovered. CB deactivated.")
            self.floating_loss_cb_active = False
            
        return False
    
    def record_trade_result(self, is_win: bool):
        """
        Records trade result and updates losing streak counter.
        Call this after each trade closes.
        
        Args:
            is_win: True if trade was profitable, False if loss
        """
        self.trade_results.append(is_win)
        if len(self.trade_results) > 10:
            self.trade_results.pop(0)  # Keep last 10 trades
        
        if is_win:
            if self.losing_streak_count >= self.losing_streak_threshold:
                print(f"[RISK RESTORE] Win after {self.losing_streak_count} losses. Resetting streak.")
            self.losing_streak_count = 0
        else:
            self.losing_streak_count += 1
            if self.losing_streak_count >= self.losing_streak_threshold:
                print(f"[RISK ALERT] ⚠️ Losing streak: {self.losing_streak_count}. Reducing risk by {(1-self.losing_streak_reduction)*100}%.")
    
    def get_losing_streak_multiplier(self) -> float:
        """
        Returns position size multiplier based on losing streak.
        
        Returns:
            1.0 if normal, 0.5 if losing streak threshold exceeded
        """
        if self.losing_streak_count >= self.losing_streak_threshold:
            return self.losing_streak_reduction  # 0.5 = 50% reduction
        return 1.0
    
    def get_volatility_multiplier(self, current_atr: float) -> float:
        """
        Returns position size multiplier based on current volatility vs normal.
        High volatility = smaller position, Low volatility = larger position.
        
        Args:
            current_atr: Current ATR value
            
        Returns:
            Multiplier (0.5 to 1.25) based on volatility ratio
        """
        if not self.volatility_scaling_enabled or self.normal_atr is None or self.normal_atr == 0:
            return 1.0
            
        volatility_ratio = current_atr / self.normal_atr
        
        if volatility_ratio > 1.5:  # High volatility (50%+ above normal)
            print(f"[DEFENSE] High volatility ({volatility_ratio:.2f}x normal): Halving size")
            return 0.5
        elif volatility_ratio > 1.2:  # Elevated volatility
            return 0.75
        elif volatility_ratio < 0.5:  # Very low volatility
            print(f"[BOOST] Low volatility ({volatility_ratio:.2f}x normal): Increasing size by 25%")
            return 1.25
        elif volatility_ratio < 0.8:  # Below normal volatility
            return 1.1
        
        return 1.0  # Normal volatility
    
    def set_normal_atr(self, atr_value: float):
        """
        Sets the baseline ATR for volatility comparison.
        Call this during initialization or after calculating historical average.
        """
        self.normal_atr = atr_value
        print(f"[RiskManager] Normal ATR baseline set to: {atr_value:.5f}")
    
    def get_risk_status(self) -> dict:
        """
        Returns current risk status for monitoring/logging.
        """
        return {
            'current_drawdown_pct': round(self.current_drawdown * 100, 2),
            'circuit_breaker_active': self.circuit_breaker_active,
            'daily_trading_halted': self.daily_trading_halted,
            'martingale_detected': self.martingale_detected,
            'floating_loss_cb_active': self.floating_loss_cb_active,
            'losing_streak_count': self.losing_streak_count,
            'lot_history': [round(x, 4) for x in self.lot_history[-5:]],
            'recent_trades': self.trade_results[-5:]
        }

