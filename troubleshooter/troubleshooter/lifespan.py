import logging
from contextlib import asynccontextmanager
from typing import Any


@asynccontextmanager
async def lifespan(app: Any):
    logging.info("Troubleshooter Agent: starting up")
    try:
        yield
    finally:
        logging.info("Troubleshooter Agent: shutting down")
