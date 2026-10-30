from pathlib import Path

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import PostForm
from .models import Post, PostMedia


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}


def save_post_media(post, uploaded_files):
    """Save uploaded images and videos for a post."""
    for uploaded_file in uploaded_files:
        extension = Path(uploaded_file.name).suffix.lower()

        if extension in IMAGE_EXTENSIONS:
            media_type = PostMedia.IMAGE
        else:
            media_type = PostMedia.VIDEO

        PostMedia.objects.create(
            post=post,
            file=uploaded_file,
            media_type=media_type,
        )


def delete_media_file(media):
    """Delete the stored file and its database record."""
    if media.file:
        media.file.delete(save=False)
    media.delete()


@login_required
def feed(request):
    if request.method == "POST":
        form = PostForm(request.POST, request.FILES)

        if form.is_valid():
            with transaction.atomic():
                post = form.save(commit=False)
                post.author = request.user
                post.save()

                save_post_media(
                    post,
                    form.cleaned_data["media_files"],
                )

            return redirect("posts:feed")
    else:
        form = PostForm()

    posts = Post.objects.select_related("author").prefetch_related("media")

    return render(
        request,
        "posts/feed.html",
        {
            "form": form,
            "posts": posts,
        },
    )


@login_required
def post_detail(request, post_id):
    post = get_object_or_404(
        Post.objects.select_related("author").prefetch_related("media"),
        pk=post_id,
    )

    return render(
        request,
        "posts/post_detail.html",
        {"post": post},
    )


@login_required
def edit_post(request, post_id):
    post = get_object_or_404(
        Post.objects.prefetch_related("media"),
        pk=post_id,
        author=request.user,
    )

    if request.method == "POST":
        form = PostForm(request.POST, request.FILES, instance=post)

        if form.is_valid():
            remove_ids = request.POST.getlist("remove_media")

            media_to_remove = list(post.media.filter(pk__in=remove_ids))

            remaining_count = post.media.count() - len(media_to_remove)
            new_files = form.cleaned_data["media_files"]

            if remaining_count + len(new_files) > 10:
                form.add_error(
                    None,
                    ValidationError(
                        "A post can contain a maximum of 10 media files. "
                        "Remove some existing files before adding more."
                    ),
                )
            else:
                with transaction.atomic():
                    updated_post = form.save()

                    for media in media_to_remove:
                        delete_media_file(media)

                    save_post_media(updated_post, new_files)

                return redirect(
                    "posts:post_detail",
                    post_id=post.id,
                )

    else:
        form = PostForm(instance=post)

    return render(
        request,
        "posts/edit_post.html",
        {
            "form": form,
            "post": post,
            "existing_media": post.media.all(),
        },
    )


@login_required
@require_POST
def delete_post(request, post_id):
    post = get_object_or_404(
        Post.objects.prefetch_related("media"),
        pk=post_id,
        author=request.user,
    )

    with transaction.atomic():
        for media in post.media.all():
            if media.file:
                media.file.delete(save=False)

        post.delete()

    return redirect("posts:feed")
