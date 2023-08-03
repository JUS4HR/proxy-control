import threading
import time

from . import __config as _c
from . import __proxy as _p
from . import __utils as _u
from . import __toast as _t
from . import __debounce as _d

AUTO_MAP_ENABLED_ENTRY = 'auto_map'
AUTO_MAP_CONFIG_ENTRY = 'auto_map_config'
DEPRECATED_STR = '配置失效'
NULL_KEY_REPLACEMENT = 'TlVMX0FTX0Y=\u0000'


def _saveConfig() -> None:
    replacedConfig = {(NULL_KEY_REPLACEMENT if k is None else k): v for k, v in _config.items()}
    _c.setGeneral(AUTO_MAP_CONFIG_ENTRY, replacedConfig)


def _loadConfig() -> dict[str | None, str | None]:
    replacedConfig: dict[str, str | None] = _c.getGeneral(AUTO_MAP_CONFIG_ENTRY, {})
    return {k if k != NULL_KEY_REPLACEMENT else None: v for k, v in replacedConfig.items()}


def _networkChangeDetection() -> None:
    global _lastSSID
    while _active:
        if not _u.isConnected():
            while _active:
                if _u.isConnected():
                    break
                time.sleep(1)
            else:
                return
            ssid = _u.getSSID()
            if ssid != _lastSSID:
                applyMapping()
                _lastSSID = ssid
        time.sleep(1)


@_d.debounce(2000)
def applyMapping(force: bool = False) -> None:
    global _lastSSID
    if force:
        _lastSSID = _u.getSSID()
    if _lastSSID in _config:  # assuming is connected
        confName = _config[_lastSSID]
        if confName is not None and confName in _c.proxyConfig:
            _c.proxyConfig[confName].apply()
            _p.setEnabled(True)
            _t.toast(f"根据网络 [{_lastSSID or '有线连接'}]，使用配置 [{confName}]")
            return
        _p.setEnabled(False)
        _t.toast(f"根据网络 [{_lastSSID or '有线连接'}]，已禁用代理")


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


_active: bool = _c.getGeneral(AUTO_MAP_ENABLED_ENTRY, False)
_lastSSID: str | None = _u.getSSID()
_thread: threading.Thread = threading.Thread(target=_networkChangeDetection, daemon=True)
_config: dict[str | None, str | None] = _loadConfig()

_checkMapping()
if _active:
    applyMapping()
    start(skipConf=True)
