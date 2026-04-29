# PayFlow AI — project context

## Goal
Learning project to prepare a senior backend + AI profile.
Full roadmap tracked in Claude.ai (saved conversation).

## Current phase
Phase 1 — Modern Python: Pydantic v2, asyncio, FastAPI

## Project structure
payflow-ai/
├── src/
│   └── payflow/
│       ├── __init__.py
│       ├── models.py       ✓ done
│       └── service.py      ✓ done
├── tests/                  (phase 2)
├── CLAUDE.md
└── pyproject.toml

## Technical decisions

### models.py
- Pydantic v2 with field_validator and model_validator
- Decimal (not float) for monetary amounts
- StrEnum for Currency, TransactionStatus, CardNetwork
- frozen=True on TransactionResult (immutability)

### service.py
- asyncio.gather to process transaction batches in parallel
- asyncio.Semaphore to limit concurrency under rate limiting
- _simulate_bank_decision prefixed with underscore (module-private)
- In phase 3, _simulate_bank_decision will be replaced by a LangGraph agent

## Phase 1 remaining
- client.py   — async HTTP client with httpx toward external bank
- router.py   — FastAPI endpoints
- main.py     — entrypoint, lifespan, app

## Upcoming phases
- Phase 2: pytest, mocking, GitHub Actions CI/CD
- Phase 3: AI agents with LangGraph, MCP protocol, A2A
- Phase 4: AWS Lambda, API Gateway, CDK deployment
- Phase 5: observability, ADR documentation, portfolio