from django import forms

from .models import ConfigProject, NamedVolume, Network, ProjectOption, Service


class ConfigProjectForm(forms.ModelForm):
    class Meta:
        model = ConfigProject
        fields = ("name", "target_type")
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Project name"}),
            "target_type": forms.Select(attrs={"class": "form-select"}),
        }


class ServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = (
            "name",
            "image",
            "build_context",
            "container_name",
            "command",
            "restart_policy",
            "ports",
            "volumes",
            "environment",
            "depends_on",
            "extra",
        )
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Service name"}),
            "image": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g., nginx:latest"}),
            "build_context": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g., ./dockerfile"}),
            "container_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Container name"}),
            "command": forms.TextInput(attrs={"class": "form-control", "placeholder": "Startup command"}),
            "restart_policy": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g., always"}),
            "ports": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": '["8000:8000"]'}),
            "volumes": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": '["/data:/data"]'}),
            "environment": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": '{"KEY": "value"}'}),
            "depends_on": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": '["service1", "service2"]'}),
            "extra": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


class ProjectOptionForm(forms.ModelForm):
    class Meta:
        model = ProjectOption
        fields = ("key", "value")
        widgets = {
            "key": forms.TextInput(attrs={"class": "form-control", "placeholder": "Option key"}),
            "value": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Option value"}),
        }


class NetworkForm(forms.ModelForm):
    class Meta:
        model = Network
        fields = (
            "name",
            "driver",
            "external",
            "attachable",
            "internal",
            "labels",
            "driver_opts",
            "extra",
        )
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Network name"}),
            "driver": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g., bridge"}),
            "external": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "attachable": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "internal": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "labels": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": '{"label": "value"}'}),
            "driver_opts": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": '{"opt": "value"}'}),
            "extra": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


class NamedVolumeForm(forms.ModelForm):
    class Meta:
        model = NamedVolume
        fields = ("name", "driver", "external", "labels", "driver_opts", "extra")
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Volume name"}),
            "driver": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g., local"}),
            "external": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "labels": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": '{"label": "value"}'}),
            "driver_opts": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": '{"opt": "value"}'}),
            "extra": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }
