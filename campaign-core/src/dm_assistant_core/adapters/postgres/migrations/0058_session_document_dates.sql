-- TKT-0118: campaign timestamp coverage. Legacy session notes are immutable
-- imported evidence — their in-game dates are recorded as an overlay (like
-- entity profiles), never by rewriting documents. Setting a date immediately
-- stamps the document's undated claims' effective_from through provenance;
-- existing dates are never overwritten (idempotent).
CREATE TABLE document_campaign_dates (
    source_document_id uuid PRIMARY KEY REFERENCES source_documents(id),
    calendar_id text NOT NULL DEFAULT 'gregorian-ce',
    campaign_year integer NOT NULL,
    campaign_month integer NOT NULL,
    campaign_day integer NOT NULL,
    reason text,
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE document_campaign_date_changes (
    id uuid PRIMARY KEY,
    source_document_id uuid NOT NULL REFERENCES source_documents(id),
    calendar_id text NOT NULL,
    campaign_year integer NOT NULL,
    campaign_month integer NOT NULL,
    campaign_day integer NOT NULL,
    reason text,
    changed_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX document_campaign_date_changes_doc_idx
    ON document_campaign_date_changes (source_document_id, changed_at DESC);

CREATE FUNCTION apply_session_document_date(
    p_document_id uuid,
    p_year integer,
    p_month integer,
    p_day integer,
    p_reason text
) RETURNS jsonb
LANGUAGE plpgsql AS $$
DECLARE
    v_stamped integer;
    v_evidenced integer;
BEGIN
    IF NOT EXISTS (SELECT 1 FROM source_documents WHERE id = p_document_id) THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'no such source document';
    END IF;
    INSERT INTO document_campaign_dates
        (source_document_id, calendar_id, campaign_year, campaign_month, campaign_day, reason)
    VALUES (p_document_id, 'gregorian-ce', p_year, p_month, p_day, p_reason)
    ON CONFLICT (source_document_id) DO UPDATE SET
        campaign_year = excluded.campaign_year,
        campaign_month = excluded.campaign_month,
        campaign_day = excluded.campaign_day,
        reason = excluded.reason,
        updated_at = now();
    INSERT INTO document_campaign_date_changes
        (id, source_document_id, calendar_id, campaign_year, campaign_month, campaign_day, reason)
    VALUES (gen_random_uuid(), p_document_id, 'gregorian-ce', p_year, p_month, p_day, p_reason);

    -- Claims inherit from their own provenance: only claims evidenced by this
    -- document, and only those still undated (never overwrite).
    WITH evidenced AS (
        SELECT c.id FROM claims c
        JOIN claim_evidence ce ON ce.claim_id = c.id
        JOIN source_spans ss ON ss.id = ce.source_span_id
        JOIN source_revisions sr ON sr.id = ss.source_revision_id
        WHERE sr.source_document_id = p_document_id
          AND c.effective_from_year IS NULL
          AND NOT EXISTS (SELECT 1 FROM claim_supersessions cs WHERE cs.superseded_claim_id = c.id)
    )
    SELECT count(*) INTO v_stamped FROM evidenced;
    UPDATE claims SET
        effective_from_year = p_year,
        effective_from_month = p_month,
        effective_from_day = p_day,
        campaign_calendar_id = 'gregorian-ce'
    WHERE id IN (
        SELECT c.id FROM claims c
        JOIN claim_evidence ce ON ce.claim_id = c.id
        JOIN source_spans ss ON ss.id = ce.source_span_id
        JOIN source_revisions sr ON sr.id = ss.source_revision_id
        WHERE sr.source_document_id = p_document_id
          AND c.effective_from_year IS NULL
    );
    SELECT count(*) INTO v_evidenced
    FROM claims c
    JOIN claim_evidence ce ON ce.claim_id = c.id
    JOIN source_spans ss ON ss.id = ce.source_span_id
    JOIN source_revisions sr ON sr.id = ss.source_revision_id
    WHERE sr.source_document_id = p_document_id;
    RETURN jsonb_build_object('claims_stamped', v_stamped,
                              'claims_evidenced', v_evidenced);
END;
$$;

-- Bulk inheritance: every dated document (DM overlay or capture-authored
-- frontmatter) stamps its still-undated claims. Idempotent by the same guard.
CREATE FUNCTION inherit_claim_dates_from_documents() RETURNS jsonb
LANGUAGE plpgsql AS $$
DECLARE
    v_overlay integer;
    v_frontmatter integer;
    v_stamped integer;
BEGIN
    WITH overlay_targets AS (
        SELECT d.source_document_id, d.campaign_year, d.campaign_month, d.campaign_day
        FROM document_campaign_dates d
    )
    SELECT count(*) INTO v_overlay FROM overlay_targets;

    WITH frontmatter_targets AS (
        SELECT DISTINCT sr.source_document_id,
               (sr.frontmatter_json->'in_game_date'->>'year')::integer,
               (sr.frontmatter_json->'in_game_date'->>'month')::smallint,
               (sr.frontmatter_json->'in_game_date'->>'day')::smallint
        FROM source_revisions sr
        WHERE sr.frontmatter_json ? 'in_game_date'
    )
    SELECT count(*) INTO v_frontmatter FROM frontmatter_targets;

    WITH dated_docs AS (
        SELECT d.source_document_id, d.campaign_year AS y, d.campaign_month AS m, d.campaign_day AS dd
        FROM document_campaign_dates d
        UNION
        SELECT sr.source_document_id,
               (sr.frontmatter_json->'in_game_date'->>'year')::integer,
               (sr.frontmatter_json->'in_game_date'->>'month')::smallint,
               (sr.frontmatter_json->'in_game_date'->>'day')::smallint
        FROM source_revisions sr
        WHERE sr.frontmatter_json ? 'in_game_date'
    ), eligible AS (
        SELECT DISTINCT c.id, docs.y, docs.m, docs.dd
        FROM claims c
        JOIN claim_evidence ce ON ce.claim_id = c.id
        JOIN source_spans ss ON ss.id = ce.source_span_id
        JOIN source_revisions sr ON sr.id = ss.source_revision_id
        JOIN dated_docs docs ON docs.source_document_id = sr.source_document_id
        WHERE c.effective_from_year IS NULL
    )
    SELECT count(*) INTO v_stamped FROM eligible;

    UPDATE claims c SET
        effective_from_year = e.y,
        effective_from_month = e.m,
        effective_from_day = e.dd,
        campaign_calendar_id = 'gregorian-ce'
    FROM (
        SELECT DISTINCT ON (claim.id) claim.id, docs.y, docs.m, docs.dd
        FROM claims claim
        JOIN claim_evidence ce ON ce.claim_id = claim.id
        JOIN source_spans ss ON ss.id = ce.source_span_id
        JOIN source_revisions sr ON sr.id = ss.source_revision_id
        JOIN (
            SELECT source_document_id, campaign_year AS y, campaign_month AS m, campaign_day AS dd,
                   updated_at AS priority FROM document_campaign_dates
            UNION ALL
            SELECT source_document_id,
                   (frontmatter_json->'in_game_date'->>'year')::integer,
                   (frontmatter_json->'in_game_date'->>'month')::smallint,
                   (frontmatter_json->'in_game_date'->>'day')::smallint,
                   captured_at AS priority
            FROM source_revisions WHERE frontmatter_json ? 'in_game_date'
        ) docs ON docs.source_document_id = sr.source_document_id
        WHERE claim.effective_from_year IS NULL
        ORDER BY claim.id, docs.priority DESC
    ) e
    WHERE c.id = e.id AND c.effective_from_year IS NULL;

    RETURN jsonb_build_object('overlay_dated_documents', v_overlay,
                              'frontmatter_dated_documents', v_frontmatter,
                              'claims_stamped', v_stamped);
END;
$$;
