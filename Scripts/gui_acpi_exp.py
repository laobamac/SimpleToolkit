'''
The MIT License (MIT)
Copyright © 2025 王孝慈

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the “Software”), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''

import shutil
import sys
import json
import os
import tempfile
import re
import subprocess
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget, QTableWidget, QTableWidgetItem,
    QTextEdit, QHBoxLayout, QLabel, QLineEdit, QPushButton, QHeaderView,
    QMessageBox, QProgressBar, QFileDialog, QDialog, QGroupBox
)
from PySide6.QtCore import Qt, QSize, QThread, Signal
from PySide6.QtGui import QFont, QIcon, QColor

CACHE_FILE = "device_cache.json"

class SSDTBuilder:
    """完整的SSDT构建工具类"""
    RESOURCES_DIR = "Resources"
    TEMPLATES = {
        # 禁用类
        'disable_s3': "SSDT-NDGP_PS3.dsl",
        'disable_off': "SSDT-NDGP_OFF.dsl",
        'disable_ioname': "SSDT-NDGP_IOName.dsl",
        # 仿冒类
        'spoof_generic': "SSDT-SH-SPOOF.dsl",
        'spoof_rx6500': "SSDT-6x50XT-GPU-SPOOF.dsl"
    }


    @classmethod
    def validate_device_id(cls, device_id, parent_window=None):
        """
        验证设备ID格式
        :param device_id: 待验证的ID字符串
        :param parent_window: 用于显示错误消息的父窗口
        :return: 是否有效
        """
        if not re.match(r'^[0-9a-fA-F]{4}$', device_id):
            if parent_window:
                QMessageBox.warning(
                    parent_window,
                    "格式错误",
                    "设备ID必须是4位16进制字符\n(例如：67DF、73BF等)",
                    QMessageBox.Ok
                )
            return False
        return True

    @classmethod
    def build_disable_ssdt(cls, acpi_paths, method, parent_window):
        """
        构建禁用设备的SSDT
        :param acpi_paths: 已转义为ACPI格式的路径列表 (如 ["SB.PCI0.GFX0"])
        :param method: 禁用方法 (s3/off/ioname)
        :param parent_window: 父窗口对象
        :return: 是否成功
        """
        # 验证输入
        if not cls._validate_input(acpi_paths, method, parent_window):
            return False

        # 获取模板路径
        template_file = cls._get_template_path(f'disable_{method}', parent_window)
        if not template_file:
            return False

        # 选择输出目录
        output_dir = cls._select_output_dir(parent_window)
        if not output_dir:
            return False

        success_count = 0
        for i, path in enumerate(acpi_paths, 1):
            # 读取并修改模板
            with open(template_file, "r", encoding="utf-8") as f:
                content = f.read().replace("{ADDR}", path)

            # 生成临时文件
            temp_dsl = os.path.join(output_dir, f"SSDT-DISABLE-{method.upper()}-{i}.dsl")
            if not cls._write_temp_file(temp_dsl, content, parent_window):
                continue

            # 编译AML
            if cls.compile_aml(temp_dsl, parent_window):
                success_count += 1
                cls._cleanup_temp_files(temp_dsl)

        # 结果处理
        if success_count > 0:
            cls._show_success(parent_window, output_dir, f"成功生成 {success_count}/{len(acpi_paths)} 个SSDT文件")
            return True
        return False

    @classmethod
    def build_gpu_spoof_ssdt(cls, acpi_path, device_id, model_name=None, is_rx6500=False, parent_window=None):
        """简化构建方法"""
        # 验证设备ID（只需验证仿冒ID）
        if not cls.validate_device_id(device_id, parent_window):
            return False

        # 获取模板路径
        template_type = 'spoof_rx6500' if is_rx6500 else 'spoof_generic'
        template_file = resource_path(os.path.join("Resources", "dsl", cls.TEMPLATES[template_type]))
    
        if not os.path.exists(template_file):
            QMessageBox.critical(parent_window, "错误", f"模板文件缺失: {os.path.basename(template_file)}")
            return False

        # 选择输出目录
        output_dir = QFileDialog.getExistingDirectory(parent_window, "选择SSDT保存目录")
        if not output_dir:
            return False

        # 处理设备ID字节序 (0xABCD -> 高字节CD, 低字节AB)
        device_id = device_id.lower().strip()
        high_byte = f"0x{device_id[2:]}"
        low_byte = f"0x{device_id[:2]}"

        # 读取并修改模板
        with open(template_file, "r", encoding="utf-8") as f:
            content = f.read()
        parts = acpi_path.split('.')
        peg_idx = next((i for i in range(len(parts)-1, -1, -1) 
                      if parts[i].startswith('PEGP')), -1)
        if peg_idx != -1:
           acpi_path_pegp = '.'.join(parts[:peg_idx])  # PEGP前
    
        # modified_content = content.replace("{ADDR}", acpi_path_pegp)
        if template_type == "spoof_generic":
           modified_content = content.replace("{ADDR}", acpi_path)
        elif template_type == "spoof_rx6500":
            modified_content = content.replace("{ADDR}", acpi_path_pegp)

        modified_content = modified_content.replace("0xAB", high_byte).replace("0xCD", low_byte)
    
        # RX6500模板不需要型号替换
        if not is_rx6500 and model_name:
            modified_content = modified_content.replace("{MODEL}", model_name)

        # 生成输出文件
        suffix = "RX6x50" if is_rx6500 else "GPU"
        output_dsl = os.path.join(output_dir, f"SSDT-SPOOF-{suffix}.dsl")
    
        try:
            with open(output_dsl, "w", encoding="utf-8") as f:
                f.write(modified_content)
        
            if cls.compile_aml(output_dsl, parent_window):
                os.remove(output_dsl)  # 删除临时DSL
                cls._show_success(parent_window, output_dir)
                return True
        except Exception as e:
            QMessageBox.critical(parent_window, "错误", f"文件保存失败: {str(e)}")
    
        return False

    @classmethod
    def compile_aml(cls, dsl_path, parent_window):
        """编译DSL为AML"""
        iasl_path = resource_path(os.path.join(cls.RESOURCES_DIR, "iasl", "iasl.exe"))
        
        if not os.path.exists(iasl_path):
            QMessageBox.critical(parent_window, "错误", 
                f"未找到IASL编译器！请确认 {iasl_path} 存在")
            return False

        try:
            result = subprocess.run(
                [iasl_path, dsl_path],
                capture_output=True,
                text=True,
                cwd=os.path.dirname(dsl_path)
            )
            
            if result.returncode != 0:
                error_msg = f"编译失败:\n{result.stderr}" if result.stderr else "未知错误"
                QMessageBox.critical(parent_window, "编译错误", error_msg)
                return False
            return True
            
        except Exception as e:
            QMessageBox.critical(parent_window, "异常错误", f"编译器执行出错: {str(e)}")
            return False

    # ======================== 私有方法 ========================
    @classmethod
    def _validate_input(cls, acpi_paths, method, parent_window):
        """验证禁用SSDT的输入参数"""
        if not acpi_paths:
            QMessageBox.warning(parent_window, "错误", "没有有效的ACPI路径！")
            return False
            
        if method not in ['s3', 'off', 'ioname']:
            QMessageBox.warning(parent_window, "错误", f"无效的禁用方法: {method}")
            return False
            
        return True

    @classmethod
    def _validate_spoof_input(cls, acpi_path, device_id, model_name, is_rx6500, parent_window):
        """验证仿冒SSDT的输入参数"""
        if not acpi_path:
            QMessageBox.warning(parent_window, "错误", "无效的ACPI路径！")
            return False
            
        if not re.match(r'^[0-9a-fA-F]{4}$', device_id):
            QMessageBox.warning(parent_window, "格式错误", 
                "设备ID必须是4位16进制字符 (如67DF)")
            return False
            
        if not is_rx6500 and not model_name:
            QMessageBox.warning(parent_window, "缺少参数", 
                "普通GPU仿冒需要指定显示名称！")
            return False
            
        return True

    @classmethod
    def _get_template_path(cls, template_type, parent_window):
        """获取模板文件路径"""
        template_file = resource_path(
            os.path.join(cls.RESOURCES_DIR, "dsl", cls.TEMPLATES.get(template_type, ""))
        )
    
        if not os.path.exists(template_file):
            QMessageBox.critical(parent_window, "错误", 
                f"模板文件缺失: {os.path.basename(template_file)}")
            return None
        
        return template_file

    @classmethod
    def _select_output_dir(cls, parent_window):
        """选择输出目录"""
        output_dir = QFileDialog.getExistingDirectory(
            parent_window, 
            "选择SSDT保存目录",
            os.path.expanduser("~/Desktop")
        )
        return output_dir if output_dir else None

    @classmethod
    def _write_temp_file(cls, file_path, content, parent_window):
        """写入临时文件"""
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return True
        except Exception as e:
            QMessageBox.critical(parent_window, "文件错误", 
                f"无法写入临时文件:\n{str(e)}")
            return False

    @classmethod
    def _cleanup_temp_files(cls, dsl_path):
        """清理临时文件"""
        try:
            # 删除DSL文件
            if os.path.exists(dsl_path):
                os.remove(dsl_path)
                
            # 删除编译日志
            log_file = dsl_path.replace(".dsl", ".aml.log")
            if os.path.exists(log_file):
                os.remove(log_file)
        except:
            pass

    @classmethod
    def _show_success(cls, parent_window, output_dir, message=None):
        """显示成功提示"""
        msg = message or "SSDT文件生成成功！"
        reply = QMessageBox.question(
            parent_window, "完成", 
            f"{msg}\n文件已保存到:\n{output_dir}\n\n是否打开目录？",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            os.startfile(output_dir)

class RX6500SpoofDialog(QDialog):
    """RX 6x50 XT专用对话框"""
    def __init__(self, parent=None, acpi_path=""):
        super().__init__(parent)
        self.acpi_path = acpi_path
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("RX 6x50 XT仿冒设置")
        self.setFixedSize(400, 200)  # 缩小对话框尺寸
        
        layout = QVBoxLayout(self)
        
        # 设备信息
        info_group = QGroupBox("目标设备")
        info_layout = QVBoxLayout()
        info_layout.addWidget(QLabel(f"ACPI路径: {self.acpi_path}"))
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        # 只需要输入仿冒ID
        param_group = QGroupBox("仿冒参数")
        param_layout = QVBoxLayout()
        
        self.spoof_id_input = QLineEdit()
        self.spoof_id_input.setPlaceholderText("输入仿冒设备ID (如67DF)")
        param_layout.addWidget(QLabel("仿冒设备ID (4位16进制):"))
        param_layout.addWidget(self.spoof_id_input)
        
        param_group.setLayout(param_layout)
        layout.addWidget(param_group)

        # 操作按钮
        btn_layout = QHBoxLayout()
        generate_btn = QPushButton("生成SSDT")
        generate_btn.clicked.connect(self.generate_ssdt)
        btn_layout.addWidget(generate_btn)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)

    def generate_ssdt(self):
        """生成专用SSDT（简化版）"""
        spoof_id = self.spoof_id_input.text().strip()
        
        if not SSDTBuilder.validate_device_id(spoof_id, self):
            return
            
        # 直接使用专用模板生成
        SSDTBuilder.build_gpu_spoof_ssdt(
            acpi_path=self.acpi_path,
            device_id=spoof_id,
            is_rx6500=True,
            parent_window=self
        )

# ======================== 路径转义工具函数 ========================
def convert_pci_path(win_path):
    """转换 Windows PCI 路径为 ACPI 格式"""
    if not win_path.startswith("PCIROOT"):
        return None
    
    parts = win_path.split("#")
    acpi_path = []
    
    for part in parts:
        if part.startswith("PCIROOT"):
            root_num = re.search(r"PCIROOT\((\d+)\)", part).group(1)
            acpi_path.append(f"PciRoot(0x{int(root_num):X})")
        elif part.startswith("PCI"):
            pci_num = re.search(r"PCI\(([0-9A-Fa-f]+)\)", part).group(1)
            if len(pci_num) == 4:
                bus = pci_num[:2].lstrip("0") or "0"
                dev = pci_num[2:].lstrip("0") or "0"
            else:
                bus = pci_num[:2].lstrip("0") or "0"
                dev = pci_num[2:].lstrip("0") or "0"
            acpi_path.append(f"Pci(0x{bus},0x{dev})")
        else:
            return None
    
    return "/".join(acpi_path)

def convert_acpi_path(win_path):
    """转换 Windows ACPI 路径为标准格式"""
    parts = win_path.split("#")
    acpi_path = []
    
    for part in parts:
        if part.startswith("ACPI"):
            name = re.search(r"ACPI\(([^)]+)\)", part).group(1)
            acpi_path.append(name.strip("_"))
        else:
            return None
    
    return ".".join(acpi_path)

# ======================== 后台线程 ========================
class DeviceLoaderThread(QThread):
    data_loaded = Signal(list)
    progress_update = Signal(int, str)
    log_update = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.process = None
        self._is_running = True

    def run(self):
        try:
            self.log_update.emit("=== 开始获取设备列表 ===")
            self.progress_update.emit(10, "正在获取设备列表...")
            
            command = """
            [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
            Get-PnpDevice | Where-Object { 
                $_.Class -notin @('Processor', 'System') 
            } | ForEach-Object {
                $prop = $_ | Get-PnpDeviceProperty -KeyName 'DEVPKEY_Device_LocationPaths' -ErrorAction SilentlyContinue;
                if ($prop -and $prop.Data -ne $null) {
                    $json = [PSCustomObject]@{
                        DeviceName = $_.FriendlyName;
                        LocationPaths = $prop.Data;
                        Status = $_.Status;
                        Class = $_.Class;
                    } | ConvertTo-Json -Compress
                    Write-Output $json
                    # 小延迟以便GUI能及时更新
                    Start-Sleep -Milliseconds 30
                }
            }
            """
            self.log_update.emit("执行 PowerShell 命令...")
            self.progress_update.emit(30, "正在执行 PowerShell...")

            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE

            # 创建进程并实时读取输出
            self.process = subprocess.Popen(
                ["C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe", "-Command", command],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE,  # 添加stdin管道以便可以发送关闭信号
                text=True,
                encoding='utf-8',
                errors='replace',
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
            )

            devices = []
            while self._is_running:
                # 非阻塞读取
                line = self.process.stdout.readline()
                if not line:
                    if self.process.poll() is not None:  # 进程已结束
                        break
                    continue
                
                line = line.strip()
                if line:
                    self.log_update.emit(line)
                    try:
                        devices.append(json.loads(line))
                    except json.JSONDecodeError as e:
                        self.log_update.emit(f"JSON解析错误: {str(e)} - 原始行: {line}")

            # 检查是否正常结束
            if self._is_running and self.process.poll() is None:
                self.log_update.emit("正在等待进程结束...")
                self.process.wait(timeout=5)

            # 保存结果
            self.progress_update.emit(90, "正在保存缓存...")
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(devices, f, ensure_ascii=False, indent=2)

            self.data_loaded.emit(devices)
            self.progress_update.emit(100, "加载完成！")
            self.log_update.emit("=== 设备列表获取完成 ===")

        except Exception as e:
            self.log_update.emit(f"[异常] {str(e)}")
            self.progress_update.emit(100, f"错误: {str(e)}")
        finally:
            self.terminate_process()

    def terminate_process(self):
        """确保终止PowerShell进程"""
        if self.process and self.process.poll() is None:
            try:
                # 尝试优雅终止
                self.process.terminate()
                self.process.wait(timeout=2)
                if self.process.poll() is None:  # 如果还在运行
                    self.process.kill()
            except Exception as e:
                self.log_update.emit(f"终止进程时出错: {str(e)}")

    def stop(self):
        """安全停止线程"""
        self._is_running = False
        self.terminate_process()
        self.quit()
        self.wait(2000)  # 等待线程结束

def resource_path(relative_path):
    """获取资源的绝对路径"""
    try:
        # PyInstaller创建的临时文件夹路径
        base_path = sys._MEIPASS
    except Exception:
        # 开发环境中的路径
        base_path = os.path.abspath(".")
    
    path = os.path.join(base_path, relative_path)
    return os.path.normpath(path)

class SSDTFunctionDialog(QDialog):
    """通用SSDT功能对话框"""
    def __init__(self, parent=None, device_info=None, method=None):
        super().__init__(parent)
        self.device_info = device_info
        self.method = method
        self.setup_ui()
    
    def setup_ui(self):
        self.setWindowTitle("SSDT生成设置")
        self.setMinimumSize(500, 300)
        
        layout = QVBoxLayout(self)
        
        # 设备信息
        info_group = QGroupBox("目标设备")
        info_layout = QVBoxLayout()
        info_layout.addWidget(QLabel(f"设备: {self.device_info.get('DeviceName', '')}"))
        
        acpi_paths = [convert_acpi_path(p) for p in self.device_info.get("LocationPaths", [])]
        acpi_paths = [p for p in acpi_paths if p]
        path_text = "\n".join(acpi_paths) if acpi_paths else "无有效ACPI路径"
        info_layout.addWidget(QLabel(f"ACPI路径:\n{path_text}"))
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # 参数输入（根据不同类型显示）
        if self.method.startswith("spoof"):
            self.setup_spoof_ui(layout)
        else:
            self.setup_disable_ui(layout)
        
        # 操作按钮
        btn_layout = QHBoxLayout()
        generate_btn = QPushButton("生成SSDT")
        generate_btn.clicked.connect(self.generate_ssdt)
        btn_layout.addWidget(generate_btn)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
    
    def setup_spoof_ui(self, layout):
        """设置仿冒参数UI"""
        param_group = QGroupBox("仿冒参数")
        param_layout = QVBoxLayout()
        
        self.device_id_input = QLineEdit()
        self.device_id_input.setPlaceholderText("输入4位16进制设备ID (如67DF)")
        param_layout.addWidget(QLabel("设备ID:"))
        param_layout.addWidget(self.device_id_input)
        
        if self.method == "spoof_generic":
            self.model_input = QLineEdit()
            self.model_input.setPlaceholderText("输入显示名称 (如Radeon RX 6900 XT)")
            param_layout.addWidget(QLabel("显示名称:"))
            param_layout.addWidget(self.model_input)
        
        param_group.setLayout(param_layout)
        layout.addWidget(param_group)
    
    def setup_disable_ui(self, layout):
        """设置禁用参数UI"""
        info_label = QLabel(f"将生成 {self.method.split('_')[-1].upper()} 类型的禁用SSDT")
        info_label.setStyleSheet("font-weight: bold; color: #AA0000;")
        layout.addWidget(info_label)
    
    def generate_ssdt(self):
        """生成SSDT文件"""
        acpi_paths = [convert_acpi_path(p) for p in self.device_info.get("LocationPaths", [])]
        acpi_paths = [p for p in acpi_paths if p]
        
        if self.method.startswith("disable"):
            SSDTBuilder.build_disable_ssdt(acpi_paths, self.method.split('_')[-1], self)
        else:
            device_id = self.device_id_input.text().strip()
            model_name = getattr(self, 'model_input', None) and self.model_input.text().strip()
            
            SSDTBuilder.build_gpu_spoof_ssdt(
                acpi_path=acpi_paths[0],
                device_id=device_id,
                model_name=model_name,
                is_rx6500=(self.method == "spoof_rx6500"),
                parent_window=self
            )

# ======================== 主窗口 ========================
class DeviceLocationViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.devices = []
        self.device_table = None
        self.loader_thread = None  # 显式初始化
        self.setup_ui()
        self.setup_ssdt_menu()
        self.check_cache()
        self.log_text = ""
        self.log_dialog = None
        # 初始化日志文件路径
        self.log_file_path = os.path.join(tempfile.gettempdir(), "acpi_helper_log.txt")
        self.ensure_log_file()

    def closeEvent(self, event):
        """重写关闭事件以确保线程和进程被正确清理"""
        if self.loader_thread and self.loader_thread.isRunning():
            self.loader_thread.stop()
            if not self.loader_thread.wait(3000):  # 等待3秒
                self.loader_thread.terminate()
        event.accept()

    def setup_ui(self):
        # 主窗口设置
        self.setWindowTitle("ACPI设备助手 by laobamac - V1.2")
        self.setMinimumSize(900, 650)
        
        # 主控件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # 1. 标题栏
        title_layout = QHBoxLayout()
        title = QLabel("📌 ACPI设备助手")
        title.setFont(QFont("Microsoft YaHei", 16, QFont.Bold))
        refresh_btn = QPushButton("🔄 刷新数据")
        refresh_btn.setFont(QFont("Microsoft YaHei", 11))
        title_layout.addWidget(title)
        title_layout.addStretch()
        title_layout.addWidget(refresh_btn)
        main_layout.addLayout(title_layout)
        refresh_btn.clicked.connect(self.refresh_data)

        # 2. 搜索栏
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setFont(QFont("Microsoft YaHei", 12))
        self.search_input.setPlaceholderText("输入设备名称搜索...")
        search_btn = QPushButton("🔍 搜索")
        search_btn.setFont(QFont("Microsoft YaHei", 12))
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(search_btn)
        main_layout.addLayout(search_layout)
        search_btn.clicked.connect(self.filter_devices)
        self.search_input.returnPressed.connect(self.filter_devices)

        # 3. 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setFont(QFont("Microsoft YaHei", 10))
        main_layout.addWidget(self.progress_bar)
        self.log_button = QPushButton("📄 查看日志")
        self.log_button.setFont(QFont("Microsoft YaHei", 10))
        self.log_button.hide()  # 默认隐藏
        main_layout.addWidget(self.log_button, alignment=Qt.AlignRight)
        self.log_button.clicked.connect(self.show_log_dialog)

        # 初始化日志文件路径
        self.log_file_path = os.path.join(tempfile.gettempdir(), "acpi_helper_log.txt")
        self.log_dialog = None
        self.ensure_log_file()
        

        # 4. 主内容区（表格+详情）
        content_layout = QHBoxLayout()
        
        # 4.1 设备表格（现在才初始化device_table）
        self.device_table = QTableWidget()
        self.device_table.setEditTriggers(QTableWidget.NoEditTriggers)  # 现在可以安全设置
        self.device_table.setColumnCount(3)
        self.device_table.setHorizontalHeaderLabels(["设备名称", "状态", "类别"])
        self.device_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.device_table.verticalHeader().setDefaultSectionSize(28)
        self.device_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.device_table.setFont(QFont("Microsoft YaHei", 11))
        self.device_table.cellClicked.connect(self.show_location_details)
        content_layout.addWidget(self.device_table, 60)  # 60%宽度

        # 4.2 详情框
        self.details_text = QTextEdit()
        self.details_text.setFont(QFont("Microsoft YaHei", 11))
        self.details_text.setReadOnly(True)
        self.details_text.setStyleSheet("""
            QTextEdit {
                background-color: #F5F5F5;
                padding: 8px;
            }
        """)
        content_layout.addWidget(self.details_text, 40)  # 40%宽度
        
        main_layout.addLayout(content_layout)

        help_menu = self.menuBar().addMenu("帮助")
        about_action = help_menu.addAction("关于")
        about_action.triggered.connect(self.show_about_dialog)

        # 5. 复制按钮
        copy_btn = QPushButton("📋 复制路径")
        copy_btn.setFont(QFont("Microsoft YaHei", 12))
        copy_btn.clicked.connect(self.copy_to_clipboard)
        main_layout.addWidget(copy_btn, alignment=Qt.AlignRight)

    def ensure_log_file(self):
        """确保日志文件存在"""
        if not os.path.exists(self.log_file_path):
            with open(self.log_file_path, "w", encoding="utf-8") as f:
                f.write("=== ACPI Helper 日志 ===\n")
    
    def show_about_dialog(self):
        """显示关于对话框"""
        about_text = f"""
        <style>
            body {{ font-family: 'Microsoft YaHei'; font-size: 12pt; }}
            .title {{ font-size: 16pt; font-weight: bold; color: #333; }}
            .version {{ color: #666; }}
            .website {{ color: #0066CC; text-decoration: none; }}
            .author {{ margin-top: 10px; }}
        </style>
        <div class="title">ACPI设备助手</div>
        <div class="version">版本: V1.2</div>
        <div class="author">作者: laobamac</div>
        <div style="margin-top: 15px;">
            网站: <a href="https://www.simplehac.cn" class="website">SimpleHac资源社 https://www.simplehac.cn</a>
        </div>
        <div style="margin-top: 15px;">
            本工具用于查看设备ACPI路径并生成SSDT补丁
        </div><br>
        <h3>交流群：</h3><div class="version">①群965625664 ②群1006766467</div>
        """
    
        about_box = QMessageBox(self)
        about_box.setWindowTitle("关于")
        about_box.setTextFormat(Qt.RichText)
        about_box.setText(about_text)
        about_box.setIconPixmap(QIcon(resource_path("Resources/gui_acpi_exp.ico")).pixmap(64, 64))
        about_box.exec()

    def append_log(self, text):
        """追加日志内容到临时文件"""
        try:
            with open(self.log_file_path, "a", encoding="utf-8") as f:
                f.write(text + "\n")
        
            # 如果日志窗口已打开，则实时更新内容
            if hasattr(self, 'log_dialog') and self.log_dialog and self.log_dialog.isVisible():
                self.update_log_display()
        except Exception as e:
            print(f"写入日志失败: {str(e)}")
    
    def show_log_dialog(self):
        """显示日志对话框"""
        if not hasattr(self, 'log_dialog') or not self.log_dialog:
            self.create_log_dialog()
        self.update_log_display()
        self.log_dialog.show()

    def create_log_dialog(self):
        """创建日志对话框"""
        self.log_dialog = QDialog(self)
        self.log_dialog.setWindowTitle("PowerShell 输出日志")
        self.log_dialog.setMinimumSize(800, 600)
        layout = QVBoxLayout(self.log_dialog)

        # 使用 log_text_edit 而不是 log_output
        self.log_text_edit = QTextEdit()
        self.log_text_edit.setFont(QFont("Consolas", 10))
        self.log_text_edit.setReadOnly(True)
        layout.addWidget(self.log_text_edit)

        # 底部按钮
        btn_layout = QHBoxLayout()
    
        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.clicked.connect(self.update_log_display)
        btn_layout.addWidget(refresh_btn)
    
        clear_btn = QPushButton("🗑️ 清空日志")
        clear_btn.clicked.connect(self.clear_log_file)
        btn_layout.addWidget(clear_btn)
    
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.log_dialog.close)
        btn_layout.addWidget(close_btn)
    
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def update_log_display(self):
        """更新日志显示内容"""
        try:
            if os.path.exists(self.log_file_path):
                with open(self.log_file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                self.log_text_edit.setPlainText(content)
                # 自动滚动到底部
                self.log_text_edit.verticalScrollBar().setValue(
                    self.log_text_edit.verticalScrollBar().maximum()
                )
        except Exception as e:
            self.log_text_edit.setPlainText(f"读取日志失败: {str(e)}")

    def clear_log_file(self):
        """清空日志文件"""
        try:
            with open(self.log_file_path, "w", encoding="utf-8") as f:
                f.write("=== 日志已清空 ===\n")
            self.update_log_display()
            QMessageBox.information(self, "成功", "日志已清空")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"清空日志失败: {str(e)}")

    def save_log_file(self):
        """保存日志到文件"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, 
            "保存日志文件", 
            os.path.expanduser("~/Desktop/acpi_helper_log.txt"), 
            "Text Files (*.txt);;All Files (*)"
        )
        if file_path:
            try:
                if os.path.exists(self.log_file_path):
                    shutil.copyfile(self.log_file_path, file_path)
                    QMessageBox.information(self, "成功", f"日志已保存到: {file_path}")
            except Exception as e:
                QMessageBox.warning(self, "错误", f"保存日志失败: {str(e)}")




    # ======================== 核心功能 ========================
    def check_cache(self):
        """检查并加载缓存"""
        if os.path.exists(CACHE_FILE):
            reply = QMessageBox.question(
                self, "发现缓存", 
                "检测到已缓存的设备数据，是否使用？\n（选择“否”将重新获取最新数据）",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.load_from_cache()
                QMessageBox.information(self, "成功", "已加载最近一次设备缓存")
                return
        QMessageBox.warning(self, "警告", "首次使用或刷新缓存时会遍历设备，耗时较长（1分钟左右），请耐心等待！！！")
        self.refresh_data()

    def load_from_cache(self):
        """从缓存加载数据"""
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                self.devices = json.load(f)
            self.update_device_table()
            self.progress_bar.hide()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载缓存失败: {str(e)}")
            self.refresh_data()

    def refresh_data(self):
        """重新获取数据"""
        QMessageBox.warning(self, "警告", "首次使用或刷新缓存时会遍历设备，耗时较长（1分钟左右），请耐心等待！！！")
        self.progress_bar.show()
        self.log_button.show()
        if self.loader_thread and self.loader_thread.isRunning():
            self.loader_thread.stop()
            # 清空日志文件
        if hasattr(self, 'log_file_path'):
            open(self.log_file_path, "w", encoding="utf-8").close()
        self.log_text = ""
            # 初始化日志文件
        self.ensure_log_file()
        with open(self.log_file_path, "w", encoding="utf-8") as f:
            f.write("=== 开始新的设备扫描 ===\n")
        self.loader_thread = DeviceLoaderThread()
        self.loader_thread.data_loaded.connect(self.on_data_loaded)
        self.loader_thread.progress_update.connect(self.update_progress)
        self.loader_thread.log_update.connect(self.append_log)
        self.loader_thread.start()

    def append_log(self, text):
        """追加日志内容到临时文件"""
        try:
            with open(self.log_file_path, "a", encoding="utf-8") as f:
                f.write(text + "\n")
        
            # 如果日志窗口已打开，则实时更新内容
            if hasattr(self, 'log_dialog') and self.log_dialog and self.log_dialog.isVisible():
                self.update_log_display()
        except Exception as e:
            print(f"写入日志失败: {str(e)}")

    def update_progress(self, value, message):
        """更新进度条"""
        self.progress_bar.setValue(value)
        self.progress_bar.setFormat(f"{message} ({value}%)")

    def on_data_loaded(self, devices):
        """数据加载完成处理"""
        self.devices = devices
        self.update_device_table()
        self.progress_bar.hide()
        self.log_button.hide()


    def get_selected_device(self):
        """获取当前选中的设备信息（新增方法）"""
        selected_row = self.device_table.currentRow()
        if selected_row >= 0:
            device_name = self.device_table.item(selected_row, 0).text()
            return next((d for d in self.devices if d["DeviceName"] == device_name), None)
        QMessageBox.warning(self, "提示", "请先在表格中选择设备！")
        return None

    def update_device_table(self, filter_text=None):
        """更新表格数据（确保不可编辑）"""
        self.device_table.setRowCount(0)
        for device in self.devices:
            device_name = device.get("DeviceName", "")
            
            if filter_text and filter_text.lower() not in device_name.lower():
                continue
                
            row = self.device_table.rowCount()
            self.device_table.insertRow(row)
            
            # 设备名称（不可编辑）
            name_item = QTableWidgetItem(device_name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            self.device_table.setItem(row, 0, name_item)
            
            # 状态（不可编辑）
            status_item = QTableWidgetItem(device.get("Status", ""))
            status_item.setFlags(status_item.flags() & ~Qt.ItemIsEditable)
            self.device_table.setItem(row, 1, status_item)
            
            # 类别（不可编辑）
            class_item = QTableWidgetItem(device.get("Class", ""))
            class_item.setFlags(class_item.flags() & ~Qt.ItemIsEditable)
            self.device_table.setItem(row, 2, class_item)

    def setup_ssdt_menu(self):
        """初始化SSDT工具菜单"""
        menu_bar = self.menuBar()
        ssdt_menu = menu_bar.addMenu("SSDT工具")
    
        # 屏蔽设备子菜单
        disable_menu = ssdt_menu.addMenu("🛑 屏蔽设备")
        disable_types = [
            ("💤 S3休眠屏蔽", "disable_s3"),
            ("🔌 OFF屏蔽", "disable_off"),
            ("🏷️ IOName屏蔽", "disable_ioname")
        ]
        for text, method in disable_types:
            action = disable_menu.addAction(text)
            action.triggered.connect(lambda _, m=method: self.show_ssdt_dialog(m))
    
        # 仿冒设备子菜单
        spoof_menu = ssdt_menu.addMenu("🎭 仿冒设备")
        spoof_types = [
            ("🖥️ 普通GPU仿冒", "spoof_generic"),
            ("🟥 RX6x50XT专用仿冒", "spoof_rx6500")
        ]
        for text, method in spoof_types:
            action = spoof_menu.addAction(text)
            action.triggered.connect(lambda _, m=method: self.show_ssdt_dialog(m))

    # 修改后的路径转义处理（确保使用ACPI转义路径）
    def show_ssdt_dialog(self, method):
        """显示SSDT功能对话框"""
        device = self.get_selected_device()
        if not device:
            return
            
        # 获取ACPI转义路径（过滤无效路径）
        acpi_paths = [convert_acpi_path(p) for p in device.get("LocationPaths", [])]
        acpi_paths = [p for p in acpi_paths if p]
    
        if not acpi_paths:
            QMessageBox.warning(self, "错误", "该设备没有有效的ACPI路径！")
            return
        
        if method == "spoof_rx6500":
            dialog = RX6500SpoofDialog(self, acpi_paths[0])
        else:
            dialog = SSDTFunctionDialog(self, device, method)
        dialog.exec()
    
    def get_selected_device(self):
        """获取当前选中的设备信息"""
        if self.device_table.currentRow() >= 0:
            device_name = self.device_table.item(self.device_table.currentRow(), 0).text()
            return next((d for d in self.devices if d["DeviceName"] == device_name), None)
        QMessageBox.warning(self, "提示", "请先在表格中选择设备！")
        return None

    def show_location_details(self, row):
        """显示路径详情"""
        device_name = self.device_table.item(row, 0).text()
        device = next((d for d in self.devices if d["DeviceName"] == device_name), None)
        if not device:
            return

        html_content = """
        <style>
            body { font-family: 'Microsoft YaHei'; font-size: 12pt; }
            .path-title { font-weight: bold; margin-top: 8px; }
            .pci-path { color: #0000CC; }
            .acpi-path { color: #0000CC; }
            .error { color: #FF0000; }
        </style>
        """

        paths = device.get("LocationPaths", [])
        if isinstance(paths, str):
            paths = [paths]

        for path in paths:
            html_content += f'<div class="path-title">原始路径:</div><div>{path}</div>'
            
            pci_converted = convert_pci_path(path)
            if pci_converted:
                html_content += f'<div class="path-title pci-path">PCI 转义:</div><div class="pci-path">{pci_converted}</div>'
            elif any(x in path for x in ["PCIROOT", "PCI("]):
                html_content += '<div class="error">⚠ PCI 转义失败: 路径包含非PCI设备</div>'
            
            acpi_converted = convert_acpi_path(path)
            if acpi_converted:
                html_content += f'<div class="path-title acpi-path">ACPI 转义:</div><div class="acpi-path">{acpi_converted}</div>'
            
            html_content += "<hr>"

        self.details_text.setHtml(html_content)

    def filter_devices(self):
        """设备搜索"""
        self.update_device_table(self.search_input.text())

    def copy_to_clipboard(self):
        """复制路径到剪贴板"""
        text = self.details_text.toPlainText()
        if text:
            QApplication.clipboard().setText(text)
            QMessageBox.information(self, "成功", "路径已复制到剪贴板！")

    def setup_ssdt_actions(self):
        """扩展SSDT功能菜单"""
        ssdt_menu = self.menuBar().addMenu("SSDT工具")
        
        actions = [
            ("屏蔽设备 (S3休眠)", lambda: self.show_ssdt_dialog("disable_s3")),
            ("屏蔽设备 (OFF)", lambda: self.show_ssdt_dialog("disable_off")),
            ("屏蔽设备 (IOName)", lambda: self.show_ssdt_dialog("disable_ioname")),
            ("仿冒普通GPU", lambda: self.show_ssdt_dialog("spoof_generic")),
            ("仿冒RX 6x50 XT", self.show_rx6500_dialog)
        ]
        
        for text, slot in actions:
            action = ssdt_menu.addAction(text)
            action.triggered.connect(slot)

    def show_rx6500_dialog(self):
        """显示RX6x50专用对话框"""
        if acpi_path := self.get_current_acpi_path():
            dialog = RX6500SpoofDialog(self, acpi_path)
            dialog.exec()

    def get_current_acpi_path(self):
        """获取当前选中设备的ACPI路径"""
        if device := self.get_selected_device():
            if paths := [convert_acpi_path(p) for p in device.get("LocationPaths", [])]:
                return paths[0]
            QMessageBox.warning(self, "错误", "该设备没有有效的ACPI路径！")
        return None

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(resource_path("Resources/gui_acpi_exp.ico")))
    window = DeviceLocationViewer()
    window.show()
    sys.exit(app.exec())