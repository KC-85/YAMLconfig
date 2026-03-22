from django.urls import path
from django.views.generic import TemplateView


app_name = "generator"

urlpatterns = [
	path("", TemplateView.as_view(template_name="generator/index.html"), name="index"),
]
