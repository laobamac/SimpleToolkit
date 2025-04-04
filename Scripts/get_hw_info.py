'''
The MIT License (MIT)
Copyright © 2025 王孝慈

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the “Software”), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''
import wmi
import re
import os
import ctypes
from colorama import init, Fore, Style

# 初始化colorama
init()

def get_terminal_size():
    """获取当前终端窗口大小"""
    try:
        # 适用于Windows
        from ctypes import windll, create_string_buffer
        h = windll.kernel32.GetStdHandle(-12)
        csbi = create_string_buffer(22)
        res = windll.kernel32.GetConsoleScreenBufferInfo(h, csbi)
        if res:
            import struct
            (_, _, _, _, _, left, top, right, bottom, _, _) = struct.unpack("hhhhHhhhhhh", csbi.raw)
            columns = right - left + 1
            lines = bottom - top + 1
            return columns, lines
    except:
        pass
    # 默认值
    return 120, 30

def calculate_required_width(cols_config):
    """计算需要的终端宽度"""
    return sum(col['width'] for col in cols_config) + (len(cols_config) - 1) * 3  # 每列间3个空格

def extract_hardware_ids(pnp_id):
    """从PNPDeviceID中提取VEN和DEV并合并为VENID&DEVID格式"""
    if not pnp_id:
        return ""
    ven_match = re.search(r'VEN_([0-9A-F]{4})', pnp_id, re.IGNORECASE)
    dev_match = re.search(r'DEV_([0-9A-F]{4})', pnp_id, re.IGNORECASE)
    if ven_match and dev_match:
        return f"{ven_match.group(1)}&{dev_match.group(1)}"
    return ""

def load_support_info(filename):
    """加载支持信息文件"""
    support_info = {}
    details_info = {}
    kext_info = {}
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and '=' in line:
                    key, value = line.split('=', 1)
                    if key.endswith('.info'):
                        device_id = key[:-5].upper()
                        details_info[device_id] = value
                    elif key.endswith('.kext'):
                        device_id = key[:-5].upper()
                        kext_info[device_id] = value
                    else:
                        support_info[key.upper()] = value
    return support_info, details_info, kext_info

def get_support_info(device_id, support_info, details_info, kext_info):
    """获取设备支持信息"""
    if not device_id:
        return None, "N/A", "未知", "无"
    
    status = support_info.get(device_id)
    detail = details_info.get(device_id, "未知")
    kext = kext_info.get(device_id, "无")
    
    return status, device_id, detail, kext

def colorize_text(text, status):
    """根据支持状态返回带颜色的文本"""
    if status is None:  # 无信息
        return f"{Fore.LIGHTBLACK_EX}{text}{Style.RESET_ALL}"
    elif status == "1":  # 支持
        return f"{Fore.GREEN}{text}{Style.RESET_ALL}"
    elif status == "0":  # 不支持
        return f"{Fore.RED}{text}{Style.RESET_ALL}"
    else:  # 其他状态
        return f"{Fore.YELLOW}{text}{Style.RESET_ALL}"

def print_aligned(cols, *args):
    """打印对齐的文本，处理颜色代码"""
    if len(args) != len(cols):
        raise ValueError("参数数量与列数不匹配")
    
    parts = []
    for i, (text, col) in enumerate(zip(args, cols)):
        # 获取不带颜色的文本长度
        clean_text = re.sub(r'\x1b\[[0-9;]*m', '', str(text))
        clean_length = len(clean_text)
        
        # 如果文本太长则截断
        if clean_length > col['width']:
            text = clean_text[:col['width']-3] + '...'
            clean_text = re.sub(r'\x1b\[[0-9;]*m', '', str(text))
            clean_length = len(clean_text)
        
        # 计算需要的填充
        padding = col['width'] - clean_length
        if padding > 0:
            text = f"{text}{' ' * padding}"
        
        parts.append(text)
    
    # 用3个空格分隔各列
    print("   ".join(parts))

def get_comprehensive_hardware_info():
    # 加载所有支持信息
    gpu_support, gpu_details, gpu_kext = load_support_info("GPUSupportInfo.list")
    hda_support, hda_details, hda_kext = load_support_info("HDASupportInfo.list")
    eth_support, eth_details, eth_kext = load_support_info("ETHSupportInfo.list")
    
    c = wmi.WMI()
    
    # 列配置
    cols = [
        {'name': 'type', 'title': '硬件', 'width': 8},
        {'name': 'model', 'title': '型号', 'width': 45},
        {'name': 'id', 'title': '设备ID', 'width': 15},
        {'name': 'status', 'title': '状态', 'width': 8},
        {'name': 'detail', 'title': '支持详情', 'width': 30},
        {'name': 'kext', 'title': '所需驱动', 'width': 25}
    ]
    
    # 计算需要的终端宽度
    required_width = calculate_required_width(cols)
    current_width, _ = get_terminal_size()
    
    # 如果当前终端宽度不够，尝试调整（Windows）
    if required_width > current_width:
        try:
            STD_OUTPUT_HANDLE = -11
            handle = ctypes.windll.kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
            ctypes.windll.kernel32.SetConsoleScreenBufferSize(handle, required_width, 100)
        except:
            pass
    
    # 打印表头
    print_aligned(cols, *[col['title'] for col in cols])
    
    # 打印分隔线（使用您喜欢的等号分隔线）
    separator = "=" * required_width
    print(separator)
    
    # CPU信息
    for cpu in c.Win32_Processor():
        print_aligned(cols,
            'CPU',
            cpu.Name.strip(),
            cpu.DeviceID or '',
            '',
            '',
            ''
        )
    
    # 内存信息
    for mem in c.Win32_PhysicalMemory():
        model = f"{mem.Manufacturer or 'Unknown'} {mem.PartNumber.strip() if mem.PartNumber else ''} {int(mem.Capacity)//(1024**3)}GB"
        print_aligned(cols,
            '内存',
            model,
            mem.SerialNumber.strip() if mem.SerialNumber else '',
            '',
            '',
            ''
        )
    
    # 硬盘信息
    for disk in c.Win32_DiskDrive():
        print_aligned(cols,
            '硬盘',
            disk.Model.strip(),
            disk.DeviceID or '',
            '',
            '',
            ''
        )
    
    # 主板信息
    for board in c.Win32_BaseBoard():
        print_aligned(cols,
            '主板',
            board.Product or 'Unknown',
            board.SerialNumber or '',
            '',
            '',
            ''
        )
    
    # 显卡信息
    for gpu in c.Win32_VideoController():
        if gpu.Name.strip() not in ["Microsoft Basic Display Driver"]:
            device_id = extract_hardware_ids(gpu.PNPDeviceID)
            status, clean_id, detail, required_kext = get_support_info(device_id, gpu_support, gpu_details, gpu_kext)
            
            status_text = "支持" if status == "1" else ("不支持" if status == "0" else "未知")
            print_aligned(cols,
                '显卡',
                gpu.Name.strip(),
                colorize_text(clean_id, status),
                colorize_text(status_text, status),
                colorize_text(detail, status),
                colorize_text(required_kext, status)
            )
    
    # 声卡信息
    for sound in c.Win32_SoundDevice():
        device_id = extract_hardware_ids(sound.PNPDeviceID)
        status, clean_id, detail, required_kext = get_support_info(device_id, hda_support, hda_details, hda_kext)
        
        status_text = "支持" if status == "1" else ("不支持" if status == "0" else "未知")
        print_aligned(cols,
            '声卡',
            sound.Name,
            colorize_text(clean_id, status),
            colorize_text(status_text, status),
            colorize_text(detail, status),
            colorize_text(required_kext, status)
        )
    
    # 网卡信息
    for nic in c.Win32_NetworkAdapter(PhysicalAdapter=True):
        device_id = extract_hardware_ids(nic.PNPDeviceID)
        status, clean_id, detail, required_kext = get_support_info(device_id, eth_support, eth_details, eth_kext)
        
        status_text = "支持" if status == "1" else ("不支持" if status == "0" else "未知")
        print_aligned(cols,
            '网卡',
            nic.Name,
            colorize_text(clean_id, status),
            colorize_text(status_text, status),
            colorize_text(detail, status),
            colorize_text(required_kext, status)
        )

if __name__ == "__main__":
    get_comprehensive_hardware_info()
    input("按Enter键退出...")