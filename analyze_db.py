import json

with open('stock_database.json', 'r', encoding='utf-8') as f:
    db = json.load(f)

stocks = db['stocks']
listed = [s for s in stocks if s['market'] == 'LISTED']
otc = [s for s in stocks if s['market'] == 'OTC']

print(f'資料庫中:')
print(f'  上市: {len(listed)} 支')
print(f'  上櫃: {len(otc)} 支')
print(f'\n上櫃股票代碼範例: {[s["code"] for s in otc[:20]]}')

# 檢查 twstock 的分類
import twstock
codes = twstock.codes

all_stocks_from_twstock = []
for code, info in codes.items():
    if info.type == '股票' and code.isdigit() and len(code) == 4:
        market = 'LISTED' if info.market == '上市' else 'OTC'
        all_stocks_from_twstock.append({
            'code': code,
            'name': info.name,
            'market': market
        })

twstock_listed = [s for s in all_stocks_from_twstock if s['market'] == 'LISTED']
twstock_otc = [s for s in all_stocks_from_twstock if s['market'] == 'OTC']

print(f'\ntwstock 清單:')
print(f'  上市: {len(twstock_listed)} 支')
print(f'  上櫃: {len(twstock_otc)} 支')

# 找出哪些上櫃股票沒有被抓到
otc_codes_in_db = set(s['code'] for s in otc)
otc_codes_in_twstock = set(s['code'] for s in twstock_otc)
missing_otc = otc_codes_in_twstock - otc_codes_in_db

print(f'\n缺少的上櫃股票數量: {len(missing_otc)}')
print(f'缺少的上櫃股票代碼範例: {list(missing_otc)[:20]}')
