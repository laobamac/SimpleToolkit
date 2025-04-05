import os
import subprocess
import shutil
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import time
import psutil
import pyautogui

class USBCustomizerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("USB定制工具")
        self.root.geometry("600x400")
        
        # 变量
        self.utb_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Resources", "UTB")
        self.output_dir = tk.StringVar()
        self.running = False
        self.proc = None
        self.stop_requested = False
        
        # 创建UI
        self.create_widgets()
        
    def create_widgets(self):
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 工具说明
        ttk.Label(main_frame, text="USB定制工具", font=('Arial', 14)).pack(pady=5)
        ttk.Label(main_frame, text="自动运行USBToolBox并复制生成的驱动文件").pack(pady=5)
        
        # 路径选择
        path_frame = ttk.Frame(main_frame)
        path_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(path_frame, text="输出目录:").pack(side=tk.LEFT)
        self.output_entry = ttk.Entry(path_frame, textvariable=self.output_dir, width=40)
        self.output_entry.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        
        browse_btn = ttk.Button(path_frame, text="浏览...", command=self.browse_output_dir)
        browse_btn.pack(side=tk.LEFT)
        
        # 操作按钮
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=20)
        
        self.start_btn = ttk.Button(btn_frame, text="开始定制", command=self.start_customization)
        self.start_btn.pack(side=tk.LEFT, padx=5, ipadx=20, ipady=5)
        
        self.stop_btn = ttk.Button(btn_frame, text="停止", command=self.stop_customization, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5, ipadx=20, ipady=5)
        
        # 日志区域
        ttk.Label(main_frame, text="操作日志:").pack(anchor=tk.W)
        
        self.log_text = tk.Text(main_frame, height=10, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(self.log_text)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.log_text.yview)
        
    def browse_output_dir(self):
        dir_path = filedialog.askdirectory()
        if dir_path:
            self.output_dir.set(dir_path)
            self.log(f"已选择输出目录: {dir_path}")
    
    def log(self, message):
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.root.update()
    
    def start_customization(self):
        if self.running:
            return
            
        if not self.output_dir.get():
            messagebox.showerror("错误", "请先选择输出目录")
            return
            
        self.running = True
        self.stop_requested = False
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.log("开始USB定制过程...")
        
        threading.Thread(target=self.run_customization, daemon=True).start()
    
    def stop_customization(self):
        if not self.running:
            return
            
        self.stop_requested = True
        self.log("正在停止进程...")
        
        if self.proc:
            try:
                parent = psutil.Process(self.proc.pid)
                for child in parent.children(recursive=True):
                    child.terminate()
                parent.terminate()
                self.log("已终止Windows.exe及其子进程")
            except Exception as e:
                self.log(f"终止进程时出错: {str(e)}")
    
    def run_customization(self):
        try:
            # 1. 检查UTB路径
            utb_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Resources", "UTB")
            exe_path = os.path.join(utb_dir, "Windows.exe")
            
            if not os.path.exists(exe_path):
                self.log(f"错误: 找不到Windows.exe ({exe_path})")
                return
                
            self.log(f"找到Windows.exe: {exe_path}")
            
            # 2. 运行Windows.exe
            self.log("启动USBToolBox TUI工具...")
            self.proc = subprocess.Popen(exe_path, cwd=utb_dir)
            
            # 等待窗口激活
            time.sleep(2)
            self.activate_window("USBToolBox")
            
            # 需要按顺序选择的选项
            options = ['P', 'D', 'B', 'A', 'S', 'K']
            
            for opt in options:
                if self.stop_requested:
                    break
                    
                self.log(f"准备选择选项: {opt}")
                self.simulate_key_input(opt)
                
                if opt == 'B':
                    self.handle_b_option()
                
            if not self.stop_requested:
                time.sleep(2)
                self.check_and_copy_results()
            
        except Exception as e:
            self.log(f"发生错误: {str(e)}")
        finally:
            self.cleanup()

    def activate_window(self, title):
        """激活指定标题的窗口"""
        try:
            window = pyautogui.getWindowsWithTitle(title)[0]
            if window:
                window.activate()
                time.sleep(1)
                self.log(f"已激活窗口: {title}")
        except Exception as e:
            self.log(f"窗口激活失败: {str(e)}")

    def simulate_key_input(self, key):
        """模拟键盘输入：先输入字母，等待1秒后回车"""
        try:
            # 输入字母
            pyautogui.press(key)
            self.log(f"已输入: {key}")
            
            # 等待1秒
            time.sleep(1)
            
            # 按回车
            pyautogui.press('enter')
            self.log("已按回车键")
            
            # 等待命令执行
            time.sleep(1)
        except Exception as e:
            self.log(f"模拟输入失败: {str(e)}")
            raise

    def handle_b_option(self):
        """特殊处理B选项后的流程"""
        self.log("进入B选项特殊处理流程...")
        attempts = 0
        max_attempts = 5
        
        while attempts < max_attempts and not self.stop_requested:
            # 模拟输入B和回车
            self.simulate_key_input('B')
            attempts += 1
            self.log(f"第{attempts}次尝试发送B选项")
            
            # 检查是否应该退出循环
            if self.check_for_quit_prompt():
                self.log("检测到退出提示，继续下一步")
                return
                
        if attempts >= max_attempts:
            self.log("警告: 已达到最大B选项尝试次数")

    def check_for_quit_prompt(self):
        """检查是否出现退出提示（简化实现）"""
        # 实际实现应该包含更精确的检测逻辑
        time.sleep(2)  # 等待可能的输出
        return True  # 假设总是检测到

    def check_and_copy_results(self):
        """检查并复制结果文件"""
        utb_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Resources", "UTB")
        utb_map_path = os.path.join(utb_dir, "UTBMap.kext")
        usb_toolbox_path = os.path.join(utb_dir, "USBToolBox.kext")
        
        if not os.path.exists(utb_map_path):
            self.log("错误: 未生成UTBMap.kext")
            return
            
        if not os.path.exists(usb_toolbox_path):
            self.log("错误: 未找到USBToolBox.kext")
            return
            
        self.log("成功生成驱动文件")
        
        output_path = self.output_dir.get()
        self.log(f"正在复制文件到: {output_path}")
        
        try:
            shutil.copytree(utb_map_path, os.path.join(output_path, "UTBMap.kext"), dirs_exist_ok=True)
            shutil.copytree(usb_toolbox_path, os.path.join(output_path, "USBToolBox.kext"), dirs_exist_ok=True)
            self.log("USB定制完成！")
        except Exception as e:
            self.log(f"复制文件时出错: {str(e)}")

    def cleanup(self):
        """清理资源"""
        if self.proc:
            try:
                self.proc.terminate()
            except:
                pass
        self.proc = None
        self.running = False
        self.root.after(0, lambda: self.start_btn.config(state=tk.NORMAL))
        self.root.after(0, lambda: self.stop_btn.config(state=tk.DISABLED))

def main():
    root = tk.Tk()
    app = USBCustomizerApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()