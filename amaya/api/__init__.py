"""FastAPI backend for the ADI rating pipeline.

Thin HTTP layer over the existing ingest → agents → scoring pipeline.
Ratings run as background asyncio tasks; progress is delivered to clients
over Server-Sent Events. No database — job state is in-memory and keyed
by rating_id. Persistence lives in the provenance ledger on disk.
"""
from amaya.api.app import create_app

__all__ = ["create_app"]
