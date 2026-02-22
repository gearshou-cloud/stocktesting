import yfinance as yf
import pandas as pd
from datetime import datetime
import time

# 台灣上市股票代碼（主要大型股）
TWSE_STOCKS = [
    '0050', '0051', '0052', '0053', '0055', '0056', '0057', '006208',
    '1101', '1102', '1216', '1301', '1303', '1326', '1402', '1590',
    '2002', '2105', '2201', '2207', '2301', '2303', '2308', '2317',
    '2324', '2327', '2330', '2344', '2345', '2347', '2353', '2354',
    '2357', '2360', '2371', '2379', '2382', '2385', '2395', '2408',
    '2409', '2412', '2454', '2474', '2492', '2498', '2603', '2609',
    '2610', '2615', '2618', '2801', '2823', '2880', '2881', '2882',
    '2883', '2884', '2885', '2886', '2887', '2890', '2891', '2892',
    '2912', '3008', '3034', '3037', '3045', '3231', '3481', '3711',
    '4904', '4938', '5871', '5876', '5880', '6005', '6415', '6505',
    '6770', '9904', '9910', '9921', '9933', '9945'
]

# 台灣上櫃股票代碼（主要大型股）
TPEX_STOCKS = [
    '3443', '3529', '3661', '3707', '4966', '4968', '5274', '6446',
    '6488', '6510', '6669', '8046', '8069', '8086', '8131', '8150',
    '8271', '8299', '8454', '8996'
]

def fetch_stock_data(code, market):
    """抓取單一股票資料"""
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
        
        # 獲取股票名稱
        info = ticker.info
        name = info.get('longName') or info.get('shortName') or code
        
        return {
            '證券代號': code,
            '證券名稱': name,
            '收盤價': round(close_price, 2),
            '漲跌幅': f"{change_pct:+.2f}%",
            '市場': market
        }
    except Exception as e:
        print(f"抓取 {code} 失敗: {e}")
        return None

def main():
    print("=" * 60)
    print("台灣股市收盤行情抓取 (使用 Yahoo Finance)")
    print(f"執行時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    all_stocks = []
    
    # 抓取上市股票
    print(f"\n正在抓取 {len(TWSE_STOCKS)} 支上市股票...")
    for i, code in enumerate(TWSE_STOCKS, 1):
        print(f"  [{i}/{len(TWSE_STOCKS)}] {code}", end='\r')
        stock_data = fetch_stock_data(code, '上市')
        if stock_data:
            all_stocks.append(stock_data)
        time.sleep(0.1)  # 避免請求過快
    
    print(f"\n✅ 成功抓取 {sum(1 for s in all_stocks if s['市場'] == '上市')} 支上市股票")
    
    # 抓取上櫃股票
    print(f"\n正在抓取 {len(TPEX_STOCKS)} 支上櫃股票...")
    for i, code in enumerate(TPEX_STOCKS, 1):
        print(f"  [{i}/{len(TPEX_STOCKS)}] {code}", end='\r')
        stock_data = fetch_stock_data(code, '上櫃')
        if stock_data:
            all_stocks.append(stock_data)
        time.sleep(0.1)
    
    print(f"\n✅ 成功抓取 {sum(1 for s in all_stocks if s['市場'] == '上櫃')} 支上櫃股票")
    
    if not all_stocks:
        print("\n❌ 無法抓取資料")
        return
    
    # 轉換為 DataFrame 並排序
    df = pd.DataFrame(all_stocks)
    df = df.sort_values('證券代號')
    
    print("\n" + "=" * 60)
    print(f"總共抓取 {len(all_stocks)} 支股票")
    print(f"上市: {sum(1 for s in all_stocks if s['市場'] == '上市')} 支 | 上櫃: {sum(1 for s in all_stocks if s['市場'] == '上櫃')} 支")
    print("=" * 60)
    
    # 顯示完整 Markdown 表格
    print("\n完整股票清單（Markdown 格式）：")
    print(df.to_markdown(index=False))
    
    # 儲存完整資料
    output_file = 'taiwan_stocks_latest.csv'
    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"\n✅ 完整資料已儲存至: {output_file}")
    
    # 儲存 Markdown 表格
    md_file = 'taiwan_stocks_latest.md'
    with open(md_file, 'w', encoding='utf-8') as f:
        f.write(f"# 台灣股市收盤行情\n\n")
        f.write(f"更新時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(df.to_markdown(index=False))
    print(f"✅ Markdown 表格已儲存至: {md_file}")

if __name__ == "__main__":
    main()
