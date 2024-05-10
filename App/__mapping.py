import threading
import time

from . import __config as _c
from . import __debounce as _d
from . import __proxy as _p
from . import __toast as _t
from . import __utils as _u

AUTO_MAP_ENABLED_ENTRY = "auto_map"
AUTO_MAP_CONFIG_ENTRY = "auto_map_config"
DEPRECATED_STR = "配置失效"
NULL_KEY_REPLACEMENT = "TlVMX0FTX0Y=\u0000"


def _saveConfig() -> None:
    _c.setGeneral(
        AUTO_MAP_CONFIG_ENTRY, {_c.nwInfoToText(k): v for k, v in _config.items()}
    )


def _loadConfig() -> dict[_p.Network, str | None]:
    return {  # type: ignore
        _c.textToNwInfo(k): v
        for k, v in _c.getGeneral(AUTO_MAP_CONFIG_ENTRY, {}).items()
    }


def _getNetworkInfo() -> _p.Network:
    return _p.Network(
        mac=(
            _u.getMacAddr(gwip) or "" if (gwip := _u.getGateway()) is not None else ""
        ),
        ssid=_u.getSSID(),
    )


def _networkChangeDetection() -> None:
    global _lastNetworkInfo
    while _active:
        if not _u.isConnected():
            while _active:
                if _u.isConnected():
                    break
                time.sleep(1)
            else:
                return
            if (nwInfo := _getNetworkInfo()) != _lastNetworkInfo:
                applyMapping()
                _lastNetworkInfo = nwInfo
        time.sleep(1)


@_d.debounce(2000)
def applyMapping(force: bool = False) -> None:
    global _lastNetworkInfo
    if force:
        _lastNetworkInfo = _getNetworkInfo()
    if _lastNetworkInfo is None:
        _p.setEnabled(False)
        _t.toast("无法获取网络信息，已禁用代理")
        return
    if _lastNetworkInfo in _config:  # assuming is connected
        confName = _config[_lastNetworkInfo]
        if confName in _c.proxyConfig:
            _c.proxyConfig[confName].proxy.apply()
            _p.setEnabled(True)
            _t.toast(
                f"根据网络 [{_lastNetworkInfo or '有线连接'}]，使用配置 [{confName}]"
            )
            return
        _p.setEnabled(False)
        _t.toast(f"根据网络 [{_lastNetworkInfo or '有线连接'}]，已禁用代理")
        return
    for info, confName in _config.items():
        if info.mac is None and info.ssid == _lastNetworkInfo.ssid:
            if confName in _c.proxyConfig:
                _c.proxyConfig[confName].proxy.apply()
                _p.setEnabled(True)
                _t.toast(f"根据网络 [{info}]，使用配置 [{confName}]")
                return
            _p.setEnabled(False)
            _t.toast(f"根据网络 [{info}]，已禁用代理")
            return
    _p.setEnabled(False)
    _t.toast(f"未找到适用于网络 [{_lastNetworkInfo}] 的配置，已禁用代理")


def _checkMapping() -> None:
    for nwInfo, confName in _config.items():
        if confName is not None and confName not in _c.proxyConfig:
            _config[nwInfo] = DEPRECATED_STR


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


def config() -> dict[_p.Network, str | None]:
    _checkMapping()
    return _config


def addMapping(nwInfo: _p.Network, confName: str | None) -> None:
    _config[nwInfo] = confName
    _saveConfig()


def removeMapping(nwInfo: _p.Network) -> None:
    _config.pop(nwInfo, None)
    _saveConfig()


_active: bool = _c.getGeneral(AUTO_MAP_ENABLED_ENTRY, False)
_lastNetworkInfo: _p.Network | None = _getNetworkInfo()
_thread: threading.Thread = threading.Thread(
    target=_networkChangeDetection, daemon=True
)
_config: dict[_p.Network, str | None] = _loadConfig()

_checkMapping()
if _active:
    applyMapping()
    start(skipConf=True)
