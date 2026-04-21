import logging
from contextlib import asynccontextmanager
from typing import Any


@asynccontextmanager
async def lifespan(app: Any):
    logging.info("SRE Coordinator Agent: starting up")
    logging.info("Will delegate to Cluster Health and Troubleshooter agents via A2A")
    try:
        yield
    finally:
        logging.info("SRE Coordinator Agent: shutting down")
