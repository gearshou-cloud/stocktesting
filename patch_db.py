import json
import yfinance as yf
import os

DATABASE_FILE = 'stock_database.json'

def patch_silicon_force():
    if not os.path.exists(DATABASE_FILE):
        print("資料庫檔案不存在")
        return

    with open(DATABASE_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 找到矽力-KY (6415)
    target_code = '6415'
    found = False
    
    print(f"正在更新 {target_code} 矽力-KY 的資料...")
    
    # 重抓數據
    ticker = yf.Ticker('6415.TW')
    hist = ticker.history(period='5d')
    latest = hist.iloc[-1]
    
    close_price = latest['Close']
    open_price = latest['Open']
    prev_close = hist.iloc[-2]['Close']
    change_pct = ((close_price - prev_close) / prev_close) * 100
    
    print(f"最新數據: 開盤 {open_price}, 收盤 {close_price}, 昨收 {prev_close}")
    print(f"是否開高? {'是' if open_price > prev_close else '否'}")

    for stock in data['stocks']:
        if stock['code'] == target_code:
            stock['open'] = round(open_price, 2)  # 補上 open 欄位
            stock['price'] = round(close_price, 2)
            stock['change_pct'] = round(change_pct, 2)
            found = True
            print("資料庫已更新！")
            break
    
    if found:
        with open(DATABASE_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print("存檔完成。請重新整理網頁查看。")
    else:
        print("在資料庫中找不到矽力-KY")

if __name__ == '__main__':
    patch_silicon_force()
