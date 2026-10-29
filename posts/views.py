from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import redirect, render

from .forms import PostForm
from .models import Post, PostMedia


@login_required
def feed(request):
    if request.method == "POST":
        form = PostForm(request.POST, request.FILES)

        if form.is_valid():
            with transaction.atomic():
                post = form.save(commit=False)
                post.author = request.user
                post.save()

                for uploaded_file in form.cleaned_data["media_files"]:
                    content_type = getattr(uploaded_file, "content_type", "") or ""

                    if content_type.startswith("image/"):
                        media_type = "image"
                    elif content_type.startswith("video/"):
                        media_type = "video"
                    else:
                        raise ValidationError("Unsupported media content type.")

                    PostMedia.objects.create(
                        post=post,
                        file=uploaded_file,
                        media_type=media_type,
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
def delete_post(request, post_id):
    if request.method == "POST":
        post = Post.objects.filter(
            id=post_id,
            author=request.user,
        ).first()

        if post:
            post.delete()

    return redirect("posts:feed")
