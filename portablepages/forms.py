from __future__ import annotations

from django import forms


class ImportForm(forms.Form):
    page_zip_file = forms.FileField(label="Page zip file", required=True)
