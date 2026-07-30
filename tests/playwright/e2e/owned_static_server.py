"""Loopback-only static server child for the schema-driven browser walker.

Python's stock ``http.server`` startup calls ``socket.getfqdn()`` before
printing its human-readable ready banner. A slow or unavailable reverse-DNS
resolver can therefore make a successfully bound test server look hung. This
child keeps the standard static-file handler while publishing a stable,
machine-readable readiness line without a DNS lookup.
"""

from __future__ import annotations

import argparse
import functools
import http.server
import socketserver
from pathlib import Path


class LoopbackThreadingHTTPServer(http.server.ThreadingHTTPServer):
    """Threading HTTP server whose startup does not perform reverse DNS."""

    def server_bind(self) -> None:
        socketserver.TCPServer.server_bind(self)
        host, port = self.server_address[:2]
        self.server_name = str(host)
        self.server_port = int(port)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--directory", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    handler = functools.partial(
        http.server.SimpleHTTPRequestHandler,
        directory=str(args.directory),
    )
    with LoopbackThreadingHTTPServer(("127.0.0.1", args.port), handler) as server:
        print(f"WALKER_SERVER_READY {server.server_port}", flush=True)
        server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
