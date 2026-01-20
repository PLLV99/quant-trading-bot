from bs4 import BeautifulSoup

f = open("ReportHistory-415089870.html", "r", encoding="utf-16")
html = f.read()
f.close()

soup = BeautifulSoup(html, "html.parser")
rows = soup.find_all("tr")

trades = []
for row in rows:
    cols = row.find_all("td")
    if len(cols) >= 14:
        try:
            profit_text = cols[-1].get_text(strip=True)
            if profit_text and profit_text.replace("-", "").replace(".", "").isdigit():
                trades.append(
                    {
                        "time": cols[0].get_text(strip=True),
                        "symbol": cols[2].get_text(strip=True),
                        "type": cols[3].get_text(strip=True),
                        "volume": cols[5].get_text(strip=True),
                        "profit": float(profit_text),
                    }
                )
        except:
            pass

print("Total trades:", len(trades))
total_pnl = sum(t["profit"] for t in trades)
wins = [t for t in trades if t["profit"] > 0]
losses = [t for t in trades if t["profit"] < 0]
print("Wins:", len(wins), "Losses:", len(losses))
if trades:
    print("Win Rate:", round(len(wins) / len(trades) * 100, 1), "%")
print("Total PnL:", round(total_pnl, 2))

gross_profit = sum(t["profit"] for t in wins)
gross_loss = sum(t["profit"] for t in losses)
print("Gross Profit:", round(gross_profit, 2))
print("Gross Loss:", round(gross_loss, 2))

if gross_loss != 0:
    print("Profit Factor:", round(gross_profit / abs(gross_loss), 2))

# By symbol
symbols = {}
for t in trades:
    s = t["symbol"]
    if s not in symbols:
        symbols[s] = {"pnl": 0, "count": 0, "wins": 0}
    symbols[s]["pnl"] += t["profit"]
    symbols[s]["count"] += 1
    if t["profit"] > 0:
        symbols[s]["wins"] += 1

print()
print("By Symbol:")
for s, data in symbols.items():
    wr = round(data["wins"] / data["count"] * 100, 1) if data["count"] > 0 else 0
    print(f"  {s}: {data['count']} trades, WR: {wr}%, PnL: {round(data['pnl'], 2)}")
