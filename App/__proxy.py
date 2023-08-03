import json
import re
import threading
import winreg
import platform
from typing import Callable

if platform.system() != 'Windows':
    raise NotImplementedError('Wrong platform for this module')

from win32api import (RegCloseKey, RegNotifyChangeKeyValue, RegOpenKeyEx, RegQueryValueEx, RegSetValueEx)
from win32con import (HKEY_CURRENT_USER, KEY_ALL_ACCESS, KEY_NOTIFY, KEY_READ, KEY_WRITE)

from . import __log as _l

PROXY_ENTRY = rf"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
PROXY_ENABLED_ENTRY = "ProxyEnable"
PROXY_SERVER_ENTRY = "ProxyServer"
PROXY_OVERRIDE_ENTRY = "ProxyOverride"

PROXY_URL_REGEX = r'^(?P<protocol>http|https|socks4|socks5)://(?P<host>[^:]+):(?P<port>\d+)$'

if platform.system() == 'Windows':
    PROXY_ALLOWED_PROTOS = ['http', 'https', 'socks4', 'socks5']
elif platform.system() == 'Linux':
    PROXY_ALLOWED_PROTOS = ['http', 'https', 'socks4', 'socks5', 'socks5h']
else:
    raise NotImplementedError(f'unsupported platform {platform.system()}')

ProxyEnabledWatcherCallbackType = Callable[[bool], None]
ProxyProtocolWatcherCallbackType = Callable[[str], None]
ProxyHostWatcherCallbackType = Callable[[str], None]
ProxyPortWatcherCallbackType = Callable[[int], None]
ProxyNoProxyiesWatcherCallbackType = Callable[[list[str]], None]


def splitURL(url: str) -> tuple[str, str, int]:
    match = re.match(PROXY_URL_REGEX, url)
    if match is None:
        raise ValueError(f'invalid proxy url {url}')
    return match.group('protocol'), match.group('host'), int(match.group('port'))


def _monitor_registry_changes() -> None:
    _l.info('started proxy watcher')
    if _key is None: return
    _lastEnabled = winreg.QueryValueEx(_key, PROXY_ENABLED_ENTRY)[0]
    _lastServer = winreg.QueryValueEx(_key, PROXY_SERVER_ENTRY)[0]
    _lastOverride = winreg.QueryValueEx(_key, PROXY_OVERRIDE_ENTRY)[0]
    while True:
        if _key is None: return
        RegNotifyChangeKeyValue(_key, False, winreg.REG_NOTIFY_CHANGE_LAST_SET, None, False)
        if _key is None: return
        _l.debug('proxy registry changed')
        enabled = winreg.QueryValueEx(_key, PROXY_ENABLED_ENTRY)[0]
        if enabled != _lastEnabled:
            _l.debug(f'proxy switched to {enabled}')
            _lastEnabled = enabled
            threading.Thread(target=enabledCallback, args=(enabled == 1, ), daemon=True).start()
        server = str(winreg.QueryValueEx(_key, PROXY_SERVER_ENTRY)[0])
        if server != _lastServer:
            _l.debug(f'proxy server changed to {server}')
            _lastServer = server
            proto, host, port = splitURL(server)
            threading.Thread(target=protoCallback, args=(proto, ), daemon=True).start()
            threading.Thread(target=hostCallback, args=(host, ), daemon=True).start()
            threading.Thread(target=portCallback, args=(port, ), daemon=True).start()
        override = str(winreg.QueryValueEx(_key, PROXY_OVERRIDE_ENTRY)[0])
        if override != _lastOverride:
            _l.debug(f'proxy override changed to {override}')
            _lastOverride = override
            threading.Thread(target=noProxyiesCallback, args=(override.split(';'), ), daemon=True).start()


class ProxyConfigEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ProxyConfig):
            return obj.dict
        return super().default(obj)


class ProxyConfigDecoder(json.JSONDecoder):
    def __init__(self, *args, **kwargs):
        super().__init__(object_hook=self.object_hook, *args, **kwargs)

    def object_hook(self, obj):
        if 'proto' in obj and 'host' in obj and 'port' in obj and 'noProxyies' in obj and 'ssids' in obj:
            return ProxyConfig(obj['proto'], obj['host'], obj['port'], obj['noProxyies'], obj['ssids'])
        return obj


class ProxyConfig:
    def __init__(self, proto: str, host: str, port: int, noProxyies: list[str] = [], ssids: list[str] = []) -> None:
        self.proto = proto
        self.host = host
        self.port = port
        self.noProxyies = noProxyies
        self.ssids = ssids

    @property
    def dict(self) -> dict:
        return {'proto': self.proto, 'host': self.host, 'port': self.port, 'noProxyies': self.noProxyies, 'ssids': self.ssids}

    @property
    def url(self) -> str:
        return f'{self.proto}://{self.host}:{self.port}'

    @property
    def noProxyiesString(self) -> str:
        return ';'.join(self.noProxyies)

    def apply(self) -> None:
        key = RegOpenKeyEx(HKEY_CURRENT_USER, PROXY_ENTRY, 0, KEY_ALL_ACCESS)
        RegSetValueEx(key, PROXY_SERVER_ENTRY, 0, 1, self.url)
        RegSetValueEx(key, PROXY_OVERRIDE_ENTRY, 0, 1, self.noProxyiesString)
        RegCloseKey(key)
        _l.info(f'applied proxy config {self} to registry')

    def __str__(self) -> str:
        return f'ProxyConfig(proto={self.proto}, host={self.host}, port={self.port}, noProxyies={self.noProxyies}, ssids={self.ssids})'

    def __repr__(self) -> str:
        return str(self)

    def __eq__(self, o: object) -> bool:
        if not isinstance(o, ProxyConfig): return False
        return self.proto == o.proto and self.host == o.host and self.port == o.port and self.noProxyies == o.noProxyies and self.ssids == o.ssids


def getFromJson(json: dict) -> ProxyConfig:
    ret = ProxyConfig(json['proto'], json['host'], json['port'], json['noProxyies'], json['ssids'])
    _l.debug(f'loaded {ret} from json')
    return ret


def getCurrentProxy() -> ProxyConfig:
    key = RegOpenKeyEx(HKEY_CURRENT_USER, PROXY_ENTRY, 0, KEY_READ)
    proxyServer = RegQueryValueEx(key, PROXY_SERVER_ENTRY)[0]
    proxyOverride = RegQueryValueEx(key, PROXY_OVERRIDE_ENTRY)[0]
    RegCloseKey(key)

    proto, host, port = splitURL(proxyServer)
    noProxyies = proxyOverride.split(';')
    ret = ProxyConfig(proto, host, port, noProxyies)
    _l.debug(f'loaded {ret} from registry')
    return ret


def getEnabled() -> bool:
    key = RegOpenKeyEx(HKEY_CURRENT_USER, PROXY_ENTRY, 0, KEY_READ)
    proxyEnabled = RegQueryValueEx(key, PROXY_ENABLED_ENTRY)[0]
    RegCloseKey(key)
    ret = proxyEnabled == 1
    _l.debug(f'loaded status {ret} from registry')
    return ret


def setEnabled(enabled: bool) -> None:
    key = RegOpenKeyEx(HKEY_CURRENT_USER, PROXY_ENTRY, 0, KEY_WRITE)
    RegSetValueEx(key, PROXY_ENABLED_ENTRY, 0, 4, int(enabled))
    RegCloseKey(key)
    _l.info(f'set proxy status to {enabled}')


def start() -> None:
    global _thread, _key
    _l.info('starting proxy watcher...')
    _key = winreg.OpenKey(HKEY_CURRENT_USER, PROXY_ENTRY, 0, KEY_READ | KEY_NOTIFY)
    _thread = threading.Thread(target=_monitor_registry_changes)
    _thread.daemon = True
    _thread.start()


def stop() -> None:
    global _key
    _l.info('stopping proxy watcher...')
    if _key is not None:
        winreg.CloseKey(_key)
        _key = None
    if _thread:
        _thread.join()


_thread: threading.Thread | None = None
_key: winreg.HKEYType | None = None
enabledCallback: ProxyEnabledWatcherCallbackType = lambda _: None
protoCallback: ProxyProtocolWatcherCallbackType = lambda _: None
hostCallback: ProxyHostWatcherCallbackType = lambda _: None
portCallback: ProxyPortWatcherCallbackType = lambda _: None
noProxyiesCallback: ProxyNoProxyiesWatcherCallbackType = lambda _: None