import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk, ImageGrab
import os
import sys

def research_imagegrab():
    """研究 ImageGrab 的功能"""
    print("=== Pillow ImageGrab 功能研究 ===")
    
    # 1. 檢查 ImageGrab 的基本功能
    print("1. ImageGrab 基本功能:")
    print(f"   - ImageGrab 模組: {ImageGrab}")
    print(f"   - 可用方法: {dir(ImageGrab)}")
    
    # 2. 測試 grabclipboard()
    print("\n2. 測試 grabclipboard():")
    try:
        clipboard_content = ImageGrab.grabclipboard()
        if clipboard_content:
            print(f"   - 剪貼簿內容類型: {type(clipboard_content)}")
            if isinstance(clipboard_content, Image.Image):
                print(f"   - 圖片尺寸: {clipboard_content.size}")
                print(f"   - 圖片模式: {clipboard_content.mode}")
            else:
                print(f"   - 內容: {clipboard_content}")
        else:
            print("   - 剪貼簿為空")
    except Exception as e:
        print(f"   - 錯誤: {e}")
    
    # 3. 測試其他可能的方法
    print("\n3. 探索其他方法:")
    
    # 檢查是否有 setclipboard 方法
    if hasattr(ImageGrab, 'setclipboard'):
        print("   - 發現 setclipboard 方法")
    else:
        print("   - 沒有 setclipboard 方法")
    
    # 檢查是否有其他剪貼簿相關方法
    clipboard_methods = [method for method in dir(ImageGrab) if 'clip' in method.lower()]
    print(f"   - 剪貼簿相關方法: {clipboard_methods}")
    
    messagebox.showinfo("研究完成", "ImageGrab 功能研究完成，請查看控制台輸出")

def test_clipboard_methods():
    """測試不同的剪貼簿方法"""
    print("\n=== 測試不同的剪貼簿方法 ===")
    
    # 創建測試圖片
    test_image = Image.new('RGB', (100, 100), color='red')
    test_path = 'test_clipboard.png'
    test_image.save(test_path)
    
    methods_tested = []
    
    # 方法1: 嘗試使用 ImageGrab 設置剪貼簿
    try:
        # 注意：ImageGrab 沒有直接的設置剪貼簿方法
        print("方法1: ImageGrab 設置剪貼簿 - 不支援")
        methods_tested.append("ImageGrab.setclipboard - 不支援")
    except Exception as e:
        print(f"方法1 失敗: {e}")
    
    # 方法2: 使用 win32clipboard (如果可用)
    try:
        import win32clipboard
        from io import BytesIO
        
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
        
        print("方法2: win32clipboard - 成功")
        methods_tested.append("win32clipboard - 成功")
        
    except Exception as e:
        print(f"方法2 失敗: {e}")
        methods_tested.append(f"win32clipboard - 失敗: {e}")
    
    # 方法3: 使用 tkinter 剪貼簿
    try:
        root = tk.Tk()
        root.withdraw()
        
        # tkinter 主要用於文字，不是圖片
        root.clipboard_clear()
        root.clipboard_append("測試文字")
        
        print("方法3: tkinter 剪貼簿 - 僅支援文字")
        methods_tested.append("tkinter 剪貼board - 僅支援文字")
        
        root.destroy()
        
    except Exception as e:
        print(f"方法3 失敗: {e}")
        methods_tested.append(f"tkinter - 失敗: {e}")
    
    # 清理測試檔案
    if os.path.exists(test_path):
        os.remove(test_path)
    
    print(f"\n測試結果總結:")
    for method in methods_tested:
        print(f"  - {method}")
    
    messagebox.showinfo("測試完成", f"剪貼簿方法測試完成\n\n結果:\n" + "\n".join(methods_tested))

def create_improved_clipboard_solution():
    """創建改進的剪貼簿解決方案"""
    print("\n=== 改進的剪貼簿解決方案 ===")
    
    solution_code = '''# 改進的剪貼簿複製方法
def copy_image_to_clipboard_improved(image_path):
    """使用多種方法複製圖片到剪貼簿"""
    
    # 方法1: win32clipboard (最可靠)
    try:
        import win32clipboard
        from io import BytesIO
        
        image = Image.open(image_path)
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
        
        return True, "win32clipboard 成功"
        
    except Exception as e:
        print(f"win32clipboard 失敗: {e}")
    
    # 方法2: 使用系統命令
    try:
        import subprocess
        import platform
        
        if platform.system() == "Windows":
            # 使用 PowerShell 複製圖片
            ps_script = f'''
            Add-Type -AssemblyName System.Windows.Forms
            $image = [System.Drawing.Image]::FromFile("{image_path}")
            $ms = New-Object System.IO.MemoryStream
            $image.Save($ms, [System.Drawing.Imaging.ImageFormat]::Png)
            $ms.Position = 0
            $data = New-Object System.Windows.Forms.DataObject
            $data.SetData("PNG", $ms)
            [System.Windows.Forms.Clipboard]::SetDataObject($data)
            $image.Dispose()
            $ms.Dispose()
            '''
            
            result = subprocess.run(['powershell', '-Command', ps_script], 
                                 capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                return True, "PowerShell 成功"
            else:
                print(f"PowerShell 失敗: {result.stderr}")
                
    except Exception as e:
        print(f"系統命令失敗: {e}")
    
    # 方法3: 複製檔案路徑
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        root.clipboard_clear()
        root.clipboard_append(image_path)
        root.destroy()
        
        return False, "已複製檔案路徑"
        
    except Exception as e:
        print(f"複製檔案路徑失敗: {e}")
    
    return False, "所有方法都失敗"

# 使用示例
success, message = copy_image_to_clipboard_improved("your_image.png")
if success:
    print(f"圖片複製成功: {message}")
else:
    print(f"複製失敗: {message}")
'''
    
    print("改進的解決方案代碼:")
    print(solution_code)
    
    # 保存到檔案
    with open('improved_clipboard_solution.py', 'w', encoding='utf-8') as f:
        f.write(solution_code)
    
    messagebox.showinfo("解決方案", "改進的剪貼簿解決方案已創建並保存到 improved_clipboard_solution.py")

# 創建GUI
root = tk.Tk()
root.title("ImageGrab 研究工具")
root.geometry("500x400")

tk.Label(root, text="Pillow ImageGrab 剪貼簿功能研究", font=("Arial", 14, "bold")).pack(pady=20)

btn1 = tk.Button(root, text="研究 ImageGrab 功能", command=research_imagegrab)
btn1.pack(pady=10)

btn2 = tk.Button(root, text="測試剪貼簿方法", command=test_clipboard_methods)
btn2.pack(pady=10)

btn3 = tk.Button(root, text="創建改進解決方案", command=create_improved_clipboard_solution)
btn3.pack(pady=10)

root.mainloop() 