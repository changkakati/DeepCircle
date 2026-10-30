from django.urls import path

from . import views

app_name = "posts"

urlpatterns = [
    path("", views.feed, name="feed"),
    path("<int:post_id>/", views.post_detail, name="post_detail"),
    path("<int:post_id>/edit/", views.edit_post, name="edit_post"),
    path("<int:post_id>/delete/", views.delete_post, name="delete_post"),
]
