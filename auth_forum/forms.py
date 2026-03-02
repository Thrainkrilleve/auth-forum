from django import forms
from django.contrib.auth.models import Group

from .models import Board, Category


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "description", "order", "is_hidden"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "order": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "is_hidden": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class BoardForm(forms.ModelForm):
    class Meta:
        model = Board
        fields = ["category", "name", "description", "order", "is_hidden", "groups", "states"]
        widgets = {
            "category": forms.Select(attrs={"class": "form-select"}),
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "order": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "is_hidden": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "groups": forms.SelectMultiple(attrs={"class": "form-select", "size": "6"}),
            "states": forms.SelectMultiple(attrs={"class": "form-select", "size": "6"}),
        }
        help_texts = {
            "groups": "Hold Ctrl / Cmd to select multiple. Leave empty to allow all users with basic_access.",
            "states": "Hold Ctrl / Cmd to select multiple. Leave empty to allow all users with basic_access.",
        }
