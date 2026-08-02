import { FormEvent, useEffect, useMemo, useRef, useState } from "react";

import type {
  CampaignClient,
  CandidateFilters,
  CandidateProposalVersion,
  CreateProposalItem,
  ImportCandidate,
  ImportReviewItem,
  ImportRunSummary,
  RetrievalResult,
} from "./campaignClient";
import type { JobPlatform, JobSnapshot } from "./jobPlatform";
import { loadPendingJob, savePendingJob } from "./operationState";
import {
  loadReviewState,
  saveReviewState,
  type PersistedReviewState,
} from "./reviewState";

interface AppProps {
  campaignClient: CampaignClient;
  jobPlatform: JobPlatform;
  storage?: Storage;
  pollIntervalMs?: number;
}

const MODE_COPY: Record<RetrievalResult["answer_mode"], { eyebrow: string; title: string }> = {
  answer: { eyebrow: "Grounded answer", title: "The archive supports this" },
  insufficient_evidence: { eyebrow: "Records incomplete", title: "Not enough evidence" },
  conflict: { eyebrow: "Conflict", title: "The records disagree" },
  possible_retcon: { eyebrow: "Review required", title: "Possible retcon detected" },
  restricted: { eyebrow: "Restricted", title: "Visible records cannot answer this" },
};

const JOB_COPY: Record<JobSnapshot["state"], string> = {
  queued: "Waiting for a worker",
  running: "Campaign Core check in progress",
  succeeded: "Campaign Core is available",
  failed: "Campaign Core check failed",
};

function ArchiveMark() {
  return (
    <svg aria-hidden="true" className="archive-mark" viewBox="0 0 40 40">
      <path d="M20 3 34 10v20l-14 7L6 30V10l14-7Z" />
      <path d="m12 14 8-4 8 4v12l-8 4-8-4V14Z" />
      <path d="M20 10v20M12 14l8 4 8-4" />
    </svg>
  );
}

function SearchIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <circle cx="11" cy="11" r="6.5" />
      <path d="m16 16 4 4" />
    </svg>
  );
}

function PulseIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <path d="M3 12h4l2.2-5 4.1 10 2.2-5H21" />
    </svg>
  );
}

function display(value: string): string {
  return value.replaceAll("_", " ");
}

function reviewSummary(review: ImportReviewItem): string {
  for (const key of ["reason", "warning", "message", "path"]) {
    const value = review.details[key];
    if (typeof value === "string" && value.trim()) return value;
  }
  return display(review.kind);
}

function phaseLabel(state: PersistedReviewState): string {
  const labels: Record<PersistedReviewState["phase"], string> = {
    idle: "No pending action",
    proposal_pending: "Pending exact confirmation",
    approved: "Approved and ready to apply",
    applied: "Applied with receipt",
    rejected: "Candidate rejected",
    deferred: "Candidate deferred",
    stale: "Stale proposal version",
    failed: "Operation failed",
  };
  return labels[state.phase];
}

function App({ campaignClient, jobPlatform, storage, pollIntervalMs = 700 }: AppProps) {
  const session = storage ?? window.sessionStorage;
  const [question, setQuestion] = useState("");
  const [queryState, setQueryState] = useState<"idle" | "loading" | "error">("idle");
  const [queryError, setQueryError] = useState("");
  const [result, setResult] = useState<RetrievalResult | null>(null);
  const [job, setJob] = useState<JobSnapshot | null>(() => loadPendingJob(session));
  const [jobActionError, setJobActionError] = useState("");
  const pollTimer = useRef<number | undefined>(undefined);

  const [runs, setRuns] = useState<ImportRunSummary[]>([]);
  const [candidates, setCandidates] = useState<ImportCandidate[]>([]);
  const [reviews, setReviews] = useState<ImportReviewItem[]>([]);
  const [queueTotal, setQueueTotal] = useState(0);
  const [reviewLoading, setReviewLoading] = useState(true);
  const [reviewError, setReviewError] = useState("");
  const [selected, setSelected] = useState<ImportCandidate | null>(null);
  const [filters, setFilters] = useState<CandidateFilters>({ review_status: "pending" });
  const [reviewState, setReviewState] = useState<PersistedReviewState>(() =>
    loadReviewState(session),
  );
  const [proposalValidated, setProposalValidated] = useState(!reviewState.proposal);
  const [resolution, setResolution] = useState<"new" | "existing">("new");
  const [entityName, setEntityName] = useState("");
  const [entityType, setEntityType] = useState("npc");
  const [subjectId, setSubjectId] = useState("");
  const [predicate, setPredicate] = useState("");
  const [observedAt, setObservedAt] = useState("");
  const [dispositionReason, setDispositionReason] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [selectedItemIds, setSelectedItemIds] = useState<string[]>([]);
  const [reviewBusy, setReviewBusy] = useState(false);

  useEffect(() => savePendingJob(session, job), [job, session]);
  useEffect(() => saveReviewState(session, reviewState), [reviewState, session]);

  useEffect(() => {
    if (!job || !["queued", "running"].includes(job.state)) return;
    let cancelled = false;
    const poll = async () => {
      try {
        const next = await jobPlatform.inspect(job.jobId);
        if (cancelled) return;
        setJob(next);
        setJobActionError("");
        if (["queued", "running"].includes(next.state)) {
          pollTimer.current = window.setTimeout(poll, pollIntervalMs);
        }
      } catch (error) {
        if (!cancelled) {
          setJobActionError(error instanceof Error ? error.message : "Job status is unavailable");
        }
      }
    };
    pollTimer.current = window.setTimeout(poll, 0);
    return () => {
      cancelled = true;
      if (pollTimer.current !== undefined) window.clearTimeout(pollTimer.current);
    };
  }, [job?.jobId, job?.state, jobPlatform, pollIntervalMs]);

  async function loadReviewWorkspace(activeFilters: CandidateFilters = filters) {
    setReviewLoading(true);
    setReviewError("");
    try {
      const [runPage, candidatePage, reviewPage] = await Promise.all([
        campaignClient.listImportRuns(),
        campaignClient.listCandidates(activeFilters),
        campaignClient.listReviews(activeFilters.run_id),
      ]);
      setRuns(runPage.items);
      setCandidates(candidatePage.items);
      setQueueTotal(candidatePage.total);
      setReviews(reviewPage.items);
      const persistedId = reviewState.selectedCandidateId;
      if (persistedId) {
        const detail = await campaignClient.getCandidate(persistedId);
        setSelected(detail);
      } else if (!selected && candidatePage.items.length > 0) {
        setSelected(candidatePage.items[0]);
      }
    } catch (error) {
      setReviewError(error instanceof Error ? error.message : "Import review is unavailable");
    } finally {
      setReviewLoading(false);
    }
  }

  useEffect(() => {
    void loadReviewWorkspace();
    if (reviewState.proposal) {
      setProposalValidated(false);
      void campaignClient
        .getProposal(reviewState.proposal.proposal_id)
        .then((current) => {
          if (
            current.version_number !== reviewState.proposal?.version_number ||
            current.content_hash !== reviewState.proposal.content_hash
          ) {
            setReviewState((prior) => ({
              ...prior,
              phase: "stale",
              proposal: current,
              approval: undefined,
              message: "The proposal changed after the displayed version was reviewed.",
            }));
          } else {
            setReviewState((prior) => ({ ...prior, proposal: current }));
            setSelectedItemIds(current.items.map((item) => item.item_id));
          }
        })
        .catch((error) => {
          setReviewState((prior) => ({
            ...prior,
            phase: "failed",
            message: error instanceof Error ? error.message : "Proposal refresh failed",
          }));
        })
        .finally(() => setProposalValidated(true));
    }
    // The initial snapshot is intentionally restored exactly once.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function ask(event: FormEvent) {
    event.preventDefault();
    const trimmed = question.trim();
    if (!trimmed) return;
    setQueryState("loading");
    setQueryError("");
    try {
      setResult(
        await campaignClient.query({
          question: trimmed,
          requester_visibility: { role: "dm" },
        }),
      );
      setQueryState("idle");
    } catch (error) {
      setQueryError(error instanceof Error ? error.message : "The archive could not be queried");
      setQueryState("error");
    }
  }

  async function startHealthCheck() {
    setJobActionError("");
    try {
      setJob(await jobPlatform.startHealthCheck());
    } catch (error) {
      setJobActionError(error instanceof Error ? error.message : "The job could not be started");
    }
  }

  async function chooseCandidate(candidateId: string) {
    if (["proposal_pending", "approved"].includes(reviewState.phase)) return;
    setReviewBusy(true);
    try {
      const detail = await campaignClient.getCandidate(candidateId);
      setSelected(detail);
      setReviewState({ selectedCandidateId: candidateId, phase: "idle" });
      setEntityName("");
      setPredicate("");
      setDispositionReason("");
    } catch (error) {
      setReviewError(error instanceof Error ? error.message : "Candidate could not be loaded");
    } finally {
      setReviewBusy(false);
    }
  }

  function claimItem(
    candidate: ImportCandidate,
    evidenceRevisionId: string,
    targetSubjectId: string,
  ): CreateProposalItem {
    return {
      mutation_kind: "create_claim",
      candidate_id: candidate.candidate_id,
      evidence_revision_id: evidenceRevisionId,
      target_id: crypto.randomUUID(),
      subject_entity_id: targetSubjectId,
      predicate: predicate.trim(),
      state: candidate.state,
      authority: candidate.authority,
      visibility: candidate.visibility,
      confidence: "1",
      is_conditional: candidate.conditional,
      predicts_subject_action: candidate.predicts_subject_action,
      recorded_at: new Date().toISOString(),
      ...(candidate.state === "observed" && observedAt
        ? { observed_at: new Date(observedAt).toISOString() }
        : {}),
    };
  }

  async function createProposal(event: FormEvent) {
    event.preventDefault();
    if (!selected || !selected.evidence[0] || !predicate.trim()) return;
    setReviewBusy(true);
    setReviewError("");
    try {
      const evidenceRevisionId = selected.evidence[0].source_revision_id;
      let items: CreateProposalItem[];
      if (resolution === "new") {
        const entityId = crypto.randomUUID();
        items = [
          {
            mutation_kind: "create_entity",
            candidate_id: selected.candidate_id,
            evidence_revision_id: evidenceRevisionId,
            target_id: entityId,
            entity_type: entityType.trim(),
            canonical_name: entityName.trim(),
          },
          claimItem(selected, evidenceRevisionId, entityId),
        ];
      } else {
        items = [claimItem(selected, evidenceRevisionId, subjectId.trim())];
      }
      const proposal = await campaignClient.createProposal(items);
      setProposalValidated(true);
      setSelectedItemIds(proposal.items.map((item) => item.item_id));
      setConfirmation("");
      setReviewState({
        selectedCandidateId: selected.candidate_id,
        phase: "proposal_pending",
        proposal,
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Proposal creation failed";
      setReviewState((prior) => ({ ...prior, phase: "failed", message }));
    } finally {
      setReviewBusy(false);
    }
  }

  async function disposition(dispositionValue: "deferred" | "rejected") {
    if (!selected || !dispositionReason.trim()) return;
    setReviewBusy(true);
    try {
      const result = await campaignClient.dispositionCandidate(
        selected.candidate_id,
        dispositionValue,
        dispositionReason.trim(),
      );
      const next = { ...selected, review_status: result.review_status };
      setSelected(next);
      setCandidates((prior) =>
        prior.map((item) => (item.candidate_id === next.candidate_id ? next : item)),
      );
      setReviewState({
        selectedCandidateId: selected.candidate_id,
        phase: result.review_status,
        message: result.reason,
      });
    } catch (error) {
      setReviewState((prior) => ({
        ...prior,
        phase: "failed",
        message: error instanceof Error ? error.message : "Disposition failed",
      }));
    } finally {
      setReviewBusy(false);
    }
  }

  async function approveProposal() {
    const proposal = reviewState.proposal;
    if (
      !proposal ||
      !proposalValidated ||
      confirmation !== "APPROVE" ||
      selectedItemIds.length === 0
    ) return;
    setReviewBusy(true);
    try {
      const scope = [...selectedItemIds].sort();
      const approval = await campaignClient.approveProposal(
        proposal,
        scope,
        `review:${proposal.proposal_id}:${proposal.version_number}:${scope.join(",")}`,
      );
      setReviewState((prior) => ({ ...prior, phase: "approved", approval, message: undefined }));
      setConfirmation("");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Approval failed";
      const stale = /stale|version|superseded/i.test(message);
      setReviewState((prior) => ({ ...prior, phase: stale ? "stale" : "failed", message }));
    } finally {
      setReviewBusy(false);
    }
  }

  async function applyApproval() {
    const { proposal, approval } = reviewState;
    if (!proposal || !approval || !proposalValidated) return;
    setReviewBusy(true);
    try {
      const receipt = await campaignClient.applyApproval(proposal, approval);
      setReviewState((prior) => ({
        ...prior,
        phase: "applied",
        receipt,
        message: undefined,
      }));
      if (selected) setSelected({ ...selected, review_status: "applied" });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Application failed";
      const stale = /stale|version|superseded/i.test(message);
      setReviewState((prior) => ({ ...prior, phase: stale ? "stale" : "failed", message }));
    } finally {
      setReviewBusy(false);
    }
  }

  const selectedReviews = useMemo(
    () => reviews.filter((review) => review.subject_id === selected?.source_document_id),
    [reviews, selected?.source_document_id],
  );
  const sourceReviews = useMemo(
    () =>
      [...reviews]
        .filter((review) => review.subject_type === "source_document")
        .sort((left, right) => {
          const leftQuarantine = left.kind === "import_quarantine" ? 0 : 1;
          const rightQuarantine = right.kind === "import_quarantine" ? 0 : 1;
          return leftQuarantine - rightQuarantine || left.kind.localeCompare(right.kind);
        }),
    [reviews],
  );
  const quarantineCount = reviews.filter(
    (review) => review.kind === "import_quarantine" || review.classification === "quarantine",
  ).length;
  const activeRun = runs.find((run) => run.import_run_id === filters.run_id) ?? runs[0];
  const proposal = reviewState.proposal;
  const modeCopy = result ? MODE_COPY[result.answer_mode] : null;
  const isPending = job && ["queued", "running"].includes(job.state);
  const proposalBlocksSelection = ["proposal_pending", "approved"].includes(reviewState.phase);

  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand" href="#ask" aria-label="DM Assistant home">
          <ArchiveMark />
          <span><strong>DM Assistant</strong><small>Campaign librarian</small></span>
        </a>
        <nav aria-label="Primary navigation">
          <a href="#ask">Ask</a>
          <a className="active" href="#review">Review</a>
          <a href="#operations">Operations</a>
        </nav>
        <div className="identity"><span>DM</span><b>Private archive</b></div>
      </header>

      <main>
        <section className="hero" id="ask">
          <p className="kicker">Starfall campaign records</p>
          <h1>Ask the archive.<br /><i>Keep the evidence.</i></h1>
          <p className="intro">Grounded answers only—every result carries its source, authority, and truth state.</p>
          <form className="ask-box" onSubmit={ask}>
            <label htmlFor="campaign-question">Campaign question</label>
            <div className="ask-row">
              <SearchIcon />
              <textarea id="campaign-question" value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="What do the records establish about…" rows={2} />
              <button disabled={!question.trim() || queryState === "loading"} type="submit">{queryState === "loading" ? "Searching…" : "Search records"}</button>
            </div>
            <div className="ask-meta"><span>Visibility</span><b>Dungeon Master</b><span className="dot" />No creative inference</div>
          </form>
        </section>

        <section aria-live="polite" className="result-region">
          {queryState === "error" && <div className="notice error"><b>Campaign Core is unavailable.</b><span>{queryError}</span></div>}
          {!result && queryState !== "error" && <div className="empty-state"><div className="empty-glyph"><SearchIcon /></div><div><b>Your evidence will appear here</b><span>Ask a question to inspect canonical records and cited context.</span></div></div>}
          {result && modeCopy && <article className={`answer-card mode-${result.answer_mode}`}><header><div><p>{modeCopy.eyebrow}</p><h2>{modeCopy.title}</h2></div><span>{result.evidence.length} evidence item{result.evidence.length === 1 ? "" : "s"}</span></header>{result.evidence.length === 0 ? <p className="no-evidence">No visible authoritative record supports an answer. Nothing was invented.</p> : <div className="evidence-list">{result.evidence.map((item) => <div className="evidence" key={item.record_id}><span className={`role role-${item.role}`}>{item.role}</span><p>{item.assertion}</p><dl><div><dt>Authority</dt><dd>{display(item.authority)}</dd></div><div><dt>State</dt><dd>{item.state}</dd></div></dl><cite>{item.citation}</cite></div>)}</div>}<footer>{result.reasons.map(display).join(" · ")}</footer></article>}
        </section>

        <section className="review-workspace" id="review">
          <div className="section-heading review-heading">
            <div><p className="kicker">Human review boundary</p><h2>Import evidence</h2></div>
            <p>One candidate, one visible version, one exact confirmation.</p>
          </div>

          {activeRun && <div className="run-summary" aria-label="Import run summary"><div><span>Imported</span><b>{activeRun.admitted_file_count}</b></div><div><span>Candidates</span><b>{activeRun.candidate_count}</b></div><div><span>Reviews</span><b>{activeRun.review_count}</b></div><div><span>Queue result</span><b>{queueTotal}</b></div><p><strong>{activeRun.root_identifier}</strong><span>{new Date(activeRun.snapshot_at).toLocaleString()}</span></p></div>}

          <form className="review-filters" onSubmit={(event) => { event.preventDefault(); void loadReviewWorkspace(filters); }}>
            <label>Import run<select aria-label="Import run" value={filters.run_id ?? ""} onChange={(event) => setFilters({ ...filters, run_id: event.target.value || undefined })}><option value="">All runs</option>{runs.map((run) => <option key={run.import_run_id} value={run.import_run_id}>{run.root_identifier}</option>)}</select></label>
            <label>Review status<select aria-label="Review status" value={filters.review_status ?? ""} onChange={(event) => setFilters({ ...filters, review_status: event.target.value || undefined })}><option value="">Any status</option><option value="pending">Pending</option><option value="proposed">Proposed</option><option value="deferred">Deferred</option><option value="rejected">Rejected</option><option value="applied">Applied</option></select></label>
            <label>Authority<select aria-label="Authority filter" value={filters.authority ?? ""} onChange={(event) => setFilters({ ...filters, authority: event.target.value || undefined })}><option value="">Any authority</option><option value="explicit_lore">Explicit lore</option><option value="real_play">Real play</option><option value="npc_intention">NPC intention</option><option value="preparation">Preparation</option><option value="brainstorm">Brainstorm</option></select></label>
            <label>Source<input aria-label="Source filter" value={filters.source ?? ""} onChange={(event) => setFilters({ ...filters, source: event.target.value || undefined })} placeholder="Path contains…" /></label>
            <button className="secondary-button" type="submit">Apply filters</button>
          </form>

          {reviewError && <div className="notice error"><b>Review unavailable.</b><span>{reviewError}</span></div>}
          <div className="review-grid">
            <aside className="candidate-queue" aria-label="Candidate review queue">
              <header><span>Candidate queue</span><b>{reviewLoading ? "Loading…" : `${candidates.length} shown`}</b></header>
              {candidates.map((candidate) => <button className={candidate.candidate_id === selected?.candidate_id ? "selected" : ""} disabled={reviewBusy || proposalBlocksSelection} key={candidate.candidate_id} onClick={() => void chooseCandidate(candidate.candidate_id)} type="button"><span>{display(candidate.authority)} · {display(candidate.state)}</span><b>{candidate.assertion_text}</b><small>{display(candidate.review_status)}</small></button>)}
              {!reviewLoading && candidates.length === 0 && <p className="queue-empty">No candidates match these filters.</p>}
              <section className="source-review-queue" aria-label="Source review items">
                <header><span>Source reviews</span><b>{sourceReviews.length} open · {quarantineCount} quarantined</b></header>
                {sourceReviews.slice(0, 20).map((review) => <article key={review.review_id}><span>{display(review.kind)} · {display(review.classification ?? "unclassified")}</span><b>{review.source_path ?? review.subject_id}</b><p>{reviewSummary(review)}</p></article>)}
                {sourceReviews.length > 20 && <p className="queue-overflow">Showing the first 20 source reviews after quarantined material.</p>}
              </section>
            </aside>

            <div className="candidate-detail">
              {!selected ? <div className="detail-empty">Select a candidate to inspect exact evidence.</div> : <>
                <header className="candidate-title"><div><span className={`status-pill status-${selected.review_status}`}>{display(selected.review_status)}</span><h3>{selected.assertion_text}</h3></div><dl><div><dt>State</dt><dd>{display(selected.state)}</dd></div><div><dt>Authority</dt><dd>{display(selected.authority)}</dd></div><div><dt>Visibility</dt><dd>{display(selected.visibility)}</dd></div></dl></header>
                {selected.evidence.map((evidence) => <article className="source-evidence" key={evidence.source_revision_id}><div><span>Exact source evidence</span><b>{evidence.source_path}</b></div><blockquote>{evidence.excerpt}</blockquote><dl><div><dt>Section</dt><dd>{evidence.section}</dd></div><div><dt>Classification</dt><dd>{display(evidence.classification)}</dd></div><div><dt>Offsets</dt><dd>{evidence.start_offset}–{evidence.end_offset}</dd></div><div><dt>Revision</dt><dd title={evidence.content_hash}>{evidence.content_hash.slice(0, 12)}</dd></div></dl></article>)}
                <div className="diagnostics"><h4>Warnings and conflicts</h4>{selectedReviews.length === 0 ? <p>No source-level diagnostics are open for this candidate.</p> : selectedReviews.map((review) => <div key={review.review_id}><span>{display(review.kind)}</span><p>{reviewSummary(review)}</p></div>)}</div>

                {!proposal && !["rejected", "deferred", "applied"].includes(reviewState.phase) && <div className="candidate-actions"><div><label htmlFor="disposition-reason">Disposition reason</label><input id="disposition-reason" value={dispositionReason} onChange={(event) => setDispositionReason(event.target.value)} placeholder="Required audit reason" /></div><button className="text-button" disabled={!dispositionReason.trim() || reviewBusy} onClick={() => void disposition("deferred")} type="button">Defer</button><button className="danger-button" disabled={!dispositionReason.trim() || reviewBusy} onClick={() => void disposition("rejected")} type="button">Reject</button></div>}

                {!proposal && selected.review_status === "pending" && <form className="resolution-form" onSubmit={createProposal}><header><span>Explicit target resolution</span><p>Campaign Core will copy the source assertion; you provide identity and structure.</p></header><fieldset><legend>Subject identity</legend><label><input checked={resolution === "new"} name="resolution" onChange={() => setResolution("new")} type="radio" />Create a new entity</label><label><input checked={resolution === "existing"} name="resolution" onChange={() => setResolution("existing")} type="radio" />Use an existing entity ID</label></fieldset>{resolution === "new" ? <div className="form-grid"><label>Canonical name<input aria-label="Canonical name" required value={entityName} onChange={(event) => setEntityName(event.target.value)} /></label><label>Entity type<input aria-label="Entity type" required value={entityType} onChange={(event) => setEntityType(event.target.value)} /></label></div> : <label>Existing entity ID<input aria-label="Existing entity ID" pattern="[0-9a-fA-F-]{36}" required value={subjectId} onChange={(event) => setSubjectId(event.target.value)} /></label>}<label>Claim predicate<input aria-label="Claim predicate" required value={predicate} onChange={(event) => setPredicate(event.target.value)} placeholder="Explicit structured predicate" /></label>{selected.state === "observed" && <label>Observed at<input aria-label="Observed at" required type="datetime-local" value={observedAt} onChange={(event) => setObservedAt(event.target.value)} /></label>}<button disabled={reviewBusy || !predicate.trim() || (resolution === "new" ? !entityName.trim() || !entityType.trim() : !subjectId.trim())} type="submit">Create exact proposal</button></form>}

                {proposal && <ProposalReview proposal={proposal} selectedItemIds={selectedItemIds} setSelectedItemIds={setSelectedItemIds} />}
                {proposal && !proposalValidated && <div className="notice"><b>Revalidating displayed version.</b><span>Approval and application remain locked until Campaign Core confirms the immutable version.</span></div>}
                {proposal && reviewState.phase === "proposal_pending" && <div className="confirmation-panel" role="region" aria-label="Pending proposal confirmation"><div><span>Visible pending action</span><b>Approve selected items from version {proposal.version_number}</b><code>{proposal.content_hash}</code></div><label>Type APPROVE<input aria-label="Exact approval confirmation" autoComplete="off" value={confirmation} onChange={(event) => setConfirmation(event.target.value)} /></label><button disabled={!proposalValidated || confirmation !== "APPROVE" || selectedItemIds.length === 0 || reviewBusy} onClick={() => void approveProposal()} type="button">Approve {selectedItemIds.length} exact item{selectedItemIds.length === 1 ? "" : "s"}</button></div>}
                {reviewState.phase === "approved" && <div className="apply-panel"><div><span>Approval recorded</span><b>{reviewState.approval?.approval_id}</b><p>Only the displayed version and selected scope can be applied.</p></div><button disabled={!proposalValidated || reviewBusy} onClick={() => void applyApproval()} type="button">Apply approved change</button></div>}
                <div className={`review-outcome outcome-${reviewState.phase}`} role="status"><b>{phaseLabel(reviewState)}</b>{reviewState.message && <span>{reviewState.message}</span>}{reviewState.receipt && <dl><div><dt>Receipt</dt><dd>{reviewState.receipt.receipt_id}</dd></div><div><dt>Outcome</dt><dd>{reviewState.receipt.outcome}</dd></div><div><dt>Applied items</dt><dd>{reviewState.receipt.applied_item_ids.length}</dd></div></dl>}</div>
              </>}
            </div>
          </div>
        </section>

        <section className="operations" id="operations"><div className="section-heading"><div><p className="kicker">Infrastructure</p><h2>Operations</h2></div><p>Background work remains visible and recoverable after refresh.</p></div><article className="operation-card"><div className="operation-icon"><PulseIcon /></div><div className="operation-copy"><span>Campaign Core</span><h3>Service health check</h3><p>Runs through the isolated Windmill job adapter. No campaign database credential crosses this boundary.</p>{job && <div className={`job-status status-${job.state}`} role="status"><div><b>{JOB_COPY[job.state]}</b><span>{job.jobId.slice(0, 12)}</span></div><div className="progress-track"><span style={{ width: `${job.progress}%` }} /></div>{job.error && <p>{job.error}</p>}</div>}{jobActionError && <p className="inline-error">Status unavailable: {jobActionError}</p>}</div><button className="secondary-button" disabled={Boolean(isPending)} onClick={startHealthCheck} type="button">{isPending ? "Checking…" : job?.state === "failed" ? "Retry check" : "Run check"}</button></article></section>
      </main>
      <footer className="page-footer"><span>Private development workspace</span><span>Sources remain authoritative</span></footer>
    </div>
  );
}

interface ProposalReviewProps {
  proposal: CandidateProposalVersion;
  selectedItemIds: string[];
  setSelectedItemIds: (itemIds: string[]) => void;
}

function ProposalReview({ proposal, selectedItemIds, setSelectedItemIds }: ProposalReviewProps) {
  return <article className="proposal-review"><header><div><span>Immutable proposal</span><h4>Version {proposal.version_number}</h4></div><code title={proposal.content_hash}>{proposal.content_hash}</code></header><div className="proposal-items">{proposal.items.map((item) => { const checked = selectedItemIds.includes(item.item_id); return <label key={item.item_id}><input checked={checked} onChange={() => setSelectedItemIds(checked ? selectedItemIds.filter((id) => id !== item.item_id) : [...selectedItemIds, item.item_id])} type="checkbox" /><div><span>Item {item.sequence} · {display(item.mutation_kind)}</span><b>{String(item.after.canonical_name ?? item.after.assertion_text ?? item.target_id)}</b><dl><ProposalField label="Target" value={item.target_type} />{item.mutation_kind === "create_entity" ? <ProposalField label="Entity type" value={item.after.entity_type} /> : <><ProposalField label="Predicate" value={item.after.predicate} /><ProposalField label="Resulting state" value={item.after.state} /><ProposalField label="Authority" value={item.after.authority} /><ProposalField label="Visibility" value={item.after.visibility} /><ProposalField label="Subject ID" value={item.after.subject_entity_id} /><ProposalField label="Object ID" value={item.after.object_entity_id} /><ProposalField label="Confidence" value={item.after.confidence} /><ProposalField label="Conditional" value={item.after.is_conditional} /><ProposalField label="Predicts subject action" value={item.after.predicts_subject_action} /><ProposalField label="Recorded at" value={item.after.recorded_at} /><ProposalField label="Observed at" value={item.after.observed_at} /></>}<ProposalField label="Target ID" value={item.target_id} /></dl></div></label>; })}</div><footer>Approval applies only to checked item IDs in this displayed version. Unchecked siblings remain unapplied.</footer></article>;
}

function ProposalField({ label, value }: { label: string; value: unknown }) {
  if (value === undefined || value === null || value === "") return null;
  const rendered = typeof value === "boolean" ? (value ? "yes" : "no") : String(value);
  return <div><dt>{label}</dt><dd>{rendered}</dd></div>;
}

export default App;
