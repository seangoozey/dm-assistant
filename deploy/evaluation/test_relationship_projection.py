from relationship_projection import Contribution, aggregate


def contribution(**changes):
    values = dict(source="a", target="b", relation="commands", description="A commands B.",
                  evidence_id="e", revision="r1", state="intended", authority="npc_intention",
                  negated=False, time_scope="present", strength=.8,
                  visibility="dm_only", attribution="narrator")
    return Contribution(**(values | changes))


def test_duplicates_do_not_inflate_strength():
    assert aggregate([contribution()] * 10) == aggregate([contribution()])


def test_state_direction_negation_and_time_not_merged():
    rows = [contribution(), contribution(state="observed"), contribution(negated=True),
            contribution(source="b", target="a"), contribution(time_scope="past")]
    assert len(aggregate(rows)) == 5


def test_order_independent_and_source_contributions_retained():
    rows = [contribution(), contribution(evidence_id="e2", strength=.6)]
    assert aggregate(rows) == aggregate(list(reversed(rows)))
    assert aggregate(rows)[0]["strength"] == .7
    assert aggregate(rows)[0]["support_count"] == 2


def test_visibility_and_speaker_cannot_be_aggregated_away():
    rows = [contribution(), contribution(visibility="party"), contribution(attribution="rumor")]
    assert len(aggregate(rows)) == 3
