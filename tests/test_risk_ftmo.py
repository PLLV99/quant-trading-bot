import unittest
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.risk.risk_manager import RiskManager

class TestFTMORiskManager(unittest.TestCase):
    def setUp(self):
        self.config = {
            'ftmo_mode': True,
            'daily_loss_limit_pct': 0.05, # 5% for easy math
            'daily_profit_target_pct': 0.10, # 10%
            'max_drawdown_ftmo_pct': 0.10
        }
        self.risk = RiskManager(self.config)
        self.initial_balance = 1000.0
        self.risk.reset_daily_stats(self.initial_balance)

    def test_daily_loss_limit(self):
        print("\n--- Testing Daily Loss Limit ---")
        # 1. Normal Trade (Loss but not limit)
        current_bal = 980.0 # -2%
        allowed, reason = self.risk.check_daily_status(current_bal)
        self.assertTrue(allowed)
        print(f"Balance {current_bal}: Allowed={allowed}")

        # 2. Hit Limit
        current_bal = 940.0 # -6% (Limit is 5%)
        allowed, reason = self.risk.check_daily_status(current_bal)
        self.assertFalse(allowed)
        self.assertEqual(reason, "DAILY_LOSS_LIMIT")
        print(f"Balance {current_bal}: Allowed={allowed} Reason={reason}")
        
        # 3. Recover (Should still be halted until reset)
        current_bal = 980.0
        allowed, reason = self.risk.check_daily_status(current_bal)
        self.assertFalse(allowed) # Still halted
        print(f"Balance {current_bal} (Recovered): Allowed={allowed} (Stays Halted)")

    def test_daily_profit_target(self):
        print("\n--- Testing Daily Profit Target ---")
        # 1. Profit
        current_bal = 1050.0 # +5%
        allowed, reason = self.risk.check_daily_status(current_bal)
        self.assertTrue(allowed)
        print(f"Balance {current_bal}: Allowed={allowed}")

        # 2. Hit Target
        current_bal = 1110.0 # +11% (Target 10%)
        allowed, reason = self.risk.check_daily_status(current_bal)
        self.assertFalse(allowed)
        self.assertEqual(reason, "DAILY_PROFIT_TARGET")
        print(f"Balance {current_bal}: Allowed={allowed} Reason={reason}")

    def test_daily_reset(self):
        print("\n--- Testing Daily Reset ---")
        # Fail first
        self.risk.check_daily_status(900.0) # -10% -> Halt
        self.assertFalse(self.risk.check_daily_status(900.0)[0])
        
        # New Day
        self.risk.reset_daily_stats(900.0)
        # Should be allowed now (relative to new 900 base)
        allowed, reason = self.risk.check_daily_status(900.0)
        self.assertTrue(allowed)
        print("Reset successful. Trading allowed.")

if __name__ == '__main__':
    unittest.main()
