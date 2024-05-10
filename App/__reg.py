import sys
from typing import Union

if sys.platform != "win32":
    raise NotImplementedError("Wrong platform for this module")

import ctypes as _ct
import ctypes.wintypes as _wt
from enum import Enum

_advapi32 = _ct.windll.advapi32

# LSTATUS RegOpenKeyExA(
#     HKEY hKey,
#     LPCSTR lpSubKey,
#     DWORD ulOptions,
#     REGSAM samDesired,
#     PHKEY phkResult
# );
_advapi32.RegOpenKeyExA.argtypes = (
    _wt.HKEY,
    _wt.LPCSTR,
    _wt.DWORD,
    _wt.DWORD,
    _ct.POINTER(_wt.HKEY),
)
_advapi32.RegOpenKeyExA.restype = _wt.LONG

# LSTATUS RegQueryValueExA(
#     HKEY hKey,
#     LPCSTR lpValueName,
#     LPDWORD lpReserved,
#     LPDWORD lpType,
#     LPBYTE lpData,
#     LPDWORD lpcbData
# );
_advapi32.RegQueryValueExA.argtypes = (
    _wt.HKEY,
    _wt.LPCSTR,
    _wt.LPDWORD,
    _wt.LPDWORD,
    _wt.LPBYTE,
    _wt.LPDWORD,
)
_advapi32.RegQueryValueExA.restype = _wt.LONG

# LSTATUS RegNotifyChangeKeyValue(
#     HKEY hKey,
#     WINBOOL bWatchSubtree,
#     DWORD dwNotifyFilter,
#     HANDLE hEvent,
#     WINBOOL fAsynchronous
# );
_advapi32.RegNotifyChangeKeyValue.argtypes = (
    _wt.HKEY,
    _wt.BOOL,
    _wt.DWORD,
    _wt.HANDLE,
    _wt.BOOL,
)
_advapi32.RegNotifyChangeKeyValue.restype = _wt.LONG


# LSTATUS RegSetValueExA(
#     HKEY hKey,
#     LPCSTR lpValueName,
#     DWORD Reserved,
#     DWORD dwType,
#     const BYTE *lpData,
#     DWORD cbData
# );
_advapi32.RegSetValueExA.argtypes = (
    _wt.HKEY,
    _wt.LPCSTR,
    _wt.DWORD,
    _wt.DWORD,
    _wt.LPBYTE,
    _wt.DWORD,
)
_advapi32.RegSetValueExA.restype = _wt.LONG

# LSTATUS RegDeleteValueA(
#     HKEY hKey,
#     LPCSTR lpValueName
# );
_advapi32.RegDeleteValueA.argtypes = (
    _wt.HKEY,
    _wt.LPCSTR,
)
_advapi32.RegDeleteValueA.restype = _wt.LONG


class RegKeyRoot(Enum):
    HKEY_CLASSES_ROOT = 0x80000000
    HKEY_CURRENT_USER = 0x80000001
    HKEY_LOCAL_MACHINE = 0x80000002
    HKEY_USERS = 0x80000003
    HKEY_PERFORMANCE_DATA = 0x80000004
    HKEY_PERFORMANCE_TEXT = 0x80000050
    HKEY_PERFORMANCE_NLSTEXT = 0x80000060
    HKEY_CURRENT_CONFIG = 0x80000005
    HKEY_DYN_DATA = 0x80000006
    HKEY_CURRENT_USER_LOCAL_SETTINGS = 0x80000007


class _RegKeyAccessGenerated:
    def __init__(self: "_RegKeyAccessGenerated", value: int):
        self._value = value

    @property
    def value(self: "_RegKeyAccessGenerated") -> int:
        return self._value

    def __or__(
        self, other: Union["RegKeyAccess", "_RegKeyAccessGenerated"]
    ) -> "_RegKeyAccessGenerated":
        return _RegKeyAccessGenerated(self.value | other.value)

    def __repr__(self: "_RegKeyAccessGenerated") -> str:
        return f"{self.__class__.__name__}({self.value})"


class RegKeyAccess(Enum):
    KEY_QUERY_VALUE = 0x0001
    KEY_SET_VALUE = 0x0002
    KEY_CREATE_SUB_KEY = 0x0004
    KEY_ENUMERATE_SUB_KEYS = 0x0008
    KEY_NOTIFY = 0x0010
    KEY_CREATE_LINK = 0x0020
    KEY_WOW64_32KEY = 0x0200
    KEY_WOW64_64KEY = 0x0100
    KEY_WOW64_RES = 0x0300
    KEY_READ = 0x20019
    KEY_WRITE = 0x20006
    KEY_EXECUTE = 0x20019
    KEY_ALL_ACCESS = 0xF003F

    def __or__(
        self, other: Union["RegKeyAccess", _RegKeyAccessGenerated]
    ) -> _RegKeyAccessGenerated:
        return _RegKeyAccessGenerated(self.value | other.value)


class RegValueType(Enum):
    REG_NONE = 0
    REG_SZ = 1
    REG_EXPAND_SZ = 2
    REG_BINARY = 3
    REG_DWORD = 4
    REG_DWORD_BIG_ENDIAN = 5
    REG_LINK = 6
    REG_MULTI_SZ = 7
    REG_RESOURCE_LIST = 8
    REG_FULL_RESOURCE_DESCRIPTOR = 9
    REG_RESOURCE_REQUIREMENTS_LIST = 10
    REG_QWORD = 11


class RegKey:
    def __init__(
        self: "RegKey",
        key: _wt.HKEY,
        path: str,
        access: RegKeyAccess | _RegKeyAccessGenerated,
    ):
        self.key = key
        self.path: bytes = path.encode("ascii")
        self.access: int = access.value
        self._handle: _wt.HKEY | None = None

    def open(self: "RegKey") -> None:
        self._handle = _wt.HKEY()
        _advapi32.RegOpenKeyExA(
            self.key,
            _wt.LPCSTR(self.path),
            _wt.DWORD(),
            _wt.DWORD(self.access),
            _ct.byref(self._handle),
        )

    def queryValue(
        self: "RegKey", value: str
    ) -> tuple[RegValueType, str | int | bytes | None]:
        type = _wt.DWORD()
        size = _wt.DWORD()
        _advapi32.RegQueryValueExA(
            self._handle,
            _wt.LPCSTR(value.encode("ascii")),
            _wt.LPDWORD(),
            _ct.byref(type),
            _wt.LPBYTE(),
            _ct.byref(size),
        )
        data = _ct.create_string_buffer(size.value)
        _advapi32.RegQueryValueExA(
            self._handle,
            _wt.LPCSTR(value.encode("ascii")),
            _wt.LPDWORD(),
            _ct.byref(type),
            _ct.cast(data, _wt.LPBYTE),
            _ct.byref(size),
        )
        if type.value == 1:
            return RegValueType(type.value), data.value.decode("ascii")
        elif type.value == 4:
            return RegValueType(type.value), int.from_bytes(
                data.raw, byteorder="little"
            )
        elif type.value == 3:
            return RegValueType(type.value), data.raw
        elif type.value == 0:
            return RegValueType(type.value), None
        else:
            raise ValueError("Invalid value type")

    def notifyChange(self: "RegKey", event: _wt.HANDLE | None = None) -> None:
        _advapi32.RegNotifyChangeKeyValue(
            self._handle,
            _wt.BOOL(True),
            _wt.DWORD(0x00000004),  # REG_NOTIFY_CHANGE_LAST_SET
            event or _wt.HANDLE(None),
            _wt.BOOL(False),
        )

    def setValue(
        self: "RegKey", value: str, data: int | str | bytes, valueType: RegValueType
    ) -> None:
        if valueType == RegValueType.REG_DWORD:
            if not isinstance(data, int):
                raise ValueError(f"Given data is not an integer: {type(data).__name__}")
            bData = data.to_bytes(_ct.sizeof(_wt.DWORD), byteorder="little")
            dataSize = _wt.DWORD(_ct.sizeof(_wt.DWORD))
        elif valueType == RegValueType.REG_SZ:
            if not isinstance(data, str):
                raise ValueError(f"Given data is not a string: {type(data).__name__}")
            bData = data.encode("ascii")
            dataSize = _wt.DWORD(len(bData))
        elif valueType == RegValueType.REG_BINARY:
            if not isinstance(data, bytes):
                raise ValueError(f"Given data is not bytes: {type(data).__name__}")
            bData = data
            dataSize = _wt.DWORD(len(bData))
        else:
            raise ValueError(f"Unsupported value type: {valueType.name}")

        _advapi32.RegSetValueExA(
            self._handle,
            _wt.LPCSTR(value.encode("ascii")),
            _wt.DWORD(),
            _wt.DWORD(valueType.value),
            _ct.cast(_wt.LPCSTR(bData), _wt.LPBYTE),
            dataSize,
        )

    def deleteValue(self: "RegKey", value: str) -> None:
        _advapi32.RegDeleteValueA(
            self._handle,
            _wt.LPCSTR(value.encode("ascii")),
        )

    def close(self: "RegKey") -> None:
        if self._handle is not None:
            _advapi32.RegCloseKey(self._handle)
            self._handle = None

    def __del__(self: "RegKey") -> None:
        self.close()

    def __enter__(self: "RegKey") -> "RegKey":
        self.open()
        return self

    def __exit__(self: "RegKey", exc_type, exc_value, traceback) -> None:
        self.close()


def getHKey(root: RegKeyRoot) -> _wt.HKEY:
    return _wt.HKEY(root.value)
