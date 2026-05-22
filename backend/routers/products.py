"""Product / Storefront routes."""
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from models import ProductCreate, Product, ProductUpdate, gen_id, now_iso
from auth_utils import get_current_user, require_roles, get_current_user_optional

router = APIRouter(prefix="/products", tags=["products"])


@router.get("")
async def list_products(
    type: Optional[str] = None,
    workshop_id: Optional[str] = None,
    category: Optional[str] = None,
):
    from database import db
    query = {}
    if type:
        query["type"] = type
    if workshop_id:
        query["workshop_id"] = workshop_id
    if category:
        query["category"] = category
    products = await db.products.find(query, {"_id": 0}).to_list(1000)
    return products


@router.get("/{product_id}")
async def get_product(product_id: str, user: Optional[dict] = Depends(get_current_user_optional)):
    from database import db
    p = await db.products.find_one({"id": product_id}, {"_id": 0})
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")
    # gating info: if workshop material, check eligibility
    if p["type"] == "workshop_material" and p.get("workshop_id"):
        if not user:
            p["locked"] = True
            p["lock_reason"] = "Sign in and register for the workshop to purchase materials."
        else:
            reg = await db.registrations.find_one(
                {
                    "workshop_id": p["workshop_id"],
                    "user_id": user["id"],
                    "payment_status": "paid",
                }
            )
            if not reg and user["role"] not in ("admin",):
                p["locked"] = True
                p["lock_reason"] = "Only registered workshop participants can purchase these materials."
            else:
                p["locked"] = False
    else:
        p["locked"] = False
    return p


@router.post("")
async def create_product(data: ProductCreate, user: dict = Depends(require_roles("admin"))):
    from database import db
    product = {**data.model_dump(), "id": gen_id(), "created_at": now_iso()}
    await db.products.insert_one(product)
    product.pop("_id", None)
    return product


@router.put("/{product_id}")
async def update_product(product_id: str, updates: ProductUpdate, user: dict = Depends(require_roles("admin"))):
    from database import db
    update_data = {k: v for k, v in updates.model_dump().items() if v is not None}
    if update_data:
        await db.products.update_one({"id": product_id}, {"$set": update_data})
    p = await db.products.find_one({"id": product_id}, {"_id": 0})
    return p


@router.delete("/{product_id}")
async def delete_product(product_id: str, user: dict = Depends(require_roles("admin"))):
    from database import db
    await db.products.delete_one({"id": product_id})
    return {"success": True}
