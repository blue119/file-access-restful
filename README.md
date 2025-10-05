# File Access Service

FastAPI-powered REST backend for browsing, downloading, and uploading files within a sandboxed storage root. The service renders a lightweight HTML explorer, exposes JSON-friendly endpoints, and keeps upload credentials rotating for safety.

## Features
- Directory browser with breadcrumb navigation and file size metadata.
- Token-protected uploads with automatic rotation and super-token override.
- Download endpoint constrained to the configured storage root via safe path resolution.
- Built-in HTML front-end and favicon assets for a zero-config landing page.

## Requirements
- Python 3.12+
- [uv](https://docs.astral.sh/uv/) for environment management

## Quick Start
```bash
# Install dependencies (creates uv-managed virtualenv)
./run.sh install

# Launch the dev server on a random high port
./run.sh run

# In a separate shell, lint the project
./run.sh lint
```

The `run` command prints `Serving on http://localhost:<port>` and starts `uvicorn` with hot reload. Visit the printed URL to explore files.

## Upload Tokens
On startup the service logs two credentials (see stdout):
- **Upload token** &mdash; 16 characters, rotates after each successful upload.
- **Super token** &mdash; 32 characters, static per process for emergency use.

Override defaults by setting environment variables **before** launching the server:
```bash
export FILE_ACCESS_SUPER_TOKEN="exampleSuperTokenWith32Chars!!"
./run.sh run
```
Values are normalized to the expected lengths (trimmed or padded with random characters). After each normal upload the token rotates and the new value is logged for distribution.

### Example Upload
```bash
curl -T README.md \
  http://localhost:<port>/upload/<token>/docs/README.md
```

### Example Download
```bash
curl -O http://localhost:<port>/download/docs/README.md
```

## API Overview
| Method | Path | Description |
| --- | --- | --- |
| GET | `/` | Render the HTML directory listing for `storage/files`. Optional `?path=subdir` query. |
| GET | `/download/{file_path}` | Stream a file if it stays within the storage root. |
| PUT | `/upload/{token}/{file_path}` | Write the request body to `file_path` when the token is valid. |
| GET | `/favicon.ico` | Serve the shared favicon asset. |

## Project Layout
```
.
├── src/
│   ├── api/main.py        # FastAPI app, routes, token management
│   ├── services/file_catalog.py
│   │                       # Directory traversal, safe path resolution helpers
│   └── storage/           # Extension point for future storage backends
├── storage/files/         # Default download root (kept under version control)
├── static/favicon.ico     # Served at /favicon.ico
├── run.sh                 # Helper for install/lint/run
├── pyproject.toml         # Project metadata and tooling configs
└── AGENTS.md              # Contributor guidelines and repository policies
```

## Testing
Pytest and HTTPX are included for integration points. Add tests under `tests/` to mirror modules (e.g., `tests/api/`, `tests/services/`).
```bash
uv run pytest
```
Aim for ≥90% statement coverage and clean up temporary filesystem artifacts in integration tests.

## Development Notes
- Keep route handlers slim; move business logic to `src/services/`.
- Use `pathlib.Path` for filesystem operations and add type hints to public functions.
- Follow the conventions documented in `AGENTS.md`, including Conventional Commit messages and security practices.

## Troubleshooting
- **uv not found**: install via `pip install uv` or follow upstream instructions.
- **Token mismatch (401)**: confirm you are using the latest token logged by the server. General tokens rotate after each successful upload.
- **Missing favicon**: ensure `static/favicon.ico` exists; the route returns 404 if removed.

## License
MIT License (add details here if a license file is introduced).
