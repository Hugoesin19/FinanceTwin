# Finance Twin API (F5)

API mínima local sobre SQLite. Spec: `docs/API.md`.

## Setup

Desde el repo, con el engine instalado:

```powershell
cd api
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ../engine
python -m pip install -e ".[dev]"
```

## Run

```powershell
$env:FINANCETWIN_DB = ".\data\financetwin.sqlite"
uvicorn financetwin_api.main:app --reload --port 8000
```

UI (F6): abrir http://127.0.0.1:8000/

## Tests

```powershell
pytest -q
```
