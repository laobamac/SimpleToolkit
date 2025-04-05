'''
The MIT License (MIT)
Copyright © 2025 王孝慈

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
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
        value = value.strip()
        
        # 验证设备ID格式
        if not key.endswith(('.info', '.kext')):
            if not re.match(r'^[0-9A-Fa-f]{4}&[0-9A-Fa-f]{4}$', key):
                return False, f"无效设备ID格式: {key}"
            
            # 状态值不能为空且必须是0或1
            if not value:
                return False, "状态值不能为空"
            if value not in ('0', '1'):
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
            key = key.strip()
            value = value.strip()
            base_key = key.split(".")[0] if "." in key else key
            
            if base_key not in result:
                result[base_key] = {"main": None, "info": None, "kext": None}
            
            if key.endswith(".info"):
                result[base_key]["info"] = value if value else None
            elif key.endswith(".kext"):
                result[base_key]["kext"] = value if value else None
            else:
                result[base_key]["main"] = value if value else None
        
        return result

def create_import_window():
    """创建导入选项窗口"""
    layout = [
        [sg.Text("选择要导入的信息类型:", font=("Microsoft YaHei", 10))],
        [
            sg.Checkbox("设备ID和状态", default=True, key="-IMPORT_MAIN-"),
            sg.Checkbox("支持详情", default=True, key="-IMPORT_INFO-"),
            sg.Checkbox("所需驱动", default=True, key="-IMPORT_KEXT-")
        ],
        [
            sg.Checkbox("覆盖现有条目", default=False, key="-OVERWRITE-"),
            sg.Checkbox("跳过格式错误行", default=True, key="-SKIP_ERRORS-")
        ],
        [
            sg.Button("选择文件并导入", key="-SELECT_IMPORT-"),
            sg.Button("取消", key="-CANCEL-")
        ]
    ]
    
    return sg.Window("导入选项", layout, modal=True)

def show_import_result(imported_count: int, skipped_count: int, skip_details: List[Tuple[str, str]]):
    """显示导入结果窗口"""
    result_layout = [
        [sg.Text(f"导入完成!\n成功导入: {imported_count} 条\n跳过: {skipped_count} 条")],
        [sg.Button("查看跳过详情", key="-VIEW_DETAILS-", disabled=not skip_details),
         sg.Button("确定", key="-OK-")]
    ]
    
    result_window = sg.Window("导入结果", result_layout, modal=True)
    
    while True:
        event_result, _ = result_window.read()
        if event_result in (sg.WIN_CLOSED, "-OK-"):
            break
        elif event_result == "-VIEW_DETAILS-" and skip_details:
            result_window.close()
            show_skip_details(skip_details)
            break
    
    result_window.close()

def show_skip_details(skip_details: List[Tuple[str, str]]):
    """显示跳过详情窗口"""
    table_values = [[item[0], item[1]] for item in skip_details]
    
    layout = [
        [sg.Text("跳过的条目详情", font=("Microsoft YaHei", 10, "bold"))],
        [sg.Table(
            values=table_values,
            headings=["条目", "原因"],
            auto_size_columns=True,
            display_row_numbers=True,
            justification='left',
            key='-SKIP_DETAILS-',
            expand_x=True,
            expand_y=True,
            num_rows=min(20, len(table_values)))
        ],
        [sg.Button("关闭", key="-CLOSE-")]
    ]
    
    detail_window = sg.Window("导入跳过详情", layout, modal=True)
    while True:
        event_detail, _ = detail_window.read()
        if event_detail in (sg.WIN_CLOSED, "-CLOSE-"):
            break
    detail_window.close()

def import_entries(window, current_entries: Dict[str, dict], current_file: str, import_options: dict, import_file: str) -> Dict[str, dict]:
    """导入条目到当前文件中"""
    # 读取导入文件内容
    try:
        with open(import_file, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        sg.popup_error(f"无法读取导入文件: {str(e)}")
        return current_entries
    
    # 解析导入文件内容
    imported_entries = {}
    skip_details = []
    
    # 先验证并解析所有条目
    for line_num, line in enumerate(content.splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
            
        # 验证格式
        valid, msg = ListFileValidator.is_valid_entry(line)
        if not valid and import_options["-SKIP_ERRORS-"]:
            skip_details.append((f"第{line_num}行", f"格式错误: {msg}"))
            continue
        elif not valid:
            sg.popup_error(f"第{line_num}行格式错误: {msg}")
            return current_entries
            
        # 解析有效条目
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        base_key = key.split(".")[0] if "." in key else key
        
        if base_key not in imported_entries:
            imported_entries[base_key] = {"main": None, "info": None, "kext": None}
        
        if key.endswith(".info"):
            imported_entries[base_key]["info"] = value if value else None
        elif key.endswith(".kext"):
            imported_entries[base_key]["kext"] = value if value else None
        else:
            imported_entries[base_key]["main"] = value if value else None
    
    # 处理导入逻辑
    imported_count = 0
    skipped_count = len(skip_details)
    overwrite = import_options["-OVERWRITE-"]
    
    for dev_id, data in imported_entries.items():
        # 检查是否已存在且不覆盖
        if dev_id in current_entries and not overwrite:
            skip_details.append((dev_id, "已存在且不覆盖"))
            skipped_count += 1
            continue
        
        # 检查是否有任何可导入的字段
        has_importable_data = False
        if import_options["-IMPORT_MAIN-"] and data.get("main") is not None:
            has_importable_data = True
        if import_options["-IMPORT_INFO-"] and data.get("info") is not None:
            has_importable_data = True
        if import_options["-IMPORT_KEXT-"] and data.get("kext") is not None:
            has_importable_data = True
        
        if not has_importable_data:
            skip_details.append((dev_id, "没有可导入的字段"))
            skipped_count += 1
            continue
        
        # 如果是新条目，直接创建
        if dev_id not in current_entries:
            current_entries[dev_id] = {"main": None, "info": None, "kext": None}
        
        # 根据选项更新数据
        if import_options["-IMPORT_MAIN-"] and data.get("main") is not None:
            current_entries[dev_id]["main"] = data["main"]
        if import_options["-IMPORT_INFO-"] and data.get("info") is not None:
            current_entries[dev_id]["info"] = data["info"]
        if import_options["-IMPORT_KEXT-"] and data.get("kext") is not None:
            current_entries[dev_id]["kext"] = data["kext"]
        
        imported_count += 1
    
    # 保存更新后的内容
    new_content = generate_file_content(current_entries)
    if save_file_content(current_file, new_content):
        show_import_result(imported_count, skipped_count, skip_details)
    
    return current_entries

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
            sg.Button("刷新", key="-REFRESH-"),
            sg.Button("导入", key="-IMPORT-")
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
    
    table_data = []
    for dev_id, data in entries.items():
        if filter_str and filter_str.lower() not in dev_id.lower():
            continue
            
        status = data["main"] or ""
        info = data["info"] or ""
        kext = data["kext"] or ""
        table_data.append([dev_id, status, info, kext])
    
    window["-ENTRY_TABLE-"].update(values=table_data)
    window["-STATUS-"].update(f"已加载 {len(table_data)} 条条目")
    
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
            if "无效设备ID格式" in msg or "状态值必须是0或1" in msg or "缺少等号分隔符" in msg:
                repairable_errors.append(line)
    return error_lines, repairable_errors

def main():
    window = create_main_window()
    current_file = None
    current_entries = {}
    current_table_data = []
    selected_index = None

    # 初始化加载第一个文件的数据
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
            file_type = values["-FILE_TYPE-"]
            current_file, _ = SUPPORT_FILES[file_type]
            current_entries = ListFileValidator.parse_file(load_file_content(current_file))
            current_table_data = update_table(window, file_type)
            window["-STATUS-"].update(f"已加载: {current_file}")

        elif event == "-ENTRY_TABLE-":
            if values["-ENTRY_TABLE-"]:
                selected_index = values["-ENTRY_TABLE-"][0]
                if selected_index < len(current_table_data):
                    selected_row = current_table_data[selected_index]
                    window["-EDIT_ID-"].update(selected_row[0])
                    window["-EDIT_STATUS-"].update(selected_row[1])
                    window["-EDIT_INFO-"].update(selected_row[2])
                    window["-EDIT_KEXT-"].update(selected_row[3])
                    window["-EDIT_ID-"].update(disabled=True)
                else:
                    sg.popup_error("选择的行索引无效")

        elif event == "-FILTER-" and current_file:
            current_table_data = update_table(window, values["-FILE_TYPE-"], values["-FILTER-"])

        elif event == "-REFRESH-" and current_file:
            current_entries = ListFileValidator.parse_file(load_file_content(current_file))
            current_table_data = update_table(window, values["-FILE_TYPE-"], values["-FILTER-"])

        elif event == "-ADD-":
            window["-EDIT_ID-"].update("")
            window["-EDIT_STATUS-"].update("")
            window["-EDIT_INFO-"].update("")
            window["-EDIT_KEXT-"].update("")
            window["-EDIT_ID-"].update(disabled=False)
            selected_index = None

        elif event == "-SAVE-" and current_file:
            dev_id = values["-EDIT_ID-"].strip().upper()
            status = values["-EDIT_STATUS-"].strip()
            info = values["-EDIT_INFO-"].strip()
            kext = values["-EDIT_KEXT-"].strip()

            if not dev_id:
                sg.popup_error("设备ID不能为空!")
                continue

            if not re.match(r'^[0-9A-F]{4}&[0-9A-F]{4}$', dev_id, re.IGNORECASE):
                sg.popup_error("设备ID格式必须为XXXX&XXXX (十六进制，如1002&67DF)")
                continue

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

            content = generate_file_content(current_entries)
            if save_file_content(current_file, content):
                current_table_data = update_table(window, values["-FILE_TYPE-"], values["-FILTER-"])
                window["-STATUS-"].update(f"已保存: {current_file}")
                window["-EDIT_ID-"].update(disabled=True)

        elif event == "-DELETE-" and current_file:
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
                        window["-EDIT_ID-"].update("")
                        window["-EDIT_STATUS-"].update("")
                        window["-EDIT_INFO-"].update("")
                        window["-EDIT_KEXT-"].update("")

        elif event == "-VALIDATE-" and current_file:
            content = load_file_content(current_file)
            errors, repairable_errors = validate_file_content(content)
            
            if errors:
                repairable_text = "可自动修复的问题行:\n"
                if repairable_errors:
                    repairable_text += "\n".join([f"第{content.splitlines().index(line)+1}行: {line}" 
                                               for line in repairable_errors])
                else:
                    repairable_text += "无"
                
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
                        lines = content.splitlines()
                        repaired_lines = [line for line in lines 
                                        if line.strip() and line.strip() not in repairable_errors]
                        
                        repaired_content = "\n".join(repaired_lines)
                        if save_file_content(current_file, repaired_content):
                            current_entries = ListFileValidator.parse_file(repaired_content)
                            current_table_data = update_table(window, values["-FILE_TYPE-"], values["-FILTER-"])
                            sg.popup_ok(f"已自动修复 {len(repairable_errors)} 处问题", title="修复完成")
                            validate_window.close()
                            break
                
                validate_window.close()
            else:
                sg.popup_ok("文件格式验证通过!", title="验证结果")

        elif event == "-IMPORT-" and current_file:
            import_window = create_import_window()
            
            while True:
                event_import, values_import = import_window.read()
                
                if event_import in (sg.WIN_CLOSED, "-CANCEL-"):
                    break
                elif event_import == "-SELECT_IMPORT-":
                    if not any([values_import["-IMPORT_MAIN-"], values_import["-IMPORT_INFO-"], values_import["-IMPORT_KEXT-"]]):
                        sg.popup_error("请至少选择一项要导入的信息类型!")
                        continue
                    
                    # 让用户选择要导入的文件
                    import_file = sg.popup_get_file("选择要导入的文件", file_types=(("列表文件", "*.list"), ("文本文件", "*.txt"), ("所有文件", "*.*")))
                    if not import_file:
                        continue
                    
                    import_window.close()
                    current_entries = import_entries(window, current_entries, current_file, values_import, import_file)
                    current_table_data = update_table(window, values["-FILE_TYPE-"], values["-FILTER-"])
                    break
            
            import_window.close()

    window.close()

if __name__ == "__main__":
    main()