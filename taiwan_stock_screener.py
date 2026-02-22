"""
台股當日強勢股篩選器
Taiwan Stock Screener - Identifies top performing stocks based on daily price movement
"""

import sys
import io
import yfinance as yf
import pandas as pd
from datetime import datetime

# 設定 UTF-8 編碼以支援中文輸出 / Configure UTF-8 encoding for Chinese output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# ============================================================================
# 配置參數 / Configuration
# ============================================================================

def get_user_filters():
    """
    獲取使用者輸入的篩選條件
    Get user input for filtering criteria
    """
    print("="*80)
    print("📊 台股強勢股篩選器 | Taiwan Stock Screener")
    print("="*80)
    print()
    
    # 股價範圍
    print("💰 請輸入股價篩選範圍 (台幣 TWD):")
    while True:
        try:
            min_price_input = input("   最低股價 [預設: 50]: ").strip()
            min_price = float(min_price_input) if min_price_input else 50.0
            if min_price <= 0:
                print("   ❌ 股價必須大於 0，請重新輸入")
                continue
            break
        except ValueError:
            print("   ❌ 請輸入有效的數字")
    
    while True:
        try:
            max_price_input = input("   最高股價 [預設: 200]: ").strip()
            max_price = float(max_price_input) if max_price_input else 200.0
            if max_price <= min_price:
                print(f"   ❌ 最高股價必須大於最低股價 ({min_price})，請重新輸入")
                continue
            break
        except ValueError:
            print("   ❌ 請輸入有效的數字")
    
    # 市值範圍
    print()
    print("📊 請輸入最小市值 (億台幣):")
    while True:
        try:
            market_cap_input = input("   最小市值 [預設: 100億]: ").strip()
            market_cap_billion = float(market_cap_input) if market_cap_input else 100.0
            if market_cap_billion <= 0:
                print("   ❌ 市值必須大於 0，請重新輸入")
                continue
            min_market_cap = market_cap_billion * 100_000_000  # 轉換為台幣
            break
        except ValueError:
            print("   ❌ 請輸入有效的數字")
    
    print()
    print("="*80)
    print(f"✅ 篩選條件設定完成:")
    print(f"   股價範圍: {min_price:.2f} - {max_price:.2f} TWD")
    print(f"   最小市值: {market_cap_billion:.2f} 億 TWD ({min_market_cap:,.0f} TWD)")
    print("="*80)
    print()
    
    return min_price, max_price, min_market_cap

# 台股代碼列表 (主要上市公司) / Taiwan stock symbols (major listed companies)
# 包含台積電、聯發科、鴻海等主要股票
TAIWAN_STOCKS = [
    '2330.TW',  # 台積電 TSMC
    '2317.TW',  # 鴻海 Hon Hai
    '2454.TW',  # 聯發科 MediaTek
    '2412.TW',  # 中華電 Chunghwa Telecom
    '2882.TW',  # 國泰金 Cathay Financial
    '2881.TW',  # 富邦金 Fubon Financial
    '2886.TW',  # 兆豐金 Mega Financial
    '2891.TW',  # 中信金 CTBC Financial
    '2303.TW',  # 聯電 UMC
    '2308.TW',  # 台達電 Delta Electronics
    '2382.TW',  # 廣達 Quanta
    '2357.TW',  # 華碩 ASUS
    '2395.TW',  # 研華 Advantech
    '3008.TW',  # 大立光 Largan
    '2002.TW',  # 中鋼 China Steel
    '1301.TW',  # 台塑 Formosa Plastics
    '1303.TW',  # 南亞 Nan Ya Plastics
    '2207.TW',  # 和泰車 Hotai Motor
    '2912.TW',  # 統一超 President Chain Store
    '2884.TW',  # 玉山金 E.Sun Financial
    '6505.TW',  # 台塑化 Formosa Petrochemical
    '2892.TW',  # 第一金 First Financial
    '2885.TW',  # 元大金 Yuanta Financial
    '2887.TW',  # 台新金 Taishin Financial
    '2890.TW',  # 永豐金 SinoPac Financial
    '3711.TW',  # 日月光投控 ASE Technology
    '2327.TW',  # 國巨 Yageo
    '2301.TW',  # 光寶科 Lite-On
    '2408.TW',  # 南亞科 Nanya Technology
    '3045.TW',  # 台灣大 Taiwan Mobile
]

# ============================================================================
# 主要功能 / Main Functions
# ============================================================================

def fetch_stock_data(symbol):
    """
    獲取單一股票的即時數據
    Fetch real-time data for a single stock
    """
    try:
        ticker = yf.Ticker(symbol)
        
        # 獲取歷史數據 (最近2天以計算漲幅)
        hist = ticker.history(period='2d')
        
        if len(hist) < 2:
            return None
        
        # 獲取基本資訊
        info = ticker.info
        
        # 提取需要的數據
        current_price = hist['Close'].iloc[-1]
        previous_close = hist['Close'].iloc[-2]
        volume = hist['Volume'].iloc[-1]
        
        # 市值 (可能以美元計價，需要轉換)
        market_cap = info.get('marketCap', 0)
        
        # 公司名稱
        name = info.get('longName') or info.get('shortName') or symbol.replace('.TW', '')
        
        # 計算漲幅
        daily_change_pct = ((current_price - previous_close) / previous_close) * 100
        
        return {
            'symbol': symbol,
            'name': name,
            'current_price': current_price,
            'previous_close': previous_close,
            'daily_change_pct': daily_change_pct,
            'volume': volume,
            'market_cap': market_cap
        }
    
    except Exception as e:
        print(f"⚠️  無法獲取 {symbol} 的數據: {str(e)}")
        return None


def filter_stocks(stock_data_list, min_price, max_price, min_market_cap):
    """
    根據價格和市值篩選股票
    Filter stocks based on price and market cap criteria
    """
    filtered = []
    
    for stock in stock_data_list:
        if stock is None:
            continue
        
        # 價格篩選
        if not (min_price <= stock['current_price'] <= max_price):
            continue
        
        # 市值篩選
        if stock['market_cap'] < min_market_cap:
            continue
        
        filtered.append(stock)
    
    return filtered


def display_results(top_stocks, min_price, max_price, min_market_cap):
    """
    顯示篩選結果
    Display screening results
    """
    print("\n" + "="*80)
    print("🔥 台股當日強勢股 TOP 3 | Taiwan Top 3 Strong Performers")
    print("="*80)
    print(f"📅 查詢時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"💰 價格範圍: {min_price:.2f} - {max_price:.2f} TWD")
    print(f"📊 最小市值: {min_market_cap:,.0f} TWD ({min_market_cap/1e8:.2f}億)")
    print("="*80 + "\n")
    
    if not top_stocks:
        print("❌ 沒有符合條件的股票")
        return
    
    for i, stock in enumerate(top_stocks, 1):
        print(f"🏆 第 {i} 名")
        print(f"   代碼: {stock['symbol']}")
        print(f"   名稱: {stock['name']}")
        print(f"   現價: {stock['current_price']:.2f} TWD")
        print(f"   漲幅: {stock['daily_change_pct']:+.2f}%")
        print(f"   成交量: {stock['volume']:,} 股")
        print(f"   市值: {stock['market_cap']:,.0f} TWD ({stock['market_cap']/1e9:.2f}B)")
        print()
    
    print("="*80)


def main():
    """
    主程式
    Main program
    """
    # 獲取使用者篩選條件
    min_price, max_price, min_market_cap = get_user_filters()
    
    print("🚀 開始篩選台股強勢股...")
    print(f"📋 分析股票數量: {len(TAIWAN_STOCKS)}")
    
    # 獲取所有股票數據
    print("\n⏳ 正在獲取股票數據...")
    stock_data_list = []
    
    for symbol in TAIWAN_STOCKS:
        print(f"   處理中: {symbol}", end='\r')
        data = fetch_stock_data(symbol)
        if data:
            stock_data_list.append(data)
    
    print(f"\n✅ 成功獲取 {len(stock_data_list)} 支股票數據")
    
    # 篩選股票
    filtered_stocks = filter_stocks(stock_data_list, min_price, max_price, min_market_cap)
    print(f"✅ 符合條件的股票: {len(filtered_stocks)} 支")
    
    # 排序 (依漲幅由高到低)
    sorted_stocks = sorted(filtered_stocks, key=lambda x: x['daily_change_pct'], reverse=True)
    
    # 取前三名
    top_3 = sorted_stocks[:3]
    
    # 顯示結果
    display_results(top_3, min_price, max_price, min_market_cap)


if __name__ == "__main__":
    main()
