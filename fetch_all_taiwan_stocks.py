import requests
import pandas as pd
from datetime import datetime
import time
import yfinance as yf

def get_twse_stock_list():
    """從台灣證券交易所取得所有上市股票代碼"""
    print("正在取得上市股票清單...")
    
    url = "https://isin.twse.com.tw/isin/C_public.jsp?strMode=2"
    
    try:
        # 讀取網頁內容
        df = pd.read_html(url, encoding='big5')[0]
        
        # 清理資料
        df.columns = df.iloc[0]
        df = df[1:]
        
        # 篩選股票（排除 ETF、特別股等）
        stocks = []
        for idx, row in df.iterrows():
            code_name = str(row['有價證券代號及名稱'])
            if '\u3000' in code_name:
                parts = code_name.split('\u3000')
                code = parts[0].strip()
                name = parts[1].strip()
                
                # 只保留一般股票（4位數字代碼）
                if code.isdigit() and len(code) == 4:
                    stocks.append({'code': code, 'name': name})
        
        print(f"✅ 取得 {len(stocks)} 支上市股票")
        return stocks
    except Exception as e:
        print(f"❌ 取得上市股票清單失敗: {e}")
        return []

def get_tpex_stock_list():
    """從櫃買中心取得所有上櫃股票代碼"""
    print("正在取得上櫃股票清單...")
    
    url = "https://isin.twse.com.tw/isin/C_public.jsp?strMode=4"
    
    try:
        # 讀取網頁內容
        df = pd.read_html(url, encoding='big5')[0]
        
        # 清理資料
        df.columns = df.iloc[0]
        df = df[1:]
        
        # 篩選股票
        stocks = []
        for idx, row in df.iterrows():
            code_name = str(row['有價證券代號及名稱'])
            if '\u3000' in code_name:
                parts = code_name.split('\u3000')
                code = parts[0].strip()
                name = parts[1].strip()
                
                # 只保留一般股票（4位數字代碼）
                if code.isdigit() and len(code) == 4:
                    stocks.append({'code': code, 'name': name})
        
        print(f"✅ 取得 {len(stocks)} 支上櫃股票")
        return stocks
    except Exception as e:
        print(f"❌ 取得上櫃股票清單失敗: {e}")
        return []

def fetch_stock_price(code, market):
    """抓取單一股票價格資料"""
    try:
        symbol = f"{code}.TW"
        ticker = yf.Ticker(symbol)
        
        # 獲取最近2天的資料
        hist = ticker.history(period='2d')
        
        if len(hist) == 0:
            return None
        
        # 獲取最新收盤價
        latest = hist.iloc[-1]
        close_price = latest['Close']
        
        # 計算漲跌幅
        if len(hist) >= 2:
            prev_close = hist.iloc[-2]['Close']
            change_pct = ((close_price - prev_close) / prev_close) * 100
        else:
            change_pct = 0
        
        return {
            '證券代號': code,
            '收盤價': round(close_price, 2),
            '漲跌幅': f"{change_pct:+.2f}%",
            '市場': market
        }
    except:
        return None

def main():
    print("=" * 70)
    print("台灣股市完整收盤行情抓取")
    print(f"執行時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    # 步驟 1: 取得股票清單
    twse_list = get_twse_stock_list()
    tpex_list = get_tpex_stock_list()
    
    if not twse_list and not tpex_list:
        print("\n❌ 無法取得股票清單")
        return
    
    print(f"\n總共需要抓取: {len(twse_list) + len(tpex_list)} 支股票")
    print("⚠️  這將需要較長時間，請耐心等待...")
    
    # 詢問是否繼續
    response = input("\n是否繼續？(y/n): ")
    if response.lower() != 'y':
        print("已取消")
        return
    
    all_stocks = []
    
    # 步驟 2: 抓取上市股票價格
    print(f"\n正在抓取 {len(twse_list)} 支上市股票價格...")
    for i, stock in enumerate(twse_list, 1):
        print(f"  [{i}/{len(twse_list)}] {stock['code']} {stock['name']}", end='\r')
        
        price_data = fetch_stock_price(stock['code'], '上市')
        if price_data:
            price_data['證券名稱'] = stock['name']
            all_stocks.append(price_data)
        
        # 每 10 支股票暫停一下，避免請求過快
        if i % 10 == 0:
            time.sleep(1)
    
    print(f"\n✅ 成功抓取 {sum(1 for s in all_stocks if s['市場'] == '上市')} 支上市股票")
    
    # 步驟 3: 抓取上櫃股票價格
    print(f"\n正在抓取 {len(tpex_list)} 支上櫃股票價格...")
    for i, stock in enumerate(tpex_list, 1):
        print(f"  [{i}/{len(tpex_list)}] {stock['code']} {stock['name']}", end='\r')
        
        price_data = fetch_stock_price(stock['code'], '上櫃')
        if price_data:
            price_data['證券名稱'] = stock['name']
            all_stocks.append(price_data)
        
        if i % 10 == 0:
            time.sleep(1)
    
    print(f"\n✅ 成功抓取 {sum(1 for s in all_stocks if s['市場'] == '上櫃')} 支上櫃股票")
    
    # 步驟 4: 整理並儲存資料
    if not all_stocks:
        print("\n❌ 沒有成功抓取任何股票資料")
        return
    
    df = pd.DataFrame(all_stocks)
    df = df[['證券代號', '證券名稱', '收盤價', '漲跌幅', '市場']]
    df = df.sort_values('證券代號')
    
    print("\n" + "=" * 70)
    print(f"總共成功抓取 {len(all_stocks)} 支股票")
    print(f"上市: {sum(1 for s in all_stocks if s['市場'] == '上市')} 支 | 上櫃: {sum(1 for s in all_stocks if s['市場'] == '上櫃')} 支")
    print("=" * 70)
    
    # 儲存 CSV
    csv_file = 'taiwan_all_stocks.csv'
    df.to_csv(csv_file, index=False, encoding='utf-8-sig')
    print(f"\n✅ CSV 檔案已儲存至: {csv_file}")
    
    # 儲存 Markdown（只顯示前 100 筆）
    md_file = 'taiwan_all_stocks_preview.md'
    with open(md_file, 'w', encoding='utf-8') as f:
        f.write(f"# 台灣股市完整收盤行情\n\n")
        f.write(f"更新時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"總共 {len(all_stocks)} 支股票（以下顯示前 100 筆）\n\n")
        f.write(df.head(100).to_markdown(index=False))
    print(f"✅ Markdown 預覽已儲存至: {md_file}")
    
    # 顯示前 20 筆
    print("\n前 20 筆資料預覽：")
    print(df.head(20).to_string(index=False))

if __name__ == "__main__":
    main()
