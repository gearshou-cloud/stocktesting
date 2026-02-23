from flask import Flask, request, jsonify, render_template, abort
from flask_cors import CORS
from datetime import datetime, timedelta
import json
import os
import yfinance as yf
import pandas as pd
import requests as req
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv

# LINE Bot SDK
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

# 任務排程
from flask_apscheduler import APScheduler

# 載入開發環境變數 (.env)
load_dotenv()

app = Flask(__name__)
CORS(app)

# LINE Bot 設定
LINE_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
LINE_SECRET = os.getenv('LINE_CHANNEL_SECRET')
LINE_USER_ID = os.getenv('LINE_USER_ID') # 定時推播的對象

line_bot_api = LineBotApi(LINE_ACCESS_TOKEN) if LINE_ACCESS_TOKEN else None
handler = WebhookHandler(LINE_SECRET) if LINE_SECRET else None

# 排程器設定
class Config:
    SCHEDULER_API_ENABLED = True

app.config.from_object(Config())
scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()

# 股票資料庫檔案
DATABASE_FILE = 'stock_database.json'

def load_stock_database():
    """載入股票資料庫"""
    if not os.path.exists(DATABASE_FILE):
        return None
    
    try:
        with open(DATABASE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"載入資料庫失敗: {e}")
        return None

_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
    'Accept': 'application/json, text/javascript, */*',
    'Referer': 'https://www.twse.com.tw/',
}

def _parse_num(s):
    """把 '1,234,567' 或 '-234' 轉為 int"""
    try:
        return int(str(s).replace(',', '').replace(' ', '') or '0')
    except:
        return 0

def _recent_trading_dates(n=3):
    """取得最近 n 個可能的交易日（YYYYMMDD 字串，不含週末）"""
    dates = []
    d = datetime.now()
    for _ in range(n * 2 + 10):      # 擴大搜尋範圍，確保能抓到足夠天數
        if d.weekday() < 5:          # 週一~週五
            dates.append(d.strftime('%Y%m%d'))
        d -= timedelta(days=1)
        if len(dates) >= n:
            break
    return dates

def fetch_institutional_data(code, market):
    """抓取最新一筆三大法人資料（嘗試最近幾個交易日）"""
    for date_str in _recent_trading_dates(3):
        try:
            result = (_fetch_twse_institutional if market == 'LISTED'
                      else _fetch_tpex_institutional)(code, date_str)
            if result:
                return result
        except Exception as e:
            print(f"[三大法人] {date_str} 抓取失敗: {e}")
    return None


def fetch_institutional_history(code, market, n_days=30):
    """
    平行抓取最近 n_days 個交易日的三大法人資料。
    回傳按日期舊→新排序的 list。
    """
    dates = _recent_trading_dates(n_days)
    print(f"[歷史法人] 開始抓取 {code} ({market}) 最近 {n_days} 天資料: {dates[0]} ~ {dates[-1]}")

    def _fetch_one(date_str):
        try:
            fn = _fetch_twse_institutional if market == 'LISTED' else _fetch_tpex_institutional
            res = fn(code, date_str)
            if res:
                print(f"  - {date_str}: OK")
            return (date_str, res)
        except Exception as e:
            print(f"  - {date_str}: 失敗 ({e})")
            return (date_str, None)

    with ThreadPoolExecutor(max_workers=10) as ex:
        pairs = list(ex.map(_fetch_one, dates))

    # 過濾 None，按日期排序（舊→新）
    valid = [(d, r) for d, r in pairs if r is not None]
    print(f"[歷史法人] 抓取完成, 成功 {len(valid)}/{len(dates)} 筆")
    valid.sort(key=lambda x: x[0])
    return [r for _, r in valid]


def _fetch_twse_institutional(code, date_str):
    """從 TWSE T86 取得上市股票三大法人資料"""
    url = (
        f"https://www.twse.com.tw/rwd/zh/fund/T86"
        f"?date={date_str}&response=json&selectType=ALLBUT0999"
    )
    resp = req.get(url, headers=_HEADERS, timeout=15, verify=False)
    data = resp.json()

    if data.get('stat') != 'OK' or 'data' not in data:
        return None

    fields = data.get('fields', [])
    for row in data['data']:
        if str(row[0]).strip() == str(code).strip():
            return _build_institutional_result(fields, row, date_str)
    return None


def _fetch_tpex_institutional(code, date_str):
    """從 TPEX 取得上櫃股票三大法人資料"""
    d_fmt = f"{date_str[:4]}/{date_str[4:6]}/{date_str[6:]}"
    url = (
        f"https://www.tpex.org.tw/web/stock/3insti/daily_trade/"
        f"3itrade_hedge_result.php?l=zh-tw&o=json&se=EW&t=D&d={d_fmt}"
    )
    resp = req.get(url, headers={**_HEADERS, 'Referer': 'https://www.tpex.org.tw/'}, timeout=15, verify=False)
    data = resp.json()

    rows = data.get('aaData') or data.get('data', [])
    for row in rows:
        if str(row[0]).strip() == str(code).strip():
            # TPEX 欄位順序：代號,名稱,外資買,外資賣,外資超,投信買,投信賣,投信超,自營買,自營賣,自營超,合計超
            return {
                'date':         f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}",
                'foreign_buy':  _parse_num(row[2]),
                'foreign_sell': _parse_num(row[3]),
                'foreign_net':  _parse_num(row[4]),
                'trust_buy':    _parse_num(row[5]),
                'trust_sell':   _parse_num(row[6]),
                'trust_net':    _parse_num(row[7]),
                'dealer_buy':   _parse_num(row[8]),
                'dealer_sell':  _parse_num(row[9]),
                'dealer_net':   _parse_num(row[10]),
                'total_net':    _parse_num(row[11]),
            }
    return None


def _build_institutional_result(fields, row, date_str):
    """從 TWSE T86 欄位對應資料"""
    mapping = {
        '外陸資買進股數':   'foreign_buy',
        '外陸資賣出股數':   'foreign_sell',
        '外陸資買賣超股數': 'foreign_net',
        '投信買進股數':     'trust_buy',
        '投信賣出股數':     'trust_sell',
        '投信買賣超股數':   'trust_net',
        '自營商買賣超股數': 'dealer_net',
        '三大法人買賣超股數':'total_net',
    }
    result = {'date': f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"}
    for i, field in enumerate(fields):
        key = mapping.get(field)
        if key:
            result[key] = _parse_num(row[i])
    # 自營商買進/賣出 TWSE T86 沒有分開提供，標記為 None
    result.setdefault('foreign_buy', 0)
    result.setdefault('foreign_sell', 0)
    result.setdefault('trust_buy', 0)
    result.setdefault('trust_sell', 0)
    result.setdefault('dealer_buy', None)
    result.setdefault('dealer_sell', None)
    result.setdefault('dealer_net', 0)
    result.setdefault('total_net', 0)
    return result


def fetch_index_data(symbol, name):
    """抓取指數資料"""
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period='5d')
        
        if len(hist) == 0:
            return {'name': name, 'value': 0, 'change_pct': 0}
        
        latest = hist.iloc[-1]
        current_value = latest['Close']
        
        # 計算漲跌幅
        if len(hist) >= 2:
            prev_close = hist.iloc[-2]['Close']
            change_pct = ((current_value - prev_close) / prev_close) * 100
        else:
            change_pct = 0
            
        return {
            'name': name,
            'value': round(current_value, 2),
            'change_pct': round(change_pct, 2)
        }
    except Exception as e:
        print(f"抓取指數失敗: {e}")
        return {'name': name, 'value': 0, 'change_pct': 0}

def filter_and_rank_stocks(min_price, max_price, min_market_cap, min_volume_lots, gap_up_only=False, taiex_change=0, otc_change=0):
    """從資料庫篩選並排序股票"""
    database = load_stock_database()
    
    if not database:
        return {
            'error': '股票資料庫不存在，請先執行 update_stock_database.py',
            'listed': [],
            'otc': [],
            'listed_all': [],
            'otc_all': [],
            'stats': {
                'total_analyzed': 0,
                'total_filtered': 0,
                'listed_outperformers': 0,
                'otc_outperformers': 0
            }
        }
    
    all_stocks = database['stocks']
    min_volume_shares = min_volume_lots * 1000  # 轉換「張」為「股」
    
    # 篩選：價格範圍、市值、成交量、開高
    filtered = []
    for stock in all_stocks:
        if min_price <= stock['price'] <= max_price:
            if stock['market_cap'] >= min_market_cap:
                if stock['volume'] >= min_volume_shares:
                    # 開高篩選 (Open > Prev Close)
                    if gap_up_only:
                        # 計算昨收 = 現價 / (1 + 漲跌幅/100)
                        prev_close = stock['price'] / (1 + stock['change_pct']/100)
                        
                        # 如果資料庫有 'open' 欄位則直接用，否則略過
                        if 'open' in stock:
                            if stock['open'] > prev_close:
                                filtered.append(stock)
                        else:
                            # 舊資料沒有 open 欄位，無法判斷，或者視為不符合
                            pass
                    else:
                        filtered.append(stock)
    
    # 分類為上市和上櫃
    listed_stocks = [s for s in filtered if s['market'] == 'LISTED']
    otc_stocks = [s for s in filtered if s['market'] == 'OTC']
    
    # 篩選優於大盤的股票
    listed_outperformers = [s for s in listed_stocks if s['change_pct'] > taiex_change]
    otc_outperformers = [s for s in otc_stocks if s['change_pct'] > otc_change]
    
    # 排序（依漲幅由高到低）
    listed_sorted = sorted(listed_stocks, key=lambda x: x['change_pct'], reverse=True)
    otc_sorted = sorted(otc_stocks, key=lambda x: x['change_pct'], reverse=True)
    listed_outperformers_sorted = sorted(listed_outperformers, key=lambda x: x['change_pct'], reverse=True)
    otc_outperformers_sorted = sorted(otc_outperformers, key=lambda x: x['change_pct'], reverse=True)
    
    return {
        'listed': listed_outperformers_sorted,  # 優於大盤的上市股票
        'otc': otc_outperformers_sorted,        # 優於大盤的上櫃股票
        'listed_all': listed_sorted,            # 所有上市股票（依漲幅排序）
        'otc_all': otc_sorted,                  # 所有上櫃股票（依漲幅排序）
        'stats': {
            'total_analyzed': len(all_stocks),
            'total_filtered': len(filtered),
            'listed_outperformers': len(listed_outperformers),
            'otc_outperformers': len(otc_outperformers),
            'update_time': database.get('update_time', 'Unknown')
        }
    }

def fetch_realtime_prices(stocks):
    """使用多執行緒抓取這組股票的即時價格"""
    def _fetch_one(s):
        try:
            suffix = '.TW' if s['market'] == 'LISTED' else '.TWO'
            symbol = f"{s['code']}{suffix}"
            t = yf.Ticker(symbol)
            # 抓取最近 1 天的 1 分鐘資料，取得最後一筆即時交易
            hist = t.history(period='1d', interval='1m')
            if not hist.empty:
                latest = hist.iloc[-1]
                # 從 Yahoo 資料抓取昨日收盤 (用於計算即時漲跌幅)
                prev_close = t.info.get('previousClose', s['price'] / (1 + s['change_pct']/100))
                current_price = round(latest['Close'], 2)
                change_pct = round(((current_price - prev_close) / prev_close) * 100, 2)
                return {
                    'code': s['code'],
                    'price': current_price,
                    'change_pct': change_pct,
                    'volume': int(latest['Volume']) if 'Volume' in latest else s['volume']
                }
        except:
            pass
        return None

    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(_fetch_one, stocks))
    
    # 建立映射表
    realtime_map = {r['code']: r for r in results if r}
    for s in stocks:
        if s['code'] in realtime_map:
            s['price'] = realtime_map[s['code']]['price']
            s['change_pct'] = realtime_map[s['code']]['change_pct']
            # 選項：如果需要成交量也同步，可以放開
            # s['volume'] = realtime_map[s['code']]['volume']
    return stocks

@app.route('/')
def index():
    return render_template('index_v2.html')

@app.route('/api/screen', methods=['POST'])
def screen_stocks():
    """股票篩選 API（含即時價格同步）"""
    try:
        data = request.get_json()
        min_price = float(data.get('min_price', 10))
        max_price = float(data.get('max_price', 1000))
        min_market_cap_billion = float(data.get('min_market_cap', 0))
        min_volume_lots = float(data.get('min_volume', 1000))
        enable_market_cap = data.get('enable_market_cap', False)
        gap_up_only = data.get('gap_up_only', False)

        min_market_cap = min_market_cap_billion * 100_000_000 if enable_market_cap else 0
        
        taiex_data = fetch_index_data('^TWII', '加權指數')
        otc_data = fetch_index_data('^TWOII', '上櫃指數')
        
        results = filter_and_rank_stocks(
            min_price, max_price, min_market_cap, min_volume_lots,
            gap_up_only, taiex_data['change_pct'], otc_data['change_pct']
        )
        
        if 'error' in results:
            return jsonify({'error': results['error']}), 500
        
        # --- 即時化關鍵步驟：校準前 30 名的價格 ---
        top_candidates = results['listed'][:15] + results['otc'][:15]
        if top_candidates:
            print(f"正在對 {len(top_candidates)} 檔候選股進行即時價格校準...")
            fetch_realtime_prices(top_candidates)

        def format_stock(s, type_name):
            return {
                'symbol': f"{s['code']}.TW",
                'name': s['name'],
                'current_price': s['price'],
                'daily_change_pct': s['change_pct'],
                'volume': s['volume'],
                'market_cap': s['market_cap'],
                'type': type_name,
                'market': s['market']
            }

        listed_stocks = [format_stock(s, 'LISTED') for s in results['listed']]
        otc_stocks = [format_stock(s, 'OTC') for s in results['otc']]
        
        return jsonify({
            'success': True,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'database_update_time': results['stats']['update_time'],
            'listed_stocks': listed_stocks,
            'otc_stocks': otc_stocks,
            'indices': {'taiex': taiex_data, 'otc': otc_data}
        })
        
    except ValueError as e:
        return jsonify({'error': f'無效的數值: {str(e)}'}), 400
    except Exception as e:
        return jsonify({'error': f'伺服器錯誤: {str(e)}'}), 500

@app.route('/api/search', methods=['GET'])
def search_stock():
    """股票搜尋 API（包含歷史資料用於圖表）"""
    try:
        query = request.args.get('q', '').strip()
        
        if not query:
            return jsonify({'error': '請輸入搜尋關鍵字'}), 400
        
        database = load_stock_database()
        
        if not database:
            return jsonify({'error': '資料庫不存在'}), 500
        
        all_stocks = database['stocks']
        
        # 搜尋：代碼或名稱包含關鍵字
        results = []
        for stock in all_stocks:
            if query.lower() in stock['code'].lower() or query in stock['name']:
                results.append(stock)
        
        # 限制結果數量
        results = results[:10]
        
        # 為每支股票抓取歷史資料（用於 K 線圖）
        enhanced_results = []
        for stock in results:
            try:
                # 上市用 .TW，上櫃用 .TWO
                suffix = '.TW' if stock['market'] == 'LISTED' else '.TWO'
                symbol = f"{stock['code']}{suffix}"
                ticker = yf.Ticker(symbol)
                
                # 抓取最近 60 天的日K資料
                hist_daily = ticker.history(period='60d', interval='1d')
                
                # 抓取最近 7 天的5分K資料
                hist_5min = ticker.history(period='7d', interval='5m')
                
                # 轉換日K資料（用於前端互動圖表）
                chart_data_daily = []
                volume_data_daily = []
                for date, row in hist_daily.iterrows():
                    # TradingView Lightweight Charts 接受 YYYY-MM-DD 字符串
                    chart_data_daily.append({
                        'time': date.strftime('%Y-%m-%d'),
                        'open': round(row['Open'], 2),
                        'high': round(row['High'], 2),
                        'low': round(row['Low'], 2),
                        'close': round(row['Close'], 2)
                    })
                    volume_data_daily.append({
                        'time': date.strftime('%Y-%m-%d'),
                        'value': int(row['Volume']),
                        'color': '#ef5350' if row['Close'] >= row['Open'] else '#26a69a'
                    })
                
                # 轉換5分K資料（用於前端互動圖表）
                chart_data_5min = []
                volume_data_5min = []
                # TradingView 對日內圖表需要 Unix Timestamp (秒)
                for date, row in hist_5min.iterrows():
                    timestamp = int(date.timestamp())
                    # 修正時區問題，yfinance 返回的是 UTC 時間，需要轉換為本地時間（如果需要顯示正確的小時）
                    # 這裡假設已經是本地時間，或者前端處理
                    # 為了保險，加上 8 小時（28800秒）如果是 UTC
                    # yfinance history 通常帶有 tz info
                    
                    chart_data_5min.append({
                        'time': timestamp,
                        'open': round(row['Open'], 2),
                        'high': round(row['High'], 2),
                        'low': round(row['Low'], 2),
                        'close': round(row['Close'], 2)
                    })
                    volume_data_5min.append({
                        'time': timestamp,
                        'value': int(row['Volume']),
                        'color': '#ef5350' if row['Close'] >= row['Open'] else '#26a69a'
                    })
                
                # 獲取籌碼資訊
                info = ticker.info
                institutional_holders = None
                try:
                    holders = ticker.institutional_holders
                    if holders is not None and not holders.empty:
                        institutional_holders = holders.head(5).to_dict('records')
                except:
                    pass
                
                enhanced_stock = {
                    **stock,
                    'chart_data_daily': chart_data_daily,
                    'volume_data_daily': volume_data_daily,
                    'chart_data_5min': chart_data_5min,
                    'volume_data_5min': volume_data_5min,
                    'institutional_holders': institutional_holders,
                    'shares_outstanding': info.get('sharesOutstanding', 0),
                    'float_shares': info.get('floatShares', 0),
                    'institutional_history': fetch_institutional_history(stock['code'], stock['market'], n_days=60)
                }
                enhanced_results.append(enhanced_stock)
            except Exception as e:
                print(f"抓取 {stock['code']} 歷史資料失敗: {e}")
                # 如果失敗，仍然返回基本資料
                enhanced_results.append(stock)
        
        return jsonify({
            'success': True,
            'query': query,
            'count': len(enhanced_results),
            'results': enhanced_results
        })
        
    except Exception as e:
        return jsonify({'error': f'搜尋失敗: {str(e)}'}), 500

# 技術分析函數
def calculate_technicals(hist):
    try:
        # 計算 MA (移動平均線)
        hist['MA5'] = hist['Close'].rolling(window=5).mean()
        hist['MA20'] = hist['Close'].rolling(window=20).mean()
        
        # 計算 RSI (相對強弱指標)
        delta = hist['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        hist['RSI'] = 100 - (100 / (1 + rs))
        
        return hist
    except Exception as e:
        print(f"計算技術指標失敗: {e}")
        return hist

def get_ai_recommendations_internal(min_price=10.0, max_price=1000.0, min_volume=2000):
    """核心推薦邏輯 - 供 API 與 LINE Bot 共用"""
    try:
        # 1. 取得大盤基準
        taiex = fetch_index_data('^TWII',  '加權指數')
        otc   = fetch_index_data('^TWOII', '上櫃指數')
        
        # 2. 篩選優於大盤的基本股池
        base = filter_and_rank_stocks(
            min_price=min_price,
            max_price=max_price,
            min_market_cap=0,
            min_volume_lots=min_volume,
            gap_up_only=False,
            taiex_change=taiex['change_pct'],
            otc_change=otc['change_pct']
        )
        
        if 'error' in base:
            return {'error': base['error']}
            
        candidates = base['listed'] + base['otc']
        
        # 計算與大盤的差距 (Alpha)，依 Alpha 排序取前 30 檔
        for s in candidates:
            idx_chg = taiex['change_pct'] if s['market'] == 'LISTED' else otc['change_pct']
            s['alpha'] = s['change_pct'] - idx_chg

        candidates.sort(key=lambda x: x['alpha'], reverse=True)
        top_candidates = candidates[:30]
        
        recommendations = []
        print(f"[智慧推薦] 從 {len(candidates)} 檔優於大盤股票中分析前 {len(top_candidates)} 檔...")
        
        for stock in top_candidates:
            try:
                suffix = '.TW' if stock['market'] == 'LISTED' else '.TWO'
                symbol = f"{stock['code']}{suffix}"
                
                # 抓取歷史數據
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period='45d')
                
                if len(hist) < 25:
                    continue
                    
                hist = calculate_technicals(hist)
                latest = hist.iloc[-1]
                
                # --- 即時資訊修正 ---
                # 用 Yahoo Finance 的實時數據更新，算出最精準的今日漲幅
                prev_close = ticker.info.get('previousClose', stock['price'] / (1 + stock['change_pct']/100))
                current_price = round(latest['Close'], 2)
                current_change = round(((current_price - prev_close) / prev_close) * 100, 2)
                current_alpha = current_change - (taiex['change_pct'] if stock['market'] == 'LISTED' else otc['change_pct'])

                is_strong, strong_label, strong_count = calc_high_days(hist)
                
                price = current_price
                ma5 = latest['MA5']
                ma20 = latest['MA20']
                rsi = latest['RSI']
                
                reasons = [f"跑贏大盤 ({current_alpha:+.2f}%)"]
                score = 2
                
                # 評分邏輯 (加分制)
                if strong_count >= 3:
                    score += 5
                    reasons.append(strong_label)
                elif strong_count >= 1:
                    score += 2
                    reasons.append(strong_label)
                
                if price > ma5 > ma20:
                    score += 3
                    reasons.append("均線多頭排列")
                
                if 55 <= rsi <= 80:
                    score += 2
                    reasons.append(f"RSI強勢範疇 ({rsi:.1f})")
                
                if score >= 5:
                    recommendations.append({
                        'code': stock['code'],
                        'name': stock['name'],
                        'price': price,
                        'change_pct': current_change,
                        'alpha': current_alpha,
                        'volume': stock['volume'],
                        'market': stock['market'],
                        'score': score,
                        'reasons': reasons
                    })
                    
            except Exception as e:
                print(f"[智慧推薦] 分析 {stock['code']} 失敗: {e}")
                continue
        
        recommendations.sort(key=lambda x: x['score'], reverse=True)
        return {'success': True, 'recommendations': recommendations}
        
    except Exception as e:
        return {'error': str(e)}

@app.route('/api/recommend', methods=['POST'])
def smart_recommend():
    """智慧推薦 API"""
    data = request.get_json() or {}
    min_price = float(data.get('min_price', 10.0))
    max_price = float(data.get('max_price', 1000.0))
    min_volume = float(data.get('min_volume', 2000))
    
    result = get_ai_recommendations_internal(min_price, max_price, min_volume)
    if 'error' in result:
        return jsonify({'error': result['error']}), 500
    return jsonify(result)

# ── LINE Bot 路由與功能 ──────────────────────────────

@app.route("/callback", methods=['POST'])
def callback():
    # 取得 LINE 的簽名
    signature = request.headers['X-Line-Signature']
    # 取得請求內容
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    msg_text = event.message.text
    user_id = event.source.user_id
    
    if "推薦" in msg_text or "選股" in msg_text:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="🚀 正在為您分析今日強勢標的，請稍候..."))
        result = get_ai_recommendations_internal()
        if result.get('success'):
            stocks = result['recommendations'][:5]
            reply = "🤖 AI 今日推薦強勢股：\n"
            for s in stocks:
                reply += f"\n📌 {s['code']} {s['name']}\n價：{s['price']} ({s['change_pct']}%)\n關鍵：{', '.join(s['reasons'][:2])}\n"
            line_bot_api.push_message(user_id, TextSendMessage(text=reply))
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="抱歉，分析時發生錯誤。"))
    elif "ID" in msg_text.upper():
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"您的 LINE User ID 是：\n{user_id}\n請將此 ID 填入雲端的環境變數中。"))

# ── 定時推播任務 (12:50) ──────────────────────────────

@scheduler.task('cron', id='daily_push', hour=12, minute=50)
def daily_push_job():
    print("[排程任務] 執行每日 12:50 推播...")
    if not LINE_ACCESS_TOKEN or not LINE_USER_ID:
        print("[排程任務] 錯誤：缺少 LINE Token 或 User ID")
        return

    result = get_ai_recommendations_internal(min_price=15.0, min_volume=2500)
    if result.get('success'):
        stocks = result['recommendations'][:8] # 取前 8 檔
        if not stocks:
            return
            
        msg = f"🔔 【每日強勢股推播】 {datetime.now().strftime('%Y-%m-%d')}\n"
        msg += "AI 已為您篩選出今日表現最優異且站穩實體高點的標的：\n"
        
        for i, s in enumerate(stocks, 1):
            msg += f"\n{i}. {s['code']} {s['name']}\n"
            msg += f"   💰 價格: {s['price']} ({s['change_pct']}%)\n"
            msg += f"   ⭐ 評分: {s['score']} | {s['reasons'][1] if len(s['reasons'])>1 else s['reasons'][0]}\n"
        
        msg += "\n⚠️ 以上僅供參考，投資請謹慎評估風險。"
        line_bot_api.push_message(LINE_USER_ID, TextSendMessage(text=msg))
        print(f"[排程任務] 已推播至 {LINE_USER_ID}")

# ─────────────────────────────────────────────


# ─────────────────────────────────────────────
#  強勢選股 技術條件引擎（可擴展）
# ─────────────────────────────────────────────

def calc_high_days(hist):
    """
    計算目前價格 高於 連續前幾個交易日「實體 K 棒高點」的天數
    紅 K 取收盤價，綠 K 取開盤價。
    """
    if len(hist) < 2:
        return False, '', 0
    
    # 決定參考價格基準（今日或延遲的最後一筆有效收盤）
    last_idx = -1
    ref_price = hist['Close'].iloc[last_idx]
    
    if pd.isna(ref_price) or ref_price <= 0:
        if len(hist) < 3:
            return False, '', 0
        last_idx = -2
        ref_price = hist['Close'].iloc[last_idx]
    
    ref_date = hist.index[last_idx].strftime('%Y-%m-%d')
    
    # 從參考點往前找
    prev_data = hist.iloc[:last_idx][::-1] 
    
    count = 0
    # print(f"  [DEBUG] {ref_date} ref_price: {ref_price:.2f}")
    for idx, row in prev_data.iterrows():
        p_open = row.get('Open', 0)
        p_close = row.get('Close', 0)
        
        if pd.isna(p_open) or pd.isna(p_close) or p_open <= 0 or p_close <= 0:
            break
            
        # 紅 K 取收盤，綠 K 取開盤 -> 即實體 K 棒的高點 max(Open, Close)
        body_high = max(p_open, p_close)
        
        # 判斷參考價是否高於該日實體高點
        if ref_price >= (body_high - 0.001): 
            count += 1
        else:
            # print(f"    - Fail at {idx.strftime('%Y-%m-%d')}: body_high {body_high:.2f} > ref {ref_price:.2f}")
            break
    
    is_strong = (count >= 1)
    status_icon = "🔥" if count >= 3 else "📈"
    label = f"{status_icon} 連續高過前 {count} 日實體高點 (基準:{ref_date})"
    
    return is_strong, label, count


# ── 新增技術條件請在此 list 加一個 tuple: (check_fn, kwargs) ──
TECH_CONDITIONS = [
    (calc_high_days, {}),
]


def run_tech_conditions(hist):
    """
    對一支股票跑所有技術條件，回傳 (passed: bool, reasons: list, score: int)
    """
    reasons = []
    total_score = 0
    all_ok = True

    for fn, kwargs in TECH_CONDITIONS:
        ok, label, score = fn(hist, **kwargs)
        if ok:
            reasons.append(label)
            total_score += score
        else:
            all_ok = False
            
    return all_ok, reasons, total_score


@app.route('/api/strong', methods=['POST'])
def strong_stocks():
    """
    強勢選股 API
    1. 用和 /api/screen 相同的基礎篩選取得「優於大盤」候選股
    2. 批次下載 10 天 K 線
    3. 套用所有技術條件（TECH_CONDITIONS）
    4. 回傳符合所有條件的股票清單
    """
    try:
        data = request.get_json() or {}

        # ── 讀取篩選參數（與 /api/screen 一致）──
        min_price           = float(data.get('min_price', 10))
        max_price           = float(data.get('max_price', 1000))
        min_market_cap_bil  = float(data.get('min_market_cap', 0))
        min_volume_lots     = float(data.get('min_volume', 1000))
        enable_market_cap   = data.get('enable_market_cap', False)
        gap_up_only         = data.get('gap_up_only', False)

        min_market_cap = min_market_cap_bil * 1e8 if enable_market_cap else 0

        # ── 1. 取得指數漲幅 ──
        taiex = fetch_index_data('^TWII',  '加權指數')
        otc   = fetch_index_data('^TWOII', '上櫃指數')

        # ── 2. 從資料庫取得優於大盤的基礎股池 ──
        base = filter_and_rank_stocks(
            min_price, max_price, min_market_cap, min_volume_lots,
            gap_up_only, taiex['change_pct'], otc['change_pct']
        )
        if 'error' in base:
            return jsonify({'error': base['error']}), 500

        candidates = base['listed'] + base['otc']   # 已經是優於大盤的股票
        
        # --- 即時化關鍵步驟：對強勢選股進行價格校準 ---
        if candidates:
            print(f"[強勢選股] 正在對 {len(candidates)} 檔股票進行即時價格校準...")
            fetch_realtime_prices(candidates)

        print(f"[強勢選股] 候選股數: {len(candidates)}")

        if not candidates:
            return jsonify({'success': True, 'count': 0, 'stocks': [],
                            'indices': {'taiex': taiex, 'otc': otc},
                            'conditions': [c.__name__ if callable(c) else str(c)
                                           for c, _ in TECH_CONDITIONS]})

        # ── 3. 批次下載 10 天 K 線（一次請求全部）──
        symbols = []
        sym_to_stock = {}
        for s in candidates:
            suffix = '.TW' if s['market'] == 'LISTED' else '.TWO'
            sym = f"{s['code']}{suffix}"
            symbols.append(sym)
            sym_to_stock[sym] = s

        print(f"[強勢選股] 批次下載 {len(symbols)} 支 K 線...")
        try:
            raw = yf.download(
                symbols,
                period='45d', # 增加為 45 天，允許更長的高點統計
                interval='1d',
                auto_adjust=True,
                group_by='ticker',
                progress=False,
                threads=True
            )
        except Exception as e:
            return jsonify({'error': f'批次下載失敗: {e}'}), 500

        single = (len(symbols) == 1)

        # ── 4. 套用技術條件 ──
        result_stocks = []
        processed_count = 0
        
        for sym in symbols:
            try:
                hist = raw if single else (raw[sym] if sym in raw.columns.get_level_values(0) else None)
                if hist is None:
                    continue
                hist = hist.dropna(how='all')
                if len(hist) < 2:
                    continue

                processed_count += 1
                passed, reasons, score = run_tech_conditions(hist)
                
                if passed:
                    s = sym_to_stock[sym]
                    result_stocks.append({
                        'code':       s['code'],
                        'name':       s['name'],
                        'price':      s['price'],
                        'change_pct': s['change_pct'],
                        'volume':     s['volume'],
                        'market':     s['market'],
                        'reasons':    reasons,
                        'score':      score,
                    })
            except Exception as e:
                print(f"[強勢選股] 分析 {sym} 失敗: {e}")
                continue

        # 排序：優先比較分數（天數），天數相同再比較漲幅
        result_stocks.sort(key=lambda x: (x['score'], x['change_pct']), reverse=True)
        print(f"[強勢選股] 處理: {processed_count}/{len(symbols)}, 符合: {len(result_stocks)}")

        return jsonify({
            'success':    True,
            'count':      len(result_stocks),
            'stocks':     result_stocks,
            'indices':    {'taiex': taiex, 'otc': otc},
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5000))
    # 部署到雲端時 host 須為 0.0.0.0 以接受外部連線
    app.run(host='0.0.0.0', port=port)
