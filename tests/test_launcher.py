import json
import unittest
from unittest.mock import patch
from urllib.parse import unquote, urlsplit

from apps.client.window import client_url, run
from packages.common.protocol import DEFAULT_AVATAR, JoinRequest, SERVER


class LauncherTests(unittest.TestCase):
    def test_profile_is_in_fragment_and_opened_without_shell(self):
        join = JoinRequest('block-yard', 'Žofka & friends', DEFAULT_AVATAR)
        url = urlsplit(client_url(join))
        self.assertEqual(url.query, '')
        self.assertEqual(url.path, '/play')
        self.assertEqual(json.loads(unquote(url.fragment)), join.payload())
        with patch('webbrowser.open', return_value=True) as opened:
            run(None, join)
        opened.assert_called_once_with(client_url(join), new=1)

    def test_failed_browser_launch_is_reported(self):
        with patch('webbrowser.open', return_value=False), self.assertRaises(RuntimeError):
            run(None, JoinRequest('block-yard', 'Guest', DEFAULT_AVATAR))
