from pathlib import Path

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Exists, OuterRef
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import CommentForm, PostForm
from .models import Comment, Like, Post, PostMedia

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}


def save_post_media(post, uploaded_files):
    for uploaded_file in uploaded_files:
        extension = Path(uploaded_file.name).suffix.lower()
        media_type = (
            PostMedia.IMAGE if extension in IMAGE_EXTENSIONS else PostMedia.VIDEO
        )
        PostMedia.objects.create(post=post, file=uploaded_file, media_type=media_type)


def feed(request):
    posts = (
        Post.objects.select_related("author")
        .prefetch_related("media", "comments", "likes")
        .order_by("-created_at")
    )

    if request.user.is_authenticated:
        user_likes = Like.objects.filter(post=OuterRef("pk"), user=request.user)
        posts = posts.annotate(is_liked=Exists(user_likes))
    else:
        posts = posts.annotate(is_liked=Exists(Like.objects.none()))

    return render(
        request,
        "posts/feed.html",
        {
            "posts": posts,
        },
    )


def post_detail(request, post_id):
    post = get_object_or_404(
        Post.objects.select_related("author", "author__profile").prefetch_related(
            "media"
        ),
        pk=post_id,
    )
    comments = post.comments.select_related("author", "author__profile").all()
    context = {
        "post": post,
        "comments": comments,
        "comment_form": CommentForm(),
        "likes_count": post.likes.count(),
        "is_liked": post.likes.filter(user=request.user).exists(),
    }
    return render(request, "posts/post_detail.html", context)


@login_required
def edit_post(request, post_id):
    post = get_object_or_404(
        Post.objects.prefetch_related("media"), pk=post_id, author=request.user
    )
    if request.method == "POST":
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            requested_ids = request.POST.getlist("remove_media")
            media_to_remove = list(post.media.filter(pk__in=requested_ids))
            new_files = form.cleaned_data.get("media_files", [])
            with transaction.atomic():
                updated_post = form.save()
                for media in media_to_remove:
                    file_name = media.file.name
                    storage = media.file.storage
                    media.delete()
                    transaction.on_commit(lambda n=file_name, s=storage: s.delete(n))
                save_post_media(updated_post, new_files)
            return redirect("posts:post_detail", post_id=post.id)
    else:
        form = PostForm(instance=post)

    return render(
        request,
        "posts/edit_post.html",
        {"form": form, "post": post, "existing_media": post.media.all()},
    )


@login_required
@require_POST
def delete_post(request, post_id):
    post = get_object_or_404(Post, pk=post_id, author=request.user)
    media_files = [
        (item.file.storage, item.file.name) for item in post.media.all() if item.file
    ]
    with transaction.atomic():
        post.delete()
        for storage, name in media_files:
            transaction.on_commit(lambda s=storage, n=name: s.delete(n))
    return redirect("posts:feed")


@login_required
@require_POST
def toggle_like(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    like, created = Like.objects.get_or_create(post=post, user=request.user)
    if not created:
        like.delete()
    next_url = request.POST.get("next", "")
    if next_url and url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return redirect(next_url)
    return redirect("posts:post_detail", post_id=post.id)


@login_required
@require_POST
def add_comment(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.post = post
        comment.author = request.user
        comment.save()
    response = redirect("posts:post_detail", post_id=post.id)
    response["Location"] += "#comments"
    return response


@login_required
@require_POST
def delete_comment(request, comment_id):
    comment = get_object_or_404(Comment, pk=comment_id)
    if comment.author_id != request.user.id:
        return HttpResponseForbidden("You cannot delete someone else's comment.")
    post_id = comment.post_id
    comment.delete()
    response = redirect("posts:post_detail", post_id=post_id)
    response["Location"] += "#comments"
    return response
