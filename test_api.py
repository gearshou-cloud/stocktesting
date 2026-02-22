from app_v3 import fetch_institutional_history
import json

def test():
    print("正在測試抓取 2330 的法人歷史資料...")
    # 2330 是台積電，一定會有資料
    history = fetch_institutional_history('2330', 'LISTED', n_days=5)
    print(f"抓取結果 (共 {len(history)} 筆):")
    print(json.dumps(history, indent=2, ensure_ascii=False))

if __name__ == '__main__':
    test()
