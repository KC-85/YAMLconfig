from django.contrib import admin

from .models import ConfigProject, NamedVolume, Network, ProjectOption, Service


@admin.register(ConfigProject)
class ConfigProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "target_type", "updated_at", "created_at")
    list_filter = ("target_type", "created_at", "updated_at")
    search_fields = ("name",)


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "project", "image", "container_name")
    list_filter = ("project",)
    search_fields = ("name", "project__name", "image", "container_name")


@admin.register(ProjectOption)
class ProjectOptionAdmin(admin.ModelAdmin):
    list_display = ("key", "project", "value")
    list_filter = ("project",)
    search_fields = ("key", "project__name", "value")


@admin.register(Network)
class NetworkAdmin(admin.ModelAdmin):
    list_display = ("name", "project", "driver", "external", "internal", "attachable")
    list_filter = ("project", "external", "internal", "attachable")
    search_fields = ("name", "project__name", "driver")


@admin.register(NamedVolume)
class NamedVolumeAdmin(admin.ModelAdmin):
    list_display = ("name", "project", "driver", "external")
    list_filter = ("project", "external")
    search_fields = ("name", "project__name", "driver")
