import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk, ImageGrab
import os

def test_imagegrab_clipboard():
    """測試 ImageGrab 的剪貼簿功能"""
    try:
        # 創建一個測試圖片
        test_image = Image.new('RGB', (200, 200), color='blue')
        test_path = 'test_imagegrab.png'
        test_image.save(test_path)
        
        print("測試 ImageGrab 功能...")
        
        # 測試 ImageGrab.grabclipboard() - 讀取剪貼簿
        clipboard_image = ImageGrab.grabclipboard()
        if clipboard_image:
            print("剪貼簿中有圖片")
        else:
            print("剪貼簿中沒有圖片")
        
        # 測試將圖片複製到剪貼簿
        # 注意：ImageGrab 主要用於截取螢幕，不是專門的剪貼簿工具
        # 但我們可以嘗試使用它來處理剪貼簿
        
        print("ImageGrab 功能測試完成")
        messagebox.showinfo("測試完成", "ImageGrab 功能測試完成，請查看控制台輸出")
        
        # 清理測試檔案
        if os.path.exists(test_path):
            os.remove(test_path)
            
    except Exception as e:
        print(f"測試失敗: {e}")
        messagebox.showerror("錯誤", f"測試失敗: {str(e)}")

def test_alternative_clipboard():
    """測試替代的剪貼簿方法"""
    try:
        # 方法1：使用 tkinter 的剪貼簿
        root = tk.Tk()
        root.withdraw()  # 隱藏主窗口
        
        # 創建測試圖片
        test_image = Image.new('RGB', (150, 150), color='green')
        test_path = 'test_tkinter.png'
        test_image.save(test_path)
        
        # 讀取圖片數據
        with open(test_path, 'rb') as f:
            image_data = f.read()
        
        # 嘗試複製到剪貼簿
        root.clipboard_clear()
        # 注意：tkinter 的剪貼簿主要用於文字，不是圖片
        
        print("tkinter 剪貼簿測試完成")
        messagebox.showinfo("測試完成", "tkinter 剪貼簿測試完成")
        
        # 清理
        if os.path.exists(test_path):
            os.remove(test_path)
        root.destroy()
        
    except Exception as e:
        print(f"替代方法測試失敗: {e}")
        messagebox.showerror("錯誤", f"替代方法測試失敗: {str(e)}")

# 創建GUI
root = tk.Tk()
root.title("ImageGrab 測試")
root.geometry("400x300")

tk.Label(root, text="Pillow ImageGrab 剪貼簿功能測試", font=("Arial", 12)).pack(pady=20)

test_btn1 = tk.Button(root, text="測試 ImageGrab", command=test_imagegrab_clipboard)
test_btn1.pack(pady=10)

test_btn2 = tk.Button(root, text="測試替代方法", command=test_alternative_clipboard)
test_btn2.pack(pady=10)

root.mainloop() 