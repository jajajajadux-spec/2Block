"""The Windows bundle installs itself to a stable per-user path."""

import os
from pathlib import Path
import shutil
import sys

from .register import register


def install():
    if sys.platform != "win32" or not getattr(sys, "frozen", False):
        raise RuntimeError("--install requires the packaged Windows executable. For source installs, use --register.")
    target = Path(os.environ["LOCALAPPDATA"]) / "2Block" / "2Block.exe"
    target.parent.mkdir(parents=True, exist_ok=True)
    source = Path(sys.executable).resolve()
    if source != target.resolve():
        # Stage first so an interrupted copy does not destroy an existing installation.
        staged = target.with_suffix(".exe.new")
        shutil.copy2(source, staged)
        os.replace(staged, target)
    register(command=[str(target)])
    import tkinter as tk
    from tkinter import messagebox
    root = tk.Tk()
    root.withdraw()
    messagebox.showinfo("2Block installed", "2Block is ready. Return to the portal and click Play Now.", parent=root)
    root.destroy()

