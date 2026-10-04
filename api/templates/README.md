# Plantilla CSV — CompanyTwinSnapshot (P5)

Importa un gemelo mínimo sin rellenar el formulario a mano.

## Archivo

- Plantilla: [`twin_snapshot_template.csv`](twin_snapshot_template.csv)
- Fixture feliz: [`../fixtures/synthetic_twin_ok.csv`](../fixtures/synthetic_twin_ok.csv)
- Fixture inválida: [`../fixtures/synthetic_twin_bad.csv`](../fixtures/synthetic_twin_bad.csv)

Datos reales de clientes: **fuera de git** (R7).

## Formato

1. UTF-8 (BOM permitido).
2. Separador `,`.
3. Secciones con cabecera `# SECTION <nombre>`.
4. Tras cada sección: fila de columnas + filas de datos (como un CSV normal).
5. Campos vacíos = omitidos / `null` según el schema.

`schema_version` se fija a `1.0` en el parser (no va en el CSV).

## Secciones

| Sección | Obligatoria | Filas | Notas |
|---|---|---|---|
| `company` | sí | 1 | `currency` MVP = `EUR` |
| `fiscal` | sí | 1 | tasas como string decimal (`0`, `0.21`) |
| `policies` | sí | 1 | al menos `min_cash` |
| `revenue_streams` | no | 0..N | ids únicos |
| `cost_items` | no | 0..N | `amount_monthly` o `pct_of_revenue` |
| `payroll` | no | 0..N | |
| `loans` | no | 0..N | si `grace_months>0` → `grace_type` capital\|total |

## API

```http
POST /companies/{company_id}/imports/twin-csv
Content-Type: multipart/form-data

file=<csv>
label=import-ui   (opcional)
```

Respuesta 200: `model_version_id`, `snapshot` validado.  
Errores de parseo/schema → `400` con `detail` (mensaje / lista de issues).

Descarga plantilla: `GET /templates/twin_snapshot_template.csv`

## UI

Decision Studio → sección **Import twin (CSV)** → elegir archivo → Importar.
