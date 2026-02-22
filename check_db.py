import json

# 讀取資料庫
with open('stock_database.json', 'r', encoding='utf-8') as f:
    db = json.load(f)

print(f"總股票數: {db['total_stocks']}")
print(f"更新時間: {db['update_time']}")
print(f"上市: {sum(1 for s in db['stocks'] if s['market'] == 'LISTED')} 支")
print(f"上櫃: {sum(1 for s in db['stocks'] if s['market'] == 'OTC')} 支")

# 顯示一些統計
stocks = db['stocks']
print(f"\n價格統計:")
print(f"  最高價: {max(s['price'] for s in stocks):.2f}")
print(f"  最低價: {min(s['price'] for s in stocks):.2f}")
print(f"\n漲幅統計:")
print(f"  最大漲幅: {max(s['change_pct'] for s in stocks):.2f}%")
print(f"  最大跌幅: {min(s['change_pct'] for s in stocks):.2f}%")
