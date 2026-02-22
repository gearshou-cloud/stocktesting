# -*- coding: utf-8 -*-
"""
🚀 美股戰情中心 V2.1
全方位股票分析儀表板 - 頁籤式設計
功能：市場狀態、監控雷達、庫存管理、進場觀測、市場獵手
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import json
import os

# --- 頁面設定 ---
st.set_page_config(
    page_title="美股戰情中心 V2.1", 
    layout="wide",
    initial_sidebar_state="collapsed"  # 預設收起側邊欄
)

# --- 自定義 CSS ---
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border-radius: 10px;
        padding: 15px;
        margin: 5px;
        border: 1px solid #0f3460;
        color: white;
    }
    .stock-up { color: #00ff88; }
    .stock-down { color: #ff4757; }
    .stock-neutral { color: #ffa502; }
    .sidebar .sidebar-content { background-color: #1a1a2e; }
    div[data-testid="stMetricValue"] { font-size: 1.5rem; color: white; }
    .watchlist-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
        border: 1px solid #0f3460;
        color: white;
    }
    .watchlist-card h4 {
        color: white !important;
        margin: 0 0 10px 0;
    }
    .watchlist-card p {
        color: white !important;
        margin: 5px 0;
    }
    .analysis-card {
        background: linear-gradient(135deg, #0f0f23 0%, #1a1a2e 100%);
        border-radius: 15px;
        padding: 25px;
        margin: 15px 0;
        border: 1px solid #16213e;
        color: white;
    }
    .analysis-card h3, .analysis-card h4 {
        color: white !important;
    }
    .analysis-card p {
        color: white !important;
    }
    /* 確保所有卡片內的文字都是白色 */
    .watchlist-card *, .analysis-card *, .metric-card * {
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)

# --- 常量定義 ---
DEFAULT_WATCHLIST = ["NVDA", "AAPL", "TSLA", "AMD", "MSFT", "GOOG", "META", "AMZN", "TSM", "AVGO"]
PORTFOLIO_FILE = "portfolio.json"
USAGE_STATS_FILE = "usage_stats.json"

# --- 輔助函數 ---
def get_market_status():
    """獲取市場狀態 (VIX 恐慌指數)"""
    try:
        vix = yf.Ticker("^VIX")
        vix_data = vix.fast_info
        vix_price = vix_data.last_price
        
        # 獲取10年期國債殖利率
        tny = yf.Ticker("^TNX")
        tny_data = tny.fast_info
        yield_rate = tny_data.last_price
        
        # 判斷市場狀態
        if vix_price < 15:
            status = "🟢 晴朗 (Safe)"
            status_class = "safe"
        elif vix_price < 25:
            status = "🟡 警戒 (Caution)"
            status_class = "warning"
        else:
            status = "🔴 恐慌 (Danger)"
            status_class = "danger"
            
        return {
            "vix": vix_price,
            "yield": yield_rate,
            "status": status,
            "status_class": status_class
        }
    except:
        return {
            "vix": 0,
            "yield": 0,
            "status": "⚪ 無法獲取",
            "status_class": "neutral"
        }

@st.cache_data(ttl=300)
def get_stock_data(ticker, period="1y", interval="1d"):
    """獲取股票歷史數據"""
    try:
        data = yf.download(ticker, period=period, interval=interval, progress=False)
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        return data
    except:
        return pd.DataFrame()

def get_realtime_quote(ticker):
    """獲取即時報價 (包含盤後)"""
    try:
        stock = yf.Ticker(ticker)
        info = stock.fast_info
        
        # 基本報價
        current_price = info.last_price
        prev_close = info.previous_close
        change_pct = ((current_price - prev_close) / prev_close) * 100
        volume = info.last_volume
        
        # 嘗試獲取盤後價格
        try:
            full_info = stock.info
            post_price = full_info.get('postMarketPrice', None)
            post_change = full_info.get('postMarketChangePercent', None)
            if post_price and post_change:
                post_change = post_change * 100
        except:
            post_price = None
            post_change = None
        
        return {
            "price": current_price,
            "prev_close": prev_close,
            "change_pct": change_pct,
            "volume": volume,
            "post_price": post_price,
            "post_change": post_change
        }
    except Exception as e:
        return None

def calculate_support_resistance(df, window=20):
    """計算支撐和阻力位"""
    if df.empty or len(df) < window:
        return None, None
    
    recent = df.tail(window)
    support = recent['Low'].min()
    resistance = recent['High'].max()
    return support, resistance

def calculate_rsi(prices, period=14):
    """計算 RSI"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def get_earnings_date(ticker):
    """獲取下次財報日期"""
    try:
        stock = yf.Ticker(ticker)
        calendar = stock.calendar
        if calendar is not None and not calendar.empty:
            if 'Earnings Date' in calendar.index:
                earnings_date = calendar.loc['Earnings Date'].iloc[0]
                if isinstance(earnings_date, pd.Timestamp):
                    return earnings_date
        return None
    except:
        return None

def load_portfolio():
    """載入投資組合"""
    if os.path.exists(PORTFOLIO_FILE):
        try:
            with open(PORTFOLIO_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_portfolio(portfolio):
    """儲存投資組合"""
    with open(PORTFOLIO_FILE, 'w') as f:
        json.dump(portfolio, f, indent=2)

def format_number(num):
    """格式化數字"""
    if num >= 1e9:
        return f"{num/1e9:.2f}B"
    elif num >= 1e6:
        return f"{num/1e6:.2f}M"
    elif num >= 1e3:
        return f"{num/1e3:.2f}K"
    return f"{num:.2f}"

def load_usage_stats():
    """載入使用統計"""
    if os.path.exists(USAGE_STATS_FILE):
        try:
            with open(USAGE_STATS_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_usage_stats(stats):
    """儲存使用統計"""
    with open(USAGE_STATS_FILE, 'w') as f:
        json.dump(stats, f, indent=2)

def record_user_action(action, ticker, details=None):
    """記錄用戶行為"""
    stats = load_usage_stats()

    if action not in stats:
        stats[action] = {}

    if ticker not in stats[action]:
        stats[action][ticker] = {
            "count": 0,
            "last_used": None,
            "details": []
        }

    stats[action][ticker]["count"] += 1
    stats[action][ticker]["last_used"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if details:
        stats[action][ticker]["details"].append({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "info": details
        })

        # 只保留最近的10條記錄
        if len(stats[action][ticker]["details"]) > 10:
            stats[action][ticker]["details"] = stats[action][ticker]["details"][-10:]

    save_usage_stats(stats)
    return stats

def get_smart_watchlist():
    """根據使用統計生成智慧監控清單"""
    stats = load_usage_stats()
    current_list = st.session_state.watchlist.copy()

    # 分析刪除行為
    removed_stocks = {}
    if "remove_stock" in stats:
        for ticker, data in stats["remove_stock"].items():
            if data["count"] > 0:
                removed_stocks[ticker] = data["count"]

    # 分析添加行為
    added_stocks = {}
    if "add_stock" in stats:
        for ticker, data in stats["add_stock"].items():
            if data["count"] > 0:
                added_stocks[ticker] = data["count"]

    # 分析分析行為
    analyzed_stocks = {}
    if "analyze_stock" in stats:
        for ticker, data in stats["analyze_stock"].items():
            if data["count"] > 0:
                analyzed_stocks[ticker] = data["count"]

    # 生成智慧清單
    smart_list = DEFAULT_WATCHLIST.copy()

    # 移除用戶經常刪除的股票
    for stock in removed_stocks:
        if removed_stocks[stock] >= 2 and stock in smart_list:
            smart_list.remove(stock)

    # 添加用戶經常使用的股票
    frequent_stocks = []
    for stock in added_stocks:
        if added_stocks[stock] >= 2 and stock not in smart_list:
            frequent_stocks.append((stock, added_stocks[stock]))

    for stock in analyzed_stocks:
        if analyzed_stocks[stock] >= 3 and stock not in smart_list and stock not in [s[0] for s in frequent_stocks]:
            frequent_stocks.append((stock, analyzed_stocks[stock]))

    # 按使用頻率排序並添加前3個
    frequent_stocks.sort(key=lambda x: x[1], reverse=True)
    for stock, _ in frequent_stocks[:3]:
        if stock not in smart_list:
            smart_list.append(stock)

    return smart_list

def get_user_insights():
    """獲取用戶使用洞察"""
    stats = load_usage_stats()
    insights = {}

    # 最常刪除的股票
    if "remove_stock" in stats:
        removed = sorted(stats["remove_stock"].items(), key=lambda x: x[1]["count"], reverse=True)
        if removed:
            insights["most_removed"] = removed[0][0]

    # 最常分析的股票
    if "analyze_stock" in stats:
        analyzed = sorted(stats["analyze_stock"].items(), key=lambda x: x[1]["count"], reverse=True)
        if analyzed:
            insights["most_analyzed"] = analyzed[0][0]

    # 最常添加的股票
    if "add_stock" in stats:
        added = sorted(stats["add_stock"].items(), key=lambda x: x[1]["count"], reverse=True)
        if added:
            insights["most_added"] = added[0][0]

    return insights

# --- 初始化 Session State ---
if 'watchlist' not in st.session_state:
    # 使用智慧清單初始化
    smart_list = get_smart_watchlist()
    st.session_state.watchlist = smart_list
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = load_portfolio()
if 'selected_stock' not in st.session_state:
    st.session_state.selected_stock = "NVDA"
if 'current_tab' not in st.session_state:
    st.session_state.current_tab = "radar"
if 'user_insights' not in st.session_state:
    st.session_state.user_insights = get_user_insights()

# --- 側邊欄設定 ---
with st.sidebar:
    st.header("⚙️ 戰情室設定")
    
    # 市場選擇
    market = st.radio("🌎 選擇市場", ["🇺🇸 美股戰情", "🇹🇼 台股戰情 (開發中)"], index=0)
    
    # 用戶名稱
    username = st.text_input("👤 用戶名稱", value="Trader")
    
    st.divider()
    
    # AI 分析開關
    st.subheader("🧠 AI 分析大腦")
    enable_ai = st.checkbox("啟用 AI 分析 (Enable)", value=True)
    
    st.divider()

    # 用戶洞察
    st.subheader("📊 用戶洞察")
    insights = get_user_insights()

    if insights:
        if "most_removed" in insights:
            st.info(f"🗑️ 最常移除: {insights['most_removed']}")
        if "most_analyzed" in insights:
            st.success(f"⚡ 最常分析: {insights['most_analyzed']}")
        if "most_added" in insights:
            st.info(f"➕ 最常新增: {insights['most_added']}")

        # 顯示智慧清單說明
        st.caption("💡 監控清單已根據您的使用習慣自動調整")
    else:
        st.caption("📝 開始使用後，系統將學習您的偏好")

    st.divider()

    # 資料管理
    st.subheader("🛠️ 資料管理")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔴 重置快取"):
            st.cache_data.clear()
            st.success("快取已重置！")
    with col2:
        if st.button("📤 強制備份"):
            save_portfolio(st.session_state.portfolio)
            save_usage_stats(load_usage_stats())  # 同時備份使用統計
            st.success("備份完成！")

# --- 主標題和市場狀態 ---
st.title("🚀 美股戰情中心 V2.1")

# --- 市場狀態指示器 ---
market_status = get_market_status()
status_cols = st.columns([2, 1, 1, 1])

with status_cols[0]:
    st.markdown(f"### {market_status['status']}")
with status_cols[1]:
    st.metric("😱 VIX/Bias", f"{market_status['vix']:.2f}")
with status_cols[2]:
    st.metric("🏦 Yield/Index", f"{market_status['yield']:.2f}")
with status_cols[3]:
    # 市場開盤狀態
    now = datetime.now()
    market_open = now.weekday() < 5 and 9 <= now.hour < 16
    st.metric("🕐 市場狀態", "Open" if market_open else "Closed")

st.divider()

# --- 主要頁籤 ---
tab1, tab2, tab3, tab4 = st.tabs([
    "📡 監控雷達", 
    "🔭 進場觀測", 
    "💼 庫存管理", 
    "🎯 市場獵手"
])

# === 頁籤 1: 監控雷達 ===
with tab1:
    st.header("📡 監控雷達 - 多股票即時監控")
    
    # 監控清單管理
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        new_stock = st.text_input("➕ 新增監控股票", placeholder="輸入股票代碼，如: PLTR")
    with col2:
        if st.button("➕ 加入清單"):
            if new_stock and new_stock.upper() not in st.session_state.watchlist:
                st.session_state.watchlist.append(new_stock.upper())
                # 記錄用戶行為
                record_user_action("add_stock", new_stock.upper(), "manual_add")
                st.success(f"✅ 已加入 {new_stock.upper()}")
                st.rerun()
            elif new_stock.upper() in st.session_state.watchlist:
                st.warning(f"⚠️ {new_stock.upper()} 已在監控清單中")
    with col3:
        if st.button("🔄 重置清單"):
            # 記錄重置行為
            record_user_action("reset_watchlist", "ALL", f"from_{len(st.session_state.watchlist)}_stocks")
            st.session_state.watchlist = DEFAULT_WATCHLIST.copy()
            st.success("✅ 已重置為預設清單")
            st.rerun()
    
    st.divider()
    
    # 掃描控制
    scan_col1, scan_col2, scan_col3 = st.columns([1, 1, 2])
    with scan_col1:
        if st.button("🔭 掃描全部", use_container_width=True):
            st.cache_data.clear()
            st.success("🔄 資料已更新")
    with scan_col2:
        show_postmarket = st.checkbox("顯示盤後", value=True)
    
    st.divider()
    
    # 監控股票清單
    st.subheader("📊 監控股票清單")
    
    # 創建網格佈局顯示股票卡片
    num_cols = 3
    rows = [st.session_state.watchlist[i:i+num_cols] for i in range(0, len(st.session_state.watchlist), num_cols)]
    
    for row in rows:
        cols = st.columns(num_cols)
        for i, ticker in enumerate(row):
            with cols[i]:
                quote = get_realtime_quote(ticker)
                if quote:
                    price = quote['price']
                    change = quote['change_pct']
                    change_color = "🟢" if change >= 0 else "🔴"
                    change_str = f"+{change:.2f}%" if change >= 0 else f"{change:.2f}%"
                    
                    # 盤後價格
                    post_str = ""
                    if show_postmarket and quote['post_price']:
                        post_color = "🌙" if quote['post_change'] >= 0 else "🌑"
                        post_change_str = f"+{quote['post_change']:.2f}%" if quote['post_change'] >= 0 else f"{quote['post_change']:.2f}%"
                        post_str = f" | {post_color} ${quote['post_price']:.2f} ({post_change_str})"
                    
                    # 股票卡片
                    st.markdown(f"""
                    <div class="watchlist-card">
                        <h4>{change_color} {ticker}</h4>
                        <p style="font-size: 20px; margin: 5px 0;"><strong>${price:.2f}</strong> {change_str}{post_str}</p>
                        <p style="margin: 5px 0;">成交量: {format_number(quote['volume'])}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # 操作按鈕
                    btn_col1, btn_col2, btn_col3 = st.columns(3)
                    with btn_col1:
                        if st.button("⚡ 分析", key=f"analyze_{ticker}", use_container_width=True):
                            st.session_state.selected_stock = ticker
                            st.session_state.current_tab = "analysis"
                            # 記錄用戶行為
                            record_user_action("analyze_stock", ticker, "from_watchlist")
                            st.rerun()
                    with btn_col2:
                        if st.button("➕ 入庫", key=f"add_{ticker}", use_container_width=True):
                            st.session_state.show_add_dialog = ticker
                            # 記錄用戶行為
                            record_user_action("add_to_portfolio", ticker, "from_watchlist")
                    with btn_col3:
                        if st.button("🗑️ 移除", key=f"remove_{ticker}", use_container_width=True):
                            st.session_state.watchlist.remove(ticker)
                            # 記錄用戶行為
                            record_user_action("remove_stock", ticker, "from_watchlist")
                            st.success(f"✅ 已移除 {ticker}")
                            st.rerun()
                else:
                    st.markdown(f"""
                    <div class="watchlist-card" style="border-color: #ff4757;">
                        <h4>❌ {ticker}</h4>
                        <p>無法獲取數據</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # 只有移除按鈕
                    if st.button("🗑️ 移除", key=f"remove_{ticker}", use_container_width=True):
                        st.session_state.watchlist.remove(ticker)
                        # 記錄用戶行為
                        record_user_action("remove_stock", ticker, "error_stock")
                        st.success(f"✅ 已移除 {ticker}")
                        st.rerun()

# === 頁籤 2: 進場觀測 ===
with tab2:
    st.header("🔭 進場觀測 - 技術分析與策略建議")
    
    # 分析代碼輸入
    input_col1, input_col2 = st.columns([4, 1])
    with input_col1:
        analyze_ticker = st.text_input("分析代碼", value=st.session_state.selected_stock, key="analysis_input")
    with input_col2:
        st.write("")  # 對齊
        st.write("")
        if st.button("⚡ 開始分析", use_container_width=True):
            st.session_state.selected_stock = analyze_ticker.upper()
            # 記錄用戶行為
            record_user_action("analyze_stock", analyze_ticker.upper(), "manual_input")
            st.rerun()
    
    # 獲取分析股票數據
    ticker = st.session_state.selected_stock
    df = get_stock_data(ticker, period="1y")
    quote = get_realtime_quote(ticker)
    
    if not df.empty and quote:
        # 計算技術指標
        df['RSI'] = calculate_rsi(df['Close'])
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['MA60'] = df['Close'].rolling(window=60).mean()
        
        support, resistance = calculate_support_resistance(df)
        earnings_date = get_earnings_date(ticker)
        
        # 分析結果卡片
        st.markdown('<div class="analysis-card">', unsafe_allow_html=True)
        
        # 關鍵指標
        st.subheader(f"📊 {ticker} 關鍵指標")
        metric_cols = st.columns(5)
        
        current_price = quote['price']
        change_pct = quote['change_pct']
        last_rsi = df['RSI'].iloc[-1] if not pd.isna(df['RSI'].iloc[-1]) else 50
        
        with metric_cols[0]:
            delta_color = "normal" if change_pct >= 0 else "inverse"
            st.metric("收盤價", f"${current_price:.2f}", f"{change_pct:+.2f}%")
        with metric_cols[1]:
            rsi_status = "🔥" if last_rsi > 70 else ("❄️" if last_rsi < 30 else "")
            st.metric("RSI", f"{last_rsi:.1f} {rsi_status}")
        with metric_cols[2]:
            if resistance:
                st.metric("上方阻力", f"${resistance:.2f}")
        with metric_cols[3]:
            if support:
                st.metric("下方支撐", f"${support:.2f}")
        with metric_cols[4]:
            if resistance:
                potential = ((resistance - current_price) / current_price) * 100
                st.metric("🚀 潛在漲幅", f"{potential:+.2f}%")
        
        # AI 策略建議
        st.subheader("🤖 AI 策略建議")
        
        # 趨勢判斷
        last_close = df['Close'].iloc[-1]
        last_ma20 = df['MA20'].iloc[-1] if not pd.isna(df['MA20'].iloc[-1]) else 0
        last_ma60 = df['MA60'].iloc[-1] if not pd.isna(df['MA60'].iloc[-1]) else 0
        
        # 狙擊手分析報告
        if last_rsi < 30:
            st.success("🔭 狙擊手分析報告: **Buy** - RSI 超賣區，可考慮分批進場")
        elif last_rsi > 70:
            st.warning("🔭 狙擊手分析報告: **Wait** - RSI 超買區，等待回調")
        elif last_close > last_ma20 > last_ma60:
            st.success("🔭 狙擊手分析報告: **Strong** - 多頭排列，趨勢向上")
        elif last_close < last_ma20 < last_ma60:
            st.error("🔭 狙擊手分析報告: **Weak** - 空頭排列，建議觀望")
        else:
            st.info("🔭 狙擊手分析報告: **Neutral** - 盤整區間，等待突破")
        
        # 趨勢掃描
        trend_col1, trend_col2 = st.columns(2)
        with trend_col1:
            short_trend = "📈 強勢" if last_close > last_ma20 else "📉 轉弱"
            long_trend = "🐂 多頭排列" if last_ma20 > last_ma60 else "🐻 空頭排列"
            st.markdown(f"""
            **🤖 趨勢掃描:**
            - 短線: {short_trend}
            - 長線: {long_trend}
            """)
        
        with trend_col2:
            # 預測區間 (簡單計算)
            volatility = df['Close'].pct_change().std() * np.sqrt(252)
            lower_bound = current_price * (1 - volatility * 0.5)
            upper_bound = current_price * (1 + volatility * 0.5)
            st.markdown(f"""
            **🔮 預測區間:** ${lower_bound:.2f} ~ ${upper_bound:.2f}
            
            **🎯 模型信心:** 🟢 中等
            """)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # 技術分析圖表
        st.subheader("📈 技術分析圖")
        
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                           vertical_spacing=0.03, 
                           row_heights=[0.7, 0.3])
        
        # K線
        fig.add_trace(go.Candlestick(
            x=df.index,
            open=df['Open'],
            high=df['High'],
            low=df['Low'],
            close=df['Close'],
            name="K線"
        ), row=1, col=1)
        
        # 均線
        fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], 
                                line=dict(color='orange', width=1), 
                                name="MA20"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MA60'], 
                                line=dict(color='blue', width=1), 
                                name="MA60"), row=1, col=1)
        
        # 支撐阻力線
        if support:
            fig.add_hline(y=support, line_dash="dash", line_color="green", 
                         annotation_text="支撐", row=1, col=1)
        if resistance:
            fig.add_hline(y=resistance, line_dash="dash", line_color="red", 
                         annotation_text="阻力", row=1, col=1)
        
        # RSI
        fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], 
                                line=dict(color='purple', width=1), 
                                name="RSI"), row=2, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)
        
        fig.update_layout(
            title=f"{ticker} 技術分析圖",
            height=600,
            xaxis_rangeslider_visible=False,
            template="plotly_dark"
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # 詳細數據
        with st.expander("🔍 詳細數據"):
            detail_cols = st.columns(3)
            with detail_cols[0]:
                st.write("**價格數據**")
                st.write(f"- 開盤: ${df['Open'].iloc[-1]:.2f}")
                st.write(f"- 最高: ${df['High'].iloc[-1]:.2f}")
                st.write(f"- 最低: ${df['Low'].iloc[-1]:.2f}")
                st.write(f"- 收盤: ${df['Close'].iloc[-1]:.2f}")
                st.write(f"- 成交量: {format_number(quote['volume'])}")
            with detail_cols[1]:
                st.write("**技術指標**")
                st.write(f"- RSI(14): {last_rsi:.2f}")
                st.write(f"- MA20: ${last_ma20:.2f}")
                st.write(f"- MA60: ${last_ma60:.2f}")
            with detail_cols[2]:
                st.write("**市場狀態**")
                market_state = "Open (交易中)" if market_open else "Closed (已收盤)"
                st.write(f"- 市場狀態: {market_state}")
                if earnings_date:
                    days_to_earnings = (earnings_date - datetime.now()).days
                    st.write(f"- 財報倒數: {days_to_earnings} 天")
                else:
                    st.write("- 財報日期: 未知")
    
    else:
        st.warning(f"無法獲取 {ticker} 的數據，請確認股票代碼是否正確")

# === 頁籤 3: 庫存管理 ===
with tab3:
    st.header("💼 庫存管理 - 投資組合追蹤")
    
    portfolio = st.session_state.portfolio
    
    if portfolio:
        # 計算總市值和收益
        total_value = 0
        total_cost = 0
        
        for ticker, holdings in portfolio.items():
            quote = get_realtime_quote(ticker)
            if quote:
                for holding in holdings:
                    current_value = quote['price'] * holding['shares']
                    cost = holding['cost'] * holding['shares']
                    total_value += current_value
                    total_cost += cost
        
        total_profit = total_value - total_cost
        total_return = ((total_value - total_cost) / total_cost * 100) if total_cost > 0 else 0
        
        # 總覽卡片
        st.markdown('<div class="analysis-card">', unsafe_allow_html=True)
        st.subheader("📊 投資組合總覽")
        
        # 顯示總覽
        port_cols = st.columns(3)
        with port_cols[0]:
            st.metric("總市值", f"${total_value:,.0f}")
        with port_cols[1]:
            st.metric("收益 ($)", f"${total_profit:,.0f}")
        with port_cols[2]:
            st.metric("報酬率 (%)", f"{total_return:+.2f}%")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # 持股明細
        st.subheader("📋 持股明細")
        
        for ticker, holdings in portfolio.items():
            quote = get_realtime_quote(ticker)
            if quote:
                for i, holding in enumerate(holdings):
                    cost = holding['cost']
                    shares = holding['shares']
                    current_value = quote['price'] * shares
                    profit = (quote['price'] - cost) * shares
                    profit_pct = ((quote['price'] - cost) / cost) * 100
                    
                    profit_emoji = "🟢" if profit_pct >= 0 else "🔴"
                    
                    with st.expander(f"{profit_emoji} **{ticker}**|${quote['price']:.2f}|成本:${cost:.2f}|收益:{profit_pct:+.1f}%"):
                        st.write(f"**股數:** {shares}")
                        st.write(f"**現值:** ${current_value:,.2f}")
                        st.write(f"**損益:** ${profit:,.2f}")
                        
                        # 建議
                        if profit_pct > 20:
                            st.success("🛡️ 建議: 獲利 > 20%，可考慮部分停利")
                        elif profit_pct > 50:
                            st.success("🎉 建議: 獲利 > 50%，強烈建議分批停利")
                        elif profit_pct < -10:
                            st.warning("⚠️ 建議: 虧損 > 10%，檢視是否需要停損")
                        elif profit_pct < -20:
                            st.error("🚨 建議: 虧損 > 20%，建議設定停損點")
                        
                        if st.button("🗑️ 移除持股", key=f"port_del_{ticker}_{i}"):
                            portfolio[ticker].pop(i)
                            if not portfolio[ticker]:
                                del portfolio[ticker]
                            save_portfolio(portfolio)
                            st.success("✅ 已移除")
                            st.rerun()
    
    # 加入新持股
    st.subheader("➕ 加入新持股")
    
    with st.form("add_stock_form"):
        add_ticker = st.text_input("股票代碼")
        add_cost = st.number_input("成本價", min_value=0.01, value=100.0)
        add_shares = st.number_input("股數", min_value=1, value=10)
        
        if st.form_submit_button("確認加入"):
            add_ticker = add_ticker.upper()
            if add_ticker:
                if add_ticker not in portfolio:
                    portfolio[add_ticker] = []
                portfolio[add_ticker].append({
                    "cost": add_cost,
                    "shares": add_shares,
                    "date": datetime.now().strftime("%Y-%m-%d")
                })
                save_portfolio(portfolio)
                st.success(f"✅ 已加入 {add_ticker}")
                st.rerun()
    
    if not portfolio:
        st.info("目前沒有任何持股記錄，請使用上方表單加入持股")

# === 頁籤 4: 市場獵手 ===
with tab4:
    st.header("🎯 市場獵手 - 策略掃描與機會發現")
    
    hunt_strategy = st.selectbox(
        "狩獵策略",
        ["📉 極度超賣 (RSI < 30)", "📈 強勢突破 (RSI > 70)", "🔄 均線黃金交叉", "📊 大量異動"]
    )
    
    scan_list = ["NVDA", "AAPL", "TSLA", "AMD", "MSFT", "GOOG", "META", "AMZN", "PLTR", "SOFI", "TSM", "AVGO"]
    
    if st.button("🔍 開始掃描", use_container_width=True):
        with st.spinner("掃描中，請稍候..."):
            results = []
            
            for ticker in scan_list:
                df = get_stock_data(ticker, period="3mo")
                if not df.empty:
                    rsi = calculate_rsi(df['Close']).iloc[-1]
                    
                    if "超賣" in hunt_strategy and rsi < 30:
                        results.append((ticker, rsi, "超賣"))
                    elif "超買" in hunt_strategy and rsi > 70:
                        results.append((ticker, rsi, "超買"))
                    elif "黃金交叉" in hunt_strategy:
                        ma20 = df['MA20'].iloc[-1]
                        ma60 = df['MA60'].iloc[-1]
                        ma20_prev = df['MA20'].iloc[-2]
                        ma60_prev = df['MA60'].iloc[-2]
                        if ma20_prev < ma60_prev and ma20 > ma60:
                            results.append((ticker, rsi, "黃金交叉"))
            
            if results:
                st.success(f"🎯 發現 {len(results)} 個符合條件的股票")
                
                for r in results:
                    col1, col2, col3, col4 = st.columns([2, 2, 2, 2])
                    with col1:
                        st.write(f"**{r[0]}**")
                    with col2:
                        st.write(f"RSI: {r[1]:.1f}")
                    with col3:
                        st.write(f"狀態: {r[2]}")
                    with col4:
                        if st.button("⚡ 分析", key=f"hunt_{r[0]}"):
                            st.session_state.selected_stock = r[0]
                            st.session_state.current_tab = "analysis"
                            # 記錄用戶行為
                            record_user_action("analyze_stock", r[0], f"hunting_strategy_{hunt_strategy}")
                            st.rerun()
            else:
                st.info("目前沒有符合條件的股票")

# --- 頁尾 ---
st.divider()
st.caption(f"🚀 美股戰情中心 V2.1 | 用戶: {username} | 更新時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
