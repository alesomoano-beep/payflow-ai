# PayFlow AI

A real Python backend that processes payments, detects fraud using AI agents (LangGraph), deploys on AWS Lambda, and has over 90% test coverage.

## Requirements

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) or pip

## Installation

```bash
# Clone the repo
git clone https://github.com/your-username/payflow-ai.git
cd payflow-ai

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Linux / macOS
.venv\Scripts\activate           # Windows

# Install the project and its dependencies
pip install -e ".[dev]"
```

## Running the server

```bash
uvicorn payflow.main:app --reload
```

The API will be available at `http://localhost:8000`.

Interactive docs (Swagger UI): `http://localhost:8000/docs`

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/payments/authorize` | Authorize a single transaction |
| `POST` | `/payments/batch` | Process up to 50 transactions in parallel |
| `GET` | `/payments/transaction/{id}` | Get transaction by ID *(coming in phase 3)* |

### Example: authorize a transaction

```bash
curl -X POST http://localhost:8000/payments/authorize \
  -H "Content-Type: application/json" \
  -d '{
    "amount": "150.75",
    "currency": "EUR",
    "card": {
      "number_last4": "4242",
      "network": "VISA",
      "holder_name": "Jane Doe"
    },
    "merchant_id": "merchant_001"
  }'
```

## Running tests

```bash
pytest
pytest --cov=payflow --cov-report=term-missing   # with coverage (94% current)
```

## CI/CD

GitHub Actions runs on every push to `main`/`develop`:
1. `ruff check` — linting
2. `mypy` — type checking
3. `pytest --cov` — tests with 82% coverage threshold

Pre-commit hooks enforce the same checks locally before every commit.

## Linting and type checking

```bash
ruff check src/       # linter
ruff format src/      # formatter
mypy src/             # type checker
```

## Project structure

```
payflow-ai/
├── src/
│   ├── payflow/
│   │   ├── schemas/
│   │   │   ├── domain.py       # Domain models: enums, TransactionRequest/Result, BatchResult
│   │   │   └── bank.py         # Bank API contract models
│   │   ├── agents/
│   │   │   ├── validator.py    # Payment validation agent (rules + LLM)
│   │   │   ├── fraud.py        # Fraud detection agent
│   │   │   ├── risk.py         # Risk scoring agent
│   │   │   └── orchestrator.py # LangGraph orchestration
│   │   ├── llm/
│   │   │   ├── base.py         # LLMProvider protocol + LLMProviderError
│   │   │   ├── anthropic.py    # Anthropic Claude provider
│   │   │   ├── gemini.py       # Google Gemini provider
│   │   │   └── huggingface.py  # HuggingFace Inference API provider (default)
│   │   ├── mcp/
│   │   │   └── server.py       # MCP server
│   │   ├── service.py          # Business logic, async batch processing
│   │   ├── client.py           # Async HTTP client (BankClient)
│   │   ├── router.py           # FastAPI endpoints
│   │   └── main.py             # App entrypoint and lifespan
│   └── tests/
│       ├── conftest.py
│       ├── test_models.py
│       ├── test_service.py
│       ├── test_router.py
│       └── test_client.py
├── CLAUDE.md
└── pyproject.toml
```

## Roadmap

| Phase | Focus | Status |
|-------|-------|--------|
| 1 | Modern Python: Pydantic v2, asyncio, FastAPI | Done |
| 2 | pytest, mocking, GitHub Actions CI/CD | Done |
| 3 | AI agents with LangGraph, MCP protocol, A2A | In progress |
| 4 | AWS Lambda, API Gateway, CDK deployment | Pending |
| 5 | Observability, ADR documentation, portfolio | Pending |
