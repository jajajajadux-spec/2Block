import json
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from apps.client.transport import Connection
from apps.server.__main__ import Server
from packages.common.protocol import DEFAULT_AVATAR


class HttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = Server(("127.0.0.1", 0))
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def test_complete_join_flow(self):
        connection = Connection(self.base)
        ticket = connection.post("/api/launches", {"gameId": "block-yard"})
        with urlopen(self.base + "/api/launches/" + ticket["launchId"]) as response:
            self.assertEqual(json.load(response), {"status": "pending"})
        session = connection.post("/api/join", {"gameId": "block-yard", "user": "Ada",
                                  "avatar": DEFAULT_AVATAR, "launchId": ticket["launchId"]})
        connection.token = session["token"]
        world = connection.post("/api/step", {"dx": 1, "dz": 0})
        self.assertEqual(world["players"][0]["user"], "Ada")
        with urlopen(self.base + "/api/launches/" + ticket["launchId"]) as response:
            self.assertEqual(json.load(response), {"status": "joined"})
        connection.post("/api/leave", {})
        with self.assertRaises(HTTPError) as raised:
            connection.post("/api/step", {})
        self.assertEqual(raised.exception.code, 401)
        raised.exception.close()

    def test_cross_origin_and_host_checks(self):
        for headers in ({"Origin": "https://evil.test"}, {"Host": "evil.test"},
                        {"Origin": "null"}, {"Sec-Fetch-Site": "cross-site"}):
            with self.subTest(headers=headers), self.assertRaises(HTTPError) as raised:
                urlopen(Request(self.base + "/api/games", headers=headers))
            self.assertEqual(raised.exception.code, 403)
            raised.exception.close()

    def test_static_allowlist_and_headers(self):
        with urlopen(self.base + "/") as response:
            self.assertIn(b"2Block", response.read())
            self.assertIn("frame-ancestors 'none'", response.headers["Content-Security-Policy"])
        for path in ("/../LICENSE", "/.git/config", "/packages/common/protocol.py"):
            with self.subTest(path=path), self.assertRaises(HTTPError) as raised:
                urlopen(self.base + path)
            self.assertEqual(raised.exception.code, 404)
            raised.exception.close()

    def test_bad_json_and_large_body(self):
        for body, mime, code in ((b"[]", "application/json", 400),
                                 (b"broken", "application/json", 400),
                                 (b"{}", "text/plain", 415),
                                 (b"a" * 8193, "application/json", 413)):
            request = Request(self.base + "/api/join", body, {"Content-Type": mime})
            with self.subTest(code=code), self.assertRaises(HTTPError) as raised:
                urlopen(request)
            self.assertEqual(raised.exception.code, code)
            raised.exception.close()

    def test_3d_assets_and_action_route(self):
        for path in ('/play', '/game/client.js', '/game/renderer.js', '/game/math.js', '/game/game.css'):
            with self.subTest(path=path), urlopen(self.base + path) as response:
                self.assertEqual(response.status, 200)
                self.assertGreater(len(response.read()), 50)
        connection = Connection(self.base)
        session = connection.post('/api/join', {'gameId': 'block-yard', 'user': 'Builder', 'avatar': DEFAULT_AVATAR})
        connection.token = session['token']
        world = connection.post('/api/action', {'kind': 'place', 'x': 2, 'y': 0, 'z': 0, 'color': '#58c9a5'})
        self.assertTrue(any(b.get('owner') == session['playerId'] for b in world['blocks']))
        connection.post('/api/leave', {})

