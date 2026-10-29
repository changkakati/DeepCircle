from django import forms
from django.core.exceptions import ValidationError

from .models import Post


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean

        if not data:
            return []

        files = data if isinstance(data, (list, tuple)) else [data]
        return [single_file_clean(item, initial) for item in files]


class PostForm(forms.ModelForm):
    media_files = MultipleFileField(
        required=False,
        label="Photos and videos",
    )

    MAX_FILES = 10
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB per file

    def clean_media_files(self):
        files = self.cleaned_data.get("media_files", [])

        if len(files) > self.MAX_FILES:
            raise ValidationError("You can upload up to 10 files.")

        allowed_extensions = {
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
            ".webp",
            ".mp4",
            ".webm",
            ".mov",
        }

        for file in files:
            extension = (
                "." + file.name.rsplit(".", 1)[-1].lower() if "." in file.name else ""
            )

            if extension not in allowed_extensions:
                raise ValidationError(f"Unsupported file type: {file.name}")

            if file.size > self.MAX_FILE_SIZE:
                raise ValidationError(f"{file.name} exceeds the 50 MB limit.")

        return files

    def clean(self):
        cleaned_data = super().clean()
        body = cleaned_data.get("body", "").strip()
        files = cleaned_data.get("media_files", [])

        if not body and not files:
            raise ValidationError("Write something or attach at least one media file.")

        return cleaned_data

    class Meta:
        model = Post
        fields = ["body"]
        widgets = {
            "body": forms.Textarea(
                attrs={
                    "placeholder": "What's happening?",
                    "rows": 4,
                    "class": "post-textarea",
                }
            ),
        }
