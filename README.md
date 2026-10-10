# Agentic Software Engineering System — URL Shortener

A runnable prototype that transforms a software requirement into a reviewable engineering workflow. It combines a FastAPI URL-shortener service with a stateful SDLC orchestrator, human approval gates, audit events, workflow metrics, and optional Gemini-powered analysis.

> **Implementation boundary:** Gemini is used for requirements analysis, architecture recommendations, and design-level security review. Implementation and test agents are deterministic mocks; they do not generate or execute application code. The brownfield scenario currently models codebase/impact analysis but does not inspect repository files automatically.

## Capabilities

- URL creation, short-code redirects, analytics, deletion, and health endpoint using FastAPI and SQLite.
- Explicit workflow dependency graph and validation.
- Stateful task execution and cross-stage artifact passing.
- Human approval before the critical implementation task.
- Failure classification, bounded retries, policy guardrails, safe-stop, checkpoints, rollback, and downstream invalidation during replanning.
- Audit events and workflow metrics in JSON engineering reports.
- `greenfield`, `brownfield`, and `ambiguous` scenarios.
- Deterministic mock mode and Gemini-backed analysis mode.

See [docs/architecture.md](docs/architecture.md) for component diagrams, control flow, design decisions, and limitations.

## Prerequisites

- Python 3.11+
- Google AI Studio API key only for Gemini mode: https://aistudio.google.com/apikey

## Setup (Windows PowerShell)

Run from the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Copy `.env.example` to `.env`. For offline mode:

```dotenv
LLM_PROVIDER=mock
GEMINI_API_KEY=
GEMINI_MODEL=gemini-3.5-flash-lite
GEMINI_TIMEOUT_SECONDS=30
GEMINI_MAX_RETRIES=2
GEMINI_MAX_OUTPUT_TOKENS=1500
```

For Gemini mode, set `LLM_PROVIDER=gemini` and supply your actual `GEMINI_API_KEY`. Never commit `.env` or expose the key. The model must be available to your API key and quota.

## Run the URL shortener API

```powershell
python -m uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs` for the exact routes and schemas. Routes are defined in `app/api/routes.py`; operations include health check, URL creation, short-code redirect, analytics, and deletion.

## Run SDLC scenarios

Mock mode (reproducible, no Gemini calls):

```powershell
python -m app.cli --scenario greenfield --provider mock
python -m app.cli --scenario brownfield --provider mock
python -m app.cli --scenario ambiguous --provider mock
```

Gemini-backed analysis (configure `.env` first):

```powershell
python -m app.cli --scenario greenfield --provider gemini
python -m app.cli --scenario brownfield --provider gemini
python -m app.cli --scenario ambiguous --provider gemini
```

When prompted, enter `y` to approve the implementation task. Any other response rejects it. Gemini mode uses real LLM calls for requirements, architecture, and design-level security review; implementation and testing remain mocked.

## Tests

```powershell
python -m pytest -q
```

Focused suites:

```powershell
python -m pytest tests/test_workflow_builder.py -q
python -m pytest tests/test_llm_client.py -q
```

The latest result reported during development was **58 passing tests**. Re-run the suite on the final commit and update this statement if the result changes. Automated tests should not need a live Gemini API call.

## Governance and observability

- Dependencies gate task eligibility.
- Critical implementation requires explicit human approval.
- Transient errors can be retried within a configured bound; permanent and policy failures are handled separately.
- Policy violations should stop unsafe execution rather than be retried as transient errors.
- Checkpoints support state restoration; replanning invalidates affected downstream tasks.
- Audit events record workflow decisions and execution events where implemented.
- Reports include workflow status, artifacts, approvals, audit events, risks/limitations, and available metrics.
- Metrics include duration/status and retry, rollback, replan, and task-failure counters. These are prototype metrics, not production telemetry.

## Scenarios

| Scenario | Purpose | Current workflow focus |
|---|---|---|
| `greenfield` | New URL-shortener capability | Requirements → architecture → security review → approval → implementation placeholder → test placeholder |
| `brownfield` | Enhancement/refactor planning | Codebase-analysis placeholder → impact-analysis placeholder → security review → approval → implementation placeholder → regression-test placeholder |
| `ambiguous` | Surface assumptions and ambiguity | Requirements → ambiguity-analysis placeholder → security review → approval → implementation placeholder → test placeholder |

The executor can schedule independent ready tasks concurrently, but the current scenario definitions are mostly sequential. Brownfield repository inspection and automated ambiguity-driven replanning are future improvements, not completed capabilities.

## Reports

Each CLI workflow writes a JSON engineering report under `artifacts/`, named using the workflow ID. Inspect the report for task artifacts, approvals, audit events, and metrics. Avoid including API keys or sensitive repository information in generated reports.

## Security considerations

- Keep keys in local environment configuration; never commit `.env`.
- Use parameterized database queries and validate URL inputs.
- Treat model output as untrusted; parse and validate structured responses before downstream use.
- A model-generated security review is advisory, not a substitute for static analysis, dependency scanning, penetration testing, or human review.
- The prototype is not hardened for public production deployment.

## Limitations and trade-offs

1. The implementation agent returns a deterministic mock result; it does not modify source code.
2. The test agent returns a deterministic mock result; it does not execute tests on generated changes.
3. Brownfield task names represent codebase/impact analysis, but repository files are not ingested automatically.
4. Gemini security review is based on supplied requirement and architecture context, not source-code scanning.
5. Live Gemini runs depend on API access, model availability, rate limits, and quota. Use mock mode for offline and repeatable runs.
6. Metrics are workflow-level prototype counters, not a full SRE telemetry solution.
7. Local SQLite and the development server are demonstration choices, not a production deployment architecture.

## Suggested demo

1. Run `python -m pytest -q` and show the passing result.
2. Run greenfield in mock mode to demonstrate reproducibility.
3. Run greenfield in Gemini mode and show generated analysis artifacts.
4. Demonstrate the approval prompt and explain why implementation is gated.
5. Show the JSON report, audit events, and metrics.
6. Explain rollback/replanning tests and candidly state the mocked implementation/testing limitations.
7. Briefly show the brownfield and ambiguous scenarios and their current boundaries.