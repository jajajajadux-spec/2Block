"""In-memory rooms. Every mutation happens under Store.lock."""

import math
import secrets
import threading
import time

from packages.common.protocol import COLOR, LAUNCH_ID, avatar, game_id, username

GAMES = [
    {"id": "block-yard", "title": "Block Yard", "tag": "Build & hang out",
     "description": "Build with friends, collect coins, and make the yard your own.", "color": "#58c9a5"},
    {"id": "sunset-steps", "title": "Sunset Steps", "tag": "Obstacle course",
     "description": "Jump the steps, dodge lava, and reach the golden checkpoint.", "color": "#ed9b63"},
]


def blocks_for(game):
    color = "#69a99b" if game == "block-yard" else "#d59265"
    blocks = []
    for x, z, height in [(-4, -4, 2), (4, -4, 3), (-4, 4, 1), (4, 4, 2)]:
        for y in range(height):
            blocks.append({"x": x, "y": y, "z": z, "color": color})
    for x, y, z in [(-8, 0, -4), (-8, 1, -6), (-6, 2, -8), (-4, 3, -8)]:
        blocks.append({"x": x, "y": y, "z": z, "color": "#e0ae62"})
    return blocks


COINS = [{"id": str(i), "x": x, "y": y, "z": z}
         for i, (x, y, z) in enumerate([(3, .8, 0), (6, .8, 3), (-5, .8, 1),
                                        (-8, 1.8, -4), (-8, 2.8, -6),
                                        (-6, 3.8, -8), (-4, 4.8, -8)])]
CHECKPOINTS = [{"id": "spawn", "x": 0, "y": 0, "z": 0},
               {"id": "steps", "x": -4, "y": 4, "z": -8}]
HAZARDS = [{"x": 8, "z": -5, "width": 4, "depth": 4}]


class Store:
    def __init__(self, clock=time.monotonic):
        self.lock = threading.RLock()
        self.clock = clock
        self.launches = {}
        self.sessions = {}
        self.rooms = {game["id"]: blocks_for(game["id"]) for game in GAMES}

    def prune(self):
        now = self.clock()
        self.launches = {k: v for k, v in self.launches.items() if v["expires"] > now}
        self.sessions = {k: v for k, v in self.sessions.items() if now - v["seen"] < 15}

    def require_game(self, value):
        game = game_id(value)
        if game not in {item["id"] for item in GAMES}:
            raise ValueError("Unknown game")
        return game

    def create_launch(self, data):
        self.prune()
        game = self.require_game(data.get("gameId"))
        if len(self.launches) >= 256:
            raise ValueError("Too many pending launches; try again shortly")
        launch = secrets.token_urlsafe(24)
        self.launches[launch] = {"gameId": game, "status": "pending",
                                 "expires": self.clock() + 120}
        return {"launchId": launch, "expiresIn": 120}

    def launch_status(self, launch):
        self.prune()
        if not LAUNCH_ID.fullmatch(launch) or launch not in self.launches:
            raise ValueError("Launch expired; click Play Now again")
        return {"status": self.launches[launch]["status"]}

    def join(self, data):
        self.prune()
        game = self.require_game(data.get("gameId"))
        name = username(data.get("user"))
        look = avatar(data.get("avatar"))
        launch = data.get("launchId")
        pending = None
        if launch is not None:
            if not isinstance(launch, str):
                raise ValueError("Invalid launch ID")
            self.launch_status(launch)
            pending = self.launches[launch]
            if pending["gameId"] != game or pending["status"] != "pending":
                raise ValueError("Launch was already used or belongs to another game")
        if sum(s["gameId"] == game for s in self.sessions.values()) >= 16:
            raise ValueError("This room is full (16 players)")
        token = secrets.token_urlsafe(32)
        player = {"id": secrets.token_hex(8), "user": name, "avatar": look,
                  "x": 0.0, "y": 0.0, "z": 0.0, "yaw": 0, "grounded": True,
                  "health": 100, "coins": 0, "collected": [], "checkpoint": "spawn"}
        self.sessions[token] = {"gameId": game, "player": player, "seen": self.clock(),
                                "vy": 0.0, "lastEdit": -100.0, "waveUntil": 0.0}
        if pending is not None:
            pending["status"] = "joined"
        return {"token": token, "playerId": player["id"],
                "world": self.snapshot(game)}

    def session(self, token):
        self.prune()
        if token not in self.sessions:
            raise PermissionError("Session expired; launch the game again")
        return self.sessions[token]

    def snapshot(self, game):
        return {"gameId": game, "blocks": [dict(b) for b in self.rooms[game]],
                "coins": COINS, "checkpoints": CHECKPOINTS, "hazards": HAZARDS,
                "players": [{**s["player"], "collected": list(s["player"]["collected"]),
                             "waving": s["waveUntil"] > self.clock()}
                            for s in self.sessions.values() if s["gameId"] == game]}

    def collides(self, game, x, y, z):
        return any(abs(x - b["x"]) < .79 and abs(z - b["z"]) < .79
                   and y < b["y"] + 1 - .001 and y + 1.75 > b["y"] + .001
                   for b in self.rooms[game])

    def respawn(self, session):
        player = session["player"]
        point = next(c for c in CHECKPOINTS if c["id"] == player["checkpoint"])
        player.update(x=float(point["x"]), y=float(point["y"]), z=float(point["z"]),
                      health=100, grounded=True)
        session["vy"] = 0

    def step(self, token, data):
        session = self.session(token)
        dx, dz = data.get("dx", 0), data.get("dz", 0)
        if any(type(v) not in (int, float) or not math.isfinite(v) or abs(v) > 1
               for v in (dx, dz)):
            raise ValueError("Movement must be finite and between -1 and 1")
        if any(type(data.get(key, False)) is not bool for key in ("jump", "sprint")):
            raise ValueError("Jump and sprint must be booleans")
        now = self.clock()
        elapsed = min(max(now - session["seen"], 0), 0.25)
        session["seen"] = now
        length = max(1, math.hypot(dx, dz))
        player = session["player"]
        if dx or dz:
            player["yaw"] = math.atan2(dx, dz)
        if data.get("jump") and player["grounded"]:
            session["vy"] = 7.8
            player["grounded"] = False
        speed = 6 if data.get("sprint") else 4
        remaining = elapsed
        while remaining > 0:
            dt = min(remaining, .02)
            remaining -= dt
            x = max(-15, min(15, player["x"] + dx / length * speed * dt))
            z = max(-15, min(15, player["z"] + dz / length * speed * dt))
            if not self.collides(session["gameId"], x, player["y"], player["z"]):
                player["x"] = x
            if not self.collides(session["gameId"], player["x"], player["y"], z):
                player["z"] = z
            session["vy"] -= 20 * dt
            y = player["y"] + session["vy"] * dt
            if y <= 0:
                player["y"], session["vy"], player["grounded"] = 0, 0, True
            elif self.collides(session["gameId"], player["x"], y, player["z"]):
                if session["vy"] < 0:
                    tops = [b["y"] + 1 for b in self.rooms[session["gameId"]]
                            if abs(player["x"] - b["x"]) < .79
                            and abs(player["z"] - b["z"]) < .79
                            and y < b["y"] + 1 <= player["y"] + .001]
                    if tops:
                        player["y"] = max(tops)
                    player["grounded"] = True
                session["vy"] = 0
            else:
                player["y"], player["grounded"] = y, False
        for coin in COINS:
            if coin["id"] not in player["collected"] and math.dist(
                    (player["x"], player["y"] + .8, player["z"]),
                    (coin["x"], coin["y"], coin["z"])) < 1:
                player["collected"].append(coin["id"])
                player["coins"] += 1
        for point in CHECKPOINTS:
            if math.dist((player["x"], player["y"], player["z"]),
                         (point["x"], point["y"], point["z"])) < .8:
                player["checkpoint"] = point["id"]
        if player["y"] < .3 and any(abs(player["x"] - h["x"]) < h["width"] / 2
                and abs(player["z"] - h["z"]) < h["depth"] / 2 for h in HAZARDS):
            self.respawn(session)
        return self.snapshot(session["gameId"])

    def action(self, token, data):
        session = self.session(token)
        player, game = session["player"], session["gameId"]
        kind = data.get("kind")
        if kind == "respawn":
            self.respawn(session)
        elif kind == "wave":
            session["waveUntil"] = self.clock() + 2
        elif kind in ("place", "remove"):
            if self.clock() - session["lastEdit"] < .2:
                raise ValueError("Build a little slower")
            x, y, z = (data.get(axis) for axis in ("x", "y", "z"))
            if any(type(v) is not int for v in (x, y, z)) or not (-14 <= x <= 14 and -14 <= z <= 14 and 0 <= y <= 7):
                raise ValueError("Choose a grid cell inside the build area")
            if math.dist((x, y, z), (player["x"], player["y"], player["z"])) > 5:
                raise ValueError("Move closer to build here")
            room = self.rooms[game]
            found = next((b for b in room if (b["x"], b["y"], b["z"]) == (x, y, z)), None)
            if kind == "remove":
                if not found or not found.get("owner"):
                    raise ValueError("Only player-built blocks can be removed")
                if found["owner"] != player["id"]:
                    raise ValueError("You can only remove your own blocks")
                if any(b['x'] == x and b['y'] == y + 1 and b['z'] == z for b in room):
                    raise ValueError("Remove the block above this one first")
                room.remove(found)
            else:
                color = data.get("color")
                if not isinstance(color, str) or not COLOR.fullmatch(color):
                    raise ValueError("Choose a valid block color")
                if found or len(room) >= 256:
                    raise ValueError("Cell occupied or room block limit reached")
                if y and not any(b["x"] == x and b["y"] == y - 1 and b["z"] == z for b in room):
                    raise ValueError("Blocks need support underneath")
                if any(abs(x - c["x"]) < 1 and abs(z - c["z"]) < 1 for c in CHECKPOINTS):
                    raise ValueError("Keep checkpoints clear")
                if any(s["gameId"] == game and abs(x - s["player"]["x"]) < .85
                       and abs(z - s["player"]["z"]) < .85
                       and y < s["player"]["y"] + 1.8 and y + 1 > s["player"]["y"]
                       for s in self.sessions.values()):
                    raise ValueError("Someone is standing there")
                room.append({"x": x, "y": y, "z": z, "color": color, "owner": player["id"]})
            session["lastEdit"] = self.clock()
        else:
            raise ValueError("Unknown action")
        return self.snapshot(game)

