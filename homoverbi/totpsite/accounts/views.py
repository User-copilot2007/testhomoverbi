import base64
from io import BytesIO
import base64 as _b64

import qrcode
import pyotp
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from django_otp import login as otp_login
from django_otp.plugins.otp_totp.models import TOTPDevice

from .models import PendingSignup, EulaAcceptance

EULA_SHA256 = "6fe894f1dbd712c6fee08ee4b318db5acad757fceca7672a1f02643d676649ba"

def _qr_png_data_uri(otpauth_url: str) -> str:
    img = qrcode.make(otpauth_url)
    buf = BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def _get_signup_secret(request: HttpRequest) -> str:
    """Return a stable base32 secret for the current signup page (stored in session)."""
    secret = request.session.get("signup_totp_secret")
    if not secret:
        secret = pyotp.random_base32()
        request.session["signup_totp_secret"] = secret
    return secret


def _base32_to_bytes(secret_b32: str) -> bytes:
    """Decode a Base32 secret (without requiring correct padding)."""
    s = (secret_b32 or "").strip().replace(" ", "").upper()
    # Base32 decoding requires padding to a multiple of 8.
    pad = (-len(s)) % 8
    if pad:
        s += "=" * pad
    return _b64.b32decode(s, casefold=True)

@require_http_methods(["GET", "POST"])
def signup(request: HttpRequest) -> HttpResponse:
    issuer = "totpsite"
    secret = _get_signup_secret(request)
    # We don't know the username yet on GET, so use a neutral label. Users can rename it in their app.
    otpauth_url = pyotp.totp.TOTP(secret).provisioning_uri(name="signup", issuer_name=issuer)
    qr_data = _qr_png_data_uri(otpauth_url)

    if request.method == "GET":
        return render(
            request,
            "registration/signup.html",
            {"qr_data": qr_data, "secret": secret},
        )

    username = (request.POST.get("username") or "").strip()
    password1 = request.POST.get("password1") or ""
    password2 = request.POST.get("password2") or ""
    token = (request.POST.get("token") or "").strip()

    if not username or not password1 or not password2 or not token:
        # accept_eula checked below
        messages.error(request, "Заповни username, password, repeat password і TOTP код.")
        return render(request, "registration/signup.html", {"qr_data": qr_data, "secret": secret}, status=400)

    if password1 != password2:
        messages.error(request, "Паролі не співпадають.")
        return render(request, "registration/signup.html", {"qr_data": qr_data, "secret": secret}, status=400)

    if User.objects.filter(username=username).exists():
        messages.error(request, "Такий username вже існує.")
        return render(request, "registration/signup.html", {"qr_data": qr_data, "secret": secret}, status=400)

    if not token.isdigit():
        messages.error(request, "TOTP код має бути 6 цифр.")
        return render(request, "registration/signup.html", {"qr_data": qr_data, "secret": secret}, status=400)

    totp = pyotp.TOTP(secret)
    if not totp.verify(token, valid_window=1):
        messages.error(request, "Невірний TOTP код. Перевір, що додаток вже бачить цей QR/secret.")
        return render(request, "registration/signup.html", {"qr_data": qr_data, "secret": secret}, status=400)

    # Create user and attach a confirmed TOTP device.
    user = User.objects.create_user(username=username, password=password1)

    EulaAcceptance.objects.create(user=user, document_sha256=EULA_SHA256, document_name='eula.pdf')


    # django-otp stores the secret as a HEX string in TOTPDevice.key.
    # Passing bytes will break later with "Odd-length string" when the model tries to hex-decode.
    key_bytes = _base32_to_bytes(secret)
    device = TOTPDevice.objects.create(
        user=user,
        confirmed=True,
        name="default",
        key=key_bytes.hex(),
    )

    # Clean up any previous 2-step artifacts (harmless if unused)
    PendingSignup.objects.filter(user=user).delete()
    request.session.pop("signup_totp_secret", None)

    login(request, user)
    otp_login(request, device)
    return redirect("/")

@require_http_methods(["GET", "POST"])
def login_view(request: HttpRequest) -> HttpResponse:
    if request.method == "GET":
        return render(request, "registration/login.html")

    username = (request.POST.get("username") or "").strip()
    password = request.POST.get("password") or ""
    token = (request.POST.get("token") or "").strip()

    user = authenticate(request, username=username, password=password)
    if user is None:
        messages.error(request, "Невірний username або password.")
        return render(request, "registration/login.html", status=400)

    if not user.is_active:
        messages.error(request, "Акаунт не активований. Заверши налаштування TOTP (реєстрацію).")
        return render(request, "registration/login.html", status=403)

    # Require confirmed TOTP device
    device = TOTPDevice.objects.filter(user=user, confirmed=True).order_by("-id").first()
    if not device:
        messages.error(request, "У акаунта немає підтвердженого TOTP. Вхід заборонено.")
        return render(request, "registration/login.html", status=403)

    if not token.isdigit():
        messages.error(request, "Потрібен TOTP код (6 цифр).")
        return render(request, "registration/login.html", status=400)

    if not device.verify_token(token):
        messages.error(request, "Невірний TOTP код.")
        return render(request, "registration/login.html", status=400)

    login(request, user)
    otp_login(request, device)
    return redirect("/")

@require_http_methods(["POST"])
def logout_view(request: HttpRequest) -> HttpResponse:
    logout(request)
    return redirect(reverse("login"))

def home(request: HttpRequest) -> HttpResponse:
    return render(request, "home.html")
