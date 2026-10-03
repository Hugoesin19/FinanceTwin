# Finance Twin Engine

Librería Python independiente del motor financiero determinista.

- Spec: `docs/MOTOR_FINANCIERO.md`
- Plan: `docs/PLAN_IMPLEMENTACION.md` (fase activa)
- Versión: `0.1.0` (`financetwin_engine.ENGINE_VERSION`)

Sin dependencias de API, web ni base de datos.

## Requisitos

- Python ≥ 3.11
- pytest (desarrollo)

## Instalación (local, €0)

Desde esta carpeta `engine/`:

```bash
python -m venv .venv
```

Windows (PowerShell):

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

Linux / macOS:

```bash
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

## Tests

```bash
pytest
```

Smoke F0:

```bash
pytest tests/unit/test_version.py -q
```

Import:

```python
from financetwin_engine import __version__
```

## Estructura

```
engine/
├── financetwin_engine/
│   ├── model/
│   ├── calc/
│   ├── analytics/
│   ├── policies/
│   ├── trace/
│   └── version.py
└── tests/
    ├── unit/
    ├── golden/
    └── invariants/
```
