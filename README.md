# FaceLogix

FaceLogix is a multi-tenant face-recognition attendance system. It combines a FastAPI API, a React 19 progressive web app, PostgreSQL with pgvector, and an internal ONNX inference service with liveness detection.

Live project site: [English](https://lunarithmai.github.io/FaceLogix/) | [Tiếng Việt](https://lunarithmai.github.io/FaceLogix/?lang=vi)

## Capabilities

- Face enrollment and check-in/check-out with liveness and image-quality checks
- Organization-scoped users, roles, devices, attendance, and reports
- Atomic bulk people import from ZIP packages with CSV-to-image mapping and manual conflict resolution
- Revocable device credentials and refresh-token sessions
- CSV attendance exports suitable for spreadsheet import
- Responsive installable web app for desktop, tablet, and mobile

## Stack

| Component | Technology |
| --- | --- |
| API | FastAPI on Python 3.11 |
| Face inference | SCRFD, ArcFace, and MiniFASNet ONNX models |
| Web app | React 19, TypeScript, Tailwind CSS 4, TanStack Query |
| Database | PostgreSQL 16 with pgvector |
| Production edge | Nginx with same-origin API proxy and TLS |
| Runtime | Docker Compose v2 |

PostgreSQL is the only stateful infrastructure dependency. Face model files live in a dedicated, read-only-at-runtime Docker volume.

## Development setup

### Requirements

- Docker Engine with Docker Compose v2
- `curl`
- At least 8 GB RAM and 2 GB free disk space for images and ONNX models

Run the bootstrap script from a clean checkout:

```bash
./scripts/dev-setup.sh
```

The script creates `docker/.env` when absent, builds the API and face images, downloads and verifies all four manifest-pinned ONNX models, starts the services, applies migrations, and requires every readiness check to pass.

Development URLs:

| Surface | URL |
| --- | --- |
| Web app | `https://localhost:5173` |
| API | `http://localhost:8000` |
| API documentation | `http://localhost:8000/api/docs` |
| Face-service readiness | `http://localhost:8001/health/ready` |
| PostgreSQL | `localhost:5432` |

Vite uses a local development certificate. The browser will require a one-time trust exception. Browser requests use the same-origin `/api/v1` path; Vite proxies that path to `VITE_PROXY_TARGET`, which defaults to `http://localhost:8000` and is `http://backend:8000` in development Compose.

Useful commands:

```bash
docker compose -f docker/docker-compose.dev.yml logs -f
docker compose -f docker/docker-compose.dev.yml down
```

For host-run services, start PostgreSQL only:

```bash
docker compose -f docker/docker-compose.infra.yml up -d
```

Install Python dependencies with the checked-in hash-locked requirements files (`pip install --require-hashes -r requirements.txt`) and frontend dependencies with `npm ci`.

## Production deployment

Production is a single-host Compose deployment. The `edge` image builds the frontend and serves it through Nginx; only ports 80 and 443 are published. The face service is internal, and the API is exposed only through the edge `/api/v1` proxy.

### 1. Create the environment

The production environment contains exactly these variables:

```text
DB_USER
DB_PASSWORD
DB_NAME
JWT_SECRET_KEY
DEVICE_TOKEN_SECRET
DOMAIN
RELEASE_TAG
```

Generate an initial file, then store it with mode 600:

```bash
./scripts/generate_secrets.sh \
  --domain attendance.example.com \
  --release-tag local \
  --output-file docker/.env
```

`RELEASE_TAG` is replaced by `deploy.sh` with `--tag` or the current 12-character Git commit. `deploy.sh` rejects blank values, `CHANGE_ME` values, short authentication secrets, and dirty tracked files.

### 2. Install TLS material

Provision a certificate outside FaceLogix. Copy the operator-managed files to:

```text
docker/nginx/ssl/fullchain.pem
docker/nginx/ssl/privkey.pem
```

The repository does not issue certificates or mount an ACME challenge directory. The deployment script validates the certificate and private key before changing services.

### 3. Deploy one coherent release

```bash
./scripts/deploy.sh
# or assign an explicit image tag
./scripts/deploy.sh --tag 2026.08.1
```

A deployment is a maintenance transaction, not a zero-downtime claim. It:

1. validates the clean checkout, environment, TLS files, Nginx template, and four-entry model manifest;
2. starts and checks PostgreSQL;
3. creates and verifies a pre-deployment database backup;
4. builds candidate backend, face, model-init, and edge images under one release tag;
5. stops edge and backend writers;
6. applies the database migration exactly once;
7. downloads or verifies models through the one-shot `model-init` service;
8. starts face, backend, and edge with the coherent tag; and
9. requires face readiness, backend readiness, and edge liveness before recording deployment state.

Deployment state is stored under ignored `docker/.deployment/`. Application rollback is available when a previous tag is recorded:

```bash
./scripts/deploy.sh --rollback
```

Rollback changes application image tags only. It intentionally does not restore or downgrade the database; migrations must remain backward-compatible with the previous application release.

## Backup and restore

Create a compressed PostgreSQL backup plus a portable SHA-256 checksum:

```bash
./scripts/backup.sh
```

Backups default to `backups/`. Override the destination or retention window with `BACKUP_DIR` and `RETENTION_DAYS`.

Restore is destructive and requires both stopped application writers and a literal confirmation:

```bash
docker compose --env-file docker/.env -f docker/docker-compose.yml stop edge backend
./scripts/restore.sh backups/facelogix-YYYYMMDDTHHMMSSZ.sql.gz --confirm RESTORE
```

`restore.sh` refuses to proceed while `edge` or `backend` is running, verifies the checksum and gzip stream, restores through the Compose PostgreSQL service, reapplies current migrations, starts the current release, and verifies backend readiness and edge liveness.

## Face models

`face_service/app/models/manifest.py` is the source of truth for the detector, embedder, and two anti-spoofing models. Every entry specifies HTTPS source URL, exact byte size, SHA-256 checksum, role, and crop parameters. Production startup cannot bypass download, checksum validation, ONNX validation, warm-up, or readiness.

For an explicit host-side install or verification:

```bash
cd face_service
python download_models.py --models-dir models
python download_models.py --models-dir models --verify-only
```

## Bulk people import

Operators can import up to 100 people at once from **Users → Import People**. Upload one ZIP
package no larger than 128 MiB with `people.csv` at its root and the referenced JPEG or PNG
files elsewhere in the archive.

Required CSV columns are `external_id`, `name`, and `image_1`. Optional columns are `email`,
`department`, and `image_2` through `image_5`. Image paths are relative to the ZIP root, each
image may be no larger than 10 MiB, and every imported account has the `member` role. The UI
provides a downloadable CSV template.

The preview reports invalid rows and existing-person matches without changing the database.
Each match must be resolved manually as `skip` or `replace`; elevated accounts can only be
skipped. Replace updates a member's imported profile fields and face enrollment. Face images are
converted to embeddings and are not retained. Import is atomic: any CSV, image, face-quality,
liveness, uniqueness, or service failure leaves all people unchanged.

## API routes

All application routes are under `/api/v1`.

- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `GET /api/v1/auth/me`
- `POST /api/v1/attendance/check-in`
- `POST /api/v1/users/import/preview`
- `POST /api/v1/users/import`
- `POST /api/v1/attendance/check-out`
- `GET /api/v1/attendance`
- `GET /api/v1/reports/dashboard`
- `GET /api/v1/reports/attendance/csv`

Health endpoints:

- edge liveness: `/health/live`
- backend dependency readiness: `/health/ready`
- internal face readiness: `/health/ready` on the face-service container

## Repository layout

```text
backend/              FastAPI API, migrations, and tests
face_service/         ONNX pipeline, manifest, downloader, and tests
frontend/             React PWA
landing/              Static GitHub Pages project site
docker/               Compose topology and production edge image
scripts/              setup, deployment, backup, restore, and secret tooling
```

## License

MIT License. See [LICENSE](LICENSE).
