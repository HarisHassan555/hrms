"""
Query helpers for asset category choice fields.
"""

from asset.models import Asset, AssetCategory


def asset_categories_for_asset_form():
    """
    Categories for the Create Asset modal.

    Uses the company-scoped manager first, then unions any category that
    already has at least one visible asset (same scope as the grouped list
    on asset-category-view). That way categories shown on the page always
    appear in the dropdown even if company M2M data on the category row is
    missing or out of sync.
    """
    scoped_ids = set(AssetCategory.objects.values_list("pk", flat=True))
    used_by_visible_assets = set(
        Asset.objects.values_list("asset_category_id", flat=True).distinct()
    )
    category_ids = scoped_ids | used_by_visible_assets
    category_ids.discard(None)
    if not category_ids:
        return AssetCategory.objects.none()
    return (
        AssetCategory.objects.entire()
        .filter(pk__in=category_ids)
        .order_by("asset_category_name")
    )
