import threading
import time

from . import __config as _c
from . import __proxy as _p
from . import __utils as _u
from . import __toast as _t

AUTO_MAP_ENABLED_ENTRY = 'auto_map'
AUTO_MAP_CONFIG_ENTRY = 'auto_map_config'
DEPRECATED_STR = '配置失效'
NULL_KEY_REPLACEMENT = 'TlVMX0FTX0Y=\u0000'
NETWORK_CHECK_INTERVAL_DEFAULT = 20


def _saveConfig() -> None:
    replacedConfig = {(NULL_KEY_REPLACEMENT if k is None else k): v for k, v in _config.items()}
    _c.setGeneral(AUTO_MAP_CONFIG_ENTRY, replacedConfig)


def _loadConfig() -> dict[str | None, str | None]:
    replacedConfig: dict[str, str | None] = _c.getGeneral(AUTO_MAP_CONFIG_ENTRY, {})
    return {k if k != NULL_KEY_REPLACEMENT else None: v for k, v in replacedConfig.items()}


def _networkChangeDetection() -> None:
    global _lastSSID
    while _active:
        if _u.isConnected():
            ssid = _u.getSSID()
            if ssid != _lastSSID:
                _lastSSID = ssid
                applyMapping()
        for _ in range(_networkCheckInterval):
            if not _active:
                break
            time.sleep(1)


def applyMapping(force: bool = False) -> None:
    global _lastSSID
    if force:
        _lastSSID = _u.getSSID()
    if _lastSSID in _config:  # assuming is connected
        confName = _config[_lastSSID]
        if confName is not None and confName in _c.proxyConfig:
            _c.proxyConfig[confName].apply()
            _p.setEnabled(True)
            # _t.toast("配置映射", f"根据网络 [{_lastSSID or '有线连接'}]，使用配置 [{confName}]")
            return
        _p.setEnabled(False)
        # _t.toast("配置映射", f"根据网络 [{_lastSSID or '有线连接'}]，已禁用代理")


def _checkMapping() -> None:
    for ssid, confName in _config.items():
        if confName is not None and confName not in _c.proxyConfig:
            _config[ssid] = DEPRECATED_STR


def start(skipConf: bool = False) -> None:
    global _active, _thread
    if not skipConf:
        _c.setGeneral(AUTO_MAP_ENABLED_ENTRY, True)
    _active = True
    if not _thread.is_alive():
        _thread = threading.Thread(target=_networkChangeDetection, daemon=True)
        _thread.start()


def stop() -> None:
    global _active
    _c.setGeneral(AUTO_MAP_ENABLED_ENTRY, False)
    _active = False
    if _thread.is_alive():
        _thread.join()


def active() -> bool:
    return _active


def config() -> dict[str | None, str | None]:
    _checkMapping()
    return _config


def addMapping(ssid: str | None, confName: str | None) -> None:
    _config[ssid] = confName
    _saveConfig()


def removeMapping(ssid: str | None) -> None:
    _config.pop(ssid, None)
    _saveConfig()

def setCheckInterval(interval: int) -> None:
    global _networkCheckInterval
    _networkCheckInterval = interval
    _c.setGeneral('network_check_interval', interval)

def getCheckInterval() -> int:
    return _networkCheckInterval

_active: bool = _c.getGeneral(AUTO_MAP_ENABLED_ENTRY, False)
_lastSSID: str | None = None
_thread: threading.Thread = threading.Thread(target=_networkChangeDetection, daemon=True)
_config: dict[str | None, str | None] = _loadConfig()
_networkCheckInterval: int = _c.getGeneral('network_check_interval', NETWORK_CHECK_INTERVAL_DEFAULT)

_checkMapping()
if _active:
    start(skipConf=True)
