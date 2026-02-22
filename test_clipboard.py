import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import win32clipboard
from io import BytesIO
import os

def test_clipboard_copy():
    """測試剪貼簿複製功能"""
    try:
        # 創建一個簡單的測試圖片
        test_image = Image.new('RGB', (100, 100), color='red')
        
        # 保存到臨時檔案
        test_path = 'test_image.png'
        test_image.save(test_path)
        
        # 嘗試複製到剪貼簿
        image = Image.open(test_path)
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        output = BytesIO()
        image.save(output, 'BMP')
        data = output.getvalue()
        output.close()
        
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data[14:])
        win32clipboard.CloseClipboard()
        
        print("圖片複製成功！")
        messagebox.showinfo("成功", "測試圖片已複製到剪貼簿")
        
        # 清理測試檔案
        if os.path.exists(test_path):
            os.remove(test_path)
            
    except Exception as e:
        print(f"複製失敗: {e}")
        messagebox.showerror("錯誤", f"複製失敗: {str(e)}")

# 創建簡單的GUI
root = tk.Tk()
root.title("剪貼簿測試")
root.geometry("300x200")

test_btn = tk.Button(root, text="測試複製圖片", command=test_clipboard_copy)
test_btn.pack(pady=20)

root.mainloop() 