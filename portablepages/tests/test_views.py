from __future__ import annotations

from django.test import TestCase
from django.urls import reverse
from wagtail.core.models import Site
from wagtail.test.testapp.models import StreamPage
from wagtail.test.utils import WagtailTestUtils

from portablepages.utils import zip_page


class ExportViewTestCase(TestCase, WagtailTestUtils):
    def setUp(self):
        self.root_page = Site.objects.get(is_default_site=True).root_page
        self.page = StreamPage(
            title="Test page",
            slug="test-page",
            body=[("text", "Hello, world!")],
            live=True,
        )
        self.root_page.add_child(instance=self.page)
        self.page.save()

    def test_export_view(self):
        self.login()
        response = self.client.get(
            reverse("export_page", kwargs={"page_id": self.page.id})
        )
        self.assertEqual(response.status_code, 200)

        self.assertIn("Content-Disposition", response.headers)
        self.assertEqual(
            response.headers["Content-Disposition"],
            "attachment; filename=test-page.zip",
        )

        self.assertIn("Content-Type", response.headers)
        self.assertEqual(response.headers["Content-Type"], "application/zip")


class ImportViewTestCase(TestCase, WagtailTestUtils):
    def setUp(self):
        self.root_page = Site.objects.get(is_default_site=True).root_page

    def test_import_view_post_file(self):
        # Zip up a test page
        test_page = StreamPage(
            title="Test page",
            slug="test-page",
            body=[("text", "Hello, world!")],
            live=True,
        )
        zipbytes = zip_page(test_page)
        zipbytes.seek(0)

        # Log in and post it
        self.login()
        response = self.client.post(
            reverse("import_page", kwargs={"page_id": self.root_page.id}),
            {"page_zip_file": zipbytes},
        )
        self.assertEqual(response.status_code, 302)
        self.root_page.refresh_from_db()

        self.assertEqual(len(self.root_page.get_children()), 1)
        new_page = self.root_page.get_children().first()

        self.assertRedirects(
            response,
            reverse(
                "wagtailadmin_pages:edit", kwargs={"page_id": new_page.id}
            ),
            status_code=302,
        )

    def test_import_view_post_invalid(self):
        self.login()
        response = self.client.post(
            reverse("import_page", kwargs={"page_id": self.root_page.id}),
            {},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("form", response.context)
        self.assertIn("page_zip_file", response.context["form"].errors)

    def test_import_view_get(self):
        self.login()
        response = self.client.get(
            reverse("import_page", kwargs={"page_id": self.root_page.id}),
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("form", response.context)
