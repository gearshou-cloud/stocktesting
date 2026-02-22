import requests
import json

_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
    'Accept': 'application/json, text/javascript, */*',
    'Referer': 'https://www.twse.com.tw/',
}

def test_raw_api():
    date_str = "20260211" # Feb 11 (Wed) - Should have data
    url = f"https://www.twse.com.tw/rwd/zh/fund/T86?date={date_str}&response=json&selectType=ALLBUT0999"
    print(f"嘗試抓取 TWSE: {url}")
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=15)
        print(f"HTTP 狀態碼: {resp.status_code}")
        # print(f"回應內容: {resp.text[:500]}")
        data = resp.json()
        print(f"API 狀態: {data.get('stat')}")
        if 'data' in data:
            print(f"成功拿到 {len(data['data'])} 筆資料")
            # 找找看 2330
            for row in data['data']:
                if row[0].strip() == '2330':
                    print(f"找到 2330: {row}")
                    break
        else:
            print("找不到 'data' 欄位")
            print(data)
    except Exception as e:
        print(f"發生錯誤: {e}")

if __name__ == '__main__':
    test_raw_api()
