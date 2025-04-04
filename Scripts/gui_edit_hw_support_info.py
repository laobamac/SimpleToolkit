'''
The MIT License (MIT)
Copyright © 2025 王孝慈

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the “Software”), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''

import PySimpleGUI as sg
import re
import os
from pathlib import Path
from typing import Dict, Tuple, List

# 定义支持文件列表及对应的颜色标签
SUPPORT_FILES = {
    "GPU支持信息": ("GPUSupportInfo.list", "显卡"),
    "声卡支持信息": ("HDASupportInfo.list", "声卡"), 
    "网卡支持信息": ("ETHSupportInfo.list", "网卡"),
}

# 创建文件如果不存在
for file, _ in SUPPORT_FILES.values():
    if not os.path.exists(file):
        Path(file).touch()

class ListFileValidator:
    """列表文件格式验证器"""
    @staticmethod
    def is_valid_entry(line: str) -> Tuple[bool, str]:
        """验证单行条目是否有效"""
        line = line.strip()
        if not line or line.startswith("#"):
            return True, ""
        
        if "=" not in line:
            return False, "缺少等号分隔符"
        
        key, value = line.split("=", 1)
        key = key.strip()
        
        # 验证设备ID格式
        if not key.endswith(('.info', '.kext')):
            if not re.match(r'^[0-9A-Fa-f]{4}&[0-9A-Fa-f]{4}$', key):
                return False, f"无效设备ID格式: {key}"
            
            if value.strip() not in ('0', '1'):
                return False, "状态值必须是0或1"
        
        return True, ""

    @staticmethod
    def parse_file(content: str) -> Dict[str, dict]:
        """解析文件内容为结构化数据"""
        result = {}
        for line in content.splitlines():
            line = line.strip()
            if not line or "=" not in line:
                continue
                
            key, value = line.split("=", 1)
            base_key = key.split(".")[0] if "." in key else key
            
            if base_key not in result:
                result[base_key] = {"main": None, "info": None, "kext": None}
            
            if key.endswith(".info"):
                result[base_key]["info"] = value.strip()
            elif key.endswith(".kext"):
                result[base_key]["kext"] = value.strip()
            else:
                result[base_key]["main"] = value.strip()
        
        return result

def create_main_window():
    """创建主编辑器窗口"""
    sg.theme('LightGrey1')
    
    layout = [
        [sg.Text("黑苹果硬件支持信息编辑器", font=("Microsoft YaHei", 14, "bold"))],
        [
            sg.Text("文件类型:", size=(8, 1)),
            sg.Combo(
                list(SUPPORT_FILES.keys()),
                key="-FILE_TYPE-",
                enable_events=True,
                size=(15, 1),
                readonly=True
            ),
            sg.Text("设备筛选:"),
            sg.Input(key="-FILTER-", size=(15, 1), enable_events=True),
            sg.Button("刷新", key="-REFRESH-")
        ],
        [
            sg.Table(
                values=[],
                headings=["设备ID", "状态", "支持详情", "所需驱动"],
                key="-ENTRY_TABLE-",
                col_widths=[12, 6, 30, 20],
                auto_size_columns=False,
                justification="left",
                select_mode=sg.TABLE_SELECT_MODE_BROWSE,
                enable_events=True,
                expand_x=True,
                expand_y=True,
                vertical_scroll_only=False
            )
        ],
        [
            sg.Frame("编辑条目", [
                [
                    sg.Text("设备ID:", size=(8, 1)),
                    sg.Input(key="-EDIT_ID-", size=(12, 1), disabled=True),
                    sg.Text("状态:"),
                    sg.Combo(["", "0", "1"], key="-EDIT_STATUS-", size=(4, 1)),
                    sg.Text("详情:"),
                    sg.Input(key="-EDIT_INFO-", size=(30, 1)),
                    sg.Text("驱动:"),
                    sg.Input(key="-EDIT_KEXT-", size=(20, 1))
                ]
            ], expand_x=True)
        ],
        [
            sg.Button("新增", key="-ADD-"),
            sg.Button("保存", key="-SAVE-"),
            sg.Button("删除", key="-DELETE-"),
            sg.Button("验证格式", key="-VALIDATE-"),
            sg.Button("退出", key="-EXIT-"),
            sg.Sizegrip()
        ],
        [sg.StatusBar("就绪", key="-STATUS-", size=(50, 1), expand_x=True)]
    ]

    window = sg.Window(
        "黑苹果支持信息编辑器 by laobamac",
        layout,
        resizable=True,
        finalize=True,
        size=(900, 600),
        element_justification='center'
    )
    window["-ENTRY_TABLE-"].expand(True, True)
    return window

def update_table(window, file_type: str, filter_str: str = "") -> None:
    filename, _ = SUPPORT_FILES[file_type]
    content = load_file_content(filename)
    entries = ListFileValidator.parse_file(content)
    
    print("entries:", entries)  # 调试输出
    
    table_data = []
    for dev_id, data in entries.items():
        if filter_str and filter_str.lower() not in dev_id.lower():
            continue
            
        status = data["main"] or ""
        info = data["info"] or ""
        kext = data["kext"] or ""
        table_data.append([dev_id, status, info, kext])
    
    print("要设置的 table_data:", table_data)  # 调试输出
    
    window["-ENTRY_TABLE-"].update(values=table_data)
    window["-STATUS-"].update(f"已加载 {len(table_data)} 条条目")
    
    # 返回表格数据用于后续操作
    return table_data

def load_file_content(filename: str) -> str:
    """加载文件内容"""
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        sg.popup_error(f"读取文件失败: {str(e)}")
        return ""

def save_file_content(filename: str, content: str) -> bool:
    """保存文件内容"""
    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    except Exception as e:
        sg.popup_error(f"保存文件失败: {str(e)}")
        return False

def generate_file_content(entries: Dict[str, dict]) -> str:
    """从条目数据生成文件内容"""
    lines = []
    for dev_id, data in entries.items():
        if data["main"] is not None:
            lines.append(f"{dev_id}={data['main']}")
        if data["info"] is not None:
            lines.append(f"{dev_id}.info={data['info']}")
        if data["kext"] is not None:
            lines.append(f"{dev_id}.kext={data['kext']}")
    return "\n".join(lines)

def validate_file_content(content: str) -> Tuple[List[str], List[str]]:
    """验证文件内容格式并返回可修复的错误"""
    error_lines = []
    repairable_errors = []
    for i, line in enumerate(content.splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        valid, msg = ListFileValidator.is_valid_entry(line)
        if not valid:
            error_entry = f"第{i}行: {msg} - {line}"
            error_lines.append(error_entry)
            # 判断是否为可自动修复的错误(格式错误或无效值)
            if "无效设备ID格式" in msg or "状态值必须是0或1" in msg or "缺少等号分隔符" in msg:
                repairable_errors.append(line)
    return error_lines, repairable_errors

def main():
    window = create_main_window()
    current_file = None
    current_entries = {}
    current_table_data = []  # 保存当前表格数据
    selected_index = None

    # 初始化默认文件（如果SUPPORT_FILES不为空）
    if SUPPORT_FILES:
        first_file_type = list(SUPPORT_FILES.keys())[0]
        window["-FILE_TYPE-"].update(first_file_type)
        current_file, _ = SUPPORT_FILES[first_file_type]
        current_entries = ListFileValidator.parse_file(load_file_content(current_file))
        current_table_data = update_table(window, first_file_type)
        window["-STATUS-"].update(f"已加载: {current_file}")

    while True:
        event, values = window.read()

        if event in (sg.WIN_CLOSED, "-EXIT-"):
            break

        elif event == "-FILE_TYPE-":
            # 文件类型选择变化
            file_type = values["-FILE_TYPE-"]
            current_file, _ = SUPPORT_FILES[file_type]
            current_entries = ListFileValidator.parse_file(load_file_content(current_file))
            current_table_data = update_table(window, file_type)
            window["-STATUS-"].update(f"已加载: {current_file}")

        elif event == "-ENTRY_TABLE-":
            # 行选择事件处理
            if values["-ENTRY_TABLE-"]:  # 确保有选择行
                selected_index = values["-ENTRY_TABLE-"][0]
                
                # 直接从当前表格数据获取（确保索引有效）
                if selected_index < len(current_table_data):
                    selected_row = current_table_data[selected_index]
                    
                    # 更新编辑区域
                    window["-EDIT_ID-"].update(selected_row[0])
                    window["-EDIT_STATUS-"].update(selected_row[1])
                    window["-EDIT_INFO-"].update(selected_row[2])
                    window["-EDIT_KEXT-"].update(selected_row[3])
                    window["-EDIT_ID-"].update(disabled=True)
                else:
                    sg.popup_error("选择的行索引无效")

        elif event == "-FILTER-" and current_file:
            # 筛选设备
            current_table_data = update_table(window, values["-FILE_TYPE-"], values["-FILTER-"])

        elif event == "-REFRESH-" and current_file:
            # 刷新数据
            current_entries = ListFileValidator.parse_file(load_file_content(current_file))
            current_table_data = update_table(window, values["-FILE_TYPE-"], values["-FILTER-"])

        elif event == "-ADD-":
            # 添加新条目
            window["-EDIT_ID-"].update("")
            window["-EDIT_STATUS-"].update("")
            window["-EDIT_INFO-"].update("")
            window["-EDIT_KEXT-"].update("")
            window["-EDIT_ID-"].update(disabled=False)
            selected_index = None

        elif event == "-SAVE-" and current_file:
            # 保存当前编辑
            dev_id = values["-EDIT_ID-"].strip().upper()
            status = values["-EDIT_STATUS-"].strip()
            info = values["-EDIT_INFO-"].strip()
            kext = values["-EDIT_KEXT-"].strip()

            if not dev_id:
                sg.popup_error("设备ID不能为空!")
                continue

            # 验证设备ID格式
            if not re.match(r'^[0-9A-F]{4}&[0-9A-F]{4}$', dev_id, re.IGNORECASE):
                sg.popup_error("设备ID格式必须为XXXX&XXXX (十六进制，如1002&67DF)")
                continue

            # 更新条目数据
            if dev_id not in current_entries:
                current_entries[dev_id] = {"main": None, "info": None, "kext": None}

            if status:
                if status not in ('0', '1'):
                    sg.popup_error("状态值必须是0或1")
                    continue
                current_entries[dev_id]["main"] = status
            if info:
                current_entries[dev_id]["info"] = info
            if kext:
                current_entries[dev_id]["kext"] = kext

            # 生成并保存文件
            content = generate_file_content(current_entries)
            if save_file_content(current_file, content):
                current_table_data = update_table(window, values["-FILE_TYPE-"], values["-FILTER-"])
                window["-STATUS-"].update(f"已保存: {current_file}")
                window["-EDIT_ID-"].update(disabled=True)

        elif event == "-DELETE-" and current_file:
            # 删除选中条目（通过selected_index或当前编辑的ID）
            dev_id = values["-EDIT_ID-"].strip()
            if not dev_id:
                sg.popup_error("没有选择要删除的条目!")
                continue

            if dev_id in current_entries:
                if sg.popup_yes_no(f"确定要删除 {dev_id} 吗?", title="确认删除") == "Yes":
                    del current_entries[dev_id]
                    content = generate_file_content(current_entries)
                    if save_file_content(current_file, content):
                        current_table_data = update_table(window, values["-FILE_TYPE-"], values["-FILTER-"])
                        window["-STATUS-"].update(f"已删除: {dev_id}")
                        # 清空编辑区
                        window["-EDIT_ID-"].update("")
                        window["-EDIT_STATUS-"].update("")
                        window["-EDIT_INFO-"].update("")
                        window["-EDIT_KEXT-"].update("")

        elif event == "-VALIDATE-" and current_file:
            # 验证文件格式
            content = load_file_content(current_file)
            errors, repairable_errors = validate_file_content(content)
            
            if errors:
                # 准备可修复错误显示文本
                repairable_text = "可自动修复的问题行:\n"
                if repairable_errors:
                    repairable_text += "\n".join([f"第{content.splitlines().index(line)+1}行: {line}" 
                                               for line in repairable_errors])
                else:
                    repairable_text += "无"
                
                # 创建验证结果窗口
                layout = [
                    [sg.Text("发现以下格式问题:", font=("Microsoft YaHei", 10, "bold"))],
                    [sg.Multiline("\n".join(errors), size=(60, 10), disabled=True)],
                    [sg.Text(repairable_text, size=(60, 5))],
                    [sg.Button("自动修复", key="-REPAIR-", disabled=not repairable_errors), 
                     sg.Button("关闭", key="-CLOSE-")]
                ]
                
                validate_window = sg.Window("验证结果", layout, modal=True)
                
                while True:
                    event_validate, _ = validate_window.read()
                    if event_validate in (sg.WIN_CLOSED, "-CLOSE-"):
                        break
                    elif event_validate == "-REPAIR-" and repairable_errors:
                        # 执行自动修复 - 删除有问题的行
                        lines = content.splitlines()
                        # 保留有效的行
                        repaired_lines = [line for line in lines 
                                        if line.strip() and line.strip() not in repairable_errors]
                        
                        # 保存修复后的内容
                        repaired_content = "\n".join(repaired_lines)
                        if save_file_content(current_file, repaired_content):
                            # 刷新数据
                            current_entries = ListFileValidator.parse_file(repaired_content)
                            current_table_data = update_table(window, values["-FILE_TYPE-"], values["-FILTER-"])
                            sg.popup_ok(f"已自动修复 {len(repairable_errors)} 处问题", title="修复完成")
                            validate_window.close()
                            break
                
                validate_window.close()
            else:
                sg.popup_ok("文件格式验证通过!", title="验证结果")

    window.close()


if __name__ == "__main__":
    main()