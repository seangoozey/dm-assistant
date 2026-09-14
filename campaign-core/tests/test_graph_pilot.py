import json
from unittest.mock import MagicMock

from dm_assistant_core.application.graph_pilot import GraphPilotRetrieval
from dm_assistant_core.domain.derived_retrieval import evaluate_suggestions
from dm_assistant_core.domain.models import ClaimState
from tests.test_derived_retrieval import query
from tests.test_evidence_comparison import record


def setup(tmp_path):
    r = record(evidence_binding="bound", assertion="The port is on the island.")
    bundle = {"records": [r.model_dump(mode="json")],
              "documents": {"doc": {"record_id": r.record_id, "text": r.assertion}},
              "graph": [[["a", {"type": "Entity", "name": "Titan"}],
                         ["b", {"type": "Entity", "name": "port"}],
                         ["c", {"type": "DocumentChunk", "document_id": "doc",
                                  "text": r.assertion}]],
                        [["a", "b", "sent_to", {}], ["c", "b", "contains", {}],
                         ["c", "a", "contains", {}]]]}
    path = tmp_path / "bundle.json"
    path.write_text(json.dumps(bundle))
    repository, fallback = MagicMock(), MagicMock()
    repository.current_records.return_value = (r,)
    fallback.query.return_value = evaluate_suggestions(query(), (), ())
    return GraphPilotRetrieval(fallback, repository, str(path)), repository, r


def test_graph_adds_nonlexical_current_context_and_trace(tmp_path):
    service, _, _ = setup(tmp_path)
    result = service.query(query().model_copy(update={"question": "Where is Titan?"}))
    assert len(result.evidence) == 1
    assert result.evidence[0].role == "context"
    assert result.answer_mode == "insufficient_evidence"
    assert "Titan ↔ port" in result.evidence[0].graph_trace[0]
    assert result.evidence[0].graph_sources[0].assertion == "The port is on the island."


def test_reverse_two_hops_find_text_without_search_name(tmp_path):
    service, _, _ = setup(tmp_path)
    path = tmp_path / "bundle.json"
    bundle = json.loads(path.read_text())
    bundle["graph"][0].append(["bridge", {"type": "Entity", "name": "Captain"}])
    bundle["graph"][1] = [["bridge", "a", "commands", {}],
                          ["bridge", "b", "travels_to", {}],
                          ["c", "b", "contains", {}], ["c", "a", "contains", {}],
                          ["c", "bridge", "contains", {}]]
    path.write_text(json.dumps(bundle))
    result = service.query(query().model_copy(update={"question": "Titan"}))
    assert len(result.evidence) == 1
    assert "Titan" not in result.evidence[0].assertion
    assert result.evidence[0].graph_trace[:2] == (
        "Connected through: Captain ↔ Titan",
        "Connected through: Captain ↔ port",
    )


def test_any_changed_record_disables_pilot(tmp_path):
    service, repository, r = setup(tmp_path)
    repository.current_records.return_value = (r.model_copy(update={"assertion": "Corrected"}),)
    assert not service.query(query().model_copy(update={"question": "Titan"})).evidence


def test_three_hops_are_not_followed(tmp_path):
    service, _, _ = setup(tmp_path)
    path = tmp_path / "bundle.json"
    bundle = json.loads(path.read_text())
    bundle["graph"][0].extend([["x", {"type": "Entity", "name": "Captain"}],
                               ["y", {"type": "Entity", "name": "Ship"}]])
    bundle["graph"][1] = [["a", "x", "knows", {}], ["x", "y", "owns", {}],
                          ["y", "b", "docks_at", {}], ["c", "b", "contains", {}]]
    path.write_text(json.dumps(bundle))
    assert not service.query(query().model_copy(update={"question": "Titan"})).evidence


def test_party_never_loads_dm_graph(tmp_path):
    service, repository, _ = setup(tmp_path)
    assert not service.query(query("party")).evidence
    repository.current_records.assert_not_called()


def test_generated_event_label_does_not_replace_planning_context(tmp_path):
    service, repository, r = setup(tmp_path)
    r = r.model_copy(update={"assertion": "The captain plans to attack the port.",
                             "state": ClaimState.INTENDED})
    repository.current_records.return_value = (r,)
    path = tmp_path / "bundle.json"
    bundle = json.loads(path.read_text())
    bundle["records"] = [r.model_dump(mode="json")]
    bundle["documents"]["doc"]["text"] = r.assertion
    bundle["graph"][0][2][1]["text"] = r.assertion
    bundle["graph"][1][0][2] = "destroys"
    path.write_text(json.dumps(bundle))
    evidence = service.query(query().model_copy(update={"question": "Titan"})).evidence[0]
    assert "destroys" not in " ".join(evidence.graph_trace)
    assert evidence.graph_sources[0].assertion == r.assertion
    assert evidence.graph_sources[0].state == "intended"


def test_roster_edges_traverse_without_shared_claims(tmp_path):
    # An audited seat stands on its receipt: the member's claims surface for a
    # faction question even when no claim co-mentions them together.
    faction_claim = record(identity="f", evidence_binding="bound", assertion="The Inquisitors enforce doctrine.")
    member_claim = record(identity="m", evidence_binding="bound", assertion="Eustice keeps the ledgers.")
    documents = {
        "doc-f": {"record_id": faction_claim.record_id, "text": faction_claim.assertion},
        "doc-m": {"record_id": member_claim.record_id, "text": member_claim.assertion},
    }
    bundle = {"records": [faction_claim.model_dump(mode="json"), member_claim.model_dump(mode="json")],
              "documents": documents,
              "graph": [[["faction", {"type": "Entity", "name": "Inquisitors"}],
                         ["member", {"type": "Entity", "name": "Eustice"}],
                         ["chunk-f", {"type": "DocumentChunk", "document_id": "doc-f",
                                       "text": faction_claim.assertion}],
                         ["chunk-m", {"type": "DocumentChunk", "document_id": "doc-m",
                                       "text": member_claim.assertion}]],
                        [["chunk-f", "faction", "contains", {}],
                         ["chunk-m", "member", "contains", {}],
                         ["member", "faction", "member_of", {"role": "Inquisitor"}],
                         ["leader", "faction", "leader_of", {"role": "Grand Inquisitor"}]]]}
    path = tmp_path / "bundle.json"
    path.write_text(json.dumps(bundle))
    repository, fallback = MagicMock(), MagicMock()
    repository.current_records.return_value = (faction_claim, member_claim)
    fallback.query.return_value = evaluate_suggestions(query(), (), ())
    service = GraphPilotRetrieval(fallback, repository, str(path))

    result = service.query(query().model_copy(update={"question": "Inquisitors"}))
    traced = {item.record_id: item for item in result.evidence if item.role == "context"}
    assert member_claim.record_id in traced
    trace_text = " ".join(traced[member_claim.record_id].graph_trace)
    assert "Eustice" in trace_text and "Inquisitor" in trace_text
    assert faction_claim.record_id in traced
