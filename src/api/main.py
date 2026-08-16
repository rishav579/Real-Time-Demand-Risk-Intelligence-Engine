"""FastAPI main application entrypoint for Demand & Risk Intelligence Engine."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import router


def create_app() -> FastAPI:
    """Construct and configure the FastAPI application."""
    app = FastAPI(
        title="Real-Time Demand & Risk Intelligence Engine API",
        description=(
            "Production-grade decision intelligence REST API providing multi-horizon demand forecasting, "
            "predictive stockout and excess risk scoring, deterministic root-cause attribution, "
            "and prescriptive replenishment recommendations."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router, prefix="/api/v1")
    app.include_router(router)  # Also expose without prefix for convenience

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api.main:app", host="127.0.0.1", port=8000, reload=True)
