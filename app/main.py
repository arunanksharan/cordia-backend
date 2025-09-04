from fastapi import FastAPI, Request
from app.core.config import settings
from app.core.logging import setup_logging
from app.api.router import api_router
from app.core.db import init_models
from contextvars import ContextVar
import asyncio

from app.modules.events.outbox import run_outbox_relay
from app.modules.vector.setup import ensure_vector_indexes


setup_logging()
app = FastAPI(title=settings.APP_NAME)

# attach request_id to log records (simple)
import logging
from contextvars import ContextVar
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")
old_factory = logging.getLogRecordFactory()
def record_factory(*args, **kwargs):
    record = old_factory(*args, **kwargs)
    record.request_id = request_id_ctx.get()
    return record
logging.setLogRecordFactory(record_factory)

@app.middleware("http")
async def add_request_id(request: Request, call_next):
    rid = request.headers.get("x-request-id", "-")
    request_id_ctx.set(rid)
    response = await call_next(request)
    return response

@app.on_event("startup")
async def on_startup():
    await init_models()
    await ensure_vector_indexes()
    app.state.outbox_task = asyncio.create_task(run_outbox_relay())

@app.on_event("shutdown")
async def on_shutdown():
    task = getattr(app.state, "outbox_task", None)
    if task:
        task.cancel()
        try:
            await task
        except Exception:
            pass


app.include_router(api_router, prefix=settings.API_PREFIX)