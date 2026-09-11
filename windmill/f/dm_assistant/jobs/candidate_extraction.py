"""Run bounded candidate extraction calls as durable sequential Windmill work."""

from __future__ import annotations

import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from uuid import UUID

from wmill import set_progress  # type: ignore[import-not-found]

MAX_BATCH_SIZE = 50


def main(candidate_ids: list[str]) -> dict[str, Any]:
    if not candidate_ids or len(candidate_ids) > MAX_BATCH_SIZE:
        raise ValueError(f"candidate_ids must contain 1 to {MAX_BATCH_SIZE} items")
    normalized_ids = [str(UUID(candidate_id)) for candidate_id in candidate_ids]
    core_url = os.environ.get("CAMPAIGN_CORE_URL", "http://campaign-core:8000").rstrip("/")
    parsed = urlsplit(core_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("CAMPAIGN_CORE_URL must be an absolute HTTP(S) URL")

    results: list[dict[str, Any]] = []
    set_progress(1)
    for index, candidate_id in enumerate(normalized_ids, start=1):
        request = Request(
            f"{core_url}/imports/candidates/{candidate_id}/extraction?requester_role=dm",
            method="POST",
        )
        try:
            with urlopen(request, timeout=210) as response:
                payload = json.load(response)
            extraction_error = payload.get("error") if isinstance(payload, dict) else None
            if extraction_error:
                results.append(
                    {
                        "candidate_id": candidate_id,
                        "ok": False,
                        "error": str(extraction_error),
                        "result": payload,
                    }
                )
            else:
                results.append({"candidate_id": candidate_id, "ok": True, "result": payload})
        except HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            results.append({"candidate_id": candidate_id, "ok": False, "error": detail})
        except (URLError, TimeoutError, OSError, json.JSONDecodeError) as error:
            results.append({"candidate_id": candidate_id, "ok": False, "error": str(error)})
        set_progress(min(99, round(index / len(normalized_ids) * 99)))
    return {"candidate_ids": normalized_ids, "results": results}
