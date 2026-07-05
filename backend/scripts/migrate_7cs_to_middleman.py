"""Flip 7C's Farmstead patches from `is_off_site` external referral products
to birthright-cart middleman products fulfilled via the vendor's custom-order
form.

After this migration:
  - Buyer adds a patch to the birthright cart at $10.
  - Buyer pays birthright via Stripe.
  - On success, birthright emails 7C's a link to their own prefilled Formester
    with everything already filled in, plus any files the buyer attached.
  - Admin reconciles wholesale ($5) with 7C's out-of-band.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database import db  # noqa: E402


# 7C's Formester config
FORM_BASE_URL = "https://ycrudzpz.formester.com/f/AiwxvFH2W"
FORM_QUERY_BASE = {"via": "birthright_7cs-farmstead"}

# Field name → source key. Sources are populated at dispatch time from the
# birthright order + shipping address.
FIELD_MAP = {
    "Name_First Name":            "first_name",
    "Name_Last Name":             "last_name",
    "Email":                      "email",
    "Phone":                      "phone",
    "Address_Street Address":     "address1",
    "Address_Street Address line 2": "address2",
    "Address_City":               "city",
    "Address_State/Province":     "state",
    "Address_Postal/Zip Code":    "postal_code",
    "Address_Country":            "country",
    # The buyer's product selection maps to the "Other" checkbox on 7C's form —
    # we then describe the actual patch in the Quantity + Message fields.
    "Product choices-7ea2b275-0c04-408f-8a36-cac2eb4917fe": "product_choice",
    "Quantity":                   "quantity_summary",
    "Message":                    "message",
    "How did you hear about us?": "referral_source",
}


async def main():
    query = {
        "$or": [
            {"vendor_slug": "7cs-farmstead"},
            {"slug": {"$regex": "^founder-patch-"}},
        ]
    }
    products = await db.products.find(query, {"_id": 0}).to_list(50)
    print(f"Migrating {len(products)} 7C's patches...")
    for p in products:
        update = {
            # Flip off_site → in-cart, fulfilled by vendor_custom_form
            "is_off_site": False,
            "fulfillable_via": "vendor_custom_form",
            "fulfillable_at": p.get("fulfillable_at") or None,
            "wholesale_price": 5.0,
            "vendor_slug": p.get("vendor_slug") or "7cs-farmstead",
            "vendor_name": p.get("vendor_name") or "7C's Farmstead",
            "vendor_form_url": FORM_BASE_URL,
            "vendor_form_query_base": FORM_QUERY_BASE,
            "vendor_form_field_map": FIELD_MAP,
            "vendor_referral_source": "Birthright",
            # Product-choice checkbox: patches map to "Other" on their form
            "vendor_product_choice_value": "Other",
        }
        await db.products.update_one({"id": p["id"]}, {"$set": update})
        print(f"  ✓ {p['name']}")
    print("\nDone.")


if __name__ == "__main__":
    asyncio.run(main())
