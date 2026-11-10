"""Entry point used by both the shell protocol handler and the terminal."""

import argparse
import sys

from packages.common.protocol import parse_link
from .transport import Connection


def main():
    parser = argparse.ArgumentParser(description="2Block desktop client")
    parser.add_argument("uri", nargs="?", help="twoblock://join?... link")
    parser.add_argument("--register", action="store_true", help="Register for this user")
    parser.add_argument("--unregister", action="store_true")
    parser.add_argument("--install", action="store_true", help="Install a packaged Windows client for this user")
    parser.add_argument("--headless", action="store_true", help="Validate and join without a window")
    args = parser.parse_args()
    management = sum((args.register, args.unregister, args.install))
    if management > 1 or (args.uri and management):
        parser.error("Protocol links cannot be combined with installation commands")
    try:
        if args.install or (getattr(sys, "frozen", False) and not any((args.uri, args.register, args.unregister))):
            from .installer import install
            install()
            return 0
        if args.register or args.unregister:
            from .register import register
            register(remove=args.unregister)
            return 0
        if not args.uri:
            parser.error("Pass a join URI, or use --register")
        join = parse_link(args.uri)
        connection = Connection(join.server)
        if args.headless:
            session = connection.post("/api/join", join.payload())
            connection.token = session["token"]
            print(f"Joined {join.game} as {join.user} ({session['playerId']})")
            connection.post("/api/leave", {})
        else:
            from .window import run
            run(connection, join)
        return 0
    except Exception as error:
        # pythonw has no terminal, so report startup failures in a dialog too.
        if sys.stderr is not None:
            print(f"2Block: {error}", file=sys.stderr)
        if not args.headless:
            try:
                import tkinter as tk
                from tkinter import messagebox
                root = tk.Tk()
                root.withdraw()
                messagebox.showerror("2Block could not start", str(error), parent=root)
                root.destroy()
            except Exception:
                pass
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

