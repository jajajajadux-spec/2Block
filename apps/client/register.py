"""Per-user registration; no administrator rights and no shell interpolation."""

import os
from pathlib import Path
import shutil
import subprocess
import sys


def launch_command():
    if getattr(sys, "frozen", False):
        return [sys.executable]
    executable = Path(sys.executable)
    if sys.platform == "win32" and executable.with_name("pythonw.exe").exists():
        executable = executable.with_name("pythonw.exe")
    return [str(executable), str(Path(__file__).parents[2] / "scripts" / "client.py")]


def register(remove=False, command=None):
    command_args = command or launch_command()
    if sys.platform == "win32":
        import winreg
        key_path = r"Software\Classes\twoblock"
        if remove:
            # Delete only the three keys owned by this registration.
            for suffix in (r"\shell\open\command", r"\shell\open", r"\shell", ""):
                try:
                    winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key_path + suffix)
                except FileNotFoundError:
                    pass
        else:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, "URL:2Block Protocol")
                winreg.SetValueEx(key, "URL Protocol", 0, winreg.REG_SZ, "")
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path + r"\shell\open\command") as key:
                handler = subprocess.list2cmdline(command_args) + ' "%1"'
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, handler)
    elif sys.platform.startswith("linux"):
        desktop = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "applications" / "twoblock.desktop"
        if remove:
            desktop.unlink(missing_ok=True)
        else:
            if not shutil.which("xdg-mime"):
                raise RuntimeError("Install xdg-utils before registering the protocol")
            desktop.parent.mkdir(parents=True, exist_ok=True)
            # Desktop Exec syntax differs from POSIX shell syntax.
            def quote(value):
                value = value.replace("%", "%%").replace("\\", "\\\\")
                for char in ('"', '`', '$'):
                    value = value.replace(char, "\\" + char)
                return '"' + value + '"'
            command = " ".join(quote(arg) for arg in command_args)
            desktop.write_text("[Desktop Entry]\nType=Application\nName=2Block\n"
                               f"Exec={command} %u\nTerminal=false\n"
                               "MimeType=x-scheme-handler/twoblock;\n", encoding="utf-8")
            subprocess.run(["xdg-mime", "default", desktop.name,
                            "x-scheme-handler/twoblock"], check=True)
    else:
        raise RuntimeError("Protocol registration is implemented for Windows and Linux. "
                           "On macOS, use the direct command; see docs/INSTALL.md.")
    print("2Block protocol " + ("removed." if remove else "registered for the current user."))

