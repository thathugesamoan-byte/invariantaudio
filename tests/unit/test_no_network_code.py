# SPDX-License-Identifier: GPL-3.0-or-later
"""Guards the privacy claim "no network access" for v0.1.0-alpha.

The package contains no HTTP/socket client code. If network code is ever added,
this test must be updated deliberately together with PRIVACY.md.
"""
import ast
from pathlib import Path

import invariantaudio

FORBIDDEN = {
    "socket", "ssl", "http", "urllib", "urllib2", "urllib3", "requests", "httpx", "aiohttp",
    "ftplib", "smtplib", "telnetlib", "xmlrpc", "websocket", "websockets", "musicbrainzngs", "acoustid",
}


def test_package_imports_no_network_modules():
    root = Path(invariantaudio.__file__).parent
    offenders = []
    for py in root.rglob("*.py"):
        for node in ast.walk(ast.parse(py.read_text())):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            for n in names:
                if n.split(".")[0] in FORBIDDEN:
                    offenders.append((py.name, n))
    assert offenders == []


def test_only_local_binaries_are_spawned():
    root = Path(invariantaudio.__file__).parent
    src = "\n".join(p.read_text() for p in root.rglob("*.py"))
    for cmd in ("curl", "wget", "ssh", "scp", "nc "):
        assert f'"{cmd.strip()}"' not in src
