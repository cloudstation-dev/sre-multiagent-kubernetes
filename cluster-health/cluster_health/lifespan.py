import logging
from contextlib import asynccontextmanager
from typing import Any


@asynccontextmanager
async def lifespan(app: Any):
    logging.info("Cluster Health Agent: starting up")
    try:
        yield
    finally:
        logging.info("Cluster Health Agent: shutting down")
