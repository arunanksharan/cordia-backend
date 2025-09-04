import logging
from .config import settings

def setup_logging():
    level = logging.DEBUG if settings.ENV == "local" else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s [%(request_id)s] %(message)s",
    )