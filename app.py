"""
台股強勢股篩選器 - Flask Web API
Taiwan Stock Screener - Flask Web Application
"""

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import yfinance as yf
from datetime import datetime

app = Flask(__name__)
CORS(app)

# 台股代碼列表 (主要上市公司)
TAIWAN_STOCKS = [
    # 上市股票 (.TW)
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
    
    # 上櫃股票 (使用 .TW 後綴，但會在程式中標記為 OTC)
    # 注意：Yahoo Finance 對台灣股票統一使用 .TW，需要用其他方式區分上市/上櫃
    '3443.TW',  # 創意 Global Unichip (上櫃)
    '6669.TW',  # 緯穎 Wiwynn (上櫃)
    '6488.TW',  # 環球晶 GlobalWafers (上櫃)
    '3707.TW',  # 漢磊 Episil (上櫃)
    '6446.TW',  # 藥華藥 PharmaEssentia (上櫃)
    '4966.TW',  # 譜瑞-KY Parade (上櫃)
    '3529.TW',  # 力旺 eMemory (上櫃)
    '6510.TW',  # 精測 Chroma ATE (上櫃)
    '4968.TW',  # 立積 Eris (上櫃)
    '3661.TW',  # 世芯-KY Alchip (上櫃)
]

# 上櫃股票代碼列表（用於判斷股票類型）
OTC_STOCK_CODES = ['3443', '6669', '6488', '3707', '6446', '4966', '3529', '6510', '4968', '3661']


def fetch_index_data(index_symbol, index_name):
    """獲取指數的即時數據（盤中表現）"""
    try:
        ticker = yf.Ticker(index_symbol)
        
        # 獲取今日盤中數據（1分鐘間隔）
        hist = ticker.history(period='1d', interval='1m')
        
        if len(hist) == 0:
            # 如果沒有分鐘數據，使用日線數據
            hist = ticker.history(period='2d')
            if len(hist) < 2:
                return None
            
            current_price = hist['Close'].iloc[-1]
            previous_close = hist['Close'].iloc[-2]
        else:
            # 使用盤中數據
            current_price = hist['Close'].iloc[-1]
            open_price = hist['Open'].iloc[0]
            previous_close = open_price  # 盤中表現以開盤價為基準
        
        daily_change_pct = ((current_price - previous_close) / previous_close) * 100
        
        return {
            'name': index_name,
            'symbol': index_symbol,
            'value': float(current_price),
            'change_pct': float(daily_change_pct)
        }
    except Exception as e:
        print(f"Error fetching index {index_symbol}: {str(e)}")
        return None


def fetch_stock_data(symbol):
    """獲取單一股票的即時數據（盤中表現）"""
    try:
        ticker = yf.Ticker(symbol)
        
        # 獲取今日盤中數據（1分鐘間隔）
        hist = ticker.history(period='1d', interval='1m')
        
        if len(hist) == 0:
            # 如果沒有分鐘數據，使用日線數據
            hist = ticker.history(period='2d')
            if len(hist) < 2:
                return None
            
            current_price = hist['Close'].iloc[-1]
            previous_close = hist['Close'].iloc[-2]
            volume = hist['Volume'].iloc[-1]
        else:
            # 使用盤中數據（開盤到現在）
            current_price = hist['Close'].iloc[-1]
            open_price = hist['Open'].iloc[0]
            previous_close = open_price  # 盤中表現以開盤價為基準
            volume = hist['Volume'].sum()  # 累計成交量
        
        info = ticker.info
        market_cap = info.get('marketCap', 0)
        name = info.get('longName') or info.get('shortName') or symbol.replace('.TW', '').replace('.TWO', '')
        daily_change_pct = ((current_price - previous_close) / previous_close) * 100
        
        # 判斷股票類型（檢查股票代碼是否在上櫃列表中）
        stock_code = symbol.replace('.TW', '').replace('.TWO', '')
        stock_type = 'OTC' if stock_code in OTC_STOCK_CODES else 'LISTED'
        
        return {
            'symbol': symbol,
            'name': name,
            'current_price': float(current_price),
            'previous_close': float(previous_close),
            'daily_change_pct': float(daily_change_pct),
            'volume': int(volume),
            'market_cap': float(market_cap),
            'type': stock_type
        }
    except Exception as e:
        print(f"Error fetching {symbol}: {str(e)}")
        return None


def filter_and_rank_stocks(min_price, max_price, min_market_cap, taiex_change, otc_change):
    """篩選並排序股票（依指數表現篩選）"""
    stock_data_list = []
    
    # 獲取所有股票數據
    for symbol in TAIWAN_STOCKS:
        data = fetch_stock_data(symbol)
        if data:
            stock_data_list.append(data)
    
    # 先依價格和市值篩選
    filtered = []
    for stock in stock_data_list:
        if min_price <= stock['current_price'] <= max_price:
            if stock['market_cap'] >= min_market_cap:
                filtered.append(stock)
    
    # 分類為上市和上櫃
    listed_stocks = [s for s in filtered if s['type'] == 'LISTED']
    otc_stocks = [s for s in filtered if s['type'] == 'OTC']
    
    # 篩選出優於大盤的股票
    listed_outperformers = [s for s in listed_stocks if s['daily_change_pct'] > taiex_change]
    otc_outperformers = [s for s in otc_stocks if s['daily_change_pct'] > otc_change]
    
    # 排序（依漲幅由高到低）
    listed_sorted = sorted(listed_stocks, key=lambda x: x['daily_change_pct'], reverse=True)
    otc_sorted = sorted(otc_stocks, key=lambda x: x['daily_change_pct'], reverse=True)
    listed_outperformers_sorted = sorted(listed_outperformers, key=lambda x: x['daily_change_pct'], reverse=True)
    otc_outperformers_sorted = sorted(otc_outperformers, key=lambda x: x['daily_change_pct'], reverse=True)
    
    return {
        'listed': listed_outperformers_sorted,  # 優於大盤的上市股票
        'otc': otc_outperformers_sorted,        # 優於大盤的上櫃股票
        'listed_all': listed_sorted,            # 所有上市股票（依漲幅排序）
        'otc_all': otc_sorted,                  # 所有上櫃股票（依漲幅排序）
        'stats': {
            'total_analyzed': len(stock_data_list),
            'total_filtered': len(filtered),
            'listed_outperformers': len(listed_outperformers),
            'otc_outperformers': len(otc_outperformers)
        }
    }


@app.route('/')
def index():
    """主頁面"""
    return render_template('index.html')


@app.route('/api/screen', methods=['POST'])
def screen_stocks():
    """股票篩選 API（含指數比較）"""
    try:
        data = request.get_json()
        
        # 驗證輸入
        min_price = float(data.get('min_price', 50))
        max_price = float(data.get('max_price', 200))
        min_market_cap_billion = float(data.get('min_market_cap', 100))
        enable_market_cap = data.get('enable_market_cap', True)
        
        if min_price <= 0 or max_price <= 0:
            return jsonify({'error': '股價必須大於 0'}), 400
        
        if min_price >= max_price:
            return jsonify({'error': '最高股價必須大於最低股價'}), 400
        
        # 轉換市值為台幣（如果啟用市值篩選）
        if enable_market_cap:
            min_market_cap = min_market_cap_billion * 100_000_000
        else:
            min_market_cap = 0  # 不限制市值
        
        # 獲取指數數據
        print("正在獲取指數數據...")
        taiex_data = fetch_index_data('^TWII', '加權指數')
        otc_data = fetch_index_data('^TWOII', '上櫃指數')  # 使用 ^TWOII 作為上櫃指數
        
        # 如果無法獲取指數，使用預設值 0
        taiex_change = taiex_data['change_pct'] if taiex_data else 0
        otc_change = otc_data['change_pct'] if otc_data else 0
        
        # 篩選股票
        print("正在篩選股票...")
        results = filter_and_rank_stocks(min_price, max_price, min_market_cap, taiex_change, otc_change)
        
        return jsonify({
            'success': True,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'indices': {
                'taiex': taiex_data if taiex_data else {'name': '加權指數', 'value': 0, 'change_pct': 0},
                'otc': otc_data if otc_data else {'name': '上櫃指數', 'value': 0, 'change_pct': 0}
            },
            'filters': {
                'min_price': min_price,
                'max_price': max_price,
                'min_market_cap': min_market_cap,
                'min_market_cap_billion': min_market_cap_billion if enable_market_cap else 0,
                'enable_market_cap': enable_market_cap
            },
            'stats': results['stats'],
            'listed_stocks': results['listed'],
            'otc_stocks': results['otc'],
            'listed_all': results['listed_all'],  # 所有上市股票排名
            'otc_all': results['otc_all']          # 所有上櫃股票排名
        })
        
    except ValueError as e:
        return jsonify({'error': f'無效的數值: {str(e)}'}), 400
    except Exception as e:
        return jsonify({'error': f'伺服器錯誤: {str(e)}'}), 500


if __name__ == '__main__':
    print("\n" + "="*80)
    print("🚀 台股強勢股篩選器 Web 介面")
    print("="*80)
    print(f"📱 請在瀏覽器開啟: http://localhost:5000")
    print(f"⏹️  按 Ctrl+C 停止伺服器")
    print("="*80 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
