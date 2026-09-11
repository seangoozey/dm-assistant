"""Read an existing synthetic Cognee store and render its native graph inspector.

No extraction, search embedding, provider calls or campaign writes. Run from the
isolated evaluation directory using its Cognee environment.
"""

import argparse
import asyncio
import hashlib
import json
import os
import socket
from pathlib import Path


async def main(scope):
    root = Path(__file__).resolve().parents[2]
    runtime = root / ".local/cognee-evaluation"
    if Path.cwd().resolve() != runtime:
        raise RuntimeError("Run from the isolated evaluation directory")
    storage = runtime / f"corpus-{scope}"
    if not (storage / "system").is_dir():
        raise RuntimeError("Existing graph store required")
    for name in list(os.environ):
        if any(part in name.upper() for part in ("API_KEY", "TOKEN", "DATABASE_URL")):
            os.environ.pop(name)
    os.environ.update({
        "TELEMETRY_DISABLED": "true", "COGNEE_SKIP_CONNECTION_TEST": "true",
        "COGNEE_LOG_FILE": "false", "LITELLM_LOCAL_MODEL_COST_MAP": "True",
        "CUSTOM_TIKTOKEN_CACHE_DIR": str(runtime / "tokenizers"),
        "LLM_PROVIDER": "custom", "LLM_MODEL": "openai/offline-placeholder",
        "LLM_ENDPOINT": "http://127.0.0.1:1/v1", "LLM_API_KEY": "offline-placeholder",
        "ENABLE_BACKEND_ACCESS_CONTROL": "false",
    })

    def deny(*args, **kwargs):
        raise RuntimeError("Network disabled for graph inspection")

    socket.socket.connect = deny
    socket.create_connection = deny
    socket.getaddrinfo = deny
    import cognee
    from cognee.infrastructure.databases.graph import get_graph_engine
    from cognee.modules.visualization.cognee_network_visualization import (
        cognee_network_visualization,
    )

    cognee.config.system_root_directory(str(storage / "system"))
    cognee.config.data_root_directory(str(storage / "data"))
    graph = await (await get_graph_engine()).get_graph_data()
    if not graph[0]:
        raise RuntimeError("Selected store has no graph nodes")
    output = runtime / f"inspector-{scope}"
    output.mkdir(exist_ok=True)
    encoded = json.dumps(graph, default=str, sort_keys=True)
    (output / "graph.json").write_text(encoded, encoding="utf-8")
    await cognee_network_visualization(graph, str(output / "graph.html"))
    summary = {"scope": scope, "synthetic_only": True, "provider_calls": 0,
               "nodes": len(graph[0]), "edges": len(graph[1]),
               "sha256": hashlib.sha256(encoded.encode()).hexdigest(),
               "graph_file": str(output / "graph.json"),
               "viewer_file": str(output / "graph.html")}
    (output / "inspection.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--scope", choices=["dm", "party", "conflict"], default="dm")
    asyncio.run(main(parser.parse_args().scope))
