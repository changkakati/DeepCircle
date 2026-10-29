from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.views.decorators.http import require_POST

from config import settings

from .forms import RegisterForm, ResendVerificationForm

User = get_user_model()


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
                reverse(
                    "accounts:verify_email",
                    kwargs={"uidb64": uid, "token": token},
                )
            )

            subject = "Verify your email address"
            message = (
                f"Hi {user.username},\n\n"
                "Thanks for registering with Social!\n\n"
                "Please verify your email address using this link:\n"
                f"{verification_url}\n\n"
                "If you did not create this account, you can ignore this email."
            )

            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )

            return render(
                request,
                "accounts/check_email.html",
                {"email": user.email},
            )
    else:
        form = RegisterForm()

    return render(request, "accounts/register.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("posts:feed")

    if request.method == "POST":
        form = AuthenticationForm(
            request,
            data=request.POST,
        )

        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect("posts:feed")
    else:
        form = AuthenticationForm(request)

    return render(
        request,
        "accounts/login.html",
        {
            "form": form,
        },
    )


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

    return render(
        request,
        "accounts/verification_invalid.html",
        status=400,
    )


def resend_verification_view(request):
    if request.method == "POST":
        form = ResendVerificationForm(request.POST)

        if form.is_valid():
            email = form.cleaned_data["email"].strip()

            user = User.objects.filter(
                email__iexact=email,
                is_active=False,
            ).first()

            if user:
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                token = default_token_generator.make_token(user)

                verification_url = request.build_absolute_uri(
                    reverse(
                        "accounts:verify_email",
                        kwargs={"uidb64": uid, "token": token},
                    )
                )

                send_mail(
                    subject="Verify your email address",
                    message=(
                        f"Hi {user.username},\n\n"
                        "Please verify your email address using this link:\n\n"
                        f"{verification_url}\n\n"
                        "If you did not request this email, you can ignore it."
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=False,
                )

            return render(
                request,
                "accounts/resend_verification_done.html",
            )
    else:
        form = ResendVerificationForm()

    return render(
        request,
        "accounts/resend_verification.html",
        {"form": form},
    )
