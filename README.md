# 台股強勢股篩選器 | Taiwan Stock Screener

現代化網頁介面，自動篩選當日台股強勢股票，根據股價和市值條件找出漲幅最高的前三名。

## 🚀 快速開始

### 1. 安裝依賴

```bash
# 建立虛擬環境
py -m venv venv

# 啟動虛擬環境 (Windows)
.\venv\Scripts\activate

# 安裝套件
pip install -r requirements.txt
```

### 2. 啟動 Web 伺服器

```bash
# 確保虛擬環境已啟動
.\venv\Scripts\activate

# 執行 Flask 應用程式
python app.py
```

### 3. 開啟瀏覽器

在瀏覽器中開啟：**http://localhost:5000**

## 🎨 使用介面

### 篩選控制

網頁介面提供三個互動式滑桿：

1. **最低股價** - 設定股價下限（預設：50 TWD）
2. **最高股價** - 設定股價上限（預設：200 TWD）
3. **最小市值** - 設定市值下限（預設：100 億 TWD）

### 操作步驟

1. 使用滑桿或數字輸入框調整篩選條件
2. 點擊「🔍 篩選股票 | Filter Stocks」按鈕
3. 等待 30-60 秒讓系統分析股票數據
4. 查看前三名強勢股結果

### 結果顯示

每支股票顯示：
- 📊 排名
- 🏷️ 股票代碼與名稱
- 💰 現價與漲幅百分比
- 📈 成交量
- 💎 市值

## ✨ 功能特色

✅ **現代化 UI** - 漸層背景、玻璃擬態效果、流暢動畫  
✅ **即時篩選** - 互動式滑桿即時調整條件  
✅ **視覺化結果** - 卡片式設計，清楚顯示股票資訊  
✅ **響應式設計** - 支援桌面與行動裝置  
✅ **載入狀態** - 顯示載入動畫與錯誤訊息

## 📁 專案結構

```
screenshots/
├── app.py                 # Flask 後端 API
├── templates/
│   └── index.html        # 網頁介面
├── static/
│   └── style.css         # 樣式表
├── requirements.txt      # Python 依賴
└── README.md            # 說明文件
```

## ⚙️ API 端點

### POST /api/screen

篩選股票 API

**請求範例：**
```json
{
  "min_price": 50,
  "max_price": 200,
  "min_market_cap": 100
}
```

**回應範例：**
```json
{
  "success": true,
  "timestamp": "2026-02-16 17:30:00",
  "filters": {
    "min_price": 50,
    "max_price": 200,
    "min_market_cap": 10000000000
  },
  "stats": {
    "total_analyzed": 30,
    "total_filtered": 8
  },
  "top_stocks": [...]
}
```

## 🔧 自訂股票清單

編輯 `app.py` 中的 `TAIWAN_STOCKS` 列表：

```python
TAIWAN_STOCKS = [
    '2330.TW',  # 台積電
    '2317.TW',  # 鴻海
    # 新增更多股票...
]
```

## ⚠️ 注意事項

- **虛擬環境必須啟動** - 否則會缺少必要套件
- **數據延遲** - Yahoo Finance 台股數據可能有 15-20 分鐘延遲
- **網路連線** - 需要網路連線以獲取股票數據
- **分析時間** - 分析 30 支股票約需 30-60 秒

## 🛑 停止伺服器

在終端機按 `Ctrl+C` 停止 Flask 伺服器

---

**開發者**: Antigravity AI  
**版本**: 2.0.0 (Web UI)  
**技術**: Flask + HTML + CSS + JavaScript
