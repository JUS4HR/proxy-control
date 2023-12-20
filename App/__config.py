import json as _json
import re
from os import path
from typing import Any, Callable, TypeVar

from . import __log as _l
from . import __utils as _u
from .__proxy import (
    ProxyConfig,
    ProxyConfigDecoder,
    ProxyConfigEncoder,
    getCurrentProxy,
    getFromJson,
)

SAVE_FILE = _u.getExeRelPath("config.json")
CONFIG_NAME_CHECK_REGEX = r"^[\w\d_]+$"

_T = TypeVar("_T")


def checkConfigName(name: str) -> bool:
    return (
        len(name) > 0
        and name[0] != "_"
        and re.match(CONFIG_NAME_CHECK_REGEX, name) is not None
    )


def save() -> None:
    with open(SAVE_FILE, "w") as f:
        _json.dump(
            {
                "proxy": proxyConfig,
                "general": generalConfig,
            },
            f,
            cls=ProxyConfigEncoder,
        )
        _l.info(f"saved {len(proxyConfig)} proxy configs to {SAVE_FILE}")


def load() -> None:
    global proxyConfig, generalConfig
    if not path.exists(SAVE_FILE):
        _l.warning(f"config file {SAVE_FILE} not found, creating new one")
        with open(SAVE_FILE, "w") as f:
            _json.dump(
                {
                    "proxy": {},
                    "general": {},
                },
                f,
                cls=ProxyConfigEncoder,
            )
            _l.info(f"created new config file {SAVE_FILE}")
    else:
        with open(SAVE_FILE, "r") as f:
            _l.info(f"loaded config file {SAVE_FILE}")
            config: dict[str, dict[str, Any]] = _json.load(f, cls=ProxyConfigDecoder)
            proxyConfig = config.get("proxy", {})
            generalConfig = config.get("general", {})


def identifyActive() -> None:
    global activeProxyKey
    if len(proxyConfig) > 0:
        try:
            # activeIndex = config.index(getCurrentProxy())
            activeProxyKey = next(
                k for k, v in proxyConfig.items() if v == getCurrentProxy()
            )
        except ValueError:
            pass
    _l.info(f"active proxy config identified as {activeProxyKey}")


def setCurrentProxy(key: str) -> None:
    global activeProxyKey
    if key not in proxyConfig:
        _l.error(f"proxy config {key} not found")
        return
    proxyConfig[key].apply()
    activeProxyKey = key
    configSetCallback(key)


def removeProxy(key: str) -> None:
    global activeProxyKey
    if key not in proxyConfig:
        _l.error(f"proxy config {key} not found")
        return
    del proxyConfig[key]
    save()
    if key == activeProxyKey:
        activeProxyKey = None


def addProxy(key: str, proxy: ProxyConfig) -> None:
    global activeProxyKey
    if key in proxyConfig:
        _l.error(f"proxy config {key} already exists")
        return
    proxyConfig[key] = proxy
    save()
    if activeProxyKey is None:
        activeProxyKey = key


def updateProxy(oldKey: str, key: str, proxy: ProxyConfig) -> None:
    global activeProxyKey
    if oldKey not in proxyConfig:
        _l.error(f"proxy config {key} not found")
        return
    if oldKey != key:
        del proxyConfig[oldKey]
    proxyConfig[key] = proxy
    save()
    if activeProxyKey == oldKey:
        activeProxyKey = key
        proxy.apply()


def setGeneral(key: str, value: Any) -> None:
    global generalConfig
    generalConfig[key] = value
    save()


def getGeneral(key: str, default: _T) -> _T:
    global generalConfig
    return generalConfig.get(key, default)


ConfigSerCallbackType = Callable[[str], None]

proxyConfig: dict[str, ProxyConfig] = {}
generalConfig: dict[str | None, Any] = {}
activeProxyKey: str | None = None
configSetCallback: ConfigSerCallbackType = lambda _: None

load()
identifyActive()
