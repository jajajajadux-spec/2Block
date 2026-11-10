"""Treat a deep link as untrusted input, even when the portal created it."""

import json
import re
from dataclasses import dataclass
from urllib.parse import parse_qs, urlsplit

SERVER = "http://127.0.0.1:8765"
GAME_ID = re.compile(r"[a-z0-9-]{1,40}\Z")
COLOR = re.compile(r"#[0-9a-fA-F]{6}\Z")
LAUNCH_ID = re.compile(r"[A-Za-z0-9_-]{32}\Z")
DEFAULT_AVATAR = {"body": "#58c9a5", "head": "#f2c78f", "hat": "none"}


def username(value):
    if not isinstance(value, str):
        raise ValueError("Player name must be text")
    value = value.strip()
    if not 1 <= len(value) <= 24 or not all(c.isprintable() for c in value):
        raise ValueError("Use a name with 1–24 printable characters")
    return value


def avatar(value):
    if not isinstance(value, dict) or set(value) != {"body", "head", "hat"}:
        raise ValueError("Avatar needs body, head and hat")
    if any(not isinstance(value[k], str) or not COLOR.fullmatch(value[k])
           for k in ("body", "head")):
        raise ValueError("Avatar colors must use #RRGGBB")
    if value["hat"] not in ("none", "cap", "tall"):
        raise ValueError("Unknown hat")
    return dict(value)


def game_id(value):
    if not isinstance(value, str) or not GAME_ID.fullmatch(value):
        raise ValueError("Invalid game ID")
    return value


@dataclass(frozen=True)
class JoinRequest:
    game: str
    user: str
    avatar: dict
    server: str = SERVER
    launch_id: str | None = None

    def payload(self):
        return {"gameId": self.game, "user": self.user, "avatar": self.avatar,
                "launchId": self.launch_id}


def parse_link(uri):
    if not isinstance(uri, str) or len(uri) > 4096:
        raise ValueError("Deep link is too long")
    if any(ord(c) < 32 or ord(c) == 127 for c in uri):
        raise ValueError("Control characters are not allowed")
    parsed = urlsplit(uri)
    if (parsed.scheme != "twoblock" or parsed.netloc != "join"
            or parsed.path not in ("", "/") or parsed.fragment):
        raise ValueError("Expected twoblock://join")
    query = parse_qs(parsed.query, keep_blank_values=True, strict_parsing=True,
                     max_num_fields=6)
    required = {"gameId", "user", "avatar", "server"}
    if not required <= query.keys() or query.keys() - required - {"launchId"}:
        raise ValueError("Missing or unknown join parameters")
    if any(len(values) != 1 for values in query.values()):
        raise ValueError("Duplicate join parameters")
    fields = {key: values[0] for key, values in query.items()}
    # The development client must never become a generic HTTP request proxy.
    if fields["server"] != SERVER:
        raise ValueError(f"This development client only trusts {SERVER}")
    launch = fields.get("launchId")
    if launch is not None and not LAUNCH_ID.fullmatch(launch):
        raise ValueError("Invalid launch ID")
    return JoinRequest(game_id(fields["gameId"]), username(fields["user"]),
                       avatar(json.loads(fields["avatar"])), SERVER, launch)

