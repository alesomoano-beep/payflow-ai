# PayFlow AI — project context

## Goal
Learning project to prepare a senior backend + AI profile.
Full roadmap tracked in Claude.ai (saved conversation).

## Current phase
Phase 3 — AI agents with LangGraph, MCP protocol, A2A

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

## Phase 1 — decisions & lessons learned

### Domain models (schemas/domain.py)
- `Decimal` en lugar de `float` para evitar errores de precisión en importes monetarios
- `StrEnum` para enums serializable directamente a JSON sin conversión extra
- `frozen=True` en `TransactionResult` para inmutabilidad — los resultados no se modifican una vez creados
- `model_validator` para validaciones cross-field (ej. límite especial de AMEX)
- `BatchResult.approval_rate` como `@property` — dato derivado, no almacenado

### API layer
- `src/` layout con `pip install -e ".[dev]"` — imports limpios sin hacks de `sys.path`
- `lifespan` con `asynccontextmanager` para startup/shutdown limpio (en lugar del deprecado `on_event`)
- `_handle_bank_errors` como context manager síncrono en router — centraliza la conversión de excepciones a HTTP codes en un solo lugar
- Batch limitado a 50 en el router (422 si se supera o está vacío) — validación en la capa HTTP, no en service

### Async
- `asyncio.gather` para paralelizar el batch — N transacciones en ~tiempo de 1
- `asyncio.Semaphore` en `process_batch_with_limit` para rate limiting configurable
- `BankClient` como async context manager — garantiza que `httpx.AsyncClient` se cierra siempre

## Phase 2 — decisions & lessons learned

### Testing patterns
- `pytest-asyncio` con `asyncio_mode = "auto"` — no hace falta `@pytest.mark.asyncio` en cada test (aunque se dejó por claridad)
- `AsyncMock` para mockear coroutines; `MagicMock` para objetos síncronos
- `patch.object(bank._client, "post", ...)` dentro del `async with` del context manager para no abrir conexiones reales
- `nonlocal` + función captura para inspeccionar el payload que se enviaría al banco (test `test_amount_converted_to_cents`)
- Fixtures en `conftest.py` compartidas entre todos los módulos de test

### CI/CD
- GitHub Actions en `.github/workflows/ci.yml`: ruff → mypy → pytest --cov (umbral 82%)
- Pre-commit hooks: `ruff --fix`, `ruff-format`, `mypy`
- **Lección clave**: pin la versión de ruff en `.pre-commit-config.yaml` y `pyproject.toml` a la misma (`>=0.15.0` / `v0.15.11`) para que el hook local y el CI apliquen las mismas reglas; discrepancias de versión causan que el hook revierta lo que el CI exige

### Coverage alcanzada
- Total: 94% (por encima del umbral de 82%)
- `main.py` 84% — líneas de startup/shutdown difíciles de testear sin servidor real (se deja para fase 4)
- `service.py` 81% — `process_batch_with_limit` (semaphore) y ramas de error cubiertos en fase 3

## Phase 3 — decisions & lessons learned

### LLM providers (llm/)
- `LLMProvider` como Protocol en `base.py` — permite intercambiar providers sin cambiar el agente
- Tres providers implementados: `AnthropicProvider`, `GeminiProvider`, `HuggingFaceProvider`
- **HuggingFaceProvider como default** (`Qwen/Qwen2.5-72B-Instruct`) — gratuito vía HF Inference API, suficiente para desarrollo
- `complete_structured` recibe un `response_model: type[BaseModel]` e inyecta el JSON schema en el system prompt — structured output sin depender de function calling

### Validator agent (agents/validator.py)
- Arquitectura híbrida: reglas deterministas (`run_rules`) + análisis LLM (`run_llm_analysis`) + decisión final (`combine_results`)
- Reglas deterministas primero — rápidas, auditables, sin coste de API
- LRU cache (`cachetools`) keyed por sha256 del payload + versión de prompt — evita llamadas LLM duplicadas
- `SYSTEM_PROMPT_VERSION` en la cache key — invalidación automática al cambiar el prompt
- Fallback a `approved=False` si el LLM falla — fail-safe conservador para pagos
- Provider inyectable en `run_validator(provider=...)` — facilita tests sin API real

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
