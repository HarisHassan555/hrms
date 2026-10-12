from __future__ import annotations

from asset.models import AssetCategory, AssetGeneralSetting, AssetLot

from .organization_seeder import get_seed_companies
from .utils import SeederResult, record, set_m2m, upsert


ASSET_CATEGORIES = [
    {
        "asset_category_name": "Laptop",
        "asset_category_description": "Portable computers assigned to employees.",
    },
    {
        "asset_category_name": "Desktop",
        "asset_category_description": "Desktop workstations and fixed computers.",
    },
    {
        "asset_category_name": "Mobile Phone",
        "asset_category_description": "Company-owned mobile phones.",
    },
    {
        "asset_category_name": "Office Equipment",
        "asset_category_description": "Shared office devices and equipment.",
    },
]

ASSET_LOTS = [
    {
        "lot_number": "DEFAULT-ASSET-BATCH",
        "lot_description": "Default batch for imported or initial company assets.",
    }
]


def seed() -> SeederResult:
    result = SeederResult()
    companies = get_seed_companies()

    for item in ASSET_CATEGORIES:
        category, status = upsert(
            AssetCategory,
            {"asset_category_name": item["asset_category_name"]},
            {"asset_category_description": item["asset_category_description"]},
        )
        m2m_status = set_m2m(category, "company_id", companies)
        if status == "existing" and m2m_status == "updated":
            status = "updated"
        record(result, status, "Asset Category", category)

    for item in ASSET_LOTS:
        lot, status = upsert(
            AssetLot,
            {"lot_number": item["lot_number"]},
            {"lot_description": item["lot_description"]},
        )
        m2m_status = set_m2m(lot, "company_id", companies)
        if status == "existing" and m2m_status == "updated":
            status = "updated"
        record(result, status, "Asset Batch", lot)

    for company in companies:
        setting, status = upsert(
            AssetGeneralSetting,
            {"company_id": company},
            {"enable_asset_fine": False},
        )
        record(result, status, "Asset General Setting", setting)

    return result
