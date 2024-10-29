import sys

if sys.platform != "win32":
    raise NotImplementedError("Wrong platform for this module")
import abc
import re
import threading
from typing import Callable, Literal

from pydantic import BaseModel, Field

from . import __log as _l
from . import __reg as reg
from . import __utils as _u

PROXY_ENTRY = rf"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
PROXY_ENABLED_ENTRY = "ProxyEnable"
PROXY_SERVER_ENTRY = "ProxyServer"
PROXY_OVERRIDE_ENTRY = "ProxyOverride"

PROXY_URL_REGEX = re.compile(
    "^(?:(?P<protocol>http|https|socks4|socks5)://)?(?P<host>[^:/]+)(?::(?P<port>\d+))?$"
)

if sys.platform == "win32":
    ProxyProto = Literal["http", "https", "socks4", "socks5"]
    PROXY_ALLOWED_PROTOS: list[ProxyProto] = ["http", "https", "socks4", "socks5"]
    DEFUALT_NO_PROXY = ["localhost", "192.168.x.x", "<local>"]
elif sys.platform == "linux":
    ProxyProto = Literal["http", "https", "socks4", "socks5", "socks5h"]
    PROXY_ALLOWED_PROTOS = ["http", "https", "socks4", "socks5", "socks5h"]
    DEFUALT_NO_PROXY = ["localhost", "127.0.0.1", "::1", ".local"]
else:
    raise NotImplementedError(f"unsupported platform {sys.platform}")

ProxyEnabledWatcherCallbackType = Callable[[bool], None]
ProxyProtocolWatcherCallbackType = Callable[[ProxyProto], None]
ProxyFollowGatewayWatcherCallbackType = Callable[[bool], None]
ProxyHostWatcherCallbackType = Callable[[str], None]
ProxyPortWatcherCallbackType = Callable[[int], None]
ProxyNoProxyiesWatcherCallbackType = Callable[[list[str]], None]


def splitURL(url: str) -> tuple[ProxyProto, str, int]:
    match = PROXY_URL_REGEX.match(url)
    if match is None:
        raise ValueError(f"invalid proxy url {url}")
    proto: ProxyProto = "http" if (mpr := f"{match.group('protocol')}".lower()) is None or mpr not in PROXY_ALLOWED_PROTOS else mpr  # type: ignore
    port: int = 80 if (mpo := match.group("port")) is None else int(mpo)
    return proto, f"{match.group('host')}", port


def _monitor_registry_changes() -> None:
    _l.info("started proxy watcher")
    if _key is None:
        return
    _lastEnabled = _key.queryValue(PROXY_ENABLED_ENTRY)[1] != 0
    _lastServer = _key.queryValue(PROXY_SERVER_ENTRY)[1]
    _lastOverride = _key.queryValue(PROXY_OVERRIDE_ENTRY)[1]
    while True:
        if _key is None:
            return
        _key.notifyChange()
        if _key is None:
            return
        _l.debug("proxy registry changed")
        enabled = _key.queryValue(PROXY_ENABLED_ENTRY)[1] != 0
        if enabled != _lastEnabled:
            _l.debug(f"proxy switched to {enabled}")
            _lastEnabled = enabled
            threading.Thread(
                target=enabledCallback, args=(enabled == 1,), daemon=True
            ).start()
        server = str(_key.queryValue(PROXY_SERVER_ENTRY)[1])
        if server != _lastServer:
            _l.debug(f"proxy server changed to {server}")
            _lastServer = server
            proto, host, port = splitURL(server)
            threading.Thread(target=protoCallback, args=(proto,), daemon=True).start()
            threading.Thread(target=hostCallback, args=(host,), daemon=True).start()
            threading.Thread(target=portCallback, args=(port,), daemon=True).start()
        override = str(_key.queryValue(PROXY_OVERRIDE_ENTRY)[1])
        if override != _lastOverride:
            _l.debug(f"proxy override changed to {override}")
            _lastOverride = override
            threading.Thread(
                target=noProxyiesCallback, args=(override.split(";"),), daemon=True
            ).start()


class Network(BaseModel):
    """To identify a network"""

    mac: str | None = Field(None, description="Network MAC address")
    ssid: str | None = Field(
        None, description="Network SSID, None for wired connection"
    )

    class Config:
        extra = "forbid"
        # allow_mutation = False

    def __hash__(self) -> int:
        return hash((type(self),) + tuple(self.__dict__.values()))

    def __repr__(self) -> str:
        return f"{self.ssid or '有线连接'} ({self.mac or '任意网关MAC'})"

    def __str__(self) -> str:
        return self.__repr__()


class Proxy(BaseModel):
    proto: ProxyProto = Field(PROXY_ALLOWED_PROTOS[0], description="Proxy protocol")
    port: int = Field(..., description="Proxy port")
    noProxyies: list[str] = Field(DEFUALT_NO_PROXY, description="No proxyies")
    proxyType: Literal["SpecificProxy", "GatewayProxy"] = Field(
        ..., description="Proxy type"
    )

    class Config:
        extra = "forbid"

    @property
    @abc.abstractmethod
    def url(self) -> str: ...

    @property
    def noProxyiesString(self) -> str:
        return ";".join(self.noProxyies)

    def apply(self) -> None:
        with reg.RegKey(
            reg.getHKey(reg.RegKeyRoot.HKEY_CURRENT_USER),
            PROXY_ENTRY,
            reg.RegKeyAccess.KEY_WRITE,
        ) as key:
            key.setValue(PROXY_SERVER_ENTRY, self.url, reg.RegValueType.REG_SZ)
            key.setValue(
                PROXY_OVERRIDE_ENTRY, self.noProxyiesString, reg.RegValueType.REG_SZ
            )
        _l.info(f"applied proxy config {self} to registry")


class SpecificProxy(Proxy):
    host: str = Field(..., description="Proxy host")
    proxyType: Literal["SpecificProxy"] = "SpecificProxy"

    @property
    def url(self) -> str:
        return f"{self.proto}://{self.host}:{self.port}"


class GatewayProxy(Proxy):
    proxyType: Literal["GatewayProxy"] = "GatewayProxy"

    @property
    def url(self) -> str:
        return f"{self.proto}://{_u.getGateway()}:{self.port}"


class ProxyConfig(BaseModel):
    """Proxy configuration"""

    proxy: SpecificProxy | GatewayProxy = Field(
        ..., description="Proxy configuration", discriminator="proxyType"
    )


def getCurrentProxy() -> ProxyConfig:
    with reg.RegKey(
        reg.getHKey(reg.RegKeyRoot.HKEY_CURRENT_USER),
        PROXY_ENTRY,
        reg.RegKeyAccess.KEY_READ,
    ) as key:
        proxyServer = str(key.queryValue(PROXY_SERVER_ENTRY)[1])
        proxyOverride = str(key.queryValue(PROXY_OVERRIDE_ENTRY)[1])
    proto, host, port = splitURL(proxyServer)
    noProxyies = proxyOverride.split(";")
    ret = ProxyConfig(
        proxy=SpecificProxy(proto=proto, host=host, port=port, noProxyies=noProxyies)
    )
    _l.debug(f"loaded {ret} from registry")
    return ret


def getEnabled() -> bool:
    with reg.RegKey(
        reg.getHKey(reg.RegKeyRoot.HKEY_CURRENT_USER),
        PROXY_ENTRY,
        reg.RegKeyAccess.KEY_READ,
    ) as key:
        ret = key.queryValue(PROXY_ENABLED_ENTRY)[1] != 0
    _l.debug(f"loaded status {ret} from registry")
    return ret


def setEnabled(enabled: bool) -> None:
    with reg.RegKey(
        reg.getHKey(reg.RegKeyRoot.HKEY_CURRENT_USER),
        PROXY_ENTRY,
        reg.RegKeyAccess.KEY_WRITE,
    ) as key:
        key.setValue(
            PROXY_ENABLED_ENTRY, 1 if enabled else 0, reg.RegValueType.REG_DWORD
        )
    _l.info(f"set proxy status to {enabled}")


def start() -> None:
    global _thread, _key
    _l.info("starting proxy watcher...")
    _key = reg.RegKey(
        reg.getHKey(reg.RegKeyRoot.HKEY_CURRENT_USER),
        PROXY_ENTRY,
        reg.RegKeyAccess.KEY_NOTIFY | reg.RegKeyAccess.KEY_READ,
    )
    _key.open()
    _thread = threading.Thread(target=_monitor_registry_changes)
    _thread.daemon = True
    _thread.start()


def stop() -> None:
    global _key
    _l.info("stopping proxy watcher...")
    if _key is not None:
        _key.close()
        _key = None
    if _thread:
        _thread.join()


_thread: threading.Thread | None = None
_key: reg.RegKey | None = None
enabledCallback: ProxyEnabledWatcherCallbackType = lambda _: None
protoCallback: ProxyProtocolWatcherCallbackType = lambda _: None
followGatewayCallback: ProxyFollowGatewayWatcherCallbackType = lambda _: None
hostCallback: ProxyHostWatcherCallbackType = lambda _: None
portCallback: ProxyPortWatcherCallbackType = lambda _: None
noProxyiesCallback: ProxyNoProxyiesWatcherCallbackType = lambda _: None
