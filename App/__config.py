import json as _json
import re
from pathlib import Path
from typing import Any, Callable, TypeVar

from . import __log as _l
from . import __utils as _u
from .__proxy import (
    Network,
    ProxyConfig,
    getCurrentProxy,
)

SAVE_FILE = _u.getExeRelPath("config.json")
CONFIG_NAME_CHECK_REGEX = r"^[\w\d_]+$"
NWINFO_TEXT_SPLITTER = " | "

_T = TypeVar("_T")


def checkConfigName(name: str) -> bool:
    return (
        len(name) > 0
        and name[0] != "_"
        and re.match(CONFIG_NAME_CHECK_REGEX, name) is not None
    )


def save() -> None:
    with SAVE_FILE.open("w", encoding="utf-8") as f:
        _json.dump(
            {
                "proxy": {k: v.model_dump() for k, v in proxyConfig.items()},
                "general": generalConfig,
            },
            f,
            ensure_ascii=False,
            indent=4,
        )
        _l.info(f"saved {len(proxyConfig)} proxy configs to {SAVE_FILE}")


def load() -> None:
    global proxyConfig, generalConfig
    if SAVE_FILE.exists():
        try:
            with SAVE_FILE.open("r", encoding="utf-8") as f:
                _l.info(f"loaded config file {SAVE_FILE}")
                config: dict[str, dict[str, Any]] = _json.load(f)
                proxyConfig = {
                    k: ProxyConfig.model_validate(v)
                    for k, v in config.get("proxy", {}).items()
                }
                generalConfig = config.get("general", {})  # type: ignore
            return
        except:
            _l.error(f"failed to load config file {SAVE_FILE}")
            SAVE_FILE.rename(SAVE_FILE.with_name(f"{SAVE_FILE.name}.bak"))
    _l.warning(f"config file {SAVE_FILE} not valid, creating new one")
    with SAVE_FILE.open("w", encoding="utf-8") as f:
        _json.dump(
            {
                "proxy": {},
                "general": {},
            },
            f,
            ensure_ascii=False,
            indent=4,
        )
        _l.info(f"created new config file {SAVE_FILE}")


def identifyActive() -> None:
    global activeProxyKey
    if len(proxyConfig) > 0:
        try:
            currentProxy = getCurrentProxy()
            activeProxyKey = next(
                k for k, v in proxyConfig.items() if v == currentProxy
            )
        except (ValueError, StopIteration):
            pass
    _l.info(f"active proxy config identified as {activeProxyKey}")


def setCurrentProxy(key: str) -> None:
    global activeProxyKey
    if key not in proxyConfig:
        _l.error(f"proxy config {key} not found")
        return
    proxyConfig[key].proxy.apply()
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
        proxy.proxy.apply()


def setGeneral(key: str, value: Any) -> None:
    global generalConfig
    generalConfig[key] = value
    save()


def getGeneral(key: str, default: _T) -> _T:
    global generalConfig
    return generalConfig.get(key, default)


def nwInfoToText(nwInfo: Network) -> str:
    return (
        f"{nwInfo.ssid}{NWINFO_TEXT_SPLITTER}{nwInfo.mac}"
        if nwInfo.ssid is not None
        else nwInfo.mac or ""
    )


def textToNwInfo(text: str) -> Network:
    return Network(
        mac=(
            (m if (m := s[-1]) else None)
            if len((s := text.rsplit(NWINFO_TEXT_SPLITTER, 1))) > 1
            else text
        ),
        ssid=(ss if (ss := s[0]) else None) if len(s) > 1 else None,
    )


ConfigSerCallbackType = Callable[[str], None]

proxyConfig: dict[str, ProxyConfig] = {}
generalConfig: dict[str | None, Any] = {}
activeProxyKey: str | None = None
configSetCallback: ConfigSerCallbackType = lambda _: None

load()
identifyActive()
