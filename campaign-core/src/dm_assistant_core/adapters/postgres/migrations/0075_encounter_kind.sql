-- TKT-0138 encounter slice / ADR-0021: encounters are Entities of their own
-- kind (Sean's ruling 2026-09-30: add `encounter`, distinct from the unused
-- `event` seed kind which stays for lore events like the Timeline). A table
-- event is an identity: authored document, participants as mentions, outcomes
-- as owned claims.

INSERT INTO kind_definitions (id, namespace, canonical_key, status)
VALUES ('20000000-0000-0000-0000-000000000009', 'entity', 'encounter', 'active')
ON CONFLICT (id) DO NOTHING;

INSERT INTO kind_versions (kind_id, version, label, description, inclusion_rule, exclusions, examples, counterexamples, behavior_version)
VALUES (
    '20000000-0000-0000-0000-000000000009', 1, 'Encounter',
    'A table event: an authored encounter with stages, participants, and outcomes. Owns its own claims; auto-mentions carry every cross-reference (ADR-0021).',
    ARRAY['An encounter document or referenceable table event.'],
    ARRAY['Sessions (the occasion, a context — ADR-0021).', 'Lore events (kind event).'],
    ARRAY['The Descent', 'the Ishirala dungeon', 'the Exile Camp meeting'],
    ARRAY['A session note', 'a historical event like the Fall of Ravenholdt'],
    1
)
ON CONFLICT (kind_id, version) DO NOTHING;
