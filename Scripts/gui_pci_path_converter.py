import tkinter as tk
from tkinter import ttk, messagebox
import re

def convert_pci_path():
    input_text = input_entry.get().strip()
    if not input_text:
        messagebox.showwarning("警告", "请输入要转换的PCI路径")
        return
    
    try:
        if input_text.startswith("PCIROOT"):
            # 转换Windows路径到DP路径
            result = convert_windows_to_dp(input_text)
        elif input_text.startswith("PciRoot"):
            # 转换DP路径到Windows路径
            result = convert_dp_to_windows(input_text)
        else:
            messagebox.showerror("错误", "无法识别的路径格式")
            return
        
        output_entry.delete(0, tk.END)
        output_entry.insert(0, result)
    except Exception as e:
        messagebox.showerror("错误", f"转换失败: {str(e)}")

def convert_windows_to_dp(windows_path):
    # 示例: PCIROOT(0)#PCI(0100)#PCI(0000) -> PciRoot(0x0)/Pci(0x1,0x0)/Pci(0x0,0x0)
    parts = windows_path.split("#")
    dp_parts = []
    
    for part in parts:
        if part.startswith("PCIROOT("):
            # 处理PCIROOT部分
            num = part[8:-1]
            dp_parts.append(f"PciRoot(0x{int(num):X})")
        elif part.startswith("PCI("):
            # 处理PCI部分
            hex_str = part[4:-1]
            if len(hex_str) != 4:
                raise ValueError(f"无效的PCI设备号: {hex_str}")
            dev = int(hex_str[:2], 16)
            func = int(hex_str[2:], 16)
            dp_parts.append(f"Pci(0x{dev:X},0x{func:X})")
        else:
            raise ValueError(f"未知的路径部分: {part}")
    
    return "/".join(dp_parts)

def convert_dp_to_windows(dp_path):
    # 示例: PciRoot(0x0)/Pci(0x1,0x0)/Pci(0x0,0x0) -> PCIROOT(0)#PCI(0100)#PCI(0000)
    parts = dp_path.split("/")
    windows_parts = []
    
    for part in parts:
        if part.startswith("PciRoot("):
            # 处理PciRoot部分
            match = re.match(r"PciRoot\(0x([0-9A-Fa-f]+)\)", part)
            if not match:
                raise ValueError(f"无效的PciRoot格式: {part}")
            num = int(match.group(1), 16)
            windows_parts.append(f"PCIROOT({int(match.group(1), 16)})")
        elif part.startswith("Pci("):
            # 处理Pci部分
            match = re.match(r"Pci\(0x([0-9A-Fa-f]+),0x([0-9A-Fa-f]+)\)", part)
            if not match:
                raise ValueError(f"无效的Pci格式: {part}")
            dev = int(match.group(1), 16)
            func = int(match.group(2), 16)
            windows_parts.append(f"PCI({dev:02d}{func:02d})")
        else:
            raise ValueError(f"未知的路径部分: {part}")
    
    return "#".join(windows_parts)

def copy_to_clipboard():
    root.clipboard_clear()
    root.clipboard_append(output_entry.get())
    messagebox.showinfo("成功", "已复制到剪贴板")

# 创建主窗口
root = tk.Tk()
root.title("PCI设备路径转换工具 by laobamac")
root.geometry("600x300")

# 输入部分
input_frame = ttk.Frame(root, padding="10")
input_frame.pack(fill=tk.X)

ttk.Label(input_frame, text="输入路径:").pack(side=tk.LEFT)
input_entry = ttk.Entry(input_frame, width=50)
input_entry.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)

# 输出部分
output_frame = ttk.Frame(root, padding="10")
output_frame.pack(fill=tk.X)

ttk.Label(output_frame, text="转换结果:").pack(side=tk.LEFT)
output_entry = ttk.Entry(output_frame, width=50)
output_entry.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)

# 按钮部分
button_frame = ttk.Frame(root, padding="10")
button_frame.pack(fill=tk.X)

convert_btn = ttk.Button(button_frame, text="转换", command=convert_pci_path)
convert_btn.pack(side=tk.LEFT, padx=5)

copy_btn = ttk.Button(button_frame, text="复制结果", command=copy_to_clipboard)
copy_btn.pack(side=tk.LEFT, padx=5)

# 示例部分
example_frame = ttk.Frame(root, padding="10")
example_frame.pack(fill=tk.BOTH, expand=True)

ttk.Label(example_frame, text="示例:").pack(anchor=tk.W)

examples = [
    ("Windows路径 → DP路径", "PCIROOT(0)#PCI(0100)#PCI(0000)", "PciRoot(0x0)/Pci(0x1,0x0)/Pci(0x0,0x0)"),
    ("DP路径 → Windows路径", "PciRoot(0x0)/Pci(0x1,0x0)/Pci(0x0,0x0)", "PCIROOT(0)#PCI(0100)#PCI(0000)")
]

for desc, inp, out in examples:
    example_text = f"{desc}\n输入: {inp}\n输出: {out}"
    ttk.Label(example_frame, text=example_text, wraplength=550, justify=tk.LEFT).pack(anchor=tk.W, pady=5)

root.mainloop()