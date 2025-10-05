# Repository Guidelines

This repository hosts the File Access RESTful service. Follow these conventions so every agent can extend the FastAPI backend quickly and safely.

## Project Structure & Module Organization
- `src/` contains the application package. Keep HTTP routing in `src/api/`, reusable logic in `src/services/`, and adapters or gateways in `src/storage/`. Shared schemas belong under `src/schemas/`.
- `static/` holds web assets shared across responses, including `favicon.ico` served at `/favicon.ico`.
- `tests/` mirrors the module layout (for example `tests/api/`, `tests/services/`) to keep fixtures close to the code they validate.
- `storage/files/` is the default download root shipped with the service. Seed sample data here when demonstrating features.
- `docs/` stores API references or design notes, while `infra/` is reserved for deployment automation whenever you add it.

## Build, Test, and Development Commands
- `./run.sh install` — create or refresh the uv-managed virtualenv with runtime and dev dependencies.
- `./run.sh lint` — run `ruff` plus `black --check` using `uv run` to enforce formatting and import hygiene.
- `./run.sh test` — execute the pytest suite in the synchronized environment.
- `./run.sh run` — pick a random free port between 10000-20000, print `Serving on http://localhost:<port>`, then launch the hot-reloading server via `uv run uvicorn`.

## Coding Style & Naming Conventions
- Target Python 3.12 with four-space indentation and type annotations on public functions. Prefer `pathlib.Path` for filesystem work.
- Use snake_case for modules/functions, PascalCase for pydantic models, and ALL_CAPS for environment-derived constants. Keep FastAPI route handlers slim; defer heavy lifting to services.

## Testing Guidelines
- Use pytest with descriptive names like `test_download_returns_file`. Integration tests touching the real filesystem belong in `tests/integration/` and should clean up temporary artifacts.
- Maintain ≥90% statement coverage (`uv run pytest --cov=src`). Add fixtures that simulate permission errors, large files, and nested directories.

## Commit & Pull Request Guidelines
- Follow Conventional Commits (`feat(api): add chunked download support`). Summaries stay ≤72 characters; expand context and breaking changes in the body.
- Every PR should link its tracking ticket, list validation steps (commands, sample responses), and include screenshots or curl transcripts for user-visible changes. Request review from a second agent for updates under `src/storage/` or deployment automation.

## Upload API Usage
- On startup the service logs two credentials: a 16-character general upload token and a 32-character super token (`INFO file_access.upload - ...`). Tokens rotate per process; override with `FILE_ACCESS_UPLOAD_TOKEN` and `FILE_ACCESS_SUPER_TOKEN` (values are trimmed/padded to the expected length) when you need deterministic deployments.
- Standard uploads: `curl -T README.md http://localhost:PORT/upload/<token>/docs/README.md`. After each successful use, the general token is regenerated, logged, and reflected in subsequent listings; be ready to distribute the new value to trusted clients.
- Super uploads may substitute the super token in the same slot for emergency access. Requests missing a valid token segment receive `401`. Nested paths continue to create directories automatically.

## Security & Configuration Tips
- Store secrets in `.env` files excluded from git; ship redacted examples at `config/example.env` to help others reproduce environments.
- Default to least-privilege permissions (e.g., `chmod 640`) on stored artifacts and document any required exceptions in `docs/security.md`.
