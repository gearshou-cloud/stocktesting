import requests
import time

def test_search():
    url = "http://127.0.0.1:5000/api/search?q=2330"
    print(f"發送請求到: {url}")
    start = time.time()
    resp = requests.get(url)
    end = time.time()
    print(f"回應狀態: {resp.status_code} (耗時 {end-start:.2f}s)")
    data = resp.json()
    if data['success']:
        s = data['results'][0]
        if 'institutional_history' in s:
            print(f"成功拿到 {len(s['institutional_history'])} 筆法人歷史資料")
        else:
            print("❌ 結果中沒有 institutional_history")
    else:
        print("❌ 請求失敗")

if __name__ == '__main__':
    test_search()
