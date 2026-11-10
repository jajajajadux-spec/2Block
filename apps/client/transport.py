"""Small HTTP transport. No environment proxies or redirects for local joins."""

import json
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Connection:
    def __init__(self, server):
        self.server = server
        self.token = None
        self.opener = build_opener(ProxyHandler({}), NoRedirect())

    def post(self, path, data):
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        request = Request(self.server + path, json.dumps(data).encode(), headers)
        with self.opener.open(request, timeout=3) as response:
            return json.load(response)

