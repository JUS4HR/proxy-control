import sys
import traceback
import os
import __main__
from tkinter import messagebox

FATAL_LOG = os.path.join(
    os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(__main__.__file__),
    'failures.log',
)

try:
    import App

    if __name__ == '__main__':
        sys.exit(App.APP.exec_())
except Exception as e:
    fatalStr = f'{e}\n{traceback.format_exc()}'
    with open(FATAL_LOG, 'w') as f:
        f.write(fatalStr)
    messagebox.showerror("Error", f"An error occurred: {e}")
