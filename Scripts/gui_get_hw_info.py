import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QLabel, QScrollArea, QFrame, QSizePolicy, QPushButton, QMessageBox)
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtCore import Qt
import wmi
import re

class HardwareCard(QFrame):
    def __init__(self, hardware_type, items, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            HardwareCard {
                background-color: white;
                border-radius: 8px;
                border: 1px solid #e0e0e0;
                padding: 10px;
            }
            QLabel {
                font-size: 12px;
            }
            .title {
                font-size: 14px;
                font-weight: bold;
                color: #333;
                margin-bottom: 6px;
            }
        """)
        
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)
        
        # 标题
        title = QLabel(hardware_type)
        title.setProperty("class", "title")
        layout.addWidget(title)
        
        # 添加硬件项
        for item in items:
            item_widget = QWidget()
            item_layout = QHBoxLayout(item_widget)
            item_layout.setContentsMargins(0, 0, 0, 0)
            item_layout.setSpacing(8)
            
            # 型号
            model_label = QLabel(item['model'])
            model_label.setWordWrap(True)
            model_label.setMinimumWidth(200)
            model_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            item_layout.addWidget(model_label)
            
            # 设备ID
            id_label = QLabel(item['id'])
            id_label.setMinimumWidth(120)
            item_layout.addWidget(id_label)
            
            # 状态
            status_label = QLabel(item['status'])
            status = item.get('raw_status', None)
            is_wildcard = item.get('is_wildcard', False)
            
            if status == "1":
                if is_wildcard:
                    status_label.setStyleSheet("color: #FFA500; font-weight: bold;")  # 橙色表示通配匹配
                else:
                    status_label.setStyleSheet("color: #2e7d32; font-weight: bold;")  # 绿色表示完全匹配
            elif status == "0":
                status_label.setStyleSheet("color: #c62828; font-weight: bold;")  # 红色表示不支持
            else:
                status_label.setStyleSheet("color: #616161; font-weight: bold;")  # 灰色表示未知
            status_label.setMinimumWidth(60)
            item_layout.addWidget(status_label)
            
            # 详情
            detail_label = QLabel(item['detail'])
            if status == "1":
                if is_wildcard:
                    detail_label.setStyleSheet("color: #FFA500;")  # 橙色表示通配匹配
                else:
                    detail_label.setStyleSheet("color: #2e7d32;")  # 绿色表示完全匹配
            elif status == "0":
                detail_label.setStyleSheet("color: #c62828;")  # 红色表示不支持
            else:
                detail_label.setStyleSheet("color: #616161;")  # 灰色表示未知
            detail_label.setWordWrap(True)
            detail_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            item_layout.addWidget(detail_label)
            
            # 驱动
            kext_label = QLabel(item['kext'])
            if status == "1":
                if is_wildcard:
                    kext_label.setStyleSheet("color: #FFA500;")  # 橙色表示通配匹配
                else:
                    kext_label.setStyleSheet("color: #2e7d32;")  # 绿色表示完全匹配
            elif status == "0":
                kext_label.setStyleSheet("color: #c62828;")  # 红色表示不支持
            else:
                kext_label.setStyleSheet("color: #616161;")  # 灰色表示未知
            kext_label.setWordWrap(True)
            kext_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            item_layout.addWidget(kext_label)
            
            layout.addWidget(item_widget)
        
        # 添加分隔线
        if items:
            line = QFrame()
            line.setFrameShape(QFrame.HLine)
            line.setFrameShadow(QFrame.Sunken)
            line.setStyleSheet("color: #e0e0e0;")
            layout.addWidget(line)

class HardwareInfoGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("硬件信息检查工具")
        self.setGeometry(100, 100, 1000, 700)
        
        # 设置主窗口样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f7fa;
            }
            QScrollArea {
                border: none;
                background: transparent;
            }
            QPushButton {
                background-color: #4a6fa5;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
                min-width: 60px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #3a5a8f;
            }
            QPushButton:pressed {
                background-color: #2a4a7f;
            }
        """)
        
        # 创建主部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)
        
        # 标题栏
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        title_label = QLabel("硬件兼容性报告")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #333;
            }
        """)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        # 刷新按钮
        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.setFixedSize(60, 24)
        self.refresh_btn.clicked.connect(self.refresh_data)
        header_layout.addWidget(self.refresh_btn)
        
        # 关于按钮
        about_btn = QPushButton("关于")
        about_btn.setFixedSize(60, 24)
        about_btn.clicked.connect(self.show_about)
        header_layout.addWidget(about_btn)
        
        # 添加状态指示图例
        legend = QWidget()
        legend_layout = QHBoxLayout(legend)
        legend_layout.setSpacing(12)
        
        supported_legend = QLabel("✅ 支持(完全匹配)")
        supported_legend.setStyleSheet("color: #2e7d32; font-size: 11px;")
        wildcard_legend = QLabel("🟠 支持(厂商匹配)")
        wildcard_legend.setStyleSheet("color: #FFA500; font-size: 11px;")
        unsupported_legend = QLabel("❌ 不支持")
        unsupported_legend.setStyleSheet("color: #c62828; font-size: 11px;")
        unknown_legend = QLabel("❓ 未知")
        unknown_legend.setStyleSheet("color: #616161; font-size: 11px;")
        
        legend_layout.addWidget(supported_legend)
        legend_layout.addWidget(wildcard_legend)
        legend_layout.addWidget(unsupported_legend)
        legend_layout.addWidget(unknown_legend)
        header_layout.addWidget(legend)
        
        main_layout.addWidget(header)
        
        # 创建滚动区域
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QScrollArea.NoFrame)
        
        # 滚动区域内容
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(4, 4, 4, 4)
        self.scroll_layout.setSpacing(10)
        
        self.scroll_area.setWidget(self.scroll_content)
        main_layout.addWidget(self.scroll_area)
        
        # 状态栏
        self.status_bar = self.statusBar()
        
        # 初始加载数据
        self.refresh_data()
    
    def refresh_data(self):
        """刷新硬件数据"""
        self.refresh_btn.setEnabled(False)
        self.status_bar.showMessage("正在加载硬件信息...")
        QApplication.processEvents()  # 立即更新UI
        
        try:
            hardware_data = self.get_hardware_data()
            self.update_ui(hardware_data)
            self.status_bar.showMessage(f"硬件信息已更新，共检测到 {sum(len(v) for v in hardware_data.values())} 项设备")
        except Exception as e:
            self.status_bar.showMessage(f"加载失败: {str(e)}")
        finally:
            self.refresh_btn.setEnabled(True)
    
    def show_about(self):
        """显示关于对话框"""
        about_text = """
        <b>硬件信息检查工具 v1.0</b><br><br>
        作者: laobamac<br>
        网站: <a href='https://www.simplehac.cn/'>SimpleHac资源社</a><br><br>
        本工具用于检查硬件兼容性信息。
        """
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle("关于")
        msg.setTextFormat(Qt.RichText)
        msg.setText(about_text)
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()
    
    def update_ui(self, hardware_data):
        """更新UI显示"""
        # 清除旧内容
        while self.scroll_layout.count():
            item = self.scroll_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # 为每种硬件类型创建卡片
        for hw_type, items in hardware_data.items():
            if items:  # 只显示有内容的硬件类型
                card = HardwareCard(hw_type, items)
                self.scroll_layout.addWidget(card)
        
        # 添加拉伸项使内容顶部对齐
        self.scroll_layout.addStretch()
    
    def get_hardware_data(self):
        """获取硬件数据并转换为适合GUI显示的格式"""
        # 加载所有支持信息
        gpu_support, gpu_details, gpu_kext = self.load_support_info("GPUSupportInfo.list")
        hda_support, hda_details, hda_kext = self.load_support_info("HDASupportInfo.list")
        eth_support, eth_details, eth_kext = self.load_support_info("ETHSupportInfo.list")
        
        c = wmi.WMI()
        hardware_data = {}
        
        # CPU信息
        cpu_items = []
        for cpu in c.Win32_Processor():
            cpu_items.append({
                'model': cpu.Name.strip(),
                'id': cpu.DeviceID or 'N/A',
                'status': 'N/A',
                'detail': '',
                'kext': '',
                'raw_status': None,
                'is_wildcard': False
            })
        hardware_data['处理器'] = cpu_items
        
        # 内存信息
        mem_items = []
        for mem in c.Win32_PhysicalMemory():
            model = f"{mem.Manufacturer or 'Unknown'} {mem.PartNumber.strip() if mem.PartNumber else ''} {int(mem.Capacity)//(1024**3)}GB"
            mem_items.append({
                'model': model,
                'id': mem.SerialNumber.strip() if mem.SerialNumber else 'N/A',
                'status': 'N/A',
                'detail': '',
                'kext': '',
                'raw_status': None,
                'is_wildcard': False
            })
        hardware_data['内存'] = mem_items
        
        # 硬盘信息
        disk_items = []
        for disk in c.Win32_DiskDrive():
            disk_items.append({
                'model': disk.Model.strip(),
                'id': disk.DeviceID or 'N/A',
                'status': 'N/A',
                'detail': '',
                'kext': '',
                'raw_status': None,
                'is_wildcard': False
            })
        hardware_data['存储设备'] = disk_items
        
        # 主板信息
        board_items = []
        for board in c.Win32_BaseBoard():
            board_items.append({
                'model': board.Product or 'Unknown',
                'id': board.SerialNumber or 'N/A',
                'status': 'N/A',
                'detail': '',
                'kext': '',
                'raw_status': None,
                'is_wildcard': False
            })
        hardware_data['主板'] = board_items
        
        # 显卡信息
        gpu_items = []
        for gpu in c.Win32_VideoController():
            if gpu.Name.strip() not in ["Microsoft Basic Display Driver"]:
                device_id = self.extract_hardware_ids(gpu.PNPDeviceID)
                status, clean_id, detail, required_kext, is_wildcard = self.get_support_info_with_wildcard(
                    device_id, gpu_support, gpu_details, gpu_kext)
                
                status_text = "支持" if status == "1" else ("不支持" if status == "0" else "未知")
                if is_wildcard and status == "1":
                    status_text = "支持(厂商)"
                gpu_items.append({
                    'model': gpu.Name.strip(),
                    'id': clean_id,
                    'status': status_text,
                    'detail': detail,
                    'kext': required_kext,
                    'raw_status': status,
                    'is_wildcard': is_wildcard
                })
        hardware_data['显卡'] = gpu_items
        
        # 声卡信息
        sound_items = []
        for sound in c.Win32_SoundDevice():
            device_id = self.extract_hardware_ids(sound.PNPDeviceID)
            status, clean_id, detail, required_kext, is_wildcard = self.get_support_info_with_wildcard(
                device_id, hda_support, hda_details, hda_kext)
            
            status_text = "支持" if status == "1" else ("不支持" if status == "0" else "未知")
            if is_wildcard and status == "1":
                status_text = "支持(厂商)"
            sound_items.append({
                'model': sound.Name,
                'id': clean_id,
                'status': status_text,
                'detail': detail,
                'kext': required_kext,
                'raw_status': status,
                'is_wildcard': is_wildcard
            })
        hardware_data['声卡'] = sound_items
        
        # 网卡信息
        nic_items = []
        for nic in c.Win32_NetworkAdapter(PhysicalAdapter=True):
            device_id = self.extract_hardware_ids(nic.PNPDeviceID)
            status, clean_id, detail, required_kext, is_wildcard = self.get_support_info_with_wildcard(
                device_id, eth_support, eth_details, eth_kext)
            
            status_text = "支持" if status == "1" else ("不支持" if status == "0" else "未知")
            if is_wildcard and status == "1":
                status_text = "支持(厂商)"
            nic_items.append({
                'model': nic.Name,
                'id': clean_id,
                'status': status_text,
                'detail': detail,
                'kext': required_kext,
                'raw_status': status,
                'is_wildcard': is_wildcard
            })
        hardware_data['网络适配器'] = nic_items
        
        return hardware_data
    
    def get_support_info_with_wildcard(self, device_id, support_info, details_info, kext_info):
        """获取设备支持信息，支持厂商通配ID匹配"""
        if not device_id:
            return None, "N/A", "未知", "无", False
        
        # 先尝试完全匹配
        status = support_info.get(device_id)
        if status is not None:
            detail = details_info.get(device_id, "未知")
            kext = kext_info.get(device_id, "无")
            return status, device_id, detail, kext, False
        
        # 如果完全匹配失败，尝试厂商通配匹配
        if '&' in device_id:
            ven_id = device_id.split('&')[0] + '&FFFF'
            status = support_info.get(ven_id)
            if status is not None:
                detail = details_info.get(ven_id, "未知(厂商通用支持)")
                kext = kext_info.get(ven_id, "无")
                return status, device_id, detail, kext, True
        
        # 如果都没有匹配到
        return None, device_id, "未知", "无", False
    
    def extract_hardware_ids(self, pnp_id):
        """从PNPDeviceID中提取VEN和DEV并合并为VENID&DEVID格式"""
        if not pnp_id:
            return ""
        ven_match = re.search(r'VEN_([0-9A-F]{4})', pnp_id, re.IGNORECASE)
        dev_match = re.search(r'DEV_([0-9A-F]{4})', pnp_id, re.IGNORECASE)
        if ven_match and dev_match:
            return f"{ven_match.group(1)}&{dev_match.group(1)}"
        return ""
    
    def load_support_info(self, filename):
        """加载支持信息文件"""
        support_info = {}
        details_info = {}
        kext_info = {}
        try:
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
        except FileNotFoundError:
            pass
        return support_info, details_info, kext_info

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 设置应用程序字体
    font = QFont()
    font.setFamily("Microsoft YaHei" if sys.platform == "win32" else "PingFang SC")
    font.setPointSize(10)
    app.setFont(font)
    
    window = HardwareInfoGUI()
    window.show()
    sys.exit(app.exec_())