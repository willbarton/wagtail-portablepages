from __future__ import annotations

import io
import json
import logging
import uuid
import zipfile
from typing import IO, Optional

from django.apps import apps
from django.core.serializers.json import DjangoJSONEncoder
from wagtail.core.utils import find_available_slug
from wagtail.models import Page

logger = logging.getLogger("portablepages")


def export_page(page: Page) -> str:
    # Get a self-contained copy of the page as JSON, including its app label
    # and model name.
    # serializable_data comes from django-modelcluster
    page_data = {
        "app_label": page.content_type.app_label,
        "model": page.content_type.model,
        "data": page.serializable_data(),
    }

    # Dump the page data to JSON
    page_json = json.dumps(
        page_data, ensure_ascii=False, indent=4, cls=DjangoJSONEncoder
    )

    logger.info(f"Exported {page.slug} to JSON")

    print(page_json)

    return page_json


def zip_page(page: Page, outfile: Optional[IO[bytes]] = None) -> IO[bytes]:
    if outfile is None:
        outfile = io.BytesIO()
        outfile.name = f"{page.slug}.zip"

    page_json = export_page(page)

    # Create a zip file with our page data using outbytes
    with zipfile.ZipFile(outfile, "w") as zip_file:
        with zip_file.open(f"{page.slug}.json", "w") as json_file:
            json_file.write(page_json.encode("utf-8"))

    logger.info(f"Compressed {page.slug} export to zip file")

    return outfile


def import_page(parent_page: Page, page_json: str, slug: Optional[str] = None):
    page_data = json.loads(page_json)

    # Get the specific model that the imported page belongs to
    model = apps.get_model(page_data["app_label"], page_data["model"])

    # Construct a bare Page object first to get the treebeard
    # assignments right.
    # from_serializable_data comes from django-modelcluster
    # page = Page.from_serializable_data(page_data["data"])
    page = model.from_serializable_data(page_data["data"])

    # Import with a different slug if a page already exists with the imported
    # slug.
    page.slug = find_available_slug(parent_page, page.slug)

    # These will all be set appropriate when we call add_child on parent_page
    page.pk = None
    page.path = None
    page.depth = None
    page.numchild = 0
    page.url_path = None

    # Generate a new translation key
    # TODO: This is probably the wrong thing to do here.
    page.translation_key = uuid.uuid4()

    # All imported pages will be drafts by default
    page.live = False

    # Add the page to the parent
    parent_page.add_child(instance=page)

    logger.info(f"Imported {page.slug} as child of {parent_page.slug}")
    print(f"Imported {page.slug} as child of {parent_page.slug}")

    return page


def unzip_page(parent_page: Page, infile: IO[bytes]):
    with zipfile.ZipFile(infile, "r") as zip_file:
        for filename in zip_file.namelist():
            with zip_file.open(filename, "r") as json_file:
                try:
                    page = import_page(
                        parent_page, json_file.read().decode("utf8")
                    )
                except TypeError:
                    logger.error(f"Error importing {filename}")
                else:
                    return page
