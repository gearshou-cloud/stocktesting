# -*- coding: utf-8 -*-
import pandas as pd
import os
import sys

# 設置輸出編碼為 UTF-8
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Load Excel
file_path = r"C:\Users\Hou_J\OneDrive - Rohde & Schwarz\[00] PM Frank\00_Planning\2025.10\OI QTY_L70_PM (updated to 20250930).xlsx"
sheet_name = "OI_updated to 20250930"

# 檢查文件是否存在
if not os.path.exists(file_path):
    print(f"[錯誤] 文件不存在: {file_path}")
    exit(1)

try:
    print(f"[信息] 正在讀取文件: {os.path.basename(file_path)}")
    print(f"[信息] 工作表: {sheet_name}")
    print()
    
    # 讀取 Excel
    df = pd.read_excel(file_path, sheet_name=sheet_name, header=None)
    print(f"[成功] 成功讀取 Excel，共 {len(df)} 行\n")
    
    # Filter: B欄 = "1TD" 且 H欄 = "003.2025"
    filtered = df[
        (df.iloc[:, 1].astype(str).str.strip() == "1TD") &
        (df.iloc[:, 7].astype(str).str.strip() == "003.2025")
    ].copy()
    
    # Convert P欄 to numeric and sum (單位: *1000 EUR)
    filtered["Revenue_kEUR"] = pd.to_numeric(filtered.iloc[:, 15], errors="coerce")
    sum_result = filtered["Revenue_kEUR"].sum()
    
    print("="*50)
    print(" 統計結果")
    print("="*50)
    print(f"篩選結果筆數: {len(filtered)}")
    print(f"Revenue 總和: {sum_result:,.2f} kEUR")
    print(f"Revenue 總和: {sum_result * 1000:,.2f} EUR")
    print("="*50)
    
except PermissionError as e:
    print(f"\n[錯誤] 權限錯誤: 無法訪問文件")
    print(f"   請關閉 Excel 或其他正在使用該文件的程序")
    exit(1)
    
except Exception as e:
    print(f"\n[錯誤] 發生錯誤: {e}")
    exit(1)
