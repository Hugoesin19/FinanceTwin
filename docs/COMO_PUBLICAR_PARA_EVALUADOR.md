# Cómo publicar Finance Twin para que el evaluador solo abra una URL

Objetivo: el profesor **no** clona el repo ni arranca servidores. Solo recibe:

1. Una **URL HTTPS**
2. La **guía rápida** (`GUIA_RAPIDA_EVALUADOR.html` → PDF)
3. (Opcional) el **documento de demostración** (`DOCUMENTO_DEMOSTRACION.html` → PDF)

**Netlify / Vercel no sirven** para esta app: son para front estático o serverless; aquí hace falta un proceso FastAPI + SQLite (Docker).

---

## Opción recomendada (gratis): Render

Ya hay `Dockerfile` + `render.yaml`. El plan Free no pide tarjeta para el web service.

### Limitaciones del free (aceptables para demo)

- Tras ~15 min sin visitas el servicio **duerme**; la primera carga puede tardar **~30–60 s**.
- El disco **no es persistente**: al despertar/redeploy la BD se vacía. El evaluador usa **Cargar escenario demo** y listo.
- Tope ~750 horas/mes de instancia (suficiente si duerme cuando no se usa).

### 1. Cuenta

1. Entra en [https://render.com](https://render.com) y regístrate con **GitHub**.
2. Autoriza el acceso al repo `FinanceTwin` (o el que uses).

### 2. Desplegar con Blueprint

1. Dashboard → **New** → **Blueprint**.
2. Elige el repositorio y la rama `main`.
3. Render lee `render.yaml` y crea el web service `financetwin-demo` (plan Free).
4. Confirma **Apply**.

Alternativa manual (sin Blueprint):

1. **New** → **Web Service** → conecta el repo.
2. Runtime: **Docker** (detecta el `Dockerfile` de la raíz).
3. Instance type: **Free**.
4. Health check path: `/health`.
5. Env (opcional): `FINANCETWIN_DB=/data/financetwin.sqlite`.
6. **Create Web Service**.

### 3. URL final

Cuando el deploy esté en verde:

`https://financetwin-demo.onrender.com`

(Si el nombre está ocupado, Render añade un sufijo; copia la URL del dashboard.)

### 4. Antes de enviarla

1. Ábrela tú (espera el cold start si hace falta) y pulsa **Cargar escenario demo**.
2. En `docs/GUIA_RAPIDA_EVALUADOR.html` (y la copia en `api/.../static/`), pon la URL real.
3. Imprime / guarda PDF de la guía rápida (y del documento de demostración si quieres).
4. Envía por correo: **enlace + 1 o 2 PDF**.

### Nota de privacidad

La instancia es una demo compartida: quien tenga la URL puede crear empresas.
No subas datos personales reales. Para evaluación basta la demo.

---

## Alternativa de pago: Fly.io (`fly.toml`)

Si vuelves a tener crédito o aceptas pagar ~unos euros/mes, `fly deploy` sigue valiendo y el volumen SQLite **sí** persiste. Ver `fly.toml` + `Dockerfile`.

---

## Qué enviar al profesor (checklist)

- [ ] URL pública funcionando (demo carga; a veces el idle “despierta” lento la 1ª vez)
- [ ] PDF: **Guía rápida de uso**
- [ ] PDF: **Documento de demostración** (capacidades / qué resuelve)
- [ ] Una frase en el correo: *“Abrir el enlace → si tarda un minuto en cargar, esperar → Cargar escenario demo → seguir la guía rápida”*

No hace falta GitHub, Python ni Docker en su lado.
