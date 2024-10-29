Taskbar Proxy Control
===

usage
---

Build with pyinstaller. Windows only, Python 3.11 (3.12 is not supported by pyqtdarktheme)

```powershell
python -m venv venv
. .\venv\Scripts\Activate.ps1
pip install -r requirements.txt
pyinstaller ProxyControl.spec
```

Run the executable in the dist folder

If could not start, check `failures.log` in the same folder

