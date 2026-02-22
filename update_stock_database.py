"""
台灣股票資料更新腳本 - 高速版（多執行緒 + 批次下載）
速度比舊版快約 10-20 倍
"""
import yfinance as yf
import pandas as pd
from datetime import datetime
import json
import os
import twstock
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

DATABASE_FILE = 'stock_database.json'
MAX_WORKERS = 20        # 同時抓取的執行緒數量
BATCH_SIZE = 50         # 批次下載的股票數量（yf.download 一次最多建議 50-100）

# 執行緒安全的鎖，避免多執行緒同時寫入
print_lock = threading.Lock()
counter_lock = threading.Lock()

def get_all_taiwan_stocks():
    """使用 twstock 取得所有台灣股票清單"""
    print("正在取得台灣股票清單...")
    try:
        listed_stocks = twstock.codes
        stocks = []
        for code, info in listed_stocks.items():
            if info.type == '股票' and code.isdigit() and len(code) == 4:
                market = 'LISTED' if info.market == '上市' else 'OTC'
                stocks.append({'code': code, 'name': info.name, 'market': market})

        listed_count = sum(1 for s in stocks if s['market'] == 'LISTED')
        otc_count    = sum(1 for s in stocks if s['market'] == 'OTC')
        print(f"✅ 取得 {len(stocks)} 支股票（上市 {listed_count}，上櫃 {otc_count}）")
        return stocks
    except Exception as e:
        print(f"❌ 取得股票清單失敗: {e}")
        return []


def batch_download(batch_stocks):
    """
    使用 yf.download() 一次批次下載多支股票的 5 天歷史資料（Open, Close, Volume）。
    回傳 symbol -> {open, close, prev_close, volume} 的 dict。
    """
    suffix_map = {}   # symbol -> stock info
    symbols    = []

    for s in batch_stocks:
        suffix = '.TW' if s['market'] == 'LISTED' else '.TWO'
        sym = f"{s['code']}{suffix}"
        symbols.append(sym)
        suffix_map[sym] = s

    try:
        # auto_adjust=True 會把 Open/Close 還原成還權後的價格
        df = yf.download(
            symbols,
            period='5d',
            interval='1d',
            auto_adjust=True,
            group_by='ticker',
            progress=False,
            threads=True
        )
    except Exception as e:
        return {}

    results = {}
    # 單支股票時 df 的欄位結構不同（沒有 ticker 層）
    single = len(symbols) == 1

    for sym in symbols:
        try:
            if single:
                sub = df
            else:
                sub = df[sym] if sym in df.columns.get_level_values(0) else None

            if sub is None or len(sub) < 2:
                continue

            sub = sub.dropna(how='all')
            if len(sub) < 2:
                continue

            latest    = sub.iloc[-1]
            prev      = sub.iloc[-2]

            close     = float(latest['Close'])
            open_p    = float(latest['Open'])
            prev_close= float(prev['Close'])
            volume    = int(latest['Volume'])

            change_pct = ((close - prev_close) / prev_close) * 100 if prev_close else 0

            results[sym] = {
                'close':      round(close, 2),
                'open':       round(open_p, 2),
                'prev_close': round(prev_close, 2),
                'change_pct': round(change_pct, 2),
                'volume':     volume,
            }
        except Exception:
            continue

    return results, suffix_map


def fetch_market_cap_batch(symbols):
    """
    用多執行緒同時抓取多支股票的市值（ticker.info）。
    回傳 symbol -> market_cap 的 dict。
    """
    caps = {}

    def _get_cap(sym):
        try:
            info = yf.Ticker(sym).fast_info
            # fast_info 比 info 快很多，直接取 market_cap
            mc = getattr(info, 'market_cap', None) or 0
            caps[sym] = int(mc)
        except Exception:
            caps[sym] = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        list(ex.map(_get_cap, symbols))

    return caps


def update_stock_database():
    """更新股票資料庫（高速版）"""
    print("=" * 70)
    print("台灣股票資料庫更新 - 高速版（多執行緒 + 批次下載）")
    print(f"開始時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # 步驟 1：取得清單
    all_list = get_all_taiwan_stocks()
    if not all_list:
        print("❌ 無法取得股票清單")
        return

    total = len(all_list)
    print(f"\n總共需要更新: {total} 支股票")
    print(f"批次大小: {BATCH_SIZE} | 下載執行緒: {MAX_WORKERS}")
    print(f"預估時間: 約 3-8 分鐘（視網路速度而定）")
    print("-" * 70)

    # ----- 批次下載 Open/Close/Volume -----
    all_price_data = {}   # sym -> price dict
    batches = [all_list[i:i+BATCH_SIZE] for i in range(0, total, BATCH_SIZE)]
    n_batches = len(batches)

    print(f"\n[階段 1/2] 批次下載價格資料（共 {n_batches} 批）...")
    start = datetime.now()

    for idx, batch in enumerate(batches, 1):
        result = batch_download(batch)
        if isinstance(result, tuple):
            price_dict, _ = result
            all_price_data.update(price_dict)

        pct = idx / n_batches * 100
        elapsed = (datetime.now() - start).seconds
        eta = int(elapsed / idx * (n_batches - idx)) if idx > 1 else 0
        print(f"  批次 {idx:3d}/{n_batches}  ({pct:5.1f}%)  剩餘約 {eta} 秒", end='\r')

    success_price = len(all_price_data)
    print(f"\n  ✅ 價格資料成功: {success_price} 支（失敗 {total - success_price} 支）")

    # ----- 批次抓取市值（ticker.fast_info，多執行緒）-----
    symbols_with_price = list(all_price_data.keys())
    print(f"\n[階段 2/2] 批次抓取市值（{len(symbols_with_price)} 支，{MAX_WORKERS} 執行緒）...")
    market_caps = fetch_market_cap_batch(symbols_with_price)
    print(f"  ✅ 市值抓取完成")

    # ----- 組合最終資料 -----
    # 建立 code -> stock_info 的雙查表
    code_info_map = {s['code']: s for s in all_list}

    all_stocks = []
    for sym, price in all_price_data.items():
        # sym 格式: "6415.TW" 或 "6415.TWO"
        code = sym.split('.')[0]
        info = code_info_map.get(code)
        if not info:
            continue

        mc = market_caps.get(sym, 0)

        all_stocks.append({
            'code':       code,
            'name':       info['name'],
            'price':      price['close'],
            'open':       price['open'],
            'change_pct': price['change_pct'],
            'volume':     price['volume'],
            'market_cap': mc,
            'market':     info['market'],
        })

    total_time = (datetime.now() - start).seconds
    print(f"\n{'='*70}")
    print(f"完成！耗時: {total_time // 60} 分 {total_time % 60} 秒")
    print(f"成功: {len(all_stocks)} 支 / 總計: {total} 支")

    if not all_stocks:
        print("❌ 沒有成功抓取任何股票資料")
        return

    # ----- 儲存 -----
    database = {
        'update_time':  datetime.now().isoformat(),
        'total_stocks': len(all_stocks),
        'stocks':       all_stocks
    }
    with open(DATABASE_FILE, 'w', encoding='utf-8') as f:
        json.dump(database, f, ensure_ascii=False, indent=2)
    print(f"✅ 資料庫已儲存至: {DATABASE_FILE}")

    df = pd.DataFrame(all_stocks)
    df.to_csv('stock_database.csv', index=False, encoding='utf-8-sig')
    print(f"✅ CSV 已儲存至: stock_database.csv")

    print(f"\n📊 統計：")
    print(f"  價格範圍: {min(s['price'] for s in all_stocks):.2f} ~ {max(s['price'] for s in all_stocks):.2f} 元")
    print(f"  漲幅範圍: {min(s['change_pct'] for s in all_stocks):.2f}% ~ {max(s['change_pct'] for s in all_stocks):.2f}%")
    print(f"完成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)


if __name__ == "__main__":
    update_stock_database()
