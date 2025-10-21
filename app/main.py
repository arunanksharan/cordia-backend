import time
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.core.logging import setup_logging
from dotenv import load_dotenv

# Load environment variables from .env file before anything else
load_dotenv()

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


logger = logging.getLogger(__name__)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    response = await call_next(request)
    
    process_time = (time.time() - start_time) * 1000
    formatted_process_time = f"{process_time:.2f}ms"
    
    logger.info(
        f"Request: {request.method} {request.url.path} - Response: {response.status_code} - Time: {formatted_process_time}"
    )
    
    return response

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.critical(f"Unhandled exception for request {request.method} {request.url.path}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"message": "An internal server error occurred."},
    )


from app.core.redis import redis_manager

@app.on_event("startup")
async def on_startup():
    await init_models()
    await ensure_vector_indexes()
    await redis_manager.connect()
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
    await redis_manager.close()


app.include_router(api_router, prefix=settings.API_PREFIX)