import os
from typing import Callable

import qdarktheme
from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QIcon, QIntValidator
from PyQt5.QtWidgets import (QAction, QApplication, QCheckBox, QComboBox, QDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit,
                             QListWidget, QMainWindow, QMenu, QMessageBox, QPushButton, QSystemTrayIcon, QTabWidget,
                             QVBoxLayout, QWidget)

from . import __config as _c
from . import __dark as _d
from . import __debounce as _deb
from . import __log as _l
from . import __mapping as _m
from . import __proxy as _p
from . import __utils as _u

MAPPING_UNSET_KW = '断开'
MAPPING_SSID_WIRED_KW = '有线网络'


def stop() -> None:
    _p.stop()
    _d.stop()
    APP.quit()
    _l.info("Stopped gracefully")


def openMSSettings() -> None:
    os.system('start ms-settings:network-proxy')


### app
class App(QApplication):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


# main window
class ConfigWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setWindowTitle("设置")
        self.tabs = QTabWidget(self)
        self.setCentralWidget(self.tabs)

        self.configTab = ConfigPage()
        self.mappingTab = MappingPage()
        self.optionsTab = OptionsPage()
        self.tabs.addTab(self.configTab, "配置")
        self.tabs.addTab(self.mappingTab, "映射")
        self.tabs.addTab(self.optionsTab, "选项")

        self.pageUpdates = {
            0: lambda: self.configTab.updateList(),
            1: lambda: self.mappingTab.updateTable(),
            2: lambda: self.optionsTab.updateOptions(),
        }
        self.tabs.currentChanged.connect(self.onCurrentChanged)

        self.setFixedSize(330, 260)
        self.setWindowFlag(getattr(Qt, 'WindowContextHelpButtonHint'), False)

        self.pageUpdates[self.tabs.currentIndex()]()

    def onCurrentChanged(self, index: int) -> None:
        _l.debug(f"Current tab changed to {index}")
        return self.pageUpdates[index]()

    def show(self) -> None:
        super().show()
        self.setWindowIcon(QIcon(_d.getTBIconPath(lastEnabled, lastWindowLight)))


# config page
class ConfigPage(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rootLayout = QHBoxLayout(self)
        self.setLayout(self.rootLayout)
        # left list
        self.list = QListWidget(self)
        self.list.setFixedWidth(200)
        self.list.itemSelectionChanged.connect(self.onSelectionChanged)
        self.list.itemDoubleClicked.connect(self.editConfig)
        self.rootLayout.addWidget(self.list)
        # right buttons
        self.buttons = QVBoxLayout()
        self.buttons.setAlignment(getattr(Qt, 'AlignTop'))
        self.rootLayout.addLayout(self.buttons)
        self.appendBtn = QPushButton("添加")
        self.appendBtn.clicked.connect(self.newConfig)
        self.buttons.addWidget(self.appendBtn)
        self.editBtn = QPushButton("编辑")
        self.editBtn.clicked.connect(self.editConfig)
        self.editBtn.setEnabled(len(self.list.selectedIndexes()) > 0)
        self.buttons.addWidget(self.editBtn)
        self.removeBtn = QPushButton("删除")
        self.removeBtn.clicked.connect(self.removeConfig)
        self.removeBtn.setEnabled(len(self.list.selectedIndexes()) > 0)
        self.buttons.addWidget(self.removeBtn)

    def updateList(self) -> None:
        self.list.clear()
        for key in _c.proxyConfig.keys():
            self.list.addItem(key)
        _l.debug("Page updated config list")

    def newConfig(self) -> None:
        editWindow = ConfigEditWindow(title="新配置")
        editWindow.accepted.connect(self.updateList)
        editWindow.move(self.mapToGlobal(self.rect().center() - editWindow.rect().center()))
        editWindow.exec_()
        self.editWindow = editWindow  # store a reference to prevent garbage collection

    def editConfig(self) -> None:
        if len(self.list.selectedIndexes() or []) == 0:
            _l.warning("No config selected")
            return
        selectedKey = self.list.selectedIndexes()[0].data()
        editWindow = ConfigEditWindow(title="编辑配置", name=selectedKey, config=_c.proxyConfig[selectedKey])
        editWindow.accepted.connect(self.updateList)
        editWindow.move(self.mapToGlobal(self.rect().center() - editWindow.rect().center()))
        editWindow.exec_()
        self.editWindow = editWindow  # store a reference to prevent garbage collection

    def removeConfig(self) -> None:
        selected_indexes = self.list.selectedIndexes()
        if not selected_indexes:
            _l.warning("No config selected")
            return
        confirm = QMessageBox.question(self, "确认", "确定要删除所选配置吗？", QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            for i in selected_indexes:
                item = i.data()
                _c.removeProxy(item)
                _l.info(f"Removed config {item}")
            self.updateList()

    def onSelectionChanged(self) -> None:
        self.removeBtn.setEnabled(len(self.list.selectedItems()) > 0)
        self.editBtn.setEnabled(len(self.list.selectedItems()) > 0)


# mapping page
class MappingPage(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rootLayout = QVBoxLayout(self)
        self.setLayout(self.rootLayout)

        self.tableLayout = QHBoxLayout()
        self.tableLayout.setAlignment(getattr(Qt, 'AlignCenter'))
        self.rootLayout.addLayout(self.tableLayout)

        self.ssidLayout = QVBoxLayout()
        self.ssidLayout.setAlignment(getattr(Qt, 'AlignTop'))
        self.ssidLabel = QLabel("网络")
        self.ssidLayout.addWidget(self.ssidLabel)
        self.ssidList = QListWidget(self)
        self.ssidList.setFixedWidth(150)
        self.ssidList.currentRowChanged.connect(self.onSelSsid)
        self.ssidList.verticalScrollBar().valueChanged.connect(self.onScrollSsid)
        self.ssidList.setVerticalScrollBarPolicy(getattr(Qt, 'ScrollBarAlwaysOff'))
        self.ssidList.itemDoubleClicked.connect(self.editMapping)
        self.ssidLayout.addWidget(self.ssidList)
        self.tableLayout.addLayout(self.ssidLayout)

        self.configLayout = QVBoxLayout()
        self.configLayout.setAlignment(getattr(Qt, 'AlignTop'))
        self.configLabel = QLabel("配置")
        self.configLayout.addWidget(self.configLabel)
        self.configList = QListWidget(self)
        self.configList.setFixedWidth(150)
        self.configList.currentRowChanged.connect(self.onSelConfig)
        self.configList.verticalScrollBar().valueChanged.connect(self.onScrollConfig)
        self.configList.itemDoubleClicked.connect(self.editMapping)
        self.configLayout.addWidget(self.configList)
        self.tableLayout.addLayout(self.configLayout)

        self.buttonsLayout = QHBoxLayout()
        self.buttonsLayout.setAlignment(getattr(Qt, 'AlignCenter'))
        self.rootLayout.addLayout(self.buttonsLayout)
        self.appendBtn = QPushButton("添加")
        self.appendBtn.clicked.connect(self.newMapping)
        self.buttonsLayout.addWidget(self.appendBtn)
        self.editBtn = QPushButton("编辑")
        self.editBtn.clicked.connect(self.editMapping)
        self.editBtn.setEnabled(len(self.ssidList.selectedIndexes()) > 0)
        self.buttonsLayout.addWidget(self.editBtn)
        self.removeBtn = QPushButton("删除")
        self.removeBtn.clicked.connect(self.removeMapping)
        self.removeBtn.setEnabled(len(self.ssidList.selectedIndexes()) > 0)
        self.buttonsLayout.addWidget(self.removeBtn)

    def updateTable(self) -> None:
        self.ssidList.clear()
        self.configList.clear()
        for ssid, config in _m.config().items():
            _l.debug(f"Adding mapping {ssid} -> {config}")
            self.ssidList.addItem(ssid or MAPPING_SSID_WIRED_KW)
            self.configList.addItem(config or MAPPING_UNSET_KW)

    def onSelSsid(self, index: int) -> None:
        self.configList.setCurrentRow(index)
        self.editBtn.setEnabled(index >= 0)
        self.removeBtn.setEnabled(index >= 0)

    def onSelConfig(self, index: int) -> None:
        self.ssidList.setCurrentRow(index)

    def onScrollSsid(self, value: int) -> None:
        self.configList.verticalScrollBar().setValue(value)

    def onScrollConfig(self, value: int) -> None:
        self.ssidList.verticalScrollBar().setValue(value)

    def newMapping(self) -> None:
        editWindow = MappingEditWindow(new=True)
        editWindow.accepted.connect(self.updateTable)
        editWindow.move(self.mapToGlobal(self.rect().center() - editWindow.rect().center()))
        editWindow.exec_()
        self.editWindow = editWindow

    def editMapping(self) -> None:
        ssid: str | None = self.ssidList.currentItem().text()
        if ssid == MAPPING_SSID_WIRED_KW:
            ssid = None
        config: str | None = self.configList.currentItem().text()
        if config == MAPPING_UNSET_KW:
            config = None
        editWindow = MappingEditWindow(new=False, oldSsid=ssid, oldConfig=config)
        editWindow.accepted.connect(self.updateTable)
        editWindow.move(self.mapToGlobal(self.rect().center() - editWindow.rect().center()))
        editWindow.exec_()
        self.editWindow = editWindow

    def removeMapping(self) -> None:
        selIndexes = self.ssidList.selectedIndexes()
        if not selIndexes:
            _l.warning("No mapping selected")
            return
        confirm = QMessageBox.question(self, "确认", "确定要删除所选映射吗？", QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            for i in selIndexes:
                item = i.data()
                if item == MAPPING_SSID_WIRED_KW:
                    item = None
                _m.removeMapping(item)
                _l.info(f"Removed mapping {item}")
            self.updateTable()


# options page
class OptionsPage(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rootLayout = QVBoxLayout(self)
        self.rootLayout.setAlignment(getattr(Qt, 'AlignTop'))
        self.setLayout(self.rootLayout)
        self.startupBtn = QCheckBox("开机启动")
        self.startupBtn.clicked.connect(self.switchStartup)
        self.rootLayout.addWidget(self.startupBtn)
        self.autoSelectBtn = QCheckBox("根据当前网络自动选择配置")
        self.autoSelectBtn.clicked.connect(self.switchAutoSelect)
        self.rootLayout.addWidget(self.autoSelectBtn)
        self.autoSelectDuration = QLineEdit()
        self.autoSelectDuration.setValidator(QIntValidator(1, 60 * 60, self))
        self.autoSelectDuration.setFixedWidth(50)
        self.autoSelectDuration.setPlaceholderText(str(_m.NETWORK_CHECK_INTERVAL_DEFAULT))
        self.autoSelectDuration.textChanged.connect(self.updateAutoSelectDuration)
        self.rootLayout.addWidget(self.autoSelectDuration)
        self.autoSelectHint = QLabel("此功能现可能占用系统资源。若禁用此项，可在托盘菜单中手动映射")
        self.autoSelectHint.setWordWrap(True)
        self.rootLayout.addWidget(self.autoSelectHint)

    def switchStartup(self) -> None:
        if self.startupEnabled:
            _u.disable_startup()
        else:
            _u.enable_startup()
        self.updateOptions()

    def updateOptions(self) -> None:
        self.startupEnabled = _u.check_startup()
        self.startupBtn.setChecked(self.startupEnabled)
        self.autoSelectBtn.setChecked(_m.active())
        self.autoSelectDuration.setText(str(_m.getCheckInterval()))

    def switchAutoSelect(self) -> None:
        if self.autoSelectBtn.isChecked():
            _m.start()
        else:
            _m.stop()

    def updateAutoSelectDuration(self, text: str) -> None:
        _m.setCheckInterval(int(text) if text else _m.NETWORK_CHECK_INTERVAL_DEFAULT)


# config edit window
class ConfigEditWindow(QDialog):
    def __init__(self, title: str, name: str = "新配置", config: _p.ProxyConfig | None = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setWindowTitle(title)
        self.new = config is None
        self.oldName = name
        self.config = config or _p.getCurrentProxy() or _p.ProxyConfig(_p.PROXY_ALLOWED_PROTOS[0], "", 80)
        self.rootLayout = QVBoxLayout(self)
        self.setLayout(self.rootLayout)
        self.form = QFormLayout()
        self.rootLayout.addLayout(self.form)
        self.name = QLineEdit()
        self.form.addRow("名称", self.name)
        self.proto = QComboBox()
        self.proto.addItems(_p.PROXY_ALLOWED_PROTOS)
        self.form.addRow("协议", self.proto)
        self.host = QLineEdit()
        self.form.addRow("主机", self.host)
        self.port = QLineEdit()
        self.form.addRow("端口", self.port)
        self.port.setValidator(QIntValidator())
        # self.username = QLineEdit()
        # self.form.addRow("用户名", self.username)
        # self.password = QLineEdit()
        # self.form.addRow("密码", self.password)
        # self.auth = QCheckBox()
        # self.form.addRow("认证", self.auth)
        self.btnLayout = QHBoxLayout()
        self.btnLayout.setAlignment(getattr(Qt, 'AlignRight'))
        self.rootLayout.addLayout(self.btnLayout)
        self.saveBtn = QPushButton("保存")
        self.saveBtn.clicked.connect(self.apply)
        self.btnLayout.addWidget(self.saveBtn)
        self.cancelBtn = QPushButton("取消")
        self.cancelBtn.clicked.connect(self.reject)
        self.btnLayout.addWidget(self.cancelBtn)

        self.name.setText(name)
        self.proto.setCurrentText(self.config.proto)
        self.host.setText(self.config.host)
        self.port.setText(str(self.config.port))
        # self.username.setText(self.config.username)
        # self.password.setText(self.config.password)
        # self.auth.setChecked(self.config.auth)

        self.setWindowFlag(getattr(Qt, 'WindowContextHelpButtonHint'), False)
        self.setFixedSize(QSize(250, 150))

    def apply(self) -> None:
        if not _c.checkConfigName(self.name.text()):
            QMessageBox.warning(self, "错误", "名称不可用")
            return
        elif self.name.text() in _c.proxyConfig and (self.name.text() != self.oldName or self.new):
            QMessageBox.warning(self, "错误", "名称已存在")
            return
        self.config.proto = self.proto.currentText()
        self.config.host = self.host.text()
        self.config.port = int(self.port.text())
        # self.config.username = self.username.text()
        # self.config.password = self.password.text()
        # self.config.auth = self.auth.isChecked()
        if self.new:
            _c.addProxy(self.name.text(), self.config)
        else:
            _c.updateProxy(self.oldName, self.name.text(), self.config)
        self.accept()


# mapping edit window
class MappingEditWindow(QDialog):
    def __init__(self, new: bool = False, oldSsid: str | None = None, oldConfig: str | None = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.new = new
        self.setWindowTitle("新映射" if new else "编辑映射")
        if new:
            currSsid = _u.getSSID()
            self.oldSsid = None if currSsid in _m.config() else currSsid
        else:
            self.oldSsid = oldSsid
        _l.debug(f"oldSsid: {self.oldSsid}")
        self.oldConfig = oldConfig
        self.rootLayout = QVBoxLayout(self)
        self.setLayout(self.rootLayout)
        self.form = QFormLayout()
        self.rootLayout.addLayout(self.form)
        self.ssid = QLineEdit()
        self.ssid.setText(self.oldSsid or "")
        self.ssid.setPlaceholderText("留空则为有线网络")
        self.form.addRow("SSID", self.ssid)
        self.config = QComboBox()
        self.config.addItems(list(_c.proxyConfig.keys()) + [MAPPING_UNSET_KW])
        self.config.setCurrentText(self.oldConfig or MAPPING_UNSET_KW)
        self.form.addRow("配置", self.config)
        self.btnLayout = QHBoxLayout()
        self.btnLayout.setAlignment(getattr(Qt, 'AlignRight'))
        self.rootLayout.addLayout(self.btnLayout)
        self.saveBtn = QPushButton("保存")
        self.saveBtn.clicked.connect(self.apply)
        self.btnLayout.addWidget(self.saveBtn)
        self.cancelBtn = QPushButton("取消")
        self.cancelBtn.clicked.connect(self.reject)
        self.btnLayout.addWidget(self.cancelBtn)
        self.config.setCurrentText(oldConfig or "")

        self.setWindowFlag(getattr(Qt, 'WindowContextHelpButtonHint'), False)
        self.setFixedSize(QSize(250, 120))

    def apply(self) -> None:
        ssid: str | None = self.ssid.text()
        if ssid == "":
            ssid = None
        if self.new and ssid in _m.config():
            QMessageBox.warning(self, "错误", "SSID已存在")
            return
        config: str | None = self.config.currentText()
        if config == MAPPING_UNSET_KW:
            config = None
        _m.addMapping(ssid, config)
        self.accept()


### tray
class TrayIcon(QSystemTrayIcon):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


@_deb.debounce(200)
def getTBDescription() -> str:
    return '\n'.join([
        "代理切换器",
        f"状态: " + ('\u2713' if lastEnabled else '\u2717'),
        f"配置: {lastConfigKey}",
        f"协议: {lastProto}",
        f"主机: {lastHost}",
        f"端口: {lastPort}",
    ])


def handleTrayClick(reason: QSystemTrayIcon.ActivationReason) -> None:
    # if reason == QSystemTrayIcon.ActivationReason.Trigger:
    #     TRAY_MENU.show()
    if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
        _p.setEnabled(not lastEnabled)


### action
class Action(QAction):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


# base actions
def updateTrayActions() -> None:
    TRAY_MENU.clear()
    for text, callback in TOP_ACTIONS:
        TRAY_MENU.addAction(Action(text, TRAY_MENU, triggered=callback))
    TRAY_MENU.addSeparator()
    TRAY_MENU.addAction(Action("设置", CONFIG_MENU, triggered=showConfigWindow))
    TRAY_MENU.addMenu(CONFIG_MENU)
    if not _m.active():
        TRAY_MENU.addAction(Action("映射配置", TRAY_MENU, triggered=lambda: _m.applyMapping(force=True)))
    TRAY_MENU.addSeparator()
    for text, callback in BOTTOM_ACTIONS:
        TRAY_MENU.addAction(Action(text, TRAY_MENU, triggered=callback))


# config actions
def updateConfigActions() -> None:
    CONFIG_MENU.clear()
    if len(_c.proxyConfig) > 0:
        for key in _c.proxyConfig.keys():
            action = Action(key, CONFIG_MENU, triggered=lambda: _c.setCurrentProxy(key))
            if key == _c.activeProxyKey:
                action.setCheckable(True)
                action.setChecked(True)
            CONFIG_MENU.addAction(action)
    else:
        CONFIG_MENU.addAction(Action("无配置", CONFIG_MENU, enabled=False))


def showConfigWindow() -> None:
    # Move config window to near the tray icon
    config_window_size = CONFIG_WINDOW.size()
    tray_geometry = TRAY_ICON.geometry()
    config_window_x = tray_geometry.x() + tray_geometry.width() / 2 - config_window_size.width() / 2
    config_window_y = tray_geometry.y() + tray_geometry.height() / 2 - config_window_size.height() / 2
    screen_geometry = QApplication.desktop().availableGeometry(CONFIG_WINDOW)
    config_window_x = min(max(config_window_x,
                              screen_geometry.left() + 50),
                          screen_geometry.right() - config_window_size.width() - 50)
    config_window_y = min(max(config_window_y,
                              screen_geometry.top() + 50),
                          screen_geometry.bottom() - config_window_size.height() - 50)
    CONFIG_WINDOW.move(int(config_window_x), int(config_window_y))
    CONFIG_WINDOW.show()


### tray menu
class TrayMenu(QMenu):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.aboutToShow.connect(updateTrayActions)


### config menu
class ConfigMenu(QMenu):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.aboutToShow.connect(updateConfigActions)


### callbacks
def enabledCallback(enabled: bool):
    global lastEnabled
    lastEnabled = enabled
    TRAY_ICON.setIcon(QIcon(_d.getTBIconPath(enabled, lastTBLight)))
    TRAY_ICON.setToolTip(getTBDescription())


def protoCallback(proto: str):
    global lastProto
    lastProto = proto
    TRAY_ICON.setToolTip(getTBDescription())


def hostCallback(host: str):
    global lastHost
    lastHost = host
    TRAY_ICON.setToolTip(getTBDescription())


def portCallback(port: int):
    global lastPort
    lastPort = port
    TRAY_ICON.setToolTip(getTBDescription())


def noProxyCallback(noProxy: list[str]):
    global lastNoProxy
    lastNoProxy = noProxy
    TRAY_ICON.setToolTip(getTBDescription())


def configSetCallback(key: str):
    global lastConfigKey, lastConfig
    lastConfigKey = key
    lastConfig = _c.proxyConfig[key]
    TRAY_ICON.setToolTip(getTBDescription())


def windowThemeCallback(light: bool):
    global lastWindowLight
    lastWindowLight = light


def tbThemeCallback(light: bool):
    global lastTBLight
    TRAY_ICON.setIcon(QIcon(_d.getTBIconPath(lastEnabled, light)))
    lastTBLight = light


### init
_p.enabledCallback = enabledCallback
_p.protoCallback = protoCallback
_p.hostCallback = hostCallback
_p.portCallback = portCallback
_p.noProxyiesCallback = noProxyCallback
_c.configSetCallback = configSetCallback
_d.windowCallback = windowThemeCallback
_d.taskbarCallback = tbThemeCallback
_p.start()
_d.start()

# status
lastEnabled = _p.getEnabled()
lastConfigKey = _c.activeProxyKey
lastConfig = _p.getCurrentProxy()
lastProto = lastConfig.proto
lastHost = lastConfig.host
lastPort = lastConfig.port
lastNoProxy = lastConfig.noProxyies
lastWindowLight = _d.isWindowLight()
lastTBLight = _d.isTBLight()

# app
qdarktheme.enable_hi_dpi()
APP = App([])
APP.setQuitOnLastWindowClosed(False)
qdarktheme.setup_theme("auto")

# static actions
TOP_ACTIONS: list[tuple[str, Callable]] = [
    ('切换 (双击图标)', lambda: _p.setEnabled(not lastEnabled)),
    ('打开系统设置', openMSSettings),
]
BOTTOM_ACTIONS: list[tuple[str, Callable]] = [
    ('关闭', stop),
]

# config window
CONFIG_WINDOW = ConfigWindow()

# tray menu
TRAY_MENU = TrayMenu()

# config menu
CONFIG_MENU = ConfigMenu("选择配置")

# tray icon
TRAY_ICON = TrayIcon(QIcon(_d.getTBIconPath(lastEnabled, lastTBLight)), APP)
TRAY_ICON.setToolTip(getTBDescription())
TRAY_ICON.setContextMenu(TRAY_MENU)
TRAY_ICON.activated.connect(handleTrayClick)
TRAY_ICON.show()