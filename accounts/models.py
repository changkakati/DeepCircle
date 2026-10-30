from django.conf import settings
from django.db import models
from django.core.validators import URLValidator


class Profile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile"
    )

    full_name = models.CharField(max_length=100, blank=True)
    bio = models.CharField(max_length=250, blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)

    avatar = models.ImageField(upload_to="profile_pictures/", blank=True, null=True)

    cover_image = models.ImageField(upload_to="profile_covers/", blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user}'s profile"


class ProfileLink(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="links")

    title = models.CharField(max_length=50)
    url = models.URLField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.title} - {self.profile.user.username}"

    def clean(self):
        super().clean()

        # Only allow normal web links.
        validator = URLValidator(schemes=["http", "https"])
        validator(self.url)
