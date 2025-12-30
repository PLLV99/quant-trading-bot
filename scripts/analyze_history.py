import pandas as pd
from bs4 import BeautifulSoup
import sys
import os

# Path to report
REPORT_PATH = "ReportHistory-415060885.html"

def analyze_report():
    if not os.path.exists(REPORT_PATH):
        print(f"File not found: {REPORT_PATH}")
        return

    print(f"Reading {REPORT_PATH}...")
    
    # Try reading as HTML table
    try:
        # Note: MT5 HTML reports are often just tables. 
        # We might need to handle encoding.
        with open(REPORT_PATH, 'r', encoding='utf-16') as f:
            content = f.read()
        
        soup = BeautifulSoup(content, 'html.parser')
        tables = soup.find_all('table')
        
        if not tables:
            print("No tables found in HTML.")
            return

        # Usually the orders are in the table (Orders or Deals)
        # Let's look for a table with many rows
        df = None
        for table in tables:
            rows = table.find_all('tr')
            if len(rows) > 10:
                # Basic parsing
                data = []
                headers = [th.get_text(strip=True) for th in rows[0].find_all('th')]
                if not headers:
                    headers = [td.get_text(strip=True) for td in rows[0].find_all('td')]
                
                for row in rows[1:]:
                    cols = [td.get_text(strip=True) for td in row.find_all('td')]
                    if len(cols) == len(headers):
                        data.append(cols)
                
                temp_df = pd.DataFrame(data, columns=headers)
                # Look for 'Time' and 'Type' columns
                if 'Time' in temp_df.columns and 'Type' in temp_df.columns:
                    df = temp_df
                    break
        
        if df is None:
            print("Could not identify Trade History table.")
            return

        print(f"Found {len(df)} trade records.")
        
        # --- Analysis ---
        # 1. Machine Gun Detection (Time delta)
        df['Time'] = pd.to_datetime(df['Time'], errors='coerce')
        df = df.sort_values('Time')
        df['TimeDiff'] = df['Time'].diff().dt.total_seconds()
        
        machine_gun_trades = df[df['TimeDiff'] < 60] # Trades within 1 minute of previous
        
        print("\n--- 💀 AUTOPSY REPORT 💀 ---")
        print(f"Total Trades Analyzed: {len(df)}")
        print(f"Rapid Fire Trades (<60s gap): {len(machine_gun_trades)} ({len(machine_gun_trades)/len(df)*100:.1f}%)")
        
        if not machine_gun_trades.empty:
            avg_gap = machine_gun_trades['TimeDiff'].mean()
            print(f"Average Gap during Rapid Fire: {avg_gap:.2f} seconds")
            print("Diagnosis: HIGH FREQUENCY OVER-TRADING (Machine Gun)")
        
        # 2. Counter Trend Check (Buy vs Sell ratios in short burst)
        # Simple check: consecutive same-side trades
        df['Action'] = df['Type'].str.lower()
        df['SameSide'] = df['Action'] == df['Action'].shift()
        consecutive_chains = df['SameSide'].sum()
        
        print(f"Consecutive Same-Side Entires: {consecutive_chains} (Trying to average down?)")

    except Exception as e:
        print(f"Error parsing report: {e}")

if __name__ == "__main__":
    # Install bs4 if needed
    try:
        import bs4
    except ImportError:
        os.system("pip install beautifulsoup4")
        
    analyze_report()
