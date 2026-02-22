from datetime import datetime, timedelta

def _recent_trading_dates(n=3):
    dates = []
    d = datetime.now()
    for _ in range(30): # Look back up to 30 calendar days
        if d.weekday() < 5:
            dates.append(d.strftime('%Y%m%d'))
        d -= timedelta(days=1)
        if len(dates) >= n:
            break
    return dates

print(f"目前日期: {datetime.now().strftime('%Y-%m-%d')}")
print(f"搜尋到的最近 10 個交易日候選: {_recent_trading_dates(10)}")
