from django.urls import path

from . import views


app_name = "generator"

urlpatterns = [
	path("", views.project_list, name="project_list"),
	path("projects/create/", views.project_create, name="project_create"),
	path("projects/<int:project_id>/", views.project_detail, name="project_detail"),
	path("projects/<int:project_id>/edit/", views.project_edit, name="project_edit"),
	path("projects/<int:project_id>/delete/", views.project_delete, name="project_delete"),
	path("projects/<int:project_id>/services/create/", views.service_create, name="service_create"),
	path("projects/<int:project_id>/services/<int:service_id>/edit/", views.service_edit, name="service_edit"),
	path("projects/<int:project_id>/services/<int:service_id>/delete/", views.service_delete, name="service_delete"),
]
