"""Network-blocked import check; run in the disposable trial directory."""

import importlib.metadata
import inspect
import json
import os
import socket
from pathlib import Path


def main() -> None:
    if Path(".env").exists():
        raise SystemExit("Run outside any directory containing .env")
    for name in list(os.environ):
        if any(part in name.upper() for part in ("API_KEY", "TOKEN", "DATABASE_URL")):
            os.environ.pop(name)
    os.environ.update({
        "TELEMETRY_DISABLED": "true", "COGNEE_SKIP_CONNECTION_TEST": "true",
        "LLM_PROVIDER": "custom", "LLM_MODEL": "openai/offline-placeholder",
        "LLM_ENDPOINT": "http://127.0.0.1:1/v1", "LLM_API_KEY": "offline-placeholder",
        "LITELLM_LOCAL_MODEL_COST_MAP": "True",
        "COGNEE_LOG_FILE": "false",
        "CUSTOM_TIKTOKEN_CACHE_DIR": str(Path("tokenizers").resolve()),
        "TIKTOKEN_CACHE_DIR": str(Path("tokenizers").resolve()),
    })
    blocked = []

    def deny(*args, **kwargs):
        blocked.append("network_attempt")
        raise RuntimeError("network disabled during preflight")

    socket.socket.connect = deny
    socket.create_connection = deny
    socket.getaddrinfo = deny
    import cognee

    print(json.dumps({
        "cognee_version": importlib.metadata.version("cognee"),
        "add_available": callable(cognee.add),
        "cognify_parameters": list(inspect.signature(cognee.cognify).parameters),
        "search_parameters": list(inspect.signature(cognee.search).parameters),
        "network_attempts_blocked": len(blocked),
        "provider_calls_sent": 0, "evaluation_run": False,
    }, indent=2))


if __name__ == "__main__":
    main()
