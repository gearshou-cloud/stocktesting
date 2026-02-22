import streamlit as st
import stock_logic as sl
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="台股智慧強勢股篩選器", layout="wide")

st.title("🔥 台股智慧強勢股篩選器")
st.markdown("---")

# Sidebar 篩選條件
st.sidebar.header("📊 篩選條件")
min_p = st.sidebar.number_input("最低股價", value=10.0, step=1.0)
max_p = st.sidebar.number_input("最高股價", value=1000.0, step=10.0)
min_v = st.sidebar.number_input("最低成交量 (張)", value=2000, step=100)

# 抓取指數
taiex = sl.fetch_index_data('^TWII', '加權指數')
otc = sl.fetch_index_data('^TWOII', '上櫃指數')

col1, col2 = st.columns(2)
with col1:
    st.metric(taiex['name'], f"{taiex['value']}", f"{taiex['change_pct']}%")
with col2:
    st.metric(otc['name'], f"{otc['value']}", f"{otc['change_pct']}%")

# 抓取基礎資料
base = sl.filter_and_rank_stocks(min_p, max_p, 0, min_v, False, taiex['change_pct'], otc['change_pct'])

# 分頁標籤
t1, t2, t3, t4 = st.tabs(["🤖 AI 智慧推薦", "💪 強勢選股", "🏆 優於大盤", "🔍 完整清單"])

if 'error' in base:
    st.error(f"🛑 錯誤: {base['error']}")
    st.warning("請確保 GitHub 儲存庫中包含 'stock_database.json' 檔案。")
else:
    with t1:
        st.subheader("🤖 AI 智慧深度推薦標的")
        if st.button("開始 AI 深度掃描", key="ai_btn"):
            with st.spinner("AI 正在分析強勢股中，請稍候..."):
                res = sl.get_ai_recommendations_internal(min_p, max_p, min_v)
                if res.get('success'):
                    data = res['recommendations']
                    if not data:
                        st.info("目前沒有完全符合條件的標的。")
                    else:
                        for s in data:
                            with st.expander(f"📌 {s['code']} {s['name']} | 價格: {s['price']} ({s['change_pct']}%)"):
                                st.write(f"**綜合評分:** {s['score']}")
                                st.write(f"**推薦原因:** {', '.join(s['reasons'])}")
                                st.write(f"**成交量:** {s['volume'] // 1000} 張")
                else:
                    st.error(f"分析失敗: {res.get('error')}")

    with t2:
        st.subheader("💪 連續守住實體高點強勢股")
        all_c = base['listed'] + base['otc']
        
        strong_list = []
        if st.button("執行強勢天數分析"):
            progress = st.progress(0)
            for i, s in enumerate(all_c):
                try:
                    symbol = f"{s['code']}.TW" if s['market'] == 'LISTED' else f"{s['code']}.TWO"
                    hist = sl.yf.Ticker(symbol).history(period='20d')
                    is_s, label, count = sl.calc_high_days(hist)
                    if is_s:
                        strong_list.append({**s, '強勢天數': count, '分析': label})
                except: continue
                progress.progress((i + 1) / len(all_c))
            
            if strong_list:
                df_s = pd.DataFrame(strong_list).sort_values('強勢天數', ascending=False)
                st.dataframe(df_s[['code', 'name', 'price', 'change_pct', '強勢天數', '分析']])
            else:
                st.info("今日無符合強勢條件標的。")

    with t3:
        st.subheader("🏆 優於大盤標的")
        st.write(f"當前門檻：上市 > {taiex['change_pct']}% | 上櫃 > {otc['change_pct']}%")
        df_l = pd.DataFrame(base['listed'])
        df_o = pd.DataFrame(base['otc'])
        
        c_l, c_o = st.columns(2)
        with c_l:
            st.write("上市優於大盤")
            if not df_l.empty: st.dataframe(df_l[['code', 'name', 'price', 'change_pct']])
            else: st.write("無符合標的")
        with c_o:
            st.write("上櫃優於大盤")
            if not df_o.empty: st.dataframe(df_o[['code', 'name', 'price', 'change_pct']])
            else: st.write("無符合標的")

    with t4:
        st.subheader("🔍 當前過濾結果 (依漲幅排序)")
        all_all = base['listed_all'] + base['otc_all']
        if all_all:
            st.dataframe(pd.DataFrame(all_all)[['code', 'name', 'price', 'change_pct', 'market', 'volume']])
        else:
            st.write("目前篩選條件下無任何股票")
