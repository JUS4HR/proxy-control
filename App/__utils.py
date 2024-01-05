import sys

if sys.platform != "win32":
    raise NotImplementedError("Wrong platform for this module")
import locale
import os
import subprocess
import sys

import __main__

from . import __reg as reg

STARTUP_REG_ENTRY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "Proxy Control"
IS_FROZEN = getattr(sys, "frozen", False)
MAIN_PATH = os.path.dirname(os.path.abspath(__main__.__file__))
SUBPROCESS_SILENT_INFO = subprocess.STARTUPINFO(
    dwFlags=subprocess.STARTF_USESHOWWINDOW, wShowWindow=subprocess.SW_HIDE
)

if IS_FROZEN:
    # running as a bundled executable
    START_COMMAND = os.path.abspath(sys.executable)
else:
    # running as a Python script
    if "CONDA_DEFAULT_ENV" in os.environ:
        START_COMMAND = f"conda activate {os.environ['CONDA_DEFAULT_ENV']} && python {os.path.abspath(__main__.__file__)}"
    else:
        START_COMMAND = f"python {os.path.abspath(__main__.__file__)}"
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
        output = bytes.decode(locale.getdefaultlocale()[1] or "utf-8")
        lines = output.split("\n")
        for line in lines:
            if line.strip().startswith("SSID"):
                return line.split(":")[1].strip()
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
    elif platform.system() == "Linux":
        home = os.path.expanduser("~")
        autostart_dir = os.path.join(home, ".config", "autostart")
        if not os.path.exists(autostart_dir):
            os.makedirs(autostart_dir)
        with open(os.path.join(autostart_dir, "myapp.desktop"), "w") as f:
            f.write("[Desktop Entry]\n")
            f.write("Type=Application\n")
            f.write("Exec={}\n".format(START_COMMAND))
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
    elif sys.platform == "linux":
        home = os.path.expanduser("~")
        autostart_dir = os.path.join(home, ".config", "autostart")
        if os.path.exists(os.path.join(autostart_dir, "myapp.desktop")):
            os.remove(os.path.join(autostart_dir, "myapp.desktop"))
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
    elif sys.platform == "linux":
        home = os.path.expanduser("~")
        autostart_dir = os.path.join(home, ".config", "autostart")
        if os.path.exists(os.path.join(autostart_dir, "myapp.desktop")):
            return True
        else:
            return False
    else:
        raise NotImplementedError("Unsupported platform")


def getBundledFilePath(relPath) -> str:
    if IS_FROZEN:
        bundle_dir = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    else:
        bundle_dir = MAIN_PATH
    return os.path.join(bundle_dir, relPath)


def getExeRelPath(relPath) -> str:
    if IS_FROZEN:
        return os.path.join(os.path.dirname(sys.executable), relPath)
    else:
        return os.path.join(MAIN_PATH, relPath)
