import yfinance as yf

# Test OTC stock with .TW suffix
print("Testing 3443.TW (創意)...")
ticker = yf.Ticker('3443.TW')
hist = ticker.history(period='2d')
print(f"Data available: {len(hist) > 0}")
if len(hist) > 0:
    print(f"Price: {hist['Close'].iloc[-1]:.2f}")
    info = ticker.info
    market_cap = info.get('marketCap', 0)
    print(f"Market Cap: {market_cap / 1e8:.2f} 億")
    print(f"Exchange: {info.get('exchange', 'UNKNOWN')}")
else:
    print("NO DATA")

print("\n" + "="*50 + "\n")

# Test another OTC stock
print("Testing 5274.TW (信驊)...")
ticker2 = yf.Ticker('5274.TW')
hist2 = ticker2.history(period='2d')
print(f"Data available: {len(hist2) > 0}")
if len(hist2) > 0:
    print(f"Price: {hist2['Close'].iloc[-1]:.2f}")
