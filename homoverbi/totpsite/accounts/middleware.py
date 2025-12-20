from django.shortcuts import redirect
from django.urls import reverse

class RequireVerifiedTOTP:
    """Block access to the site unless user is authenticated AND OTP-verified.
    Allow access to auth endpoints and admin.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path

        # Allow these paths without OTP
        allowed_prefixes = (
            "/accounts/login/",
            "/accounts/logout/",
            "/accounts/signup/",
            "/admin/",
            "/static/",
        )
        if path.startswith(allowed_prefixes):
            return self.get_response(request)

        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return redirect(reverse("login"))

        # django-otp provides is_verified()
        if not getattr(user, "is_verified", lambda: False)():
            # If user is logged in but not verified, force them to login again (with token)
            return redirect(reverse("login"))

        return self.get_response(request)
