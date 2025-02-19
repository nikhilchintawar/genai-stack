from fastapi import FastAPI

from genai_stack.genai_server.routers import (
    session_routes,
    retriever_routes,
    vectordb_routes,
    etl_routes,
    model_routes,
)


def get_genai_server_app():
    """Returns the app instance of FastAPI."""

    app = FastAPI(title="GenAI Stack", version="0.2.0")

    """Add middleware if required."""
    # app.middleware()

    """Run Server"""
    # to run this file locally, execute:
    # uvicorn genai_stack.genai_platform.genai_stack_server:app --reload

    """Connecting all the routers to app."""
    app.include_router(session_routes.router)
    app.include_router(retriever_routes.router)
    app.include_router(vectordb_routes.router)
    app.include_router(etl_routes.router)
    app.include_router(model_routes.router)

    return app
