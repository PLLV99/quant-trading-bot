# AntiGravity Bot - Change Log & Performance Tracker

> เอกสารนี้ใช้ติดตามการเปลี่ยนแปลง Bot และประเมินผลว่าแก้ปัญหาได้จริงหรือไม่

---

## 📊 Performance Baseline (Before Changes)

| Metric | Value | Date | Note |
|--------|-------|------|------|
| Starting Balance | $500 | Jan 2026 | Demo Account |
| Peak Balance | $902.27 | 2 Feb 2026 | Before Gold SL hit |
| Current Balance | $546.90 | 2 Feb 2026 | After -$355 loss |
| Max Drawdown | 39.99% | 29 Jan 2026 | 2 consecutive Gold SL |
| Profit Factor | 1.20 | 2 Feb 2026 | Too low, target >1.5 |
| Win Rate | 50% | 2 Feb 2026 | OK but not great |

---

## 🔄 Change History

### v2.0.0 - "Pullback Sniper" Strategy Redesign (22 Feb 2026) 🎯

**ปัญหาที่พบ:** 214 trades, Win Rate 31%, PF 0.91, -$207 net loss
**สาเหตุหลัก:** EMA crossover entry (lagging) + H1 noise + R:R 1:2 ต่ำเกินไป

**การเปลี่ยนแปลงหลัก:**

| Component | v1.x (Old) | v2.0 (New) |
|-----------|-----------|------------|
| Entry | EMA crossover | **Pullback to EMA18** |
| Timeframe | H1 | **H4** |
| SL | 2.5x ATR | **1.5x ATR** |
| TP | 5.0x ATR (1:2) | **4.5x ATR (1:3)** |
| ADX | > 25 | **> 20** |
| RSI filter | 20-80 | **35-65 pullback zone** |
| Cooldown | 60 min | **240 min** |
| Trailing | 3-level | **4-level** |

**ไฟล์ที่แก้:**
- `config.py` - New pullback parameters
- `modules/strategy_engine.py` - Pullback indicators + rewritten signal logic
- `scripts/run_mt5_live.py` - H4 TF, 1:3 R:R, 4-level trailing stop

**คณิตศาสตร์:** Win 35% × 3R - Loss 65% × 1R = **+0.48R expected per trade**

**สถานะ:** ✅ Implemented (22 Feb 2026)

### v1.1.0 - Max Loss Cap (Pending Implementation)
**วันที่:** 2 Feb 2026  
**ปัญหาที่พบ:** Single trade loss -$355 (39% of peak balance)  
**สาเหตุ:** SL กว้างเกินไป (355 pips) โดยไม่ลด lot size

**การแก้ไข:**
```python
# เพิ่มใน config.py หรือ risk module
"max_loss_per_trade_usd": 50  # ห้ามเสียเกิน $50 ต่อ trade

# Logic: ถ้า SL กว้าง → ลด lot size อัตโนมัติ
# lot_size = min(base_lot, max_loss / (sl_pips * pip_value))
```

**ผลที่คาดหวัง:**
- Max DD ลดจาก 40% → ประมาณ 10%
- Profit Factor เพิ่มจาก 1.20 → ประมาณ 3-5
- Recovery เร็วขึ้น (เสีย $50 vs $355)

**สถานะ:** ✅ Implemented (2 Feb 2026)

---

### v1.2.0 - Max Loss Cap Bug Fix (7 Feb 2026) 🐛

**ปัญหาที่พบ:**
- `run_mt5_live.py` ใช้ function `calculate_lot_size()` ของตัวเอง
- ไม่ได้เรียกใช้ `max_loss_per_trade_usd` จาก RiskManager
- ทำให้ trades หลัง v1.1 ยังเสียเกิน $50

**การแก้ไข:**
- แก้ไข `calculate_lot_size()` ให้รับ `risk_manager` parameter
- ใช้ `min(balance * risk_pct, max_loss_cap)` ในการคำนวณ
- เพิ่ม logging เพื่อยืนยันว่า Max Loss Cap ทำงาน

**ไฟล์ที่แก้:** `scripts/run_mt5_live.py` (lines 81-126, 371-375, 401-405)

**สถานะ:** ✅ Implemented (7 Feb 2026)

---

### v1.3.0 - ADX Trend Filter (7 Feb 2026) 🎯

**แนะนำโดย:** NotebookLM Analysis

**ปัญหาที่พบ:**
- Bot เทรดในตลาด Sideways (ไม่มีเทรนด์)
- โดน Stop Loss บ่อยเพราะตลาด Choppy

**การแก้ไข:**
- เพิ่มการคำนวณ **ADX (Average Directional Index)**
- เพิ่มเงื่อนไข: **ADX > 25** ถึงจะเปิด order
- ถ้า ADX < 25 → Bot จะ Hold (ไม่เทรด)

**ไฟล์ที่แก้:** `modules/strategy_engine.py` (lines 96-124, 326-338)

**สถานะ:** ✅ Implemented (7 Feb 2026)

---

### v1.3.1 - Dynamic Risk Fix (7 Feb 2026) 🔧

**ปัญหาที่พบ:**
- Max Loss Cap $50 fixed = 25% ของ $198!
- ควรจะเป็น 2% เสมอ ไม่ใช่ค่าตายตัว

**การแก้ไข:**
- ลบ `max_loss_per_trade_usd = $50` ออก
- ใช้ **2% ของ balance เท่านั้น**
- เพิ่ม safety cap: Balance <$300 = max 0.02 lots

**ตัวอย่าง:**
- $198 balance → Max loss $3.96/trade
- $500 balance → Max loss $10/trade

**ไฟล์ที่แก้:** `scripts/run_mt5_live.py` (lines 81-135)

**สถานะ:** ✅ Implemented (7 Feb 2026)

---

### v1.0.1 - Remove Oil & Silver
**วันที่:** ~20 Jan 2026  
**ปัญหาที่พบ:** Oil และ Silver performance แย่  
**การแก้ไข:** ลบออกจาก PORTFOLIO_CONFIG

**ผลลัพธ์:** ✅ ลด trades ที่แพ้ แต่ยังมีปัญหา DD จาก Gold

---

## 📈 Weekly Performance Tracking

| Week | Start Bal | End Bal | P/L | DD% | Trades | Win% | Notes |
|------|-----------|---------|-----|-----|--------|------|-------|
| 19-25 Jan | $123 | $404 | +$281 | 15% | 25 | 40% | Gold rally |
| 26 Jan-1 Feb | $404 | $477 | +$73 | 40% | 16 | 31% | Flash crash 29 Jan |
| 2-8 Feb | $546 | - | - | - | - | - | Pending... |

---

## 🎯 Quality Metrics (Long-term Viability)

### Target for "100 Year Survival"
| Metric | Current | Target | Status |
|--------|---------|--------|--------|
| Profit Factor | 1.20 | >1.5 | ❌ ต้องปรับ |
| Max DD | 40% | <20% | ❌ อันตราย |
| Recovery Factor | 0.40 | >1.0 | ❌ ต้องปรับ |
| Sharpe Ratio | 0.20 | >0.5 | ❌ ต้องปรับ |
| Avg Loss/Avg Win | 0.83 | <0.5 | ⚠️ พอได้ |
| Consecutive Losses | 7 | <5 | ❌ สูงไป |

### Risk of Ruin Calculator
```
Current settings:
- Win Rate: 50%
- Avg Win: $123
- Avg Loss: $103
- Risk per trade: Variable (up to 39%!)

Risk of Ruin = HIGH ⚠️

After Max Loss Cap ($50):
- Risk per trade: ~9% of balance
- Risk of Ruin = MEDIUM → acceptable
```

---

## 📝 Lessons Learned

### ❌ สิ่งที่ไม่ work:
1. **ATR-based SL without lot adjustment** - SL กว้างแต่ lot เต็ม = หายนะ
2. **Oil trading** - ไม่เหมาะกับ strategy นี้
3. **Re-entry immediately after SL** - 29 Jan เข้า Gold 2 ครั้งใน 13 นาที = -$264

### ✅ สิ่งที่ work:
1. **Gold trending moves** - ช่วงที่ trend ทำกำไรได้ดีมาก
2. **BTC short ช่วง bearish** - 3 consecutive wins (+$115)
3. **TP at reasonable levels** - ไม่ greedy เกินไป

---

## 🔮 Future Improvements Queue

| Priority | Feature | Expected Impact | Status |
|----------|---------|-----------------|--------|
| 🔴 HIGH | Max Loss Cap $50 | ลด DD 7x | ⏳ Pending |
| 🟡 MED | Cooldown after SL (1hr) | ป้องกัน consecutive loss | 💡 Idea |
| 🟡 MED | Trend filter (EMA200) | ลด trades สวน trend | 💡 Idea |
| 🟢 LOW | Dynamic TP based on ATR | เพิ่ม win rate | 💡 Idea |

---

## 📅 Review Schedule

- **Weekly:** ทุกวันอาทิตย์ - ดู performance
- **Monthly:** สรุป metrics และเปรียบเทียบกับเดือนก่อน
- **After changes:** 2 สัปดาห์หลังแก้ไข - ประเมินผล

---

*Last updated: 2 Feb 2026*
