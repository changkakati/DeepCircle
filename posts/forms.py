from pathlib import Path

from django import forms
from django.core.exceptions import ValidationError

from .models import Comment, Post


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault(
            "widget",
            MultipleFileInput(
                attrs={
                    "accept": (
                        "image/jpeg,image/png,image/gif,image/webp,"
                        "video/mp4,video/webm,video/quicktime"
                    )
                }
            ),
        )
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        if not data:
            return []
        files = data if isinstance(data, (list, tuple)) else [data]
        return [super(MultipleFileField, self).clean(file, initial) for file in files]


class PostForm(forms.ModelForm):
    media_files = MultipleFileField(required=False, label="Photos and videos")

    MAX_FILES = 10
    MAX_FILE_SIZE = 50 * 1024 * 1024
    IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
    VIDEO_EXTENSIONS = {".mp4", ".webm", ".mov"}

    def clean_media_files(self):
        files = self.cleaned_data.get("media_files", [])
        if len(files) > self.MAX_FILES:
            raise ValidationError("You can upload a maximum of 10 media files per post.")

        for uploaded_file in files:
            extension = Path(uploaded_file.name).suffix.lower()
            if extension not in self.IMAGE_EXTENSIONS | self.VIDEO_EXTENSIONS:
                raise ValidationError(
                    f"Unsupported file type: {uploaded_file.name}. Use JPG, PNG, GIF, WEBP, MP4, WEBM or MOV."
                )
            if uploaded_file.size > self.MAX_FILE_SIZE:
                raise ValidationError(f"{uploaded_file.name} exceeds the 50 MB per-file limit.")
            content_type = getattr(uploaded_file, "content_type", None)
            if content_type:
                if extension in self.IMAGE_EXTENSIONS and not content_type.startswith("image/"):
                    raise ValidationError(f"{uploaded_file.name} does not appear to be an image.")
                if extension in self.VIDEO_EXTENSIONS and not content_type.startswith("video/"):
                    raise ValidationError(f"{uploaded_file.name} does not appear to be a video.")
        return files

    def clean(self):
        cleaned_data = super().clean()
        body = (cleaned_data.get("body") or "").strip()
        files = cleaned_data.get("media_files", [])
        has_existing_media = False

        if self.instance and self.instance.pk:
            remove_ids = self.data.getlist("remove_media") if hasattr(self.data, "getlist") else []
            has_existing_media = self.instance.media.exclude(pk__in=remove_ids).exists()
            if has_existing_media and len(remove_ids) > self.instance.media.count():
                remove_ids = remove_ids[: self.instance.media.count()]

            remaining_count = self.instance.media.exclude(pk__in=remove_ids).count()
            if remaining_count + len(files) > self.MAX_FILES:
                raise ValidationError(
                    "A post can contain a maximum of 10 media files. Remove existing files before adding more."
                )

        if not body and not files and not has_existing_media:
            raise ValidationError("Write something or attach at least one photo or video.")

        cleaned_data["body"] = body
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
                    "maxlength": 5000,
                }
            )
        }


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ["body"]
        widgets = {
            "body": forms.Textarea(
                attrs={
                    "rows": 2,
                    "placeholder": "Write a comment...",
                    "class": "comment-input",
                    "maxlength": 1000,
                }
            )
        }

    def clean_body(self):
        body = self.cleaned_data["body"].strip()
        if not body:
            raise ValidationError("Comment cannot be empty.")
        return body
