# Despliegue de Luneta en producción

Guía para publicar Luneta en Internet con **dominio propio**, usando servicios gestionados (opción recomendada).

## Arquitectura

```mermaid
flowchart LR
  User[Usuarios] --> CF[Cloudflare DNS + CDN]
  CF --> Pages["Cloudflare Pages<br/>luneta.org"]
  CF --> Render["Render<br/>api.luneta.org"]
  Pages -->|VITE_API_URL| Render
  Render --> Atlas[(MongoDB Atlas)]
  Render --> R2[(Cloudflare R2)]
  Render --> SMTP[Brevo / Resend]
  Render --> Gemini[Google Gemini API]
```

| Componente | Servicio | URL ejemplo |
|------------|----------|-------------|
| Frontend (SPA) | Cloudflare Pages | `https://luneta.org` |
| API (FastAPI) | Render (Docker) | `https://api.luneta.org` |
| Base de datos | MongoDB Atlas M0 | (solo backend) |
| Imágenes / avatares | Cloudflare R2 | (S3-compatible, solo backend) |
| Email transaccional | Brevo o Resend | SMTP |
| IA (sugerencias) | Google AI Studio | API key Gemini |

**Coste orientativo:** 0–15 €/mes (Atlas M0 gratis, Pages gratis, Render free tier con limitaciones, dominio ~10 €/año, R2 con free tier generoso).

---

## Requisitos previos

- Repositorio en **GitHub** (ya lo tienes).
- Tarjeta para registrar el dominio (Cloudflare Registrar recomendado si usas Pages + R2).
- Cuentas a crear (gratis): [Cloudflare](https://dash.cloudflare.com/sign-up), [MongoDB Atlas](https://www.mongodb.com/cloud/atlas/register), [Render](https://dashboard.render.com/register), [Brevo](https://www.brevo.com) o [Resend](https://resend.com), [Google AI Studio](https://aistudio.google.com/apikey) (Gemini).

Plantilla de variables: [`.env.production.example`](../.env.production.example).

---

## Paso 1 — Registrar el dominio

1. Entra en [Cloudflare Dashboard](https://dash.cloudflare.com) → **Domain Registration** → busca y compra tu dominio (p. ej. `luneta.org`).
2. El dominio quedará gestionado en Cloudflare DNS (necesario para Pages y R2).

Convención usada en esta guía:

- `luneta.org` → frontend
- `api.luneta.org` → API

---

## Paso 2 — MongoDB Atlas

1. Crea un cluster **M0 (free)** en la región más cercana a Frankfurt (Render EU).
2. **Database Access** → usuario con contraseña fuerte → rol `readWrite` en la base `luneta`.
3. **Network Access** → **Add IP Address** → `0.0.0.0/0` (necesario en Render free; en planes de pago puedes restringir IPs).
4. **Connect** → driver Python → URI con nombre de base **`/luneta`** en la ruta:
   `mongodb+srv://USER:PASS@cluster....mongodb.net/luneta?retryWrites=true&w=majority`
5. Pon la URI en `.env` (`MONGODB_URI=...`) y verifica:
   `python infra/scripts/check_mongodb_connection.py`

---

## Paso 3 — Cloudflare R2 (almacenamiento)

1. Cloudflare → **R2** → Create bucket → nombre `luneta-assets`.
2. **Manage R2 API Tokens** → Create API token con permiso Read/Write en ese bucket.
3. Anota:
   - **Account ID**
   - **Access Key ID** y **Secret Access Key**
   - Endpoint S3: `https://<ACCOUNT_ID>.r2.cloudflarestorage.com`

Variables para la API:

```env
S3_ENDPOINT=https://<ACCOUNT_ID>.r2.cloudflarestorage.com
S3_PUBLIC_ENDPOINT=https://<ACCOUNT_ID>.r2.cloudflarestorage.com
S3_REGION=auto
S3_ACCESS_KEY=<access_key>
S3_SECRET_KEY=<secret_key>
S3_BUCKET_LUNETA=luneta-assets
```

El bucket se crea solo la primera vez que la API sube un archivo (`ensure_bucket`).

---

## Paso 4 — Email (Brevo)

1. Cuenta en Brevo → **SMTP y API** → **Generar una nueva clave SMTP** (no la clave API).
2. **No restrinjas por IP** si la API irá en Render (IPs variables). Brevo autentica por usuario + clave SMTP.
3. Verifica el dominio en Brevo (DNS en Cloudflare: SPF/DKIM que indique Brevo).
4. Variables en Render / `.env`:

```env
EMAIL_FROM="Luneta <no-reply@luneta.org>"
EMAIL_SMTP_HOST=smtp-relay.brevo.com
EMAIL_SMTP_PORT=587
EMAIL_SMTP_USER=tu-email-de-cuenta-brevo@ejemplo.com
EMAIL_SMTP_PASSWORD=clave-smtp-generada-en-brevo
EMAIL_FAIL_SILENTLY=false
```

- **Usuario SMTP:** el email con el que te registraste en Brevo.
- **Contraseña SMTP:** la clave SMTP generada (no la contraseña de login ni la clave API).

---

## Paso 5 — Desplegar la API en Render

### Opción A — Blueprint (recomendada)

1. [Render Dashboard](https://dashboard.render.com) → **New** → **Blueprint**.
2. Conecta el repo de GitHub y selecciona `render.yaml` en la raíz.
3. Rellena las variables marcadas como `sync: false` (ver tabla abajo).
4. Tras el deploy, anota la URL temporal: `https://luneta-api-xxxx.onrender.com`.

### Opción B — Manual

1. **New** → **Web Service** → repo GitHub.
2. **Runtime:** Docker.
3. **Root Directory:** vacío; **Dockerfile Path:** `apps/api/Dockerfile`; **Docker Context:** `apps/api`.
4. **Health Check Path:** `/health`.
5. Añade las variables de entorno.

### Variables obligatorias en Render

| Variable | Valor |
|----------|--------|
| `WEB_URL` | `https://luneta.org` (URL pública del front) |
| `MONGODB_URI` | URI de Atlas |
| `AUTH_TOKEN_SECRET` | Secreto largo aleatorio (ver abajo) |
| `S3_*` | Credenciales R2 |
| `EMAIL_*` | SMTP Brevo |
| `GEMINI_API_KEY` | Si usas sugerencias IA |
| `DEV_EXPOSE_LAST_EMAIL_VERIFICATION_TOKEN` | `false` |

Generar `AUTH_TOKEN_SECRET`:

```powershell
& "C:\Users\danim\Desktop\Proyectos Datos\Luneta\.venv\Scripts\Activate.ps1"
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

### Dominio custom en Render

1. Render → servicio `luneta-api` → **Settings** → **Custom Domains** → `api.luneta.org`.
2. Render muestra un CNAME; en Cloudflare DNS:
   - Tipo **CNAME**, nombre `api`, destino el que indique Render.
   - Proxy **DNS only** (nube gris) si Render pide validación TLS directa; si funciona con proxy naranja, déjalo.
3. Espera certificado HTTPS (unos minutos).

Comprueba: `https://api.luneta.org/health` → `{"status":"ok"}` (o equivalente).

---

## Paso 6 — Frontend en Cloudflare Pages

1. Cloudflare → **Workers & Pages** → **Create** → **Pages** → **Connect to Git** → repo Luneta.
2. Configuración de build:

| Campo | Valor |
|-------|--------|
| Production branch | `main` |
| Root directory | `apps/web` |
| Build command | `npm install && npm run build` |
| Build output directory | `dist` |

3. **Environment variables** (Production):

| Variable | Valor |
|----------|--------|
| `VITE_API_URL` | `https://api.luneta.org` |

4. Deploy. URL temporal: `https://luneta-xxxx.pages.dev`.

### Dominio custom en Pages

1. Pages → proyecto → **Custom domains** → `luneta.org` y opcionalmente `www.luneta.org`.
2. Cloudflare añade los registros DNS automáticamente si el dominio está en la misma cuenta.
3. Redirige `www` → apex si quieres una sola URL canónica (regla Redirect en Cloudflare).

Comprueba: abre `https://luneta.org` y la consola del navegador no debe mostrar errores CORS hacia la API.

---

## Paso 7 — Datos iniciales (catálogos y admin)

Con la API en marcha y MongoDB vacío, ejecuta **desde tu máquina** apuntando a Atlas (usa la misma `MONGODB_URI` de producción solo si entiendes el riesgo; mejor hacerlo una vez controlado):

```powershell
cd "C:\Users\danim\Desktop\Proyectos Datos\Luneta"
& .\.venv\Scripts\Activate.ps1
$env:MONGODB_URI = "mongodb+srv://..."
python infra/scripts/seed_ethical_risk_catalog.py
python infra/scripts/seed_scenario_classification_catalog.py
python infra/scripts/create_admin.py
```

Sigue las instrucciones interactivas de `create_admin.py` para el primer administrador.

---

## Paso 8 — Checklist de verificación

- [ ] `GET https://api.luneta.org/health` responde OK.
- [ ] `https://luneta.org` carga el home.
- [ ] Registro de usuario → llega email de verificación (revisa spam).
- [ ] Enlace de verificación abre `https://luneta.org/verify-email?...` (depende de `WEB_URL`).
- [ ] Login y flujo básico de escenarios.
- [ ] Subida de imagen de portada (confirma R2).
- [ ] Sugerencias IA (si configuraste Gemini).

---

## Notas importantes

### Render free tier

- El servicio **se duerme** tras ~15 min sin tráfico; la primera petición puede tardar ~30–60 s.
- Para demo pública estable, valora el plan Starter (~7 USD/mes).

### Seguridad

- Nunca subas `.env` con secretos al repo.
- `AUTH_TOKEN_SECRET` distinto en producción vs local.
- `DEV_EXPOSE_LAST_EMAIL_VERIFICATION_TOKEN=false` en producción.

### CORS

La API permite `*` en desarrollo. Para producción estricta puedes restringir `allow_origins` a `[settings.web_url]` en `apps/api/app/main.py`.

### CI

El workflow [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) ya ejecuta tests y `pnpm build`; conviene que `main` esté verde antes de desplegar.

### Alternativa: web en Docker

Si prefieres servir el front también en Render:

```bash
docker build -f apps/web/Dockerfile.prod --build-arg VITE_API_URL=https://api.luneta.org -t luneta-web .
```

Usa el puerto **8080** del contenedor nginx.

---

## Resumen de URLs en local vs producción

| | Local | Producción |
|---|-------|------------|
| Abrir en navegador | `http://localhost:5173` | `https://luneta.org` |
| API (llamadas HTTP) | `http://localhost:8000` | `https://api.luneta.org` |

El front **llama** a la API; el usuario **abre** la URL del front en el navegador.
