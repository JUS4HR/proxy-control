from windows_toasts import ToastDuration, ToastText1, WindowsToaster

from . import __utils as _u


def toast(message: str, long: bool = False):
    _text.SetBody(message)
    _text.SetDuration(ToastDuration.Long if long else ToastDuration.Short)
    _toaster.show_toast(_text)


_toaster = WindowsToaster(_u.APP_NAME)
_text = ToastText1()
