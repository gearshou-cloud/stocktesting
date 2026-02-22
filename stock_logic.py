import json
import os
import yfinance as yf
import pandas as pd
import requests as req
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

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

def fetch_index_data(symbol, name):
    """抓取指數資料"""
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period='5d')
        if len(hist) == 0:
            return {'name': name, 'value': 0, 'change_pct': 0}
        latest = hist.iloc[-1]
        current_value = latest['Close']
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
    """核心過濾邏輯"""
    database = load_stock_database()
    if not database:
        return {'error': '資料庫不存在'}
    
    all_stocks = database['stocks']
    min_volume_shares = min_volume_lots * 1000
    
    filtered = []
    for stock in all_stocks:
        if min_price <= stock['price'] <= max_price:
            if stock['market_cap'] >= min_market_cap:
                if stock['volume'] >= min_volume_shares:
                    if gap_up_only and 'open' in stock:
                        prev_close = stock['price'] / (1 + stock['change_pct']/100)
                        if stock['open'] > prev_close:
                            filtered.append(stock)
                    elif not gap_up_only:
                        filtered.append(stock)
    
    listed_out = [s for s in filtered if s['market'] == 'LISTED' and s['change_pct'] > taiex_change]
    otc_out = [s for s in filtered if s['market'] == 'OTC' and s['change_pct'] > otc_change]
    
    listed_sorted = sorted([s for s in filtered if s['market'] == 'LISTED'], key=lambda x: x['change_pct'], reverse=True)
    otc_sorted = sorted([s for s in filtered if s['market'] == 'OTC'], key=lambda x: x['change_pct'], reverse=True)
    
    return {
        'listed': sorted(listed_out, key=lambda x: x['change_pct'], reverse=True),
        'otc': sorted(otc_out, key=lambda x: x['change_pct'], reverse=True),
        'listed_all': listed_sorted,
        'otc_all': otc_sorted,
        'update_time': database.get('update_time', 'Unknown')
    }

def calculate_technicals(hist):
    """計算技術指標"""
    try:
        hist['MA5'] = hist['Close'].rolling(window=5).mean()
        hist['MA20'] = hist['Close'].rolling(window=20).mean()
        delta = hist['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        hist['RSI'] = 100 - (100 / (1 + rs))
        return hist
    except Exception as e:
        print(f"指標計算錯誤: {e}")
        return hist

def calc_high_days(hist):
    """計算強勢天數"""
    if len(hist) < 2: return False, '', 0
    last_idx = -1
    ref_price = hist['Close'].iloc[last_idx]
    if pd.isna(ref_price) or ref_price <= 0:
        if len(hist) < 3: return False, '', 0
        last_idx = -2
        ref_price = hist['Close'].iloc[last_idx]
    
    prev_data = hist.iloc[:last_idx][::-1] 
    count = 0
    for idx, row in prev_data.iterrows():
        p_high = max(row['Open'], row['Close'])
        if ref_price >= (p_high - 0.001): count += 1
        else: break
    
    is_strong = (count >= 1)
    status_icon = "🔥" if count >= 3 else "📈"
    return is_strong, f"{status_icon} 連續守住 {count} 日實體高點", count

def get_ai_recommendations_internal(min_price=10.0, max_price=1000.0, min_volume=2000):
    """智慧推薦邏輯"""
    taiex = fetch_index_data('^TWII', 'TAIEX')
    otc = fetch_index_data('^TWOII', 'OTC')
    base = filter_and_rank_stocks(min_price, max_price, 0, min_volume, False, taiex['change_pct'], otc['change_pct'])
    
    if 'error' in base: return base
    candidates = base['listed'] + base['otc']
    for s in candidates:
        idx_chg = taiex['change_pct'] if s['market'] == 'LISTED' else otc['change_pct']
        s['alpha'] = s['change_pct'] - idx_chg

    candidates.sort(key=lambda x: x['alpha'], reverse=True)
    top_candidates = candidates[:30]
    
    recommends = []
    for stock in top_candidates:
        try:
            symbol = f"{stock['code']}.TW" if stock['market'] == 'LISTED' else f"{stock['code']}.TWO"
            hist = yf.Ticker(symbol).history(period='45d')
            if len(hist) < 25: continue
            hist = calculate_technicals(hist)
            latest = hist.iloc[-1]
            is_strong, label, count = calc_high_days(hist)
            
            score = 2
            reasons = [f"Alpha: {stock['alpha']:+.2f}%"]
            if count >= 3: score += 5; reasons.append(f"強勢連{count}日")
            elif count >= 1: score += 2; reasons.append(f"轉強{count}日")
            
            if latest['Close'] > latest['MA5'] > latest['MA20']: score += 3; reasons.append("均線多頭")
            if 55 <= latest['RSI'] <= 80: score += 2; reasons.append("RSI強勢")
            
            if score >= 5:
                recommends.append({**stock, 'reasons': reasons, 'score': score, 'price': round(latest['Close'], 2)})
        except: continue
        
    recommends.sort(key=lambda x: x['score'], reverse=True)
    return {'success': True, 'recommendations': recommends}
