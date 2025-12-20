from django.contrib import admin

from .models import PendingSignup, EulaAcceptance

admin.site.register(PendingSignup)
admin.site.register(EulaAcceptance)
