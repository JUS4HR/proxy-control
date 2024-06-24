from windows_toasts import Toast, ToastDuration, WindowsToaster

from . import __utils as _u


def toast(message: str, long: bool = False):
    _text.text_fields = [message]
    _text.duration =(ToastDuration.Long if long else ToastDuration.Short)
    _toaster.show_toast(_text)


_toaster = WindowsToaster(_u.APP_NAME)
_text = Toast()
