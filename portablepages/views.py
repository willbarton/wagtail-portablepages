from __future__ import annotations

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from wagtail.models import Page

from portablepages.forms import ImportForm
from portablepages.utils import unzip_page, zip_page


def export_view(request: HttpRequest, page_id: int) -> HttpResponse:
    page = get_object_or_404(Page, id=page_id).specific
    page_bytes = zip_page(page)
    response = HttpResponse(page_bytes, content_type="application/zip")
    response["Content-Disposition"] = f"attachment; filename={page.slug}.zip"
    return response


def import_view(request: HttpRequest, page_id: int) -> HttpResponse:
    parent_page = get_object_or_404(Page, id=page_id).specific

    if request.method == "POST":
        input_form = ImportForm(request.POST, request.FILES)

        if input_form.is_valid():
            zipbytes = request.FILES["page_zip_file"]
            new_page = unzip_page(parent_page, zipbytes)
            return redirect("wagtailadmin_pages:edit", new_page.id)
    else:
        input_form = ImportForm()

    return TemplateResponse(
        request,
        "portablepages/import_page.html",
        {
            "parent_page": parent_page,
            "form": input_form,
        },
    )
