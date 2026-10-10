# Agentic Software Engineering System — URL Shortener

A runnable prototype demonstrating how an agentic software engineering system can coordinate the software development lifecycle (SDLC), from requirements analysis and architecture planning to security review, human approval, implementation, and testing.

The project combines a FastAPI URL-shortener application with a stateful workflow orchestrator, configurable mock and Gemini providers, approval gates, policy enforcement, failure handling, audit events, and engineering reports.

> **Implementation boundary:** Gemini can support requirements analysis, architecture recommendations, security review, and implementation proposals. The Gemini implementation path separates proposal generation from patch application and requires human approval before applying an allowed patch. The mock provider uses deterministic agents. Test-agent behavior and brownfield repository analysis have prototype limitations described below.

## Capabilities

- **URL-shortener API:** Create short URLs, redirect, track analytics, delete URLs, enforce expiration, and check service health.
- **Workflow orchestration:** Represent SDLC activities as a dependency graph with dependency validation and cycle detection.
- **Parallel execution:** Schedule independent ready tasks concurrently.
- **State and context:** Maintain workflow status, task results, artifacts, retry counts, approvals, and audit events.
- **Human-in-the-loop governance:** Pause before critical implementation actions and handle approval or rejection.
- **Gemini implementation workflow:** Generate a reviewable patch proposal, validate the proposed changes, require approval, and apply allowed changes with backup and rollback handling.
- **Failure handling:** Classify failures, retry eligible transient failures within configured bounds, and stop execution for policy violations.
- **Recovery and replanning:** Support checkpoints, state restoration, and invalidation of affected downstream tasks.
- **Observability:** Generate JSON engineering reports containing workflow results, artifacts, approvals, audit events, and available metrics.
- **Multiple scenarios:** Support greenfield, brownfield, and ambiguous-requirements workflows.
- **Provider flexibility:** Run deterministic mock workflows without live model calls or use Gemini-backed analysis when configured.

See [docs/architecture.md](docs/architecture.md) for component diagrams, control flow, design decisions, and limitations.

## Architecture

The system has two main parts:

1. **URL-shortener application:** FastAPI, Pydantic, SQLite, and service/repository layers.
2. **SDLC orchestrator:** Workflow graph, state management, agent registry, approval manager, policy guard, retry/failure handling, checkpoints, replanning, metrics, and reporting.

The orchestrator schedules tasks only when their dependencies are complete. Independent ready tasks can execute concurrently. Critical implementation tasks can pause the workflow for human approval.

### Greenfield workflow

Requirements analysis is followed by architecture and risk analysis. Security review precedes implementation.

**Gemini provider:**

`Requirements → Architecture and Risk Analysis → Security Review → Implementation Proposal → Human Approval → Patch Application → Tests`

Architecture and risk analysis can run in parallel when their dependencies are satisfied.

**Mock provider:**

`Requirements → Architecture and Risk Analysis → Security Review → Human Approval → Mock Implementation → Mock Tests`

The mock path is intended for reproducible demonstrations and offline testing.

### Additional scenarios

- **Brownfield:** Models codebase analysis, impact analysis, security review, implementation, and regression testing.
- **Ambiguous requirements:** Models requirements analysis, ambiguity analysis, security review, implementation, and testing.

The scenario definitions describe the intended workflow stages. Brownfield repository inspection and fully automated ambiguity-driven replanning are not yet end-to-end automated capabilities.

## Prerequisites

- Python 3.11 or later.
- Google AI Studio API key for Gemini mode: https://aistudio.google.com/apikey

## Setup (Windows PowerShell)

Run from the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Copy `.env.example` to `.env`.

For offline mock mode:

```dotenv
LLM_PROVIDER=mock
GEMINI_API_KEY=
GEMINI_MODEL=gemini-3.5-flash-lite
GEMINI_TIMEOUT_SECONDS=30
GEMINI_MAX_RETRIES=2
GEMINI_MAX_OUTPUT_TOKENS=1500
```

For Gemini mode, set `LLM_PROVIDER=gemini` and supply your actual `GEMINI_API_KEY`. Never commit `.env` or expose the API key. Model availability, API access, and quota limits may affect live Gemini runs.

## Run the URL-shortener API

```powershell
python -m uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/docs for the interactive API documentation and exact request/response schemas.

Routes are defined in `app/api/routes.py`; business logic and persistence are implemented in the application service and repository layers.

## Run SDLC scenarios

### Mock provider

```powershell
python -m app.cli --scenario greenfield --provider mock
python -m app.cli --scenario brownfield --provider mock
python -m app.cli --scenario ambiguous --provider mock
```

Mock mode provides deterministic behavior without requiring a live Gemini API call.

### Gemini provider

Configure `.env` first, then run:

```powershell
python -m app.cli --scenario greenfield --provider gemini
python -m app.cli --scenario brownfield --provider gemini
python -m app.cli --scenario ambiguous --provider gemini
```

Follow the CLI approval prompt. Approving permits the implementation-apply task to proceed through its validation and patch-application logic. Rejecting the request blocks implementation and records the rejection in workflow state and reporting.

Gemini availability and quota can affect these commands. Use mock mode for repeatable demonstrations and automated tests.

## Implementation proposal and approval

The Gemini implementation workflow separates proposing changes from applying them.

1. The proposal agent produces a structured patch proposal.
2. The proposal is saved under `artifacts/proposals/`.
3. The CLI presents the proposed patch for human review.
4. The approval manager records the decision.
5. If approved, the apply agent validates the workflow identifier, allowed target files, original source contents, and expected match counts.
6. Backups are created before patch application.
7. Application failures trigger rollback handling and audit events.

The allowlist and validation checks reduce the risk of unintended modifications. They are not a substitute for code review, isolated execution, or comprehensive security controls.

## Tests

Run the full suite:

```powershell
python -m pytest -q
```

Run focused suites:

```powershell
python -m pytest tests/test_workflow_builder.py -q
python -m pytest tests/test_llm_client.py -q
python -m pytest tests/test_implementation_apply_agent.py -q
```

**Development test baseline:** 71 tests passed in the latest reported run. Re-run the suite after the final README and code changes to verify the final result. Automated tests should not require live Gemini API calls.

## Governance and observability

- Dependency checks determine task eligibility.
- Policy checks run before task execution.
- Critical implementation tasks require human approval.
- Approval rejection blocks the implementation task.
- Eligible transient failures are retried within configured limits.
- Policy violations trigger safe-stop behavior rather than transient retries.
- Checkpoints capture workflow state for supported restoration operations.
- Replanning can invalidate affected downstream task results.
- Audit events record workflow decisions and execution events where implemented.
- Engineering reports include status, artifacts, approvals, audit events, risks or limitations, and available metrics.
- Metrics cover workflow status and duration, along with retry, rollback, replan, and task-failure counters where recorded.

These are prototype orchestration capabilities, not a production-grade distributed workflow or observability platform.

## Reports and generated artifacts

CLI workflows write JSON engineering reports under `artifacts/`, using the workflow identifier in the filename.

Implementation proposals and backups are stored in their respective artifact directories. Review these outputs when demonstrating the proposal, approval, application, and rollback lifecycle.

Do not include API keys or sensitive repository information in generated reports. Generated reports, databases, and local configuration should not be committed unless explicitly required by the assignment.

## Security considerations

- Keep API keys in local environment configuration and exclude `.env` from version control.
- Validate URL inputs and use parameterized database operations.
- Treat model-generated content as untrusted input.
- Validate structured proposals and restrict patch targets before application.
- Require human approval before applying critical implementation changes.
- Treat model-generated security reviews as advisory, not as replacements for static analysis, dependency scanning, penetration testing, or human review.
- Do not run this prototype as a hardened public production service.

## Limitations and trade-offs

1. Mock implementation and test agents provide deterministic demonstration behavior rather than a complete autonomous implementation-and-test loop.
2. Gemini implementation proposals are constrained by the apply agent's validation rules and allowed target files.
3. The prototype does not provide a fully isolated sandbox for applying model-generated changes.
4. Brownfield analysis models workflow stages but does not automatically ingest and analyze the complete repository.
5. Security review is based on supplied context and is not comprehensive source-code security scanning.
6. Concurrent task execution and failure paths require further stress testing before production use.
7. Metrics are workflow-level counters rather than full production telemetry.
8. SQLite and the local development server are demonstration choices, not a production deployment architecture.
9. Live Gemini runs depend on model availability, network access, rate limits, and API quota.

## Suggested demonstration

1. Run `python -m pytest -q` and show the passing result.
2. Run the greenfield mock scenario to demonstrate deterministic execution.
3. Run the Gemini greenfield scenario to show analysis and proposal generation.
4. Show the proposed patch and explain the human approval gate.
5. Demonstrate approval rejection and explain why implementation is blocked.
6. Inspect the JSON engineering report, audit events, and metrics.
7. Run the implementation rollback test.
8. Explain parallel scheduling, retry behavior, policy guardrails, checkpoints, and replanning.
9. Demonstrate brownfield and ambiguous scenarios while clearly explaining their current limitations.