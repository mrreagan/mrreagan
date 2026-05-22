"""Birthright Foundation - Main FastAPI server."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI, APIRouter, Request
from starlette.middleware.cors import CORSMiddleware
import logging

from database import db, client  # single source of truth for MongoDB

app = FastAPI(title="Birthright API", version="1.0.0")
api_router = APIRouter(prefix="/api")


@api_router.get("/")
async def root():
    return {
        "name": "Birthright Foundation API",
        "motto": "Secure Bonds > Thrive",
        "version": "1.0.0",
    }


@api_router.get("/health")
async def health():
    return {"status": "ok"}


# Include routers
from routers.auth import router as auth_router
from routers.workshops import router as workshops_router
from routers.products import router as products_router
from routers.checkout import router as checkout_router, stripe_webhook
from routers.community import router as community_router
from routers.foundation import router as foundation_router

api_router.include_router(auth_router)
api_router.include_router(workshops_router)
api_router.include_router(products_router)
api_router.include_router(checkout_router)
api_router.include_router(community_router)
api_router.include_router(foundation_router)


@api_router.post("/webhook/stripe")
async def stripe_webhook_endpoint(request: Request):
    return await stripe_webhook(request)


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origin_regex=r"https?://.*",
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("birthright")


@app.on_event("startup")
async def startup_event():
    try:
        from seed_data import seed_if_empty
        await seed_if_empty(db)
        logger.info("Seed check complete.")
    except Exception as e:
        logger.error(f"Seeding error: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    client.close()
