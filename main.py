import sys
import traceback

import __main__

try:
    import App

    if __name__ == "__main__":
        sys.exit(App.APP.exec_())
except Exception as e:
    from pathlib import Path

    fatalStr = f"{e}\n{traceback.format_exc()}"
    with (
        (
            Path(sys.executable).parent
            if getattr(sys, "frozen", False)
            else Path(__main__.__file__).parent
        )
        / "failures.log"
    ).open("w", encoding="utf-8") as f:
        f.write(fatalStr)
