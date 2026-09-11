-- Carry pre-existing live table notes into the operational encounter model.
-- Explicit lifecycle choices already stored in 0034 always win.
INSERT INTO campaign_session_run_encounters (
    run_id,
    source_document_id,
    source_path,
    encounter_name,
    first_activity_at,
    last_activity_at,
    last_section_key,
    last_section_title
)
SELECT DISTINCT ON (notes.run_id, notes.source_document_id)
    notes.run_id,
    notes.source_document_id,
    notes.source_path,
    notes.encounter_name,
    min(notes.captured_at) OVER encounter_activity,
    max(notes.captured_at) OVER encounter_activity,
    notes.section_key,
    notes.section_title
FROM campaign_session_run_notes AS notes
WHERE notes.context_kind = 'encounter'
  AND notes.source_document_id IS NOT NULL
WINDOW encounter_activity AS (PARTITION BY notes.run_id, notes.source_document_id)
ORDER BY notes.run_id, notes.source_document_id, notes.captured_at DESC, notes.note_id DESC
ON CONFLICT (run_id, source_document_id) DO NOTHING;

INSERT INTO campaign_encounter_progress (
    source_document_id,
    source_path,
    encounter_name,
    status,
    last_session_run_id
)
SELECT DISTINCT ON (notes.source_document_id)
    notes.source_document_id,
    notes.source_path,
    notes.encounter_name,
    'in_progress',
    notes.run_id
FROM campaign_session_run_notes AS notes
WHERE notes.context_kind = 'encounter'
  AND notes.source_document_id IS NOT NULL
ORDER BY notes.source_document_id, notes.captured_at DESC, notes.note_id DESC
ON CONFLICT (source_document_id) DO NOTHING;
