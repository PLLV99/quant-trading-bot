"""
Test Suite for Enhanced Risk Engine (Option A)
Tests: Martingale Detection, Floating Loss Tracking, Losing Streak CB, Volatility Scaling
"""

import unittest
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.risk.risk_manager import RiskManager


class TestMartingaleDetection(unittest.TestCase):
    """Tests for Martingale pattern detection."""
    
    def setUp(self):
        self.config = {
            'martingale_detection_enabled': True,
            'ftmo_mode': False
        }
        self.risk = RiskManager(self.config)
    
    def test_no_martingale_constant_lots(self):
        """Constant lot sizes should NOT trigger martingale."""
        self.risk.detect_martingale(0.01)
        self.risk.detect_martingale(0.01)
        result = self.risk.detect_martingale(0.01)
        self.assertFalse(result)
        self.assertFalse(self.risk.martingale_detected)
        print("✅ Constant lots: No martingale detected")
    
    def test_martingale_increasing_lots(self):
        """3 consecutive increasing lots should trigger martingale."""
        self.risk.detect_martingale(0.01)
        self.risk.detect_martingale(0.02)
        result = self.risk.detect_martingale(0.03)
        self.assertTrue(result)
        self.assertTrue(self.risk.martingale_detected)
        print("✅ Increasing lots: Martingale detected correctly")
    
    def test_martingale_resets_after_normal(self):
        """Martingale flag should reset after normal behavior."""
        # Trigger martingale
        self.risk.detect_martingale(0.01)
        self.risk.detect_martingale(0.02)
        self.risk.detect_martingale(0.03)
        self.assertTrue(self.risk.martingale_detected)
        
        # Then normal behavior
        self.risk.lot_history = []  # Reset
        self.risk.detect_martingale(0.01)
        self.risk.detect_martingale(0.01)
        result = self.risk.detect_martingale(0.01)
        self.assertFalse(result)
        print("✅ Martingale flag resets after normal behavior")


class TestFloatingLossTracking(unittest.TestCase):
    """Tests for floating (unrealized) loss circuit breaker."""
    
    def setUp(self):
        self.config = {
            'floating_loss_limit_pct': 0.03,  # 3%
            'ftmo_mode': False
        }
        self.risk = RiskManager(self.config)
    
    def test_no_cb_when_in_profit(self):
        """Should not trigger CB when in profit."""
        result = self.risk.update_floating_loss(100.0, 10000.0)  # +$100
        self.assertFalse(result)
        self.assertFalse(self.risk.floating_loss_cb_active)
        print("✅ In profit: No CB triggered")
    
    def test_no_cb_small_loss(self):
        """Should not trigger CB for small losses under limit."""
        result = self.risk.update_floating_loss(-200.0, 10000.0)  # -2%
        self.assertFalse(result)
        self.assertFalse(self.risk.floating_loss_cb_active)
        print("✅ Small loss (2%): No CB triggered")
    
    def test_cb_triggers_on_large_loss(self):
        """Should trigger CB when floating loss exceeds limit."""
        result = self.risk.update_floating_loss(-400.0, 10000.0)  # -4%
        self.assertTrue(result)
        self.assertTrue(self.risk.floating_loss_cb_active)
        print("✅ Large loss (4%): CB triggered correctly")
    
    def test_cb_resets_on_recovery(self):
        """CB should reset when floating PnL recovers to profit."""
        # Trigger CB
        self.risk.update_floating_loss(-400.0, 10000.0)
        self.assertTrue(self.risk.floating_loss_cb_active)
        
        # Recover
        result = self.risk.update_floating_loss(50.0, 10000.0)
        self.assertFalse(result)
        self.assertFalse(self.risk.floating_loss_cb_active)
        print("✅ CB resets on recovery to profit")


class TestLosingStreak(unittest.TestCase):
    """Tests for losing streak circuit breaker."""
    
    def setUp(self):
        self.config = {
            'losing_streak_threshold': 3,
            'ftmo_mode': False
        }
        self.risk = RiskManager(self.config)
    
    def test_no_reduction_on_wins(self):
        """Winning trades should not reduce risk."""
        self.risk.record_trade_result(True)
        self.risk.record_trade_result(True)
        self.risk.record_trade_result(True)
        self.assertEqual(self.risk.get_losing_streak_multiplier(), 1.0)
        print("✅ All wins: No risk reduction")
    
    def test_no_reduction_under_threshold(self):
        """Losses under threshold should not reduce risk."""
        self.risk.record_trade_result(False)
        self.risk.record_trade_result(False)
        self.assertEqual(self.risk.losing_streak_count, 2)
        self.assertEqual(self.risk.get_losing_streak_multiplier(), 1.0)
        print("✅ 2 losses: No risk reduction (threshold is 3)")
    
    def test_reduction_at_threshold(self):
        """3 consecutive losses should reduce risk by 50%."""
        self.risk.record_trade_result(False)
        self.risk.record_trade_result(False)
        self.risk.record_trade_result(False)
        self.assertEqual(self.risk.losing_streak_count, 3)
        self.assertEqual(self.risk.get_losing_streak_multiplier(), 0.5)
        print("✅ 3 losses: Risk reduced to 50%")
    
    def test_streak_resets_on_win(self):
        """Win after losing streak should reset counter."""
        # Build losing streak
        self.risk.record_trade_result(False)
        self.risk.record_trade_result(False)
        self.risk.record_trade_result(False)
        self.assertEqual(self.risk.losing_streak_count, 3)
        
        # Win resets
        self.risk.record_trade_result(True)
        self.assertEqual(self.risk.losing_streak_count, 0)
        self.assertEqual(self.risk.get_losing_streak_multiplier(), 1.0)
        print("✅ Win resets losing streak")


class TestVolatilityScaling(unittest.TestCase):
    """Tests for volatility-based position sizing."""
    
    def setUp(self):
        self.config = {
            'volatility_scaling_enabled': True,
            'normal_atr': 0.001,  # Baseline ATR
            'ftmo_mode': False
        }
        self.risk = RiskManager(self.config)
    
    def test_normal_volatility(self):
        """Normal volatility should return 1.0 multiplier."""
        mult = self.risk.get_volatility_multiplier(0.001)  # Same as normal
        self.assertEqual(mult, 1.0)
        print("✅ Normal volatility: Multiplier = 1.0")
    
    def test_high_volatility(self):
        """High volatility (>1.5x) should halve position size."""
        mult = self.risk.get_volatility_multiplier(0.002)  # 2x normal
        self.assertEqual(mult, 0.5)
        print("✅ High volatility (2x): Multiplier = 0.5")
    
    def test_elevated_volatility(self):
        """Elevated volatility (1.2x-1.5x) should reduce position size."""
        mult = self.risk.get_volatility_multiplier(0.0013)  # 1.3x normal
        self.assertEqual(mult, 0.75)
        print("✅ Elevated volatility (1.3x): Multiplier = 0.75")
    
    def test_low_volatility(self):
        """Very low volatility (<0.5x) should increase position size."""
        mult = self.risk.get_volatility_multiplier(0.0004)  # 0.4x normal
        self.assertEqual(mult, 1.25)
        print("✅ Low volatility (0.4x): Multiplier = 1.25")
    
    def test_disabled_scaling(self):
        """When disabled, should always return 1.0."""
        self.risk.volatility_scaling_enabled = False
        mult = self.risk.get_volatility_multiplier(0.005)  # 5x normal
        self.assertEqual(mult, 1.0)
        print("✅ Scaling disabled: Multiplier = 1.0 regardless of ATR")


class TestRiskStatus(unittest.TestCase):
    """Tests for risk status monitoring."""
    
    def setUp(self):
        self.config = {'ftmo_mode': False}
        self.risk = RiskManager(self.config)
    
    def test_get_risk_status(self):
        """Should return complete risk status dict."""
        # Simulate some state
        self.risk.current_drawdown = 0.05
        self.risk.circuit_breaker_active = True
        self.risk.record_trade_result(False)
        self.risk.record_trade_result(False)
        
        status = self.risk.get_risk_status()
        
        self.assertIn('current_drawdown_pct', status)
        self.assertIn('circuit_breaker_active', status)
        self.assertIn('losing_streak_count', status)
        self.assertIn('lot_history', status)
        self.assertEqual(status['circuit_breaker_active'], True)
        self.assertEqual(status['losing_streak_count'], 2)
        print("✅ Risk status returns complete dict")


if __name__ == '__main__':
    print("\n" + "="*60)
    print("[TEST] ENHANCED RISK ENGINE TESTS (Option A)")
    print("="*60 + "\n")
    unittest.main(verbosity=2)
