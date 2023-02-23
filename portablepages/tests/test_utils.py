from __future__ import annotations

import io
import json
import zipfile

from django.test import TestCase
from wagtail.core.models import Site
from wagtail.test.testapp.models import StreamPage

from portablepages.utils import export_page, import_page, unzip_page, zip_page


class ExportPageTestCase(TestCase):
    def setUp(self):
        self.page = StreamPage(
            title="Test page",
            slug="test-page",
            body=[("text", "Hello, world!")],
            live=True,
        )

    def test_export_page(self):
        page_json = export_page(self.page)

        page_data = json.loads(page_json)

        self.assertEqual(page_data["app_label"], "tests")
        self.assertEqual(page_data["model"], "streampage")
        self.assertEqual(page_data["data"]["title"], self.page.title)
        self.assertEqual(page_data["data"]["slug"], self.page.slug)

        self.assertListEqual(
            json.loads(page_data["data"]["body"]),
            list(self.page.body.raw_data),
        )

    def test_zip_page(self):
        zipbytes = zip_page(self.page)

        with zipfile.ZipFile(zipbytes, "r") as zip_file:
            self.assertIn(f"{self.page.slug}.json", zip_file.namelist())


class ImportPageTestCase(TestCase):
    def setUp(self):
        self.root_page = Site.objects.get(is_default_site=True).root_page
        self.original_page = StreamPage(
            title="Test page",
            slug="test-page",
            body=[("text", "Hello, world!")],
            live=True,
        )
        self.page_json = export_page(self.original_page)
        self.zipbytes = zip_page(self.original_page)

    def test_import_page(self):
        page = import_page(self.root_page, self.page_json)

        self.assertEqual(page.title, self.original_page.title)
        self.assertEqual(page.slug, self.original_page.slug)
        self.assertEqual(page.body, self.original_page.body)

    def test_unzip_page(self):
        self.assertTrue(len(self.root_page.get_children()) == 0)

        unzip_page(self.root_page, self.zipbytes)

        self.assertTrue(len(self.root_page.get_children()) == 1)

        page = self.root_page.get_children()[0].specific
        self.assertEqual(page.title, self.original_page.title)
        self.assertEqual(page.slug, self.original_page.slug)
        self.assertEqual(page.body, self.original_page.body)

    def test_unzip_page_invalid_page_export(self):
        invalid_zipbytes = io.BytesIO()
        with zipfile.ZipFile(invalid_zipbytes, "w") as zip_file:
            with zip_file.open("test.json", "w") as json_file:
                json_file.write("null".encode("utf-8"))

        with self.assertLogs("portablepages", level="ERROR") as logfile:
            unzip_page(self.root_page, invalid_zipbytes)

        self.assertIn(
            "ERROR:portablepages:Error importing test.json", logfile.output
        )
