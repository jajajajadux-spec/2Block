"""Open the shared WebGL client from a validated desktop activation."""

import json
from urllib.parse import quote
import webbrowser


def client_url(join):
    # Fragments stay out of HTTP logs; the page removes it before joining.
    return join.server + '/play#' + quote(json.dumps(join.payload()), safe='')


def run(connection, join):
    if not webbrowser.open(client_url(join), new=1):
        raise RuntimeError('No browser opened. Visit the portal and choose Play Now.')
