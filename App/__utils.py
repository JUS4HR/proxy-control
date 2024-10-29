import sys

if sys.platform != "win32":
    raise NotImplementedError("Wrong platform for this module")
import re
import locale
import os
import subprocess
from pathlib import Path
import chardet

import __main__

from . import __reg as reg

STARTUP_REG_ENTRY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "Proxy Control"
IS_FROZEN = getattr(sys, "frozen", False)
MAIN_PATH = Path(__main__.__file__).parent
SUBPROCESS_SILENT_INFO = subprocess.STARTUPINFO(
    dwFlags=subprocess.STARTF_USESHOWWINDOW, wShowWindow=subprocess.SW_HIDE
)
MAC_ADDR_PATTERN = re.compile(r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$")

if IS_FROZEN:
    # running as a bundled executable
    START_COMMAND = Path(sys.executable).resolve().__str__()
else:
    # running as a Python script
    if "CONDA_DEFAULT_ENV" in os.environ:
        START_COMMAND = f"conda activate {os.environ['CONDA_DEFAULT_ENV']} && python {Path(__main__.__file__).resolve().as_posix()}"
    else:
        START_COMMAND = f"python {Path(__main__.__file__).resolve().as_posix()}"
    if sys.platform == "win32":
        START_COMMAND = f'powershell -Command "{START_COMMAND}"'


def isConnected() -> bool:
    import socket

    try:
        socket.create_connection(("8.8.8.8", 53), timeout=1).close()
        return True
    except OSError:
        pass
    return False


def getSSID() -> str | None:
    try:
        bytes = subprocess.check_output(
            ["netsh", "wlan", "show", "interfaces"], startupinfo=SUBPROCESS_SILENT_INFO
        )
        detected_encoding = chardet.detect(bytes)['encoding']
        encoding = detected_encoding or locale.getdefaultlocale()[1] or "utf-8"
        output = bytes.decode(encoding)
        lines = output.split("\n")
        for line in lines:
            if line.strip().startswith("SSID"):
                return line.split(":")[1].strip()
    except subprocess.CalledProcessError:
        pass
    return None


def getMacAddr(ip: str) -> str | None:
    try:
        bytes = subprocess.check_output(
            ["arp", "-a", ip], startupinfo=SUBPROCESS_SILENT_INFO
        )
        output = bytes.decode(locale.getdefaultlocale()[1] or "utf-8")
        lines = output.split("\n")
        if len(lines) > 3:
            return macAddrValidate(lines[3].split()[1])
    except subprocess.CalledProcessError:
        pass
    return None


def enable_startup():
    if sys.platform == "win32":
        with reg.RegKey(
            reg.getHKey(reg.RegKeyRoot.HKEY_CURRENT_USER),
            STARTUP_REG_ENTRY,
            reg.RegKeyAccess.KEY_WRITE,
        ) as key:
            key.setValue(APP_NAME, START_COMMAND, reg.RegValueType.REG_SZ)
    elif platform.system() == "Linux":  # UNTESTED
        autostart_dir = Path.home() / ".config" / "autostart"
        autostart_dir.mkdir(parents=True, exist_ok=True)
        desktop_file = autostart_dir / "myapp.desktop"
        with desktop_file.open("w", encoding="utf-8") as f:
            f.write("[Desktop Entry]\n")
            f.write("Type=Application\n")
            f.write(f"Exec={START_COMMAND}\n")
            f.write("Hidden=false\n")
            f.write("NoDisplay=false\n")
            f.write("X-GNOME-Autostart-enabled=true\n")
            f.write("Name[en_US]=MyApp\n")
            f.write("Name=MyApp\n")
    else:
        raise NotImplementedError("Unsupported platform")


def disable_startup():
    if sys.platform == "win32":
        with reg.RegKey(
            reg.getHKey(reg.RegKeyRoot.HKEY_CURRENT_USER),
            STARTUP_REG_ENTRY,
            reg.RegKeyAccess.KEY_WRITE,
        ) as key:
            try:
                key.deleteValue(APP_NAME)
            except WindowsError:
                pass
    elif sys.platform == "linux":  # UNTESTED
        autostart_dir = Path.home() / ".config" / "autostart"
        desktop_file = autostart_dir / "myapp.desktop"
        if desktop_file.exists():
            desktop_file.unlink()
    else:
        raise NotImplementedError("Unsupported platform")


def check_startup() -> bool:
    if sys.platform == "win32":
        with reg.RegKey(
            reg.getHKey(reg.RegKeyRoot.HKEY_CURRENT_USER),
            STARTUP_REG_ENTRY,
            reg.RegKeyAccess.KEY_READ,
        ) as key:
            try:
                value = key.queryValue(APP_NAME)[1]
                return value == START_COMMAND
            except WindowsError:
                return False
    elif sys.platform == "linux":  # UNTESTED
        if (Path.home() / ".config" / "autostart" / "myapp.desktop").exists():
            return True
        else:
            return False
    else:
        raise NotImplementedError("Unsupported platform")


def getBundledFilePath(relPath: str | os.PathLike) -> Path:
    if IS_FROZEN:
        bundle_dir = getattr(sys, "_MEIPASS", Path(sys.executable).parent)
    else:
        bundle_dir = MAIN_PATH
    return Path(bundle_dir) / relPath


def getExeRelPath(relPath: str | os.PathLike) -> Path:
    return Path(sys.executable).parent / relPath if IS_FROZEN else MAIN_PATH / relPath


def getGateway() -> str | None:
    if sys.platform == "win32":
        bytes = subprocess.check_output(
            ["route", "print"], startupinfo=SUBPROCESS_SILENT_INFO
        )
        output = bytes.decode(locale.getdefaultlocale()[1] or "utf-8")
        lines = output.split("\n")
        for line in lines:
            if " 0.0.0.0 " in line:
                return line.split()[2]
    elif sys.platform == "linux":  # UNTESTED
        bytes = subprocess.check_output(["ip", "route"])
        output = bytes.decode(locale.getdefaultlocale()[1] or "utf-8")
        lines = output.split("\n")
        for line in lines:
            if "default" in line:
                return line.split()[2]
    else:
        raise NotImplementedError("Unsupported platform")
    return None


def getGwMac() -> str | None:
    return getMacAddr(gwip) if (gwip := getGateway()) else None


def macAddrValidate(m: str | None) -> str | None:
    if m is not None and MAC_ADDR_PATTERN.match(m := m.strip()):
        return m.lower().replace("-", ":")
    return None
