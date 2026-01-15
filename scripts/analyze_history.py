import pandas as pd
from bs4 import BeautifulSoup
import sys
import os

import glob
import os

def get_latest_report():
    # Find all html/xlsx files with "Report" in name
    files = glob.glob("*Report*.html") + glob.glob("*Report*.xlsx")
    if not files:
        return None
    # Return newest file
    return max(files, key=os.path.getctime)

REQUIRED_COLUMNS = ['Time', 'Symbol', 'Profit'] # Minimum needed

def analyze_report():
    report_path = get_latest_report()
    
    if not report_path:
        print("❌ No Report File found! (Please save report as HTML from MT5)")
        return

    print(f"📄 Analyzing Latest Report: {report_path}...")
    
    # Try reading as HTML table
    try:
        # Note: MT5 HTML reports are often just tables. 
        # We might need to handle encoding.
        with open(report_path, 'r', encoding='utf-16') as f:
            content = f.read()
        
        soup = BeautifulSoup(content, 'html.parser')
        tables = soup.find_all('table')
        
        if not tables:
            print("No tables found in HTML.")
            return

        # Try to find the trade table by looking for the header row
        df = None
        for table in tables:
            rows = table.find_all('tr')
            header_row_index = -1
            headers = []
            
            # Find the header row
            for ie, row in enumerate(rows):
                cells = [c.get_text(strip=True) for c in row.find_all(['td', 'th'])]
                if 'Time' in cells and 'Symbol' in cells and 'Profit' in cells:
                    header_row_index = ie
                    headers = cells
                    break
            
            if header_row_index != -1:
                # We found the header row, parse data
                print(f"DEBUG: Found Header Row: {headers} (Count: {len(headers)})")
                data = []
                for row in rows[header_row_index+1:]:
                    cols = [td.get_text(strip=True) for td in row.find_all('td')]
                    
                    # Fix: Allow rows with MORE columns (ignore extras)
                    if len(cols) >= len(headers):
                         # Take only the columns that match header count
                         data.append(cols[:len(headers)])
                    
                    # Also check for Summary Section directly
                    if "Total Net Profit:" in cols:
                        try:
                            idx = cols.index("Total Net Profit:")
                            net_profit = cols[idx+1] # Value is usually next cell
                            print(f"\n[SUMMARY FOUND] Total Net Profit found in report: ${net_profit}")
                        except:
                            pass

                # Dedup headers: MT5 has Time/Price twice (Open/Close)
                # Header: Time, Position, Symbol, Type, Vol, Price, SL, TP, Time, Price, Comm, Swap, Profit
                # Expected map: 0->OpenTime, 5->OpenPrice, 8->CloseTime, 9->ClosePrice
                if headers.count('Time') == 2:
                    first_time = headers.index('Time')
                    headers[first_time] = 'OpenTime'
                    headers[headers.index('Time')] = 'CloseTime'
                
                if headers.count('Price') == 2:
                    first_price = headers.index('Price')
                    headers[first_price] = 'OpenPrice'
                    headers[headers.index('Price')] = 'ClosePrice'

                df = pd.DataFrame(data, columns=headers)
                print(f"Found Trade Table with {len(df)} rows.")
                break # Found it, stop looking

        if df is None:
            print("Could not identify Trade History table.")
            return

        # Clean Profit column (remove spaces, handle negative numbers with spaces if any)
        # MT5 HTML might have separate table for Orders vs Deals vs Positions.
        # "Positions" table is usually what we want for PnL.
        
        print(f"Found {len(df)} trade records.")
        
        # --- Analysis ---
        # Clean Profit Data
        # Remove spaces and convert to float
        if 'Profit' in df.columns:
            df['Profit'] = df['Profit'].astype(str).str.replace(' ', '').str.replace(',', '')
            df['Profit'] = pd.to_numeric(df['Profit'], errors='coerce')
            
            total_profit = df['Profit'].sum()
            win_rate = (df['Profit'] > 0).mean() * 100
            
            # Advanced Metrics
            gross_profit = df[df['Profit'] > 0]['Profit'].sum()
            gross_loss = abs(df[df['Profit'] < 0]['Profit'].sum())
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else 999.0
            
            avg_win = df[df['Profit'] > 0]['Profit'].mean() if not df[df['Profit'] > 0].empty else 0
            avg_loss = df[df['Profit'] < 0]['Profit'].mean() if not df[df['Profit'] < 0].empty else 0
            risk_reward_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else 0
            
            # Distribution Stats (Fat Tails check)
            skew = df['Profit'].skew()
            kurtosis = df['Profit'].kurtosis()
            
            print(f"Total Profit from HTML: ${total_profit:.2f}")
            print(f"Win Rate: {win_rate:.2f}%")
            print(f"Profit Factor (PF): {profit_factor:.2f} (Target > 1.5)")
            print(f"RR Ratio: {risk_reward_ratio:.2f} (Avg Win/Avg Loss)")
            print(f"Skew: {skew:.2f} (Negative = Risk of Blowup)")
            print(f"Kurtosis: {kurtosis:.2f} (High = Extreme Events)")

        print("\n--- AUTOPSY REPORT ---")
        print(f"Total Trades Analyzed: {len(df)}")

        # 1. Machine Gun Detection (Time delta)
        if 'OpenTime' in df.columns:
            df['OpenTime'] = pd.to_datetime(df['OpenTime'], errors='coerce')
            df = df.sort_values('OpenTime')
            df['TimeDiff'] = df['OpenTime'].diff().dt.total_seconds()
            
            machine_gun_trades = df[df['TimeDiff'] < 60] # Trades within 1 minute of previous
            
            print(f"Rapid Fire Trades (<60s gap): {len(machine_gun_trades)} ({len(machine_gun_trades)/len(df)*100:.1f}%)")
            
            if not machine_gun_trades.empty:
                avg_gap = machine_gun_trades['TimeDiff'].mean()
                print(f"Average Gap during Rapid Fire: {avg_gap:.2f} seconds")
                print("Diagnosis: HIGH FREQUENCY OVER-TRADING (Machine Gun)")
        else:
             print("WARNING: 'OpenTime' column not found for timing analysis.")
        
        # 2. Counter Trend Check (Buy vs Sell ratios in short burst)
        # Simple check: consecutive same-side trades
        df['Action'] = df['Type'].str.lower()
        df['SameSide'] = df['Action'] == df['Action'].shift()
        consecutive_chains = df['SameSide'].sum()

        # Consecutive Wins/Losses
        df['Win'] = df['Profit'] > 0
        df['Streak'] = (df['Win'] != df['Win'].shift()).cumsum()
        streaks = df.groupby(['Win', 'Streak']).size()
        max_win_streak = streaks[True].max() if True in streaks.index.get_level_values(0) else 0
        max_loss_streak = streaks[False].max() if False in streaks.index.get_level_values(0) else 0
        
        print(f"Max Consecutive Wins: {max_win_streak}")
        print(f"Max Consecutive Losses: {max_loss_streak}")
        
        # --- Breakdown by Symbol ---
        print("\n--- 🔍 ASSET PERFORMANCE (The Culprit?) ---")
        if 'Symbol' in df.columns and 'Profit' in df.columns:
            symbol_stats = df.groupby('Symbol')['Profit'].agg(['sum', 'count', 'mean', 'min', 'max'])
            symbol_stats['WinRate'] = df.groupby('Symbol')['Profit'].apply(lambda x: (x > 0).sum() / len(x) * 100)
            symbol_stats = symbol_stats.sort_values('sum')
            print(symbol_stats)
            
            # Deep Dive into XAUUSD
            print("\n--- 🥇 XAUUSD FORENSIC ---")
            gold_trades = df[df['Symbol'].str.contains('XAU', case=False, na=False)]
            if not gold_trades.empty:
                print(gold_trades[['OpenTime', 'Type', 'OpenPrice', 'ClosePrice', 'Profit']].tail(15).to_string())
                
                # Check for "Fighting the Trend" (Series of Sells in Uptrend or vice versa)
                # Simple logic: If last 5 trades are all LOSS and SAME SIDE
                last_5 = gold_trades.tail(5)
                losses = last_5[last_5['Profit'] < 0]
                if len(losses) >= 4:
                    print("\n⚠️ DIAGNOSIS: Trend Fighting Detected! (Consecutive Losses)")
                    if len(losses['Type'].unique()) == 1:
                         print(f"   Bot kept spamming {losses['Type'].iloc[0]} orders while price moved against it.")

        else:
            print("Could not analyze by Symbol (Missing columns)")

    except Exception as e:
        print(f"Error parsing report: {e}")

if __name__ == "__main__":
    analyze_report()
