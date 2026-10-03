# ADR 0001 — Préstamo ya dispuesto antes del ancla

Fecha: 2026-10-03  
Estado: accepted

## Contexto

`MODELO` §11.2 convierte `disbursement_year_month` → `disbursement_t`.  
Si el préstamo se dispuso **antes** del `anchor` (`disbursement_t < 0`), el principal ya está en caja histórica (`opening_cash`).

El motor (`MOTOR` §7.5.1) hace `loan_drawdowns += principal` en `disbursement_t`.  
Si el mapper clampéa a `disbursement_t = 0` sin más, **se dobla la caja**.

La spec no define el run-off completo de deuda viva (fuera de alcance fino MVP).

## Decisión

1. Campo adapter en `Loan` del motor: `skip_drawdown: bool = False`.
2. Mapper: si `months_between(anchor, disbursement) < 0`, mapear con `disbursement_t = 0`, `skip_drawdown = True` (principal vivo desde t=0 **sin** entrada de caja).
3. `build_loan_schedule`: si `skip_drawdown`, inicializa outstanding sin `drawdown`.

## Alternativas

- Excluir el préstamo → subestima servicio de deuda.
- Run-off completo de cuadro residual → diferido (ADR futuro / bump motor).

## Consecuencias

- Specs a actualizar: nota en MOTOR §4.1 Loan (campo adapter) en próximo bump menor.
- Tests: préstamo pre-ancla no aumenta `loan_drawdowns` en t=0.
