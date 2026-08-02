# React Shell Validation

The campaign librarian raw app is validated at three boundaries.

## Component and adapter tests

From `windmill/f/dm_assistant/apps/library.raw_app`, run `npm ci`, `npm test`, and `npm run typecheck`. The tests cover grounded evidence and citations, DM requester visibility, Campaign Core failures, Windmill adapters, full review pagination, exact candidate evidence, quarantine visibility, explicit proposal construction, one versioned confirmation, scoped approval/application, durable receipts, reject/defer behavior, stale versions, apply failures, queue filters, pending-job restoration, and visible job-start failures.

## Workspace source policy

Run `python tests/validate_react_shell.py` from the repository root. It repeats the app tests and strict type check, builds the Windmill raw app, and rejects direct database access or Windmill calls outside the adapter boundary. `python tests/validate_repository.py` includes this gate.

## Disposable deployment smoke test

Deploy the scoped workspace to a disposable Windmill instance and confirm:

1. the app route returns successfully;
2. a health job runs through Windmill and reaches Campaign Core;
3. the `query_campaign` backend runnable can call Campaign Core through the worker's internal URL;
4. an unsupported question returns `insufficient_evidence` with no fabricated evidence; and
5. the review workspace shows Campaign Core's import totals, pending candidate queue, quarantined source-review count, and exact selected evidence;
6. read-only queue filters return the totals supplied by Campaign Core; and
7. a second workspace deployment has no changes.

Use the authenticated Windmill raw-app route `/apps_raw/get/f/dm_assistant/apps/library`; `/run/<workspace>/...` is interpreted as a job route after login. The app URL requires no Campaign Core query parameter. The browser calls the generated backend binding, and the backend runnable uses the internal `CAMPAIGN_CORE_URL`.

Do not exercise disposition, proposal, approval, or application controls against the preserved live import merely to satisfy a UI smoke test. The complete mutation path is covered with sanitized component fixtures; a deployed mutation test must use a disposable campaign database.
