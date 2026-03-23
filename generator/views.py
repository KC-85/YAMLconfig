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
