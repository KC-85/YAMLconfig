from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

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
from .yaml_builder import build_output


def _refresh_project_output(project: ConfigProject) -> None:
    project.output_text = build_output(project)
    project.save(update_fields=["output_text", "updated_at"])

@login_required
def project_list(request: HttpRequest) -> HttpResponse:
    projects = ConfigProject.objects.filter(owner=request.user)
    return render(request, "generator/index.html", {"projects": projects})

@login_required
def project_detail(request: HttpRequest, project_id: int) -> HttpResponse:
    project = get_object_or_404(ConfigProject, id=project_id, owner=request.user)
    services = project.services.all()
    options = project.options.all()
    networks = project.networks.all()
    volumes = project.named_volumes.all()

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

@login_required
def project_create(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = ConfigProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.owner = request.user
            project.save()
            _refresh_project_output(project)
            messages.success(request, "Project created successfully.")
            return redirect("generator:project_detail", project_id=project.id)
    else:
        form = ConfigProjectForm()

    return render(request, "generator/index.html", {"form": form})

@login_required
def project_edit(request: HttpRequest, project_id: int) -> HttpResponse:
    project = get_object_or_404(ConfigProject, id=project_id, owner=request.user)

    if request.method == "POST":
        form = ConfigProjectForm(request.POST, instance=project)
        if form.is_valid():
            form.save()
            _refresh_project_output(project)
            messages.success(request, "Project updated successfully.")
            return redirect("generator:project_detail", project_id=project.id)
    else:
        form = ConfigProjectForm(instance=project)

    return render(request, "generator/index.html", {"form": form, "project": project})

@login_required
def project_delete(request: HttpRequest, project_id: int) -> HttpResponse:
    project = get_object_or_404(ConfigProject, id=project_id, owner=request.user)

    if request.method == "POST":
        project.delete()
        messages.success(request, "Project deleted successfully.")
        return redirect("generator:project_list")

    return render(request, "generator/index.html", {"project": project})


@login_required
def service_create(request: HttpRequest, project_id: int) -> HttpResponse:
    project = get_object_or_404(ConfigProject, id=project_id, owner=request.user)

    if request.method == "POST":
        form = ServiceForm(request.POST)
        if form.is_valid():
            service = form.save(commit=False)
            service.project = project
            service.save()
            _refresh_project_output(project)
            messages.success(request, "Service created successfully.")
            return redirect("generator:project_detail", project_id=project.id)
    else:
        form = ServiceForm()

    return render(request, "generator/index.html", {"form": form, "project": project})

@login_required
def service_edit(request: HttpRequest, project_id: int, service_id: int) -> HttpResponse:
    project = get_object_or_404(ConfigProject, id=project_id, owner=request.user)
    service = get_object_or_404(Service, id=service_id, project=project)

    if request.method == "POST":
        form = ServiceForm(request.POST, instance=service)
        if form.is_valid():
            form.save()
            _refresh_project_output(project)
            messages.success(request, "Service updated successfully.")
            return redirect("generator:project_detail", project_id=project.id)
    else:
        form = ServiceForm(instance=service)

    return render(request, "generator/index.html", {"form": form, "project": project, "service": service})

@login_required
def service_delete(request: HttpRequest, project_id: int, service_id: int) -> HttpResponse:
    project = get_object_or_404(ConfigProject, id=project_id, owner=request.user)
    service = get_object_or_404(Service, id=service_id, project=project)

    if request.method == "POST":
        service.delete()
        _refresh_project_output(project)
        messages.success(request, "Service deleted successfully.")

        return redirect("generator:project_detail", project_id=project.id)

    return render(request, "generator/index.html", {"project": project, "service": service})


@login_required
def option_create(request: HttpRequest, project_id: int) -> HttpResponse:
    project = get_object_or_404(ConfigProject, id=project_id, owner=request.user)

    if request.method == "POST":
        form = ProjectOptionForm(request.POST)
        if form.is_valid():
            option = form.save(commit=False)
            option.project = project
            option.save()
            _refresh_project_output(project)
            messages.success(request, "Option created successfully.")
            return redirect("generator:project_detail", project_id=project.id)
    else:
        form = ProjectOptionForm()

    return render(request, "generator/index.html", {"form": form, "project": project})

@login_required
def option_edit(request: HttpRequest, project_id: int, option_id: int) -> HttpResponse:
    project = get_object_or_404(ConfigProject, id=project_id, owner=request.user)
    option = get_object_or_404(ProjectOption, id=option_id, project=project)

    if request.method == "POST":
        form = ProjectOptionForm(request.POST, instance=option)
        if form.is_valid():
            form.save()
            _refresh_project_output(project)
            messages.success(request, "Option updated successfully.")
            return redirect("generator:project_detail", project_id=project.id)
    else:
        form = ProjectOptionForm(instance=option)

    return render(request, "generator/index.html", {"form": form, "project": project, "option": option})

@login_required
def option_delete(request: HttpRequest, project_id: int, option_id: int) -> HttpResponse:
    project = get_object_or_404(ConfigProject, id=project_id, owner=request.user)
    option = get_object_or_404(ProjectOption, id=option_id, project=project)

    if request.method == "POST":
        option.delete()
        _refresh_project_output(project)
        messages.success(request, "Option deleted successfully.")
        return redirect("generator:project_detail", project_id=project.id)

    return render(request, "generator/index.html", {"project": project, "option": option})


@login_required
def network_create(request: HttpRequest, project_id: int) -> HttpResponse:
    project = get_object_or_404(ConfigProject, id=project_id, owner=request.user)

    if request.method == "POST":
        form = NetworkForm(request.POST)
        if form.is_valid():
            network = form.save(commit=False)
            network.project = project
            network.save()
            _refresh_project_output(project)
            messages.success(request, "Network created successfully.")
            return redirect("generator:project_detail", project_id=project.id)
    else:
        form = NetworkForm()

    return render(request, "generator/index.html", {"form": form, "project": project})

@login_required
def network_edit(request: HttpRequest, project_id: int, network_id: int) -> HttpResponse:
    project = get_object_or_404(ConfigProject, id=project_id, owner=request.user)
    network = get_object_or_404(Network, id=network_id, project=project)

    if request.method == "POST":
        form = NetworkForm(request.POST, instance=network)
        if form.is_valid():
            form.save()
            _refresh_project_output(project)
            messages.success(request, "Network updated successfully.")
            return redirect("generator:project_detail", project_id=project.id)
    else:
        form = NetworkForm(instance=network)

    return render(request, "generator/index.html", {"form": form, "project": project, "network": network})

@login_required
def network_delete(request: HttpRequest, project_id: int, network_id: int) -> HttpResponse:
    project = get_object_or_404(ConfigProject, id=project_id, owner=request.user)
    network = get_object_or_404(Network, id=network_id, project=project)

    if request.method == "POST":
        network.delete()
        _refresh_project_output(project)
        messages.success(request, "Network deleted successfully.")
        return redirect("generator:project_detail", project_id=project.id)

    return render(request, "generator/index.html", {"project": project, "network": network})


@login_required
def volume_create(request: HttpRequest, project_id: int) -> HttpResponse:
    project = get_object_or_404(ConfigProject, id=project_id, owner=request.user)

    if request.method == "POST":
        form = NamedVolumeForm(request.POST)
        if form.is_valid():
            volume = form.save(commit=False)
            volume.project = project
            volume.save()
            _refresh_project_output(project)
            messages.success(request, "Volume created successfully.")
            return redirect("generator:project_detail", project_id=project.id)
    else:
        form = NamedVolumeForm()

    return render(request, "generator/index.html", {"form": form, "project": project})

@login_required
def volume_edit(request: HttpRequest, project_id: int, volume_id: int) -> HttpResponse:
    project = get_object_or_404(ConfigProject, id=project_id, owner=request.user)
    volume = get_object_or_404(NamedVolume, id=volume_id, project=project)

    if request.method == "POST":
        form = NamedVolumeForm(request.POST, instance=volume)
        if form.is_valid():
            form.save()
            _refresh_project_output(project)
            messages.success(request, "Volume updated successfully.")
            return redirect("generator:project_detail", project_id=project.id)
    else:
        form = NamedVolumeForm(instance=volume)

    return render(request, "generator/index.html", {"form": form, "project": project, "volume": volume})

@login_required
def volume_delete(request: HttpRequest, project_id: int, volume_id: int) -> HttpResponse:
    project = get_object_or_404(ConfigProject, id=project_id, owner=request.user)
    volume = get_object_or_404(NamedVolume, id=volume_id, project=project)

    if request.method == "POST":
        volume.delete()
        _refresh_project_output(project)
        messages.success(request, "Volume deleted successfully.")
        return redirect("generator:project_detail", project_id=project.id)

    return render(request, "generator/index.html", {"project": project, "volume": volume})
