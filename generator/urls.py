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
	path("projects/<int:project_id>/options/create/", views.option_create, name="option_create"),
	path("projects/<int:project_id>/options/<int:option_id>/edit/", views.option_edit, name="option_edit"),
	path("projects/<int:project_id>/options/<int:option_id>/delete/", views.option_delete, name="option_delete"),
	path("projects/<int:project_id>/networks/create/", views.network_create, name="network_create"),
	path("projects/<int:project_id>/networks/<int:network_id>/edit/", views.network_edit, name="network_edit"),
	path("projects/<int:project_id>/networks/<int:network_id>/delete/", views.network_delete, name="network_delete"),
	path("projects/<int:project_id>/volumes/create/", views.volume_create, name="volume_create"),
	path("projects/<int:project_id>/volumes/<int:volume_id>/edit/", views.volume_edit, name="volume_edit"),
	path("projects/<int:project_id>/volumes/<int:volume_id>/delete/", views.volume_delete, name="volume_delete"),
]
