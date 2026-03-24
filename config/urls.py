"""URL configuration for YAMLconfig project."""

from django.contrib import admin
from django.urls import include, path


urlpatterns = [
	path("admin/", admin.site.urls),
	path("accounts/", include("django.contrib.auth.urls")),
	# path("accounts/", include("allauth.urls")),  # re-enable once allauth is configured
	path("", include("generator.urls")),
]
