import os
import sys
import threading
import winreg
from typing import Callable

import __main__
import win32api

from . import __log as _l
from . import __utils as _u

THEME_ENTRY = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
WINDOW_THEME_ENTRY = "AppsUseLightTheme"
TASKBAR_THEME_ENTRY = "SystemUsesLightTheme"

ICON_PATH = os.path.join('App', 'assets')
ICON_NAME_LIGHT = 'l'
ICON_NAME_DARK = 'd'
ICON_NAME_INTACT = 'i'
ICON_NAME_BROKEN = 'b'
ICON_EXT = '.ico'

FROZEN = getattr(sys, 'frozen', False)

ThemeWatcherCallbackType = Callable[[bool], None]


def _monitor_registry_changes() -> None:
    _l.info(f'started theme watcher')
    if _key is None: return
    lastWindow: bool = winreg.QueryValueEx(_key, WINDOW_THEME_ENTRY)[0] == 1
    lastTaskbar: bool = winreg.QueryValueEx(_key, TASKBAR_THEME_ENTRY)[0] == 1
    while True:
        if _key is None: return
        win32api.RegNotifyChangeKeyValue(_key, False, winreg.REG_NOTIFY_CHANGE_LAST_SET, None, False)
        if _key is None: return
        _l.debug(f'theme registry changed')
        window: bool = winreg.QueryValueEx(_key, WINDOW_THEME_ENTRY)[0] == 1
        taskbar: bool = winreg.QueryValueEx(_key, TASKBAR_THEME_ENTRY)[0] == 1
        if window != lastWindow:
            lastWindow = window
            _l.debug(f'window theme changed to {window}')
            threading.Thread(target=windowCallback, args=(window, )).start()
        if taskbar != lastTaskbar:
            lastTaskbar = taskbar
            _l.debug(f'taskbar theme changed to {taskbar}')
            threading.Thread(target=taskbarCallback, args=(taskbar, )).start()


def isTBLight() -> bool:
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, THEME_ENTRY, 0, winreg.KEY_READ)
    light = winreg.QueryValueEx(key, TASKBAR_THEME_ENTRY)[0]
    winreg.CloseKey(key)
    return light == 1


def isWindowLight() -> bool:
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, THEME_ENTRY, 0, winreg.KEY_READ)
    light = winreg.QueryValueEx(key, WINDOW_THEME_ENTRY)[0]
    winreg.CloseKey(key)
    return light == 1


def getTBIconPath(intact: bool, light: bool | None = None) -> str:
    path = _u.getBundledFilePath(
        os.path.join(
            ICON_PATH,
            f'{ICON_NAME_LIGHT if (light if light is not None else isTBLight()) else ICON_NAME_DARK}{ICON_NAME_INTACT if intact else ICON_NAME_BROKEN}{ICON_EXT}'
        ))
    _l.debug(f'using taskbar icon: {path}')
    return path


def start() -> None:
    global _thread, _key
    _l.info('starting theme watcher...')
    _key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, THEME_ENTRY, 0, winreg.KEY_NOTIFY | winreg.KEY_READ)
    _thread = threading.Thread(target=_monitor_registry_changes)
    _thread.daemon = True
    _thread.start()


def stop() -> None:
    global _key
    _l.info('stopping theme watcher...')
    if _key is not None:
        winreg.CloseKey(_key)
        _key = None
    if _thread:
        _thread.join()
    _l.info('stopped theme watcher.')


_key: winreg.HKEYType | None = None
_thread: threading.Thread | None = None
windowCallback: ThemeWatcherCallbackType = lambda _: None
taskbarCallback: ThemeWatcherCallbackType = lambda _: None