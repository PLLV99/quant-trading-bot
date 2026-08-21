"""
📊 Unified Trade Report Analyzer - AntiGravity Bot
Supports both HTML and Excel (.xlsx) exports from MT5

Features:
- Win Rate, Profit Factor, Expectancy, R:R Ratio
- Sharpe Ratio, Sortino Ratio (Risk-Adjusted)
- Max Drawdown, Recovery Factor
- Symbol breakdown, FTMO Compliance
- Machine Gun Detection, Trend Fighting Analysis
- Skew/Kurtosis (Fat Tail Risk)
"""

import pandas as pd
import numpy as np
from datetime import datetime
from bs4 import BeautifulSoup
import glob
import sys
# The reports below use box-drawing characters and emoji. A Windows console
# defaults to cp1252 and raises UnicodeEncodeError on the first line printed,
# so force UTF-8 rather than stripping the output back to ASCII.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# defaults to cp1252 and raises UnicodeEncodeError on the first line printed,
# so force UTF-8 rather than stripping the output back to ASCII.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import os


# =============================================================================
# LOADERS - Support HTML and Excel
# =============================================================================


def get_latest_report():
    """Find newest report file in current directory"""
    files = glob.glob("*Report*.html") + glob.glob("*Report*.xlsx")
    if not files:
        return None
    return max(files, key=os.path.getctime)


def load_html_report(filepath):
    """Parse MT5 HTML Trade History report"""
    with open(filepath, "r", encoding="utf-16") as f:
        content = f.read()

    soup = BeautifulSoup(content, "html.parser")
    tables = soup.find_all("table")

    if not tables:
        return None

    for table in tables:
        rows = table.find_all("tr")
        header_row_index = -1
        headers = []

        for ie, row in enumerate(rows):
            cells = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
            if "Time" in cells and "Symbol" in cells and "Profit" in cells:
                header_row_index = ie
                headers = cells
                break

        if header_row_index != -1:
            data = []
            for row in rows[header_row_index + 1 :]:
                cols = [td.get_text(strip=True) for td in row.find_all("td")]
                if len(cols) >= len(headers):
                    data.append(cols[: len(headers)])

            # Fix duplicate column names
            if headers.count("Time") == 2:
                first_time = headers.index("Time")
                headers[first_time] = "OpenTime"
                headers[headers.index("Time")] = "CloseTime"

            if headers.count("Price") == 2:
                first_price = headers.index("Price")
                headers[first_price] = "OpenPrice"
                headers[headers.index("Price")] = "ClosePrice"

            df = pd.DataFrame(data, columns=headers)

            # Clean and convert columns
            if "Profit" in df.columns:
                df["Profit"] = (
                    df["Profit"].astype(str).str.replace(" ", "").str.replace(",", "")
                )
                df["Profit"] = pd.to_numeric(df["Profit"], errors="coerce")

            if "OpenTime" in df.columns:
                df["OpenTime"] = pd.to_datetime(df["OpenTime"], errors="coerce")

            if "CloseTime" in df.columns:
                df["CloseTime"] = pd.to_datetime(df["CloseTime"], errors="coerce")

            return df

    return None


def load_excel_report(filepath):
    """Parse MT5 Excel Trade History report"""
    df_raw = pd.read_excel(filepath, header=None)

    trades = []
    in_trades = False

    for i, row in df_raw.iterrows():
        if str(row[0]).strip() == "Positions":
            in_trades = True
            continue
        if str(row[0]).strip() == "Orders":
            break
        if in_trades and i > 6:
            try:
                if pd.isna(row[0]) or "Time" in str(row[0]):
                    continue
                trade = {
                    "OpenTime": pd.to_datetime(str(row[0])),
                    "Position": row[1],
                    "Symbol": str(row[2]),
                    "Type": str(row[3]),
                    "Volume": float(row[4]) if pd.notna(row[4]) else 0,
                    "OpenPrice": float(row[5]) if pd.notna(row[5]) else 0,
                    "SL": row[6],
                    "TP": row[7],
                    "CloseTime": (
                        pd.to_datetime(str(row[8])) if pd.notna(row[8]) else None
                    ),
                    "ClosePrice": float(row[9]) if pd.notna(row[9]) else 0,
                    "Commission": float(row[10]) if pd.notna(row[10]) else 0,
                    "Swap": float(row[11]) if pd.notna(row[11]) else 0,
                    "Profit": float(row[12]) if pd.notna(row[12]) else 0,
                }
                trades.append(trade)
            except:
                continue

    return pd.DataFrame(trades)


def load_report(filepath):
    """Auto-detect and load report file"""
    if filepath.endswith(".xlsx"):
        return load_excel_report(filepath)
    elif filepath.endswith(".html"):
        return load_html_report(filepath)
    else:
        raise ValueError(f"Unsupported file format: {filepath}")


# =============================================================================
# QUANT METRICS
# =============================================================================


def calc_sharpe(returns, risk_free_rate=0.02):
    """Sharpe Ratio (Annualized)"""
    if len(returns) < 2 or returns.std() == 0:
        return 0
    excess = returns.mean() - (risk_free_rate / 252)
    return (excess / returns.std()) * np.sqrt(252)


def calc_sortino(returns, risk_free_rate=0.02):
    """Sortino Ratio - Only penalizes downside volatility"""
    if len(returns) < 2:
        return 0
    downside = returns[returns < 0]
    if len(downside) == 0 or downside.std() == 0:
        return float("inf") if returns.mean() > 0 else 0
    excess = returns.mean() - (risk_free_rate / 252)
    return (excess / downside.std()) * np.sqrt(252)


def calc_max_drawdown(cumulative_pnl):
    """Maximum Drawdown from cumulative P&L"""
    peak = cumulative_pnl.expanding().max()
    dd = cumulative_pnl - peak
    return dd.min()


# =============================================================================
# MAIN ANALYSIS
# =============================================================================


def analyze(df, initial_balance=300.0):
    """Full Quant Analysis - All Metrics"""

    output_lines = []

    def log(msg=""):
        print(msg)
        output_lines.append(str(msg))

    log("=" * 70)
    log("📊 UNIFIED TRADE REPORT ANALYSIS - AntiGravity Bot")
    log("=" * 70)
    log(f'Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    log(f"Balance: ${initial_balance:.2f}")
    log()

    if df is None or len(df) == 0:
        log("❌ No trades found!")
        return None

    total = len(df)
    winners = df[df["Profit"] > 0]
    losers = df[df["Profit"] < 0]
    win_rate = len(winners) / total * 100

    # === BASIC STATS ===
    log("📈 TRADE STATISTICS")
    log("-" * 50)
    log(f"Total Trades:    {total}")
    log(f"Winners:         {len(winners)} ({win_rate:.1f}%)")
    log(f"Losers:          {len(losers)} ({100-win_rate:.1f}%)")
    log()

    # === P&L ===
    total_pnl = df["Profit"].sum()
    gross_profit = winners["Profit"].sum() if len(winners) > 0 else 0
    gross_loss = losers["Profit"].sum() if len(losers) > 0 else 0
    avg_win = winners["Profit"].mean() if len(winners) > 0 else 0
    avg_loss = losers["Profit"].mean() if len(losers) > 0 else 0

    log("💰 P&L")
    log("-" * 50)
    log(f"Total P&L:       ${total_pnl:.2f} ({total_pnl/initial_balance*100:.1f}%)")
    log(f"Gross Profit:    ${gross_profit:.2f}")
    log(f"Gross Loss:      ${gross_loss:.2f}")
    log(f"Avg Win:         ${avg_win:.2f}")
    log(f"Avg Loss:        ${avg_loss:.2f}")
    log()

    # === QUANT METRICS ===
    pf = abs(gross_profit / gross_loss) if gross_loss != 0 else float("inf")
    rr = abs(avg_win / avg_loss) if avg_loss != 0 else 0
    expectancy = (win_rate / 100 * avg_win) + ((100 - win_rate) / 100 * avg_loss)

    returns = df["Profit"] / initial_balance
    sharpe = calc_sharpe(returns)
    sortino = calc_sortino(returns)

    cumulative = df["Profit"].cumsum()
    max_dd = calc_max_drawdown(cumulative)
    max_dd_pct = max_dd / initial_balance * 100
    recovery = abs(total_pnl / max_dd) if max_dd != 0 else float("inf")

    # Skew/Kurtosis (Fat Tails)
    skew = df["Profit"].skew()
    kurt = df["Profit"].kurtosis()

    log("📐 QUANT METRICS")
    log("-" * 50)
    log(f'Profit Factor:   {pf:.2f} {"✅" if pf > 1.5 else "⚠️"}')
    log(f"R:R Ratio:       1:{rr:.2f}")
    log(f"Expectancy:      ${expectancy:.2f}/trade")
    log(f'Sharpe Ratio:    {sharpe:.2f} {"✅" if sharpe > 1 else "⚠️"}')
    log(f"Sortino Ratio:   {sortino:.2f}")
    log(f"Max Drawdown:    ${max_dd:.2f} ({max_dd_pct:.1f}%)")
    log(f"Recovery Factor: {recovery:.2f}")
    log(f'Skew:            {skew:.2f} {"⚠️ Blow-up Risk" if skew < -1 else ""}')
    log(f'Kurtosis:        {kurt:.2f} {"⚠️ Fat Tails" if kurt > 3 else ""}')
    log()

    # === BY SYMBOL ===
    log("🎯 BY SYMBOL")
    log("-" * 50)
    for sym in df["Symbol"].unique():
        s = df[df["Symbol"] == sym]
        s_pnl = s["Profit"].sum()
        s_wr = len(s[s["Profit"] > 0]) / len(s) * 100
        status = "✅" if s_pnl > 0 else "❌"
        log(
            f"{sym:12} | {len(s):3} trades | WR: {s_wr:5.1f}% | P&L: ${s_pnl:8.2f} {status}"
        )
    log()

    # === CONSECUTIVE STREAKS ===
    loss_streak = win_streak = max_loss = max_win = 0
    for p in df["Profit"]:
        if p < 0:
            loss_streak += 1
            max_loss = max(max_loss, loss_streak)
            win_streak = 0
        else:
            win_streak += 1
            max_win = max(max_win, win_streak)
            loss_streak = 0

    # === MACHINE GUN DETECTION ===
    rapid_fire = 0
    if "OpenTime" in df.columns:
        df = df.sort_values("OpenTime")
        df["TimeDiff"] = df["OpenTime"].diff().dt.total_seconds()
        rapid_fire = len(df[df["TimeDiff"] < 60])

    log("⚠️  RISK FLAGS")
    log("-" * 50)
    log(f'Max Consecutive Losses:  {max_loss} {"🔴" if max_loss > 5 else ""}')
    log(f"Max Consecutive Wins:    {max_win}")
    log(
        f'Rapid Fire Trades (<60s): {rapid_fire} {"🔴 Machine Gun!" if rapid_fire > 5 else ""}'
    )
    log()

    # === FTMO CHECK ===
    daily_limit = initial_balance * 0.05
    max_dd_limit = initial_balance * 0.10

    log("✅ FTMO COMPLIANCE")
    log("-" * 50)
    log(
        f'Daily Loss (5%):  ${daily_limit:.2f} - {"✅ PASS" if abs(max_dd) < daily_limit else "❌ FAIL"}'
    )
    log(
        f'Max DD (10%):     ${max_dd_limit:.2f} - {"✅ PASS" if abs(max_dd) < max_dd_limit else "❌ FAIL"}'
    )
    log()

    # === VERDICT ===
    log("=" * 70)
    grade = "A"
    if pf < 1.0:
        grade = "F"
    elif pf < 1.5:
        grade = "B"
    if abs(max_dd) > max_dd_limit:
        grade = "F"
    if max_loss > 7:
        grade = min(grade, "C")
    if sharpe > 1.5 and pf > 2.0:
        grade = "A+"

    log(f"🏆 GRADE: {grade}")
    log(f"   Return: {total_pnl/initial_balance*100:.1f}%")
    log("=" * 70)

    # WRITE TO FILE
    with open("report_summary.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(output_lines))

    return {
        "grade": grade,
        "pnl": total_pnl,
        "win_rate": win_rate,
        "pf": pf,
        "sharpe": sharpe,
        "max_dd": max_dd,
    }


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    filepath = sys.argv[1] if len(sys.argv) > 1 else get_latest_report()
    balance = float(sys.argv[2]) if len(sys.argv) > 2 else 300.0

    if not filepath:
        print("❌ No report file found!")
        sys.exit(1)

    print(f"\n📄 Loading: {filepath}\n")
    df = load_report(filepath)
    analyze(df, balance)
