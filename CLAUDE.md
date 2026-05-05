# PayFlow AI — project context

## Goal
Learning project to prepare a senior backend + AI profile.
Full roadmap tracked in Claude.ai (saved conversation).

## Current phase
Phase 2 — pytest, mocking, coverage

## Project structure
```
payflow-ai/
├── src/
│   ├── payflow/
│   │   ├── __init__.py
│   │   ├── schemas/
│   │   │   ├── domain.py       ✓ done  (models de dominio: enums, TransactionRequest, TransactionResult, BatchResult)
│   │   │   └── bank.py         ✓ done  (BankTransactionPayload, BankTransactionResponse)
│   │   ├── service.py          ✓ done
│   │   ├── client.py           ✓ done
│   │   ├── router.py           ✓ done
│   │   └── main.py             ✓ done
│   └── tests/
│       ├── conftest.py
│       ├── test_models.py      ✓ done
│       ├── test_service.py     ✓ done
│       ├── test_router.py      ✓ done
│       └── test_client.py      ✓ done
├── CLAUDE.md
└── pyproject.toml
```

## Technical decisions

### schemas/domain.py
- Pydantic v2 con `field_validator` y `model_validator`
- `Decimal` (no float) para importes monetarios
- `StrEnum` para `Currency`, `TransactionStatus`, `CardNetwork`
- `CardInfo` como modelo anidado dentro de `TransactionRequest`
- `frozen=True` en `TransactionResult` (inmutabilidad)
- `BatchResult` con `@property approval_rate`

### schemas/bank.py
- Modelos separados para el contrato con el banco externo
- `BankTransactionPayload`: convierte amount a cents (int), sin decimales
- `BankTransactionResponse`: incluye `raw_response: dict` para depuración

### service.py
- `asyncio.gather` para procesar lotes en paralelo
- `asyncio.Semaphore` en `process_batch_with_limit` para rate limiting
- `_simulate_bank_decision` prefijado con underscore (módulo-privado)
- En fase 3, `_simulate_bank_decision` será reemplazado por un agente LangGraph

### client.py
- `BankClient` como async context manager (`__aenter__` / `__aexit__`)
- Jerarquía de excepciones: `BankClientError` → `BankTimeoutError`, `BankNetworkError`, `BankResponseError`
- Convierte amount a cents al construir `BankTransactionPayload`

### router.py
- `_handle_bank_errors` como context manager síncrono para centralizar manejo de errores HTTP
- Batch limitado a 50 transacciones (422 si se supera o está vacío)
- `/transaction/{id}` es placeholder hasta fase 3

### main.py
- `lifespan` con `asynccontextmanager` para startup/shutdown
- CORS abierto (`allow_origins=["*"]`) — restringir en producción
- Logging estructurado con `%(asctime)s %(levelname)s %(name)s`

## Upcoming phases
- Phase 3: AI agents with LangGraph, MCP protocol, A2A
- Phase 4: AWS Lambda, API Gateway, CDK deployment
- Phase 5: observability, ADR documentation, portfolio
