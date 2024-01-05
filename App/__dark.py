import os
import sys
import threading
from . import __reg as reg
from typing import Callable

import __main__

from . import __log as _l
from . import __utils as _u

THEME_ENTRY = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
WINDOW_THEME_ENTRY = "AppsUseLightTheme"
TASKBAR_THEME_ENTRY = "SystemUsesLightTheme"

ICON_PATH = os.path.join("App", "assets")
ICON_NAME_LIGHT = "l"
ICON_NAME_DARK = "d"
ICON_NAME_INTACT = "i"
ICON_NAME_BROKEN = "b"
ICON_EXT = ".ico"

FROZEN = getattr(sys, "frozen", False)

ThemeWatcherCallbackType = Callable[[bool], None]


def _monitor_registry_changes() -> None:
    _l.info(f"started theme watcher")
    if _key is None:
        return
    lastWindow: bool = _key.queryValue(WINDOW_THEME_ENTRY)[1] == 1
    lastTaskbar: bool = _key.queryValue(TASKBAR_THEME_ENTRY)[1] == 1
    while True:
        if _key is None:
            return
        _key.notifyChange()
        if _key is None:
            return
        _l.debug(f"theme registry changed")
        window: bool = _key.queryValue(WINDOW_THEME_ENTRY)[1] == 1
        taskbar: bool = _key.queryValue(TASKBAR_THEME_ENTRY)[1] == 1
        if window != lastWindow:
            lastWindow = window
            _l.debug(f"window theme changed to {window}")
            threading.Thread(target=windowCallback, args=(window,)).start()
        if taskbar != lastTaskbar:
            lastTaskbar = taskbar
            _l.debug(f"taskbar theme changed to {taskbar}")
            threading.Thread(target=taskbarCallback, args=(taskbar,)).start()


def isTBLight() -> bool:
    with reg.RegKey(
        reg.getHKey(reg.RegKeyRoot.HKEY_CURRENT_USER),
        THEME_ENTRY,
        reg.RegKeyAccess.KEY_READ,
    ) as key:
        return key.queryValue(TASKBAR_THEME_ENTRY)[1] == 1


def isWindowLight() -> bool:
    with reg.RegKey(
        reg.getHKey(reg.RegKeyRoot.HKEY_CURRENT_USER),
        THEME_ENTRY,
        reg.RegKeyAccess.KEY_READ,
    ) as key:
        return key.queryValue(WINDOW_THEME_ENTRY)[1] == 1


def getTBIconPath(intact: bool, light: bool | None = None) -> str:
    path = _u.getBundledFilePath(
        os.path.join(
            ICON_PATH,
            f"{ICON_NAME_LIGHT if (light if light is not None else isTBLight()) else ICON_NAME_DARK}{ICON_NAME_INTACT if intact else ICON_NAME_BROKEN}{ICON_EXT}",
        )
    )
    _l.debug(f"using taskbar icon: {path}")
    return path


def start() -> None:
    global _thread, _key
    _l.info("starting theme watcher...")
    _key = reg.RegKey(
        reg.getHKey(reg.RegKeyRoot.HKEY_CURRENT_USER),
        THEME_ENTRY,
        reg.RegKeyAccess.KEY_NOTIFY | reg.RegKeyAccess.KEY_READ,
    )
    _key.open()
    _thread = threading.Thread(target=_monitor_registry_changes)
    _thread.daemon = True
    _thread.start()


def stop() -> None:
    global _key
    _l.info("stopping theme watcher...")
    if _key is not None:
        _key.close()
        _key = None
    if _thread:
        _thread.join()
    _l.info("stopped theme watcher.")


_key: reg.RegKey | None = None
_thread: threading.Thread | None = None
windowCallback: ThemeWatcherCallbackType = lambda _: None
taskbarCallback: ThemeWatcherCallbackType = lambda _: None
