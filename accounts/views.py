from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.views.decorators.http import require_POST

from .forms import ProfileForm, ProfileLinkForm, RegisterForm, ResendVerificationForm
from .models import Profile, ProfileLink

User = get_user_model()


@login_required
@require_POST
def delete_profile_link(request, link_id):
    link = get_object_or_404(ProfileLink, pk=link_id, profile__user=request.user)

    link.delete()
    messages.success(request, "Link deleted successfully.")

    return redirect("accounts:edit_profile")


@login_required
def add_profile_link(request):
    profile, created = Profile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        form = ProfileLinkForm(request.POST)

        if form.is_valid():
            if profile.links.count() >= 10:
                messages.error(request, "You can add a maximum of 10 links.")
            else:
                link = form.save(commit=False)
                link.profile = profile
                link.save()

                messages.success(request, "Profile link added successfully.")
                return redirect("accounts:edit_profile")
    else:
        form = ProfileLinkForm()

    return render(
        request,
        "accounts/profile_link_form.html",
        {
            "form": form,
            "page_title": "Add Profile Link",
        },
    )


@login_required
def edit_profile_link(request, link_id):
    link = get_object_or_404(ProfileLink, pk=link_id, profile__user=request.user)

    if request.method == "POST":
        form = ProfileLinkForm(request.POST, instance=link)

        if form.is_valid():
            form.save()
            messages.success(request, "Profile link updated successfully.")
            return redirect("accounts:edit_profile")
    else:
        form = ProfileLinkForm(instance=link)

    return render(
        request,
        "accounts/profile_link_form.html",
        {
            "form": form,
            "page_title": "Edit Profile Link",
        },
    )


@login_required
def profile_view(request, username):
    profile_user = get_object_or_404(User, username=username)

    profile, created = Profile.objects.get_or_create(user=profile_user)

    posts = (
        profile_user.posts.select_related("author")
        .prefetch_related("media", "likes", "comments")
        .order_by("-created_at")
    )

    context = {
        "profile_user": profile_user,
        "profile": profile,
        "posts": posts,
        "post_count": posts.count(),
        "is_own_profile": request.user == profile_user,
        "profile_links": profile.links.all(),
    }

    return render(request, "accounts/profile.html", context)


@login_required
def edit_profile(request):
    profile, created = Profile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        form = ProfileForm(request.POST, request.FILES, instance=profile)

        if form.is_valid():
            form.save()

            messages.success(request, "Your profile has been updated successfully.")

            return redirect("accounts:profile", username=request.user.username)

        messages.error(request, "Please correct the errors below.")

    else:
        form = ProfileForm(instance=profile)

    return render(
        request,
        "accounts/edit_profile.html",
        {
            "form": form,
            "profile": profile,
        },
    )


def register_view(request):
    if request.user.is_authenticated:
        return redirect("posts:feed")
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            user.save()
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            verification_url = request.build_absolute_uri(
                reverse("accounts:verify_email", kwargs={"uidb64": uid, "token": token})
            )
            send_mail(
                "Verify your email address",
                (
                    f"Hi {user.username},\n\nThanks for registering with Social!\n\n"
                    f"Verify your email address using this link:\n{verification_url}\n\n"
                    "If you did not create this account, you can ignore this email."
                ),
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )
            return render(request, "accounts/check_email.html", {"email": user.email})
    else:
        form = RegisterForm()
    return render(request, "accounts/register.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("posts:feed")
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect("posts:feed")
    else:
        form = AuthenticationForm(request)
    return render(request, "accounts/login.html", {"form": form})


@require_POST
def logout_view(request):
    logout(request)
    return redirect("accounts:login")


def verify_email(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    if user is not None and default_token_generator.check_token(user, token):
        if not user.is_active:
            user.is_active = True
            user.save(update_fields=["is_active"])
        return render(request, "accounts/verification_success.html")
    return render(request, "accounts/verification_invalid.html", status=400)


def resend_verification_view(request):
    if request.method == "POST":
        form = ResendVerificationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"].strip()
            user = User.objects.filter(email__iexact=email, is_active=False).first()
            if user:
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                token = default_token_generator.make_token(user)
                verification_url = request.build_absolute_uri(
                    reverse(
                        "accounts:verify_email", kwargs={"uidb64": uid, "token": token}
                    )
                )
                send_mail(
                    "Verify your email address",
                    (
                        f"Hi {user.username},\n\nPlease verify your email address using this link:\n\n"
                        f"{verification_url}\n\nIf you did not request this email, ignore it."
                    ),
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    fail_silently=False,
                )
            return render(request, "accounts/resend_verification_done.html")
    else:
        form = ResendVerificationForm()
    return render(request, "accounts/resend_verification.html", {"form": form})
