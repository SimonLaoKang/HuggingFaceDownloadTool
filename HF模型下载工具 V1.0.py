import sys
import os
import requests
import datetime
import re
import urllib.parse
import winreg
import subprocess
import configparser
import win32api
from concurrent.futures import ThreadPoolExecutor, wait
from bs4 import BeautifulSoup
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTextEdit, QFileDialog, QAbstractItemView, QRadioButton, QButtonGroup, QSpinBox, QTreeWidget, QTreeWidgetItem, QMenu, QCheckBox, QProgressBar
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QTextCursor


def auto_find_idm_path():
    # 1. 查找注册表 HKEY_LOCAL_MACHINE\SOFTWARE\Internet Download Manager
    reg_paths = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Internet Download Manager"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Internet Download Manager"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\Internet Download Manager"),
    ]
    for root, subkey in reg_paths:
        try:
            with winreg.OpenKey(root, subkey) as key:
                if "Uninstall" in subkey:
                    display_icon, _ = winreg.QueryValueEx(key, "DisplayIcon")
                    path = display_icon.split(",")[0].strip()
                else:
                    path, _ = winreg.QueryValueEx(key, "Path")
                    path = os.path.join(path, "IDMan.exe")
                if os.path.exists(path):
                    return path
        except Exception:
            continue

    # 2. 常见安装路径
    common_paths = [
        r"C:\Program Files (x86)\Internet Download Manager\IDMan.exe",
        r"C:\Program Files\Internet Download Manager\IDMan.exe"
    ]
    for path in common_paths:
        if os.path.exists(path):
            return path

    # 3. HKEY_USERS 下 DownloadManager ExePath
    try:
        with winreg.OpenKey(winreg.HKEY_USERS, "") as users_key:
            for i in range(winreg.QueryInfoKey(users_key)[0]):
                sid = winreg.EnumKey(users_key, i)
                subkey = sid + r"\SOFTWARE\DownloadManager"
                try:
                    with winreg.OpenKey(winreg.HKEY_USERS, subkey) as key:
                        exe_path, _ = winreg.QueryValueEx(key, "ExePath")
                        if exe_path and os.path.exists(exe_path):
                            return exe_path
                except Exception:
                    continue
    except Exception:
        pass

    # 4. HKEY_USERS 下 MuiCache
    try:
        with winreg.OpenKey(winreg.HKEY_USERS, "") as users_key:
            for i in range(winreg.QueryInfoKey(users_key)[0]):
                sid = winreg.EnumKey(users_key, i)
                subkey = sid + r"\SOFTWARE\Classes\Local Settings\Software\Microsoft\Windows\Shell\MuiCache"
                try:
                    with winreg.OpenKey(winreg.HKEY_USERS, subkey) as key:
                        for j in range(winreg.QueryInfoKey(key)[1]):
                            name, value, _ = winreg.EnumValue(key, j)
                            if "IDMan.exe" in str(name) and os.path.exists(name):
                                return name
                            if "IDMan.exe" in str(value) and os.path.exists(value):
                                return value
                except Exception:
                    continue
    except Exception:
        pass

    return None

def save_idm_path_to_ini(path):
    ini_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "idm_path.ini")
    config = configparser.ConfigParser()
    config["IDM"] = {"path": path if path else ""}
    with open(ini_path, "w", encoding="utf-8") as f:
        config.write(f)

def get_idm_path_from_ini():
    ini_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "idm_path.ini")
    config = configparser.ConfigParser()
    if os.path.exists(ini_path):
        config.read(ini_path, encoding="utf-8")
        if "IDM" in config and "path" in config["IDM"]:
            path = config["IDM"]["path"]
            if os.path.exists(path):
                return path
    return None

# 程序启动时自动检测并生成 ini
idm_path = auto_find_idm_path()
save_idm_path_to_ini(idm_path)

def get_idm_path_from_ini():
    ini_path = os.path.join(os.path.dirname(sys.argv[0]), "idm_path.ini")
    config = configparser.ConfigParser()
    if os.path.exists(ini_path):
        config.read(ini_path, encoding="utf-8")
        if "IDM" in config and "path" in config["IDM"]:
            path = config["IDM"]["path"]
            if os.path.exists(path):
                return path
    return None

def save_idm_path_to_ini(path):
    ini_path = os.path.join(os.path.dirname(sys.argv[0]), "idm_path.ini")
    config = configparser.ConfigParser()
    config["IDM"] = {"path": path}
    with open(ini_path, "w", encoding="utf-8") as f:
        config.write(f)

def get_idm_path_from_ini():
    ini_path = os.path.join(os.path.dirname(sys.argv[0]), "idm_path.ini")
    config = configparser.ConfigParser()
    if os.path.exists(ini_path):
        config.read(ini_path, encoding="utf-8")
        if "IDM" in config and "path" in config["IDM"]:
            path = config["IDM"]["path"]
            print(f"控制台调试：读取到IDM路径: {path}")  # 调试输出
            if os.path.exists(path):
                return path
    return None

def url_encode_path(path):
    # 只对每一段做编码，防止斜杠被编码
    return "/".join(urllib.parse.quote(part) for part in path.split("/"))

def log_with_time(msg):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"[{now}] {msg}"

def get_headers(token): # 获取请求头
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}

def get_repo_type(repo_id, base_url, token=None):
    api_url = f"{base_url}/api/datasets/{repo_id}"
    resp = requests.get(api_url, headers=get_headers(token))
    if resp.status_code == 200:
        return "datasets"
    api_url = f"{base_url}/api/models/{repo_id}"
    resp = requests.get(api_url, headers=get_headers(token))
    if resp.status_code == 200:
        return "models"
    return None

def list_repo_files(repo_id, repo_type, base_url, token=None):
    api_url = f"{base_url}/api/{repo_type}/{repo_id}"
    resp = requests.get(api_url, headers=get_headers(token))
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    data = resp.json()
    # 直接返回 siblings 字典列表
    return data.get('siblings', [])

def parse_hf_html(html, base_url, repo_id, parent_path="", session=None):
    if session is None:
        session = requests.Session()
    soup = BeautifulSoup(html, "html.parser")
    file_infos = []
    size_pattern = re.compile(r"^\d+(\.\d+)?\s?(Bytes|KB|MB|GB|TB|PB)$", re.IGNORECASE)
    for li in soup.find_all("li", class_="grid"):
        a_tags = li.find_all("a", href=True)
        if not a_tags:
            continue
        main_a = a_tags[0]
        href = main_a["href"]
        # 文件夹
        if "/tree/" in href:
            name_span = main_a.find("span", class_="truncate")
            folder_name = name_span.text.strip() if name_span else main_a.text.strip()
            if parent_path:
                folder_path = f"{parent_path}/{folder_name}"
            else:
                folder_path = folder_name
            sub_url = f"{base_url}/{repo_id}/tree/main/{folder_path}"
            try:
                resp = session.get(sub_url, headers={"User-Agent": "Mozilla/5.0"})
                resp.raise_for_status()
                sub_html = resp.text
                file_infos.extend(parse_hf_html(sub_html, base_url, repo_id, folder_path, session))
            except Exception as e:
                print(f"递归解析目录失败: {sub_url} 错误: {e}")
        # 文件
        elif "/blob/" in href:
            name_span = main_a.find("span", class_="truncate")
            filename = name_span.text.strip() if name_span else main_a.text.strip()
            # 获取文件大小
            size = "未知"
            for tag in li.find_all(["div", "span"]):
                txt = tag.get_text(strip=True)
                if txt and size_pattern.match(txt):
                    size = txt
                    break
            # 获取修改时间
            time_tag = li.find("time")
            time_str = time_tag["datetime"] if time_tag and time_tag.has_attr("datetime") else "未知"
            # 拼接完整路径
            if parent_path:
                rfilename = f"{parent_path}/{filename}"
            else:
                rfilename = filename
            file_infos.append({
                "rfilename": rfilename,
                "size_str": size,
                "last_modified": time_str
            })
    return file_infos

def get_repo_type_and_files(repo_id, base_url, token=None):
    """
    判断仓库类型（datasets/models），并用网页解析返回(type, files)
    files结构统一为[{rfilename, size_str, last_modified}]
    """
    headers = {"User-Agent": "Mozilla/5.0"}
    # 先试 datasets 仓库网页
    datasets_url = f"{base_url}/datasets/{repo_id}/tree/main"
    try:
        resp = requests.get(datasets_url, headers=headers)
        if resp.status_code == 200:
            files = parse_hf_html(resp.text, base_url, f"datasets/{repo_id}")
            return "datasets", files
    except Exception:
        pass
    # 再试 model 仓库网页
    model_url = f"{base_url}/{repo_id}/tree/main"
    try:
        resp = requests.get(model_url, headers=headers)
        if resp.status_code == 200:
            files = parse_hf_html(resp.text, base_url, repo_id)
            return "models", files
    except Exception:
        pass
    return None, None

class HFDownloaderGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HuggingFace 镜像/原始模型/数据集下载工具")
        self.resize(700, 500)
        self.idm_path = get_idm_path_from_ini()
        self.init_ui()
        if self.idm_path:
            self.idm_path_label.setText(f"IDM路径：{self.idm_path}")
            try:
                subprocess.Popen([self.idm_path])
                self.safe_log("已自动启动IDM")
            except Exception as e:
                self.safe_log(f"启动IDM失败: {e}")
        else:
            self.idm_path_label.setText("IDM路径：未设置")

    def init_ui(self):
        layout = QVBoxLayout()
    
        # 地址选择
        addr_layout = QHBoxLayout()
        self.origin_radio = QRadioButton("原始地址")
        self.mirror_radio = QRadioButton("镜像地址")
        self.origin_radio.setChecked(False)
        self.mirror_radio.setChecked(True)
        self.addr_group = QButtonGroup()
        self.addr_group.addButton(self.origin_radio)
        self.addr_group.addButton(self.mirror_radio)
        self.origin_input = QLineEdit("https://huggingface.co")
        self.mirror_input = QLineEdit("https://hf-mirror.com")
        addr_layout.addWidget(self.origin_radio)
        addr_layout.addWidget(self.origin_input)
        addr_layout.addWidget(self.mirror_radio)
        addr_layout.addWidget(self.mirror_input)
        layout.addLayout(addr_layout)
    
        # 输入区
        form_layout = QHBoxLayout()
        self.repo_input = QLineEdit()
        self.repo_input.setPlaceholderText("模型或数据集仓库名（如 sjidnd/LIb_damoxing）")
        self.token_input = QLineEdit()
        self.token_input.setPlaceholderText("HuggingFace Token（可选）")
        self.token_input.setEchoMode(QLineEdit.EchoMode.Password)
        form_layout.addWidget(QLabel("仓库名:"))
        form_layout.addWidget(self.repo_input)
        form_layout.addWidget(QLabel("Token:"))
        form_layout.addWidget(self.token_input)
        layout.addLayout(form_layout)
    
        
        # 文件树控件和总大小
        file_list_layout = QHBoxLayout()
        file_list_label = QLabel("仓库文件列表")
        self.selected_count_label = QLabel("已选文件数：0")
        self.total_size_label = QLabel("总大小：0 B")
        file_list_layout.addWidget(file_list_label)
        file_list_layout.addWidget(self.selected_count_label)
        file_list_layout.addWidget(self.total_size_label)
        file_list_layout.addStretch()
        layout.addLayout(file_list_layout)

        self.file_tree_widget = QTreeWidget()
        self.file_tree_widget.setHeaderLabels(["名称", "大小", "修改时间"])
        self.file_tree_widget.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        layout.addWidget(self.file_tree_widget)
        self.load_btn = QPushButton("读取文件列表")
        self.select_toggle_btn = QPushButton("全选/全不选")
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.load_btn)
        btn_layout.addWidget(self.select_toggle_btn)
        layout.addLayout(btn_layout)

        # IDM路径选择区
        idm_layout = QHBoxLayout()
        self.idm_path_label = QLabel("IDM路径：未设置")
        self.idm_choose_btn = QPushButton("选择IDM路径")
        self.idm_choose_btn.clicked.connect(self.choose_idm_path)
        idm_layout.addWidget(self.idm_path_label)
        idm_layout.addWidget(self.idm_choose_btn)
        layout.addLayout(idm_layout)
    
        # 日志区
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        layout.addWidget(QLabel("日志："))
        layout.addWidget(self.log_box)

        # 下载目录提示（突出显示）
        path_layout = QHBoxLayout()
        self.download_path = os.path.expanduser("~")  # 默认下载到用户目录
        path_label = QLabel("下载目录（可点击选择路径）：")
        path_label.setStyleSheet("font-weight: bold;")
        self.download_path_label = QLabel()
        self.download_path_label.setStyleSheet("color: red; font-weight: bold; font-size: 14px;")
        self.update_download_path_label()
        path_layout.addWidget(path_label)
        # path_layout.addSpacing(10)  # 增加间距
        path_layout.addWidget(self.download_path_label)
        path_layout.addStretch()    # 右侧自动补齐
        layout.addLayout(path_layout)

        # URL编码选项
        action_btn_layout = QHBoxLayout()
        self.encode_checkbox = QCheckBox("下载地址使用URL编码(兼容好)")
        self.encode_checkbox.setChecked(True)
        action_btn_layout.addWidget(self.encode_checkbox)

        # 自动开始下载选项
        self.auto_start_checkbox = QCheckBox("添加后自动开始下载")
        self.auto_start_checkbox.setChecked(False)
        action_btn_layout.addWidget(self.auto_start_checkbox)
    
        # 按钮区
        self.export_btn = QPushButton("导出下载链接")
        action_btn_layout.addWidget(self.export_btn)
        self.download_btn = QPushButton("导入IDM队列")
        action_btn_layout.addWidget(self.download_btn)
        layout.addLayout(action_btn_layout)
        self.setLayout(layout)
    
        # 事件绑定
        self.load_btn.clicked.connect(self.load_file_list)
        self.select_toggle_btn.clicked.connect(self.toggle_select_all)
        self.file_tree_widget.itemChanged.connect(self.on_tree_item_changed)
        self.export_btn.clicked.connect(self.export_download_links)
        self.download_btn.clicked.connect(self.batch_multithread_download)
        path_label.mousePressEvent = self.choose_download_path_event
        self.download_path_label.mousePressEvent = self.choose_download_path_event
    
        # 右键菜单
        self.file_tree_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.file_tree_widget.customContextMenuRequested.connect(self.on_tree_right_click)
     
    def is_real_idm_exe(path):
        if not path or not os.path.exists(path):
            return False
        if os.path.basename(path).lower() != "idman.exe":
            return False
        try:
            info = win32api.GetFileVersionInfo(path, '\\')
            # 获取语言和代码页
            lang, codepage = win32api.VerQueryValue(info, r'\VarFileInfo\Translation')[0]
            str_info_path = r'\StringFileInfo\%04X%04X\FileDescription' % (lang, codepage)
            description = win32api.VerQueryValue(info, str_info_path)
            if "Internet Download Manager" in description:
                return True
        except Exception:
            pass
        return False
    
    def choose_idm_path(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "请选择IDMan.exe路径",
            "",
            "IDMan.exe (IDMan.exe)"
        )
        if self.is_real_idm_exe(file_path):
            self.idm_path = file_path
            self.idm_path_label.setText(f"IDM路径：{file_path}")
            save_idm_path_to_ini(file_path)
            self.safe_log("已手动选择并保存IDM路径")
            # 自动启动IDM
            try:
                subprocess.Popen([file_path])
                self.safe_log("已自动启动IDM")
            except Exception as e:
                self.safe_log(f"启动IDM失败: {e}")
        else:
            self.safe_log("未选择有效的IDMan.exe文件")

    def update_total_size_label(self):
        total_size = 0
        file_count = 0
        def collect_size(item):
            nonlocal total_size, file_count
            for i in range(item.childCount()):
                child = item.child(i)
                # 只统计勾选的叶子节点（文件）
                if child.childCount() == 0 and child.checkState(0) == Qt.CheckState.Checked:
                    size_str = child.text(1)
                    size = self.parse_size(size_str)
                    total_size += size
                    file_count += 1
                else:
                    collect_size(child)
        root = self.file_tree_widget.invisibleRootItem()
        collect_size(root)
        self.total_size_label.setText(f"总大小：{self.format_size(total_size)}")
        self.selected_count_label.setText(f"已选文件数：{file_count}")

    def parse_size(self, size_str):
        size_str = size_str.strip().replace(" ", "")
        if not size_str or size_str == "未知":
            return 0
        # 兼容 Byte/Bytes
        units = {
            "B": 1, "BYTE": 1, "BYTES": 1,
            "KB": 1024, "MB": 1024**2, "GB": 1024**3,
            "TB": 1024**4, "PB": 1024**5
        }
        import re
        m = re.match(r"([\d\.]+)([A-Za-z]+)", size_str, re.IGNORECASE)
        if not m:
            return 0
        num, unit = m.groups()
        unit = unit.upper()
        if unit == "BYTES" or unit == "BYTE":
            unit = "B"
        try:
            return float(num) * units.get(unit, 1)
        except Exception:
            return 0

    def choose_download_path_event(self, event):
        download_dir = QFileDialog.getExistingDirectory(self, "请选择下载目录", self.download_path)
        if download_dir:
            self.download_path = download_dir
            self.update_download_path_label()

    def update_download_path_label(self):
        self.download_path_label.setText(self.download_path)

    def auto_choose_download_path(self):
        download_dir = QFileDialog.getExistingDirectory(self, "请选择下载目录", self.download_path)
        if download_dir:
            self.download_path = download_dir
        self.update_download_path_label()

    def safe_log(self, msg):
        QTimer.singleShot(0, lambda: self.log_box.append(msg))

    def set_progress_bar(self, val):
        QTimer.singleShot(0, lambda: self.progress_bar.setValue(val))

    def set_total_progress_bar(self, val):
        QTimer.singleShot(0, lambda: self.total_progress_bar.setValue(val))

    def on_tree_right_click(self, pos):
        item = self.file_tree_widget.itemAt(pos)
        if item is None:
            return
        # 只对叶子节点（文件）显示菜单
        if item.childCount() == 0:
            menu = QMenu(self)
            action_copy = menu.addAction("复制下载地址")
            action = menu.exec(self.file_tree_widget.viewport().mapToGlobal(pos))
            if action == action_copy:
                # 直接用网页解析时保存的 href 字段
                href = item.data(0, Qt.ItemDataRole.UserRole + 1)  # 新增：存储href字段
                base_url = self.get_base_url().rstrip("/")
                if not href:
                    # 兼容老数据，回退用拼接方式
                    rfilename = item.data(0, Qt.ItemDataRole.UserRole)
                    repo_id = self.repo_input.text().strip()
                    repo_type = get_repo_type(repo_id, base_url)
                    if self.encode_checkbox.isChecked():
                        rfilename = url_encode_path(rfilename)
                    if repo_type == "datasets":
                        href = f"/datasets/{repo_id}/resolve/main/{rfilename}?download=true"
                    else:
                        href = f"/{repo_id}/resolve/main/{rfilename}?download=true"
                url = base_url + href
                QApplication.clipboard().setText(url)
                self.safe_log(log_with_time(f"已复制下载地址：{url}"))

    def add_file_to_tree(self, root, path_parts, size, last_modified, full_path):
        if not path_parts or not path_parts[0]:
            return
        name = path_parts[0]
        # 查找是否已存在该节点
        child = None
        for i in range(root.childCount()):
            item = root.child(i)
            if item.text(0) == name:
                child = item
                break
        if child is None:
            # 判断是否为文件还是目录
            if len(path_parts) == 1:
                # 文件节点
                child = QTreeWidgetItem([name, size, last_modified])
                child.setFlags(child.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                child.setCheckState(0, Qt.CheckState.Checked)
                child.setData(0, Qt.ItemDataRole.UserRole, full_path)
            else:
                # 目录节点
                child = QTreeWidgetItem([name, "", ""])
                child.setFlags(child.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                child.setCheckState(0, Qt.CheckState.Checked)
                child.setData(0, Qt.ItemDataRole.UserRole, None)
            root.addChild(child)
        # 递归添加子项
        if len(path_parts) > 1:
            self.add_file_to_tree(child, path_parts[1:], size, last_modified, full_path)

    def load_file_list(self):
        repo_id = self.repo_input.text().strip()
        token = self.token_input.text().strip()
        base_url = self.get_base_url()
        if not repo_id:
            self.safe_log(log_with_time("请填写仓库名！"))
            return
    
        repo_type, files = get_repo_type_and_files(repo_id, base_url, token if token else None)
        if repo_type is None or files is None:
            self.safe_log(log_with_time("仓库无效，既不是模型也不是数据集，请检查仓库名或地址。"))
            return
        if not files:
            self.safe_log(log_with_time("未获取到文件列表！"))
            return
        
        self.file_tree_widget.clear()
        repo_root = QTreeWidgetItem([repo_id, "", ""]) # 仓库根节点
        repo_root.setFlags(repo_root.flags() | Qt.ItemFlag.ItemIsUserCheckable) # 允许用户勾选
        repo_root.setCheckState(0, Qt.CheckState.Checked) # 勾选状态
        repo_root.setData(0, Qt.ItemDataRole.UserRole, None) # 仓库根节点没有具体路径
        self.file_tree_widget.addTopLevelItem(repo_root) # 添加仓库根节点
        for f in files: # 遍历文件列表
            rfilename = f.get('rfilename', f.get('path', '')) # 获取相对路径
            size = f.get('size', f.get('size_str', '')) # 获取文件大小
            if isinstance(size, int): # 如果是整数，格式化为字符串
                size = self.format_size(size) # 格式化大小
            last_modified = f.get('lastModified', '') or f.get('last_modified', '') or "未知" # 获取最后修改时间
            if "T" in last_modified: # 如果是 ISO 格式，提取日期部分
                last_modified = last_modified.split("T")[0] # 提取日期
            path_parts = rfilename.split("/") # 分割路径
            self.add_file_to_tree(repo_root, path_parts, size, last_modified, rfilename) # 完整路径
        self.file_tree_widget.expandAll() # 展开所有节点
        for col in range(self.file_tree_widget.columnCount()):
            self.file_tree_widget.resizeColumnToContents(col)
        self.update_total_size_label()
        self.safe_log(log_with_time(f"{repo_type}文件列表加载完成，共 {len(files)} 个文件。"))

    def export_download_links(self):
        repo_id = self.repo_input.text().strip()
        token = self.token_input.text().strip()
        base_url = self.get_base_url()
        file_list = self.get_checked_files()

        if not repo_id:
            self.safe_log(log_with_time("请填写仓库名！"))
            return
        if not file_list:
            self.safe_log(log_with_time("请至少勾选一个文件！"))
            return
        repo_type = get_repo_type(repo_id, base_url, token if token else None)
        if not repo_type:
            self.safe_log(log_with_time("仓库类型识别失败！"))
            return
        urls = []
        for filename in file_list:
            if self.encode_checkbox.isChecked():
                filename_encoded = url_encode_path(filename)
            else:
                filename_encoded = filename
            if repo_type == "datasets":
                url = f"{base_url}/datasets/{repo_id}/resolve/main/{filename_encoded}"
            else:
                url = f"{base_url}/{repo_id}/resolve/main/{filename_encoded}"
            urls.append(url)
        try:
            # 获取脚本所在目录
            script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
            # 仓库名做文件名时替换斜杠为下划线
            repo_id_safe = repo_id.replace("/", "_")
            txt_path = os.path.join(script_dir, f"hf_download_urls_{repo_id_safe}.txt")
            with open(txt_path, "w", encoding="utf-8") as f:  # 覆盖写入
                for url in urls:
                    f.write(url + "\n")
            self.safe_log(log_with_time(f"已导出 {len(urls)} 个下载链接到 {txt_path}"))
        except Exception as e:
            self.safe_log(log_with_time(f"导出失败: {e}"))

    def on_tree_item_changed(self, item, column):
        # 勾选/取消文件夹时递归所有子项
        state = item.checkState(0)
        for i in range(item.childCount()):
            child = item.child(i)
            child.setCheckState(0, state)
        # 更新总大小和已选文件数
        self.update_total_size_label()

    def toggle_select_all(self):
        # 判断是否全选
        def all_checked(parent):
            for i in range(parent.childCount()):
                item = parent.child(i)
                if item.checkState(0) != Qt.CheckState.Checked:
                    return False
                if not all_checked(item):
                    return False
            return True
        root = self.file_tree_widget.invisibleRootItem()
        checked = all_checked(root)
        def set_all(parent, state):
            for i in range(parent.childCount()):
                item = parent.child(i)
                item.setCheckState(0, state)
                set_all(item, state)
        set_all(root, Qt.CheckState.Unchecked if checked else Qt.CheckState.Checked)
        self.update_total_size_label()

    def get_checked_files(self, parent=None, path=""):
        if parent is None:
            parent = self.file_tree_widget.invisibleRootItem()
        files = []
        for i in range(parent.childCount()):
            item = parent.child(i)
            # 只收集叶子节点（文件），且被勾选
            if item.childCount() == 0 and item.checkState(0) == Qt.CheckState.Checked:
                rfilename = item.data(0, Qt.ItemDataRole.UserRole)
                if rfilename:
                    files.append(rfilename)
            else:
                files.extend(self.get_checked_files(item, path))
        return files


    def update_select_toggle_btn_text(self):
        def all_checked(parent):
            for i in range(parent.childCount()):
                item = parent.child(i)
                if item.checkState(0) != Qt.CheckState.Checked:
                    return False
                if not all_checked(item):
                    return False
            return True
        root = self.file_tree_widget.invisibleRootItem()
        checked = all_checked(root)
        self.select_toggle_btn.setText("全不选" if checked else "全选")

    def batch_multithread_download(self):
        idm_path = get_idm_path_from_ini()
        if not idm_path:
            self.safe_log(log_with_time("未检测到IDM，请确认已安装或手动选择路径！"))
            return


        # 获取选中的文件
        file_list = self.get_checked_files()
        if not file_list:
            self.safe_log(log_with_time("请至少勾选一个文件！"))
            return

        repo_id = self.repo_input.text().strip()
        token = self.token_input.text().strip()
        base_url = self.get_base_url()
        repo_type = get_repo_type(repo_id, base_url, token if token else None)
        if not repo_type:
            self.safe_log(log_with_time("仓库类型识别失败！"))
            return

        # 生成下载链接
        urls = []
        for filename in file_list:
            if self.encode_checkbox.isChecked():
                filename_encoded = url_encode_path(filename)
            else:
                filename_encoded = filename
            if repo_type == "datasets":
                url = f"{base_url}/datasets/{repo_id}/resolve/main/{filename_encoded}"
            else:
                url = f"{base_url}/{repo_id}/resolve/main/{filename_encoded}"
            urls.append((url, filename))

        save_dir = self.download_path

        # 添加到IDM下载队列
        for url, filename in urls:
            repo_dir = repo_id.replace("/", "_")
            save_full_path = os.path.join(save_dir, repo_dir, *filename.split("/"))
            os.makedirs(os.path.dirname(save_full_path), exist_ok=True)
            cmd = [
                idm_path,
                '/d', url,
                '/p', os.path.dirname(save_full_path),
                '/f', os.path.basename(filename),
                '/a',
            ]
            #说明：
            #/d 后跟下载链接
            #/f 后跟保存的文件名
            #/p 后跟保存目录
            #/n 静默下载
            #/a 添加到队列不自动开始（可选）
            #/u /p 可加用户名密码
            try:
                subprocess.run(cmd, check=True)
                self.safe_log(log_with_time(f"已添加到IDM队列: {filename}"))
            except Exception as e:
                self.safe_log(log_with_time(f"添加到IDM失败: {filename}，错误: {e}"))

        # 根据勾选决定是否自动开始
        if self.auto_start_checkbox.isChecked():
            try:
                subprocess.run([idm_path, '/s'], check=True)
                self.safe_log(log_with_time("已通知IDM开始下载队列。"))
            except Exception as e:
                self.safe_log(log_with_time(f"启动IDM队列失败: {e}"))

    def get_base_url(self):
        return self.origin_input.text().strip() if self.origin_radio.isChecked() else self.mirror_input.text().strip()

    @staticmethod
    def format_size(num):
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if num < 1024.0:
                return f"{num:.2f}{unit}"
            num /= 1024.0
        return f"{num:.2f}PB"

if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        win = HFDownloaderGUI()
        win.show()
        sys.exit(app.exec())
    except Exception as e:
        print(f"主线程异常: {e}")