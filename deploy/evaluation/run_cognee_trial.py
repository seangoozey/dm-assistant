"""One synthetic Cognee smoke trial; persistent conservative budget gateway required."""

import argparse
import asyncio
import json
import os
import secrets
from pathlib import Path

from budget_gateway import CHAT_MODEL, EMBED_MODEL, Ledger, start_gateway
from dotenv import dotenv_values


async def trial(search_only=False, cross_document=False, retire_cross_source=False, replace_cross_source=False, evidence_expansion=False, corpus_scope=None, live_pilot=False, live_generation="live-pilot-v2", live_search_only=False, relevance_trial=False, relevance_search_only=False):
    root = Path(__file__).resolve().parents[2]
    runtime = root / ".local" / "cognee-evaluation"
    if Path.cwd().resolve() != runtime:
        raise RuntimeError("Run from the isolated trial directory")
    values = dotenv_values(root / "deploy" / ".env")
    key = values.get("CAMPAIGN_OPENROUTER_API_KEY") or values.get("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("Existing OpenRouter credential unavailable")
    del values
    for name in list(os.environ):
        if any(part in name.upper() for part in ("API_KEY", "TOKEN", "DATABASE_URL")):
            os.environ.pop(name)
    ledger = Ledger(runtime / "trial-budget.sqlite")
    token = secrets.token_urlsafe(32)
    server = start_gateway(key, ledger, token, allow_requests=not retire_cross_source)
    endpoint = f"http://127.0.0.1:{server.server_port}/v1"
    os.environ.update({
        "TELEMETRY_DISABLED": "true", "COGNEE_SKIP_CONNECTION_TEST": "true",
        "COGNEE_LOG_FILE": "false", "LITELLM_LOCAL_MODEL_COST_MAP": "True",
        "CUSTOM_TIKTOKEN_CACHE_DIR": str(runtime / "tokenizers"),
        "LLM_PROVIDER": "custom", "LLM_MODEL": f"openai/{CHAT_MODEL}",
        "LLM_ENDPOINT": endpoint, "LLM_API_KEY": token,
        "LLM_MAX_COMPLETION_TOKENS": "8192",
        "EMBEDDING_PROVIDER": "openai_compatible", "EMBEDDING_MODEL": EMBED_MODEL,
        "EMBEDDING_ENDPOINT": endpoint, "EMBEDDING_API_KEY": token,
        "EMBEDDING_DIMENSIONS": "3072", "EMBEDDING_BATCH_SIZE": "32",
        "CACHING": "false", "ENABLE_BACKEND_ACCESS_CONTROL": "false",
    })
    report = {"model": CHAT_MODEL, "synthetic_only": True, "success": False}
    if live_pilot:
        report["synthetic_only"] = False
    try:
        if not retire_cross_source and not ledger.can_reserve():
            report["error_type"] = "BudgetExhausted"
            return
        import cognee
        from cognee.infrastructure.databases.graph import get_graph_engine

        # Keep this graph separate from the earlier single-passage experiment.
        storage = runtime / "cross-document" if cross_document or retire_cross_source or replace_cross_source or evidence_expansion else runtime
        if corpus_scope:
            storage = runtime / f"corpus-{corpus_scope}"
        if live_pilot:
            storage = runtime / live_generation
        if relevance_trial:
            storage = runtime / "relevance-v1"
        cognee.config.system_root_directory(str(storage / "system"))
        cognee.config.data_root_directory(str(storage / "data"))
        if relevance_trial:
            from relevance_trial import run
            await run(cognee, report, ledger, search_only=relevance_search_only)
            return
        if live_pilot:
            from live_pilot import run
            await run(cognee, report, ledger, live_generation, live_search_only)
            return
        if corpus_scope:
            from corpus_trial import run

            await run(cognee, report, ledger, corpus_scope)
            return
        if evidence_expansion:
            from cross_document_trial import expanded_query

            await expanded_query(cognee, report)
            return
        if replace_cross_source:
            from cross_document_trial import replace_geography

            await replace_geography(cognee, report)
            return
        if retire_cross_source:
            from cross_document_trial import retire_geography

            await retire_geography(cognee, report)
            return
        if cross_document:
            from cross_document_trial import run

            await run(cognee, report, ledger)
            return
        if search_only:
            from cognee.modules.search.types import SearchType

            report["queries"] = []
            for question in (
                "Where was the Sky Titan commanded to attack?",
                "Where is the Fire Titan summoning?",
                "Who opposes the cultists?",
            ):
                print(f"Retrieving context: {question}", flush=True)
                result = await asyncio.wait_for(cognee.search(
                    query_text=question, query_type=SearchType.GRAPH_COMPLETION,
                    datasets=["synthetic-command-ritual"], only_context=True, top_k=5,
                ), timeout=90)
                report["queries"].append({"question": question, "context": result})
            report["success"] = True
            return
        # No expected relationships or answers supplied to discovery.
        text = (
            "[source: synthetic-command] The Regent commanded the Sky Titan to destroy "
            "the castle at Eastwatch on Minor Isle.\n"
            "[source: synthetic-ritual] The Fire Titan summoning is on Ember Island. "
            "Eastwatch opposes the cultists."
        )
        print("Adding synthetic passage", flush=True)
        await cognee.add(text, dataset_name="synthetic-command-ritual")
        print("Running bounded cognify", flush=True)
        result = await asyncio.wait_for(
            cognee.cognify(datasets=["synthetic-command-ritual"], chunks_per_batch=1), timeout=180,
        )
        graph = await get_graph_engine()
        graph_data = await graph.get_graph_data()
        report.update(success=True, pipeline_result=str(result), graph=graph_data)
    except Exception as error:  # noqa: BLE001 - preserve budget report without leaking upstream data
        # Keep raw diagnostic details local; never print credentials or provider payloads.
        report.update(error_type=type(error).__name__)
        print(f"Trial failed: {type(error).__name__}", flush=True)
    finally:
        report["budget"] = ledger.summary()
        filename = "retrieval-report.json" if search_only else "trial-report.json"
        if relevance_trial:
            filename = "relevance-v1-expanded-report.json" if relevance_search_only else "relevance-v1-report.json"
        if cross_document:
            filename = "cross-document-report.json"
        if retire_cross_source:
            filename = "cross-document-retirement-report.json"
        if replace_cross_source:
            filename = "cross-document-replacement-report.json"
        if evidence_expansion:
            filename = "evidence-expansion-report.json"
        if corpus_scope:
            filename = f"corpus-{corpus_scope}-report.json"
        if live_pilot:
            filename = f"{live_generation}-{'search-' if live_search_only else ''}report.json"
        (runtime / filename).write_text(json.dumps(report, default=str, indent=2))
        server.shutdown()
        server.server_close()
        print(json.dumps({k: v for k, v in report.items()
                          if k not in {"graph", "before_graph", "pipeline_result", "queries", "expanded_results", "raw_context", "edge_paths", "rankings"}}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--search-only", action="store_true")
    modes.add_argument("--cross-document", action="store_true")
    modes.add_argument("--retire-cross-source", action="store_true")
    modes.add_argument("--replace-cross-source", action="store_true")
    modes.add_argument("--evidence-expansion", action="store_true")
    modes.add_argument("--corpus-scope", choices=["dm", "party", "conflict"])
    modes.add_argument("--live-pilot", action="store_true")
    modes.add_argument("--relevance-trial", action="store_true")
    parser.add_argument("--relevance-search-only", action="store_true")
    parser.add_argument("--live-generation", choices=["live-pilot-v2", "live-pilot-v3"], default="live-pilot-v2")
    parser.add_argument("--live-search-only", action="store_true")
    args = parser.parse_args()
    asyncio.run(trial(search_only=args.search_only, cross_document=args.cross_document,
                      retire_cross_source=args.retire_cross_source,
                      replace_cross_source=args.replace_cross_source, evidence_expansion=args.evidence_expansion,
                      corpus_scope=args.corpus_scope, live_pilot=args.live_pilot, live_generation=args.live_generation, live_search_only=args.live_search_only, relevance_trial=args.relevance_trial, relevance_search_only=args.relevance_search_only))
