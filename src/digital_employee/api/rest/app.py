"""REST application bootstrap."""

from __future__ import annotations


def create_app():
    try:
        from fastapi import FastAPI
    except ModuleNotFoundError as exc:  # pragma: no cover - environment dependent
        raise RuntimeError(
            "FastAPI is not installed in this bootstrap environment; use the CLI until REST dependencies are available."
        ) from exc

    app = FastAPI(title="Digital Employee Platform", version="0.1.0")

    @app.get("/healthz")
    async def healthz():
        return {"ok": True, "service": "digital-employee"}

    return app
