import json
import unittest
from urllib.parse import urlencode

from packages.common.protocol import DEFAULT_AVATAR, SERVER, parse_link


def link(**overrides):
    fields = {"gameId": "block-yard", "user": "Ada & friends", "server": SERVER,
              "avatar": json.dumps(DEFAULT_AVATAR)}
    fields.update(overrides)
    return "twoblock://join?" + urlencode(fields)


class ProtocolTests(unittest.TestCase):
    def test_encoded_name_and_avatar(self):
        parsed = parse_link(link(user="Žofka & #1"))
        self.assertEqual(parsed.user, "Žofka & #1")
        self.assertEqual(parsed.avatar, DEFAULT_AVATAR)

    def test_untrusted_servers(self):
        for value in ("http://evil.test", "http://127.0.0.1:8765@evil.test",
                      SERVER + "/", "file:///etc/passwd", "http://localhost:8765",
                      "http://127.0.0.1:22"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_link(link(server=value))

    def test_bad_links(self):
        for value in (link() + "&user=duplicate", link() + "#fragment",
                      link().replace("//join", "//other"), link().replace("twoblock:", "https:"),
                      link() + "&extra=1", link() + "\n", "twoblock://join?broken",
                      "twoblock://join?", "x" * 4097):
            with self.subTest(value=value[:80]), self.assertRaises(ValueError):
                parse_link(value)

    def test_bad_profiles(self):
        for values in ({"user": ""}, {"user": "a" * 25}, {"user": "x\ny"},
                       {"gameId": "../private"}, {"avatar": "null"},
                       {"avatar": "[]"}, {"avatar": "{}"}, {"avatar": "broken"},
                       {"avatar": json.dumps({**DEFAULT_AVATAR, "body": "red"})},
                       {"avatar": json.dumps({**DEFAULT_AVATAR, "hat": "script"})},
                       {"launchId": "bad"}):
            with self.subTest(values=values), self.assertRaises(ValueError):
                parse_link(link(**values))

    def test_uri_cannot_inject_management_flags(self):
        from unittest.mock import patch
        from apps.client.__main__ import main
        for flag in ("--register", "--unregister", "--install"):
            with self.subTest(flag=flag), patch("sys.argv", ["client", link(), flag]), \
                    patch("sys.stderr"), self.assertRaises(SystemExit) as raised:
                main()
            self.assertEqual(raised.exception.code, 2)

