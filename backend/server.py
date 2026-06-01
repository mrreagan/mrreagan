"""Birthright Foundation - Main FastAPI server."""
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI, APIRouter, Request
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware
import logging

from database import db, client  # single source of truth for MongoDB

app = FastAPI(title="Birthright API", version="1.11.0")
api_router = APIRouter(prefix="/api")

# Serve product mockup images & other static assets at /api/static/*
STATIC_DIR = Path(__file__).parent / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/api/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@api_router.get("/")
async def root() -> dict[str, str]:
    return {
        "name": "Birthright Foundation API",
        "motto": "Secure Bonds > Thrive",
        "version": "1.11.0",
    }


@api_router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


# Include routers
from routers.auth import router as auth_router
from routers.password_reset import router as password_reset_router
from routers.workshops import router as workshops_router
from routers.products import router as products_router
from routers.checkout import router as checkout_router, stripe_webhook
from routers.community import router as community_router
from routers.foundation import router as foundation_router
from routers.registrations import router as registrations_router
from routers.workshop_photos import router as workshop_photos_router
from routers.chat_ws import router as chat_ws_router
from routers.reviews import router as reviews_router
from routers.governance import router as governance_router
from routers.legal import router as legal_router
from routers.audit import router as audit_router
from routers.partners import router as partners_router, admin_router as partners_admin_router
from routers.partner_prospects import router as partner_prospects_router
from routers.search import router as search_router
from routers.subscriptions import router as subscriptions_router, admin_router as subscriptions_admin_router
from routers.referrals import public_router as referrals_public_router, my_router as referrals_my_router, admin_router as referrals_admin_router
from routers.reports import my_router as reports_my_router, admin_router as reports_admin_router
from routers.vendor_catalog import vendor_router as vendor_catalog_router, admin_router as vendor_catalog_admin_router
from routers.foundation_roles import (
    public_router as foundation_roles_public_router,
    applications_router as foundation_roles_apps_router,
    admin_router as foundation_roles_admin_router,
    admin_apps_router as foundation_roles_admin_apps_router,
)
from routers.outbound import router as outbound_router, admin_router as outbound_admin_router
from routers.partner_sales import (
    my_router as partner_sales_my_router,
    admin_router as partner_sales_admin_router,
    webhook_router as partner_sales_webhook_router,
)
from routers.featured import (
    public_router as featured_public_router,
    my_router as featured_my_router,
    admin_router as featured_admin_router,
)
from routers.founding import (
    public_router as founding_public_router,
    admin_router as founding_admin_router,
)
from routers.research import (
    public_router as research_public_router,
    my_router as research_my_router,
    admin_router as research_admin_router,
)
from routers.payouts import (
    my_router as payouts_my_router,
    admin_router as payouts_admin_router,
)
from routers.shares import (
    public_router as shares_public_router,
    my_router as shares_my_router,
)
from routers.dm import (
    router as dm_router,
    my_prefs_router as dm_my_prefs_router,
    admin_router as dm_admin_router,
    ws_router as dm_ws_router,
)
from routers.disputes import (
    router as disputes_router,
    my_router as disputes_my_router,
    admin_router as disputes_admin_router,
    ombudsman_router as ombudsman_router,
)
from routers.refunds import (
    admin_router as refunds_admin_router,
    clawback_router as clawback_router,
)
from routers.assistant import router as assistant_router
from routers.ai_wallet import (
    my_router as ai_wallet_my_router,
    admin_router as ai_wallet_admin_router,
)
from routers.research_ai import router as research_ai_router
from routers.vendor_ai import router as vendor_ai_router
from routers.connect import router as connect_router, ws_router as connect_ws_router
from routers.link_preview import router as link_preview_router
from routers.studio import router as studio_router, admin_router as studio_admin_router
from routers.printful import router as printful_router
from routers.lulu import router as lulu_router
from routers.gather import router as gather_router, admin_router as gather_admin_router
from routers.gallery import router as gallery_router

api_router.include_router(auth_router)
api_router.include_router(password_reset_router)
api_router.include_router(workshops_router)
api_router.include_router(products_router)
api_router.include_router(checkout_router)
api_router.include_router(community_router)
api_router.include_router(foundation_router)
api_router.include_router(registrations_router)
api_router.include_router(workshop_photos_router)
api_router.include_router(chat_ws_router)
api_router.include_router(reviews_router)
api_router.include_router(governance_router)
api_router.include_router(legal_router)
api_router.include_router(audit_router)
api_router.include_router(partner_prospects_router)
api_router.include_router(search_router)
api_router.include_router(partners_router)
api_router.include_router(partners_admin_router)
api_router.include_router(subscriptions_router)
api_router.include_router(subscriptions_admin_router)
api_router.include_router(referrals_public_router)
api_router.include_router(referrals_my_router)
api_router.include_router(referrals_admin_router)
api_router.include_router(reports_my_router)
api_router.include_router(reports_admin_router)
api_router.include_router(vendor_catalog_router)
api_router.include_router(vendor_catalog_admin_router)
api_router.include_router(foundation_roles_public_router)
api_router.include_router(foundation_roles_apps_router)
api_router.include_router(foundation_roles_admin_router)
api_router.include_router(foundation_roles_admin_apps_router)
api_router.include_router(outbound_router)
api_router.include_router(outbound_admin_router)
api_router.include_router(partner_sales_my_router)
api_router.include_router(partner_sales_admin_router)
api_router.include_router(partner_sales_webhook_router)
api_router.include_router(featured_public_router)
api_router.include_router(featured_my_router)
api_router.include_router(featured_admin_router)
api_router.include_router(founding_public_router)
api_router.include_router(founding_admin_router)
api_router.include_router(research_public_router)
api_router.include_router(research_my_router)
api_router.include_router(research_admin_router)
api_router.include_router(payouts_my_router)
api_router.include_router(payouts_admin_router)
api_router.include_router(shares_public_router)
api_router.include_router(shares_my_router)
api_router.include_router(dm_router)
api_router.include_router(dm_my_prefs_router)
api_router.include_router(dm_admin_router)
api_router.include_router(dm_ws_router)
api_router.include_router(disputes_router)
api_router.include_router(disputes_my_router)
api_router.include_router(disputes_admin_router)
api_router.include_router(ombudsman_router)
api_router.include_router(refunds_admin_router)
api_router.include_router(clawback_router)
api_router.include_router(assistant_router)
api_router.include_router(ai_wallet_my_router)
api_router.include_router(ai_wallet_admin_router)
api_router.include_router(research_ai_router)
api_router.include_router(vendor_ai_router)
api_router.include_router(connect_router)
api_router.include_router(connect_ws_router)
api_router.include_router(link_preview_router)
api_router.include_router(studio_router)
api_router.include_router(studio_admin_router)
api_router.include_router(printful_router)
api_router.include_router(lulu_router)
api_router.include_router(gather_router)
api_router.include_router(gather_admin_router)
api_router.include_router(gallery_router)


@api_router.post("/webhook/stripe")
async def stripe_webhook_endpoint(request: Request) -> Any:
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
async def startup_event() -> None:
    try:
        from seed_data import seed_if_empty
        await seed_if_empty(db)
        logger.info("Seed check complete.")
    except Exception as e:
        logger.error(f"Seeding error: {e}")
    try:
        from runtime_seed import ensure_catalog_seeded, repair_known_broken_images, backfill_partner_economy_fields, ensure_foundation_roles_seeded, ensure_sample_partners_seeded, ensure_sample_research_artifacts, ensure_agreement_v2_published, ensure_founder_collection_seeded, ensure_governing_member_images
        await ensure_catalog_seeded(db)
        await ensure_founder_collection_seeded(db)
        await ensure_governing_member_images(db)
        await repair_known_broken_images(db)
        await backfill_partner_economy_fields(db)
        await ensure_foundation_roles_seeded(db)
        await ensure_sample_partners_seeded(db)
        await ensure_sample_research_artifacts(db)
        await ensure_agreement_v2_published(db)
    except Exception as e:
        logger.error(f"Runtime seed/repair error: {e}")
    try:
        from utils.gather_seed import seed_geographic_tree
        result = await seed_geographic_tree(db)
        logger.info(f"Gather hierarchy: inserted {result['inserted']} (total {result['total_now']}).")
    except Exception as e:
        logger.error(f"Gather seed error: {e}")
    try:
        from utils.scheduler import start_scheduler
        start_scheduler()
    except Exception as e:
        logger.error(f"Scheduler start error: {e}")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    try:
        from utils.scheduler import stop_scheduler
        stop_scheduler()
    except Exception:
        pass
    client.close()
