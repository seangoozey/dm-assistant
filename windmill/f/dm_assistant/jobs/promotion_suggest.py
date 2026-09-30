"""Run one AI promotion-suggestion pass as durable background Windmill work (TKT-0137).

The app fires this job and walks away; the suggestion set lands in the
working Lore item when the job completes. Long AI calls must never occupy
the UI's request path.
"""

from __future__ import annotations

import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


def main(command: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(command, dict) or not command.get("idempotency_key"):
        raise ValueError("command must include an idempotency_key")
    core_url = os.environ.get("CAMPAIGN_CORE_URL", "http://campaign-core:8000").rstrip("/")
    parsed = urlsplit(core_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("CAMPAIGN_CORE_URL must be an absolute HTTP(S) URL")

    body = json.dumps(command).encode("utf-8")
    request = Request(
        f"{core_url}/promotion/suggest?requester_role=dm",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=200) as response:
            return json.load(response)  # type: ignore[no-any-return]
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise ValueError(f"Campaign Core rejected the suggestion run: {detail}") from error
    except (URLError, TimeoutError, OSError) as error:
        raise ValueError(f"Campaign Core could not be reached: {error}") from error
