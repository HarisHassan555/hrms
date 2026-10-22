"""Create-asset modal category dropdown queryset."""

from django.test import TestCase

from asset.category_queryset import asset_categories_for_asset_form
from asset.forms import AssetForm
from asset.models import AssetCategory
from horilla.testkit import CompanyFilterTestMixin, make_company


class AssetFormCategoryQuerysetTests(CompanyFilterTestMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.company_a = make_company("Asset Form Co A")
        cls.company_b = make_company(
            "Asset Form Co B",
            address="2 Test St",
            city="Testville",
            zip="00002",
        )
        cls.category_no_company = AssetCategory.objects.create(
            asset_category_name="Orphan Category",
            asset_category_description="No company M2M",
        )
        cls.category_b = AssetCategory.objects.create(
            asset_category_name="Company B Category",
            asset_category_description="Linked to B",
        )
        cls.category_b.company_id.add(cls.company_b)

    def test_orphan_category_included_without_company_m2m(self):
        self.set_company_context(self.company_a.pk)
        qs = asset_categories_for_asset_form()
        self.assertIn(self.category_no_company, list(qs))

    def test_company_scoped_category_visible_for_matching_company(self):
        self.set_company_context(self.company_b.pk)
        qs = asset_categories_for_asset_form()
        self.assertIn(self.category_b, list(qs))

    def test_asset_form_html_includes_category_options(self):
        self.set_company_context(self.company_b.pk)
        html = str(AssetForm()["asset_category_id"])
        self.assertIn(f'value="{self.category_b.pk}"', html)
        self.assertIn("Company B Category", html)

