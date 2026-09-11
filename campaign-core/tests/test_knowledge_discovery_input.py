from tests.support.connected_knowledge_harness import load
from tests.support.knowledge_discovery_input import discovery_input


def test_discovery_receives_prose_and_provenance_but_no_answer_key():
    corpus = load()
    data = discovery_input(corpus, corpus.cases[0].id)
    assert set(data) == {"schema_version", "synthetic_only", "sources"}
    assert data["sources"]
    for source in data["sources"]:
        assert set(source) == {
            "record_id", "entity_id", "assertion", "source_id", "citation", "state",
            "authority", "visibility", "accepted",
        }
        assert source["assertion"] and source["citation"]


def test_changing_gold_does_not_change_discovery_input():
    corpus = load()
    case = corpus.cases[0]
    changed = case.model_copy(update={"required_ids": ["noise"],
                                     "required_paths": [["noise", "regent"]],
                                     "expected_mode": "conflict"})
    alternative = corpus.model_copy(update={"cases": [changed]})
    assert discovery_input(corpus, case.id) == discovery_input(alternative, case.id)


def test_scenario_exclusion_and_order_do_not_supply_gold_edges():
    corpus = load()
    case = corpus.cases[0]
    data = discovery_input(corpus, case.id)
    assert not {"old", "contradiction"} & {source["record_id"] for source in data["sources"]}
    reversed_corpus = corpus.model_copy(update={"records": list(reversed(corpus.records))})
    assert data == discovery_input(reversed_corpus, case.id)
