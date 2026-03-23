from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from .forms import (
    ConfigProjectForm,
    NamedVolumeForm,
    NetworkForm,
    ProjectOptionForm,
    ServiceForm,
)
from .models import (
    ConfigProject,
    NamedVolume,
    Network,
    ProjectOption,
    Service,
)

def project_list(request: HttpRequest) -> HttpResponse:
    projects = ConfigProject.objects.all()
    return render(request, "generator/index.html", {"projects": projects})

def project_detail(request: HttpRequest, project_id: int) -> HttpResponse:
    project = get_object_or_404(ConfigProject, id=project_id)
    services = project.services.all()
    options = project.options.all()
    networks = project.networks.all()
    volumes = project.volumes.all()

    return render(
        request,
        "generator/index.html",
        {
            "project": project,
            "services": services,
            "options": options,
            "networks": networks,
            "volumes": volumes,
        },
    )

def project_create(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = ConfigProjectForm(request.POST)
        if form.is_valid():
            project = form.save()
            messages.success(request, "Project created successfully.")
            return redirect("generator:project_detail", project_id=project.id)
    else:
        form = ConfigProjectForm()

    return render(request, "generator/index.html", {"form": form})

def project_edit(request: HttpRequest, project_id: int) -> HttpResponse:
    project = get_object_or_404(ConfigProject, id=project_id)

    if request.method == "POST":
        form = ConfigProjectForm(request.POST, instance=project)
        if form.is_valid():
            form.save()
            messages.success(request, "Project updated successfully.")
            return redirect("generator:project_detail", project_id=project.id)
    else:
        form = ConfigProjectForm(instance=project)

    return render(request, "generator/index.html", {"form": form, "project": project})

def project_delete(request: HttpRequest, project_id: int) -> HttpResponse:
    project = get_object_or_404(ConfigProject, id=project_id)

    if request.method == "POST":
        project.delete()
        messages.success(request, "Project deleted successfully.")
        return redirect("generator:project_list")

    return render(request, "generator/index.html", {"project": project})


def service_create(request: HttpRequest, project_id: int) -> HttpResponse:
    project = get_object_or_404(ConfigProject, id=project_id)

    if request.method == "POST":
        form = ServiceForm(request.POST)
        if form.is_valid():
            service = form.save(commit=False)
            service.project = project
            service.save()
            messages.success(request, "Service created successfully.")
            return redirect("generator:project_detail", project_id=project.id)
    else:
        form = ServiceForm()

    return render(request, "generator/index.html", {"form": form, "project": project})

def service_edit(request: HttpRequest, project_id: int, service_id: int) -> HttpResponse:
    project = get_object_or_404(ConfigProject, id=project_id)
    service = get_object_or_404(Service, id=service_id, project=project)

    if request.method == "POST":
        form = ServiceForm(request.POST, instance=service)
        if form.is_valid():
            form.save()
            messages.success(request, "Service updated successfully.")
            return redirect("generator:project_detail", project_id=project.id)
    else:
        form = ServiceForm(instance=service)

    return render(request, "generator/index.html", {"form": form, "project": project, "service": service})

def service_delete(request: HttpRequest, project_id: int, service_id: int) -> HttpResponse:
    project = get_object_or_404(ConfigProject, id=project_id)
    service = get_object_or_404(Service, id=service_id, project=project)

    if request.method == "POST":
        service.delete()
        messages.success(request, "Service deleted successfully.")

        return redirect("generator:project_detail", project_id=project.id)

    return render(request, "generator/index.html", {"project": project, "service": service})
