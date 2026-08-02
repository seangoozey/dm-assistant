"""Check Campaign Core through its HTTP boundary without database credentials."""

from __future__ import annotations

import json
import os
from typing import Any
from urllib.parse import urlsplit
from urllib.request import urlopen


def main() -> dict[str, Any]:
    """Return Campaign Core's typed health response."""
    core_url = os.environ.get("CAMPAIGN_CORE_URL", "http://campaign-core:8000")
    normalized = core_url.rstrip("/")
    parsed = urlsplit(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("core_url must be an absolute HTTP(S) URL")
    with urlopen(f"{normalized}/health", timeout=10) as response:
        payload = json.load(response)
    if not isinstance(payload, dict):
        raise TypeError("Campaign Core health response must be an object")
    return payload
