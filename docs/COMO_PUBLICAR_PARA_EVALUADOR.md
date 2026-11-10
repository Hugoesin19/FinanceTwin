# Cómo publicar Finance Twin para que el evaluador solo abra una URL

Objetivo: el profesor **no** clona el repo ni arranca servidores. Solo recibe:

1. Una **URL HTTPS**
2. La **guía rápida** (`GUIA_RAPIDA_EVALUADOR.html` → PDF)
3. (Opcional) el **documento de demostración** (`DOCUMENTO_DEMOSTRACION.html` → PDF)

---

## Opción recomendada: Fly.io (ya hay `Dockerfile` + `fly.toml`)

### 1. Instalar Fly CLI (Windows, PowerShell)

```powershell
iwr https://fly.io/install.ps1 -useb | iex
```

Cierra y abre la terminal. Comprueba:

```powershell
fly version
```

### 2. Cuenta y login

```powershell
fly auth login
```

(Se abre el navegador.)

### 3. Volumen de datos (SQLite)

Desde la raíz del proyecto (`d:\tfgade`):

```powershell
fly volumes create financetwin_data --size 1 --region cdg --app financetwin-demo
```

(`mad` está deprecada en Fly; usar `cdg` / París, alineado con `fly.toml`.)

Si el nombre de app en `fly.toml` (`financetwin-demo`) está cogido, cámbialo ahí y en los comandos.

### 4. Desplegar

```powershell
cd d:\tfgade
fly deploy
```

### 5. URL final

```powershell
fly status
fly apps open
```

La URL suele ser: `https://financetwin-demo.fly.dev` (o el nombre que hayas puesto).

### 6. Antes de enviarla

1. Ábrela tú y pulsa **Cargar escenario demo**.
2. En `docs/GUIA_RAPIDA_EVALUADOR.html`, sustituye `[PEGAR AQUÍ LA URL…]` por la URL real.
3. Imprime / guarda PDF de la guía rápida (y del documento de demostración si quieres).
4. Envía por correo: **enlace + 1 o 2 PDF**.

### Nota de privacidad

La instancia es una demo compartida: quien tenga la URL puede crear empresas.
No subas datos personales reales del profesor ni de terceros. Para evaluación basta la demo.

---

## Qué enviar al profesor (checklist)

- [ ] URL pública funcionando (demo carga en &lt; 30–60 s; a veces el idle “despierta” lento)
- [ ] PDF: **Guía rápida de uso**
- [ ] PDF: **Documento de demostración** (capacidades / qué resuelve)
- [ ] Una frase en el correo: *“Abrir el enlace → Cargar escenario demo → seguir la guía rápida”*

No hace falta GitHub, Python ni Docker en su lado.
