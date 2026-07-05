import json
from collections.abc import Mapping
from typing import Any

from django import forms

from .models import ConfigProject, NamedVolume, Network, ProjectOption, Service
from .yaml_builder import DOCKERFILE_OPTION_KEYS


class LineListField(forms.Field):
    """Accept one value per line while retaining JSON-list compatibility."""

    default_error_messages = {
        "invalid": "Enter one value per line or a valid JSON list.",
        "invalid_item": "Each list item must be text or an integer.",
    }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault(
            "widget",
            forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        )
        kwargs.setdefault("required", False)
        super().__init__(*args, **kwargs)

    def to_python(self, value: Any) -> list[str]:
        if value in self.empty_values:
            return []

        if isinstance(value, str):
            text = value.strip()
            if not text:
                return []
            if text.startswith("["):
                try:
                    items = json.loads(text)
                except json.JSONDecodeError as exc:
                    raise forms.ValidationError(
                        self.error_messages["invalid"],
                        code="invalid",
                    ) from exc
                if not isinstance(items, list):
                    raise forms.ValidationError(
                        self.error_messages["invalid"],
                        code="invalid",
                    )
            else:
                items = text.splitlines()
        elif isinstance(value, (list, tuple)):
            items = value
        else:
            raise forms.ValidationError(
                self.error_messages["invalid"],
                code="invalid",
            )

        result: list[str] = []
        for item in items:
            if isinstance(item, bool) or not isinstance(item, (str, int)):
                raise forms.ValidationError(
                    self.error_messages["invalid_item"],
                    code="invalid_item",
                )
            normalized = str(item).strip()
            if normalized and normalized not in result:
                result.append(normalized)
        return result

    def prepare_value(self, value: Any) -> Any:
        if isinstance(value, (list, tuple)):
            return "\n".join(str(item) for item in value)
        return value


class KeyValueField(forms.Field):
    """Accept KEY=value lines while retaining JSON-object compatibility."""

    default_error_messages = {
        "invalid": "Enter one KEY=value pair per line or a valid JSON object.",
        "missing_separator": "Line %(line)d must use the KEY=value format.",
        "missing_key": "Line %(line)d must include a key before '='.",
        "duplicate_key": "The key '%(key)s' is listed more than once.",
        "nested_value": "Values must be strings, numbers, booleans, or null.",
    }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault(
            "widget",
            forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        )
        kwargs.setdefault("required", False)
        super().__init__(*args, **kwargs)

    def to_python(self, value: Any) -> dict[str, Any]:
        if value in self.empty_values:
            return {}

        if isinstance(value, Mapping):
            values = dict(value)
        elif isinstance(value, str):
            text = value.strip()
            if not text:
                return {}
            if text.startswith("{"):
                try:
                    values = json.loads(text)
                except json.JSONDecodeError as exc:
                    raise forms.ValidationError(
                        self.error_messages["invalid"],
                        code="invalid",
                    ) from exc
                if not isinstance(values, dict):
                    raise forms.ValidationError(
                        self.error_messages["invalid"],
                        code="invalid",
                    )
            else:
                values = {}
                for line_number, line in enumerate(text.splitlines(), start=1):
                    if not line.strip():
                        continue
                    if "=" not in line:
                        raise forms.ValidationError(
                            self.error_messages["missing_separator"],
                            code="missing_separator",
                            params={"line": line_number},
                        )
                    key, item_value = line.split("=", maxsplit=1)
                    key = key.strip()
                    if not key:
                        raise forms.ValidationError(
                            self.error_messages["missing_key"],
                            code="missing_key",
                            params={"line": line_number},
                        )
                    if key in values:
                        raise forms.ValidationError(
                            self.error_messages["duplicate_key"],
                            code="duplicate_key",
                            params={"key": key},
                        )
                    values[key] = item_value.strip()
        else:
            raise forms.ValidationError(
                self.error_messages["invalid"],
                code="invalid",
            )

        normalized: dict[str, Any] = {}
        for key, item_value in values.items():
            key = str(key).strip()
            if not key:
                raise forms.ValidationError(
                    self.error_messages["missing_key"],
                    code="missing_key",
                    params={"line": 1},
                )
            if isinstance(item_value, (Mapping, list, tuple)):
                raise forms.ValidationError(
                    self.error_messages["nested_value"],
                    code="nested_value",
                )
            normalized[key] = item_value
        return normalized

    def prepare_value(self, value: Any) -> Any:
        if not isinstance(value, Mapping):
            return value
        if all(isinstance(item, str) for item in value.values()):
            return "\n".join(f"{key}={item}" for key, item in value.items())
        return json.dumps(value, indent=2, sort_keys=True)


class JSONObjectField(forms.JSONField):
    default_error_messages = {
        **forms.JSONField.default_error_messages,
        "not_object": "Enter a JSON object using curly braces, for example {\"key\": \"value\"}.",
    }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault(
            "widget",
            forms.Textarea(
                attrs={
                    "class": "form-control font-mono",
                    "rows": 4,
                    "placeholder": '{"key": "value"}',
                }
            ),
        )
        kwargs.setdefault("required", False)
        super().__init__(*args, **kwargs)

    def to_python(self, value: Any) -> dict[str, Any]:
        parsed = super().to_python(value)
        if parsed is None or parsed == "":
            return {}
        if not isinstance(parsed, dict):
            raise forms.ValidationError(
                self.error_messages["not_object"],
                code="not_object",
            )
        return parsed

    def prepare_value(self, value: Any) -> Any:
        if isinstance(value, Mapping):
            return json.dumps(value, indent=2, sort_keys=True)
        return super().prepare_value(value)


class ConfigProjectForm(forms.ModelForm):
    class Meta:
        model = ConfigProject
        fields = ("name", "target_type")
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Project name"}),
            "target_type": forms.Select(attrs={"class": "form-select"}),
        }


class ServiceForm(forms.ModelForm):
    ports = LineListField(
        help_text="Enter one port or host mapping per line, for example 8000:80.",
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "8000:80\n8443:443",
            }
        ),
    )
    volumes = LineListField(
        help_text="Enter one volume mount per line.",
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "./data:/app/data\ncache:/app/cache",
            }
        ),
    )
    environment = KeyValueField(
        help_text="Enter one environment variable per line using KEY=value.",
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "APP_ENV=development\nDEBUG=true",
            }
        ),
    )
    depends_on = LineListField(
        help_text="Enter one existing service name per line.",
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "database\nredis",
            }
        ),
    )
    extra = JSONObjectField(
        help_text="Optional advanced service settings as a JSON object.",
    )

    def __init__(
        self,
        *args: Any,
        project: ConfigProject | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        if project is None and self.instance.pk:
            project = self.instance.project
        self.project = project

    def clean(self) -> dict[str, Any]:
        cleaned_data = super().clean()
        dependencies = cleaned_data.get("depends_on") or []
        service_name = cleaned_data.get("name")

        if self.project and service_name:
            matching_services = self.project.services.filter(name=service_name)
            if self.instance.pk:
                matching_services = matching_services.exclude(pk=self.instance.pk)
            if matching_services.exists():
                self.add_error(
                    "name",
                    "A service with this name already exists in the project.",
                )

        if service_name and service_name in dependencies:
            self.add_error("depends_on", "A service cannot depend on itself.")

        if self.project and dependencies:
            available_services = self.project.services.all()
            if self.instance.pk:
                available_services = available_services.exclude(pk=self.instance.pk)
            available_names = set(
                available_services.values_list("name", flat=True)
            )
            unknown = sorted(set(dependencies) - available_names - {service_name})
            if unknown:
                self.add_error(
                    "depends_on",
                    "Unknown service(s): "
                    f"{', '.join(unknown)}. Add those services first.",
                )

        return cleaned_data

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
        }


class ProjectOptionForm(forms.ModelForm):
    def __init__(
        self,
        *args: Any,
        project: ConfigProject | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        if project is None and self.instance.pk:
            project = self.instance.project
        self.project = project

    def clean(self) -> dict[str, Any]:
        cleaned_data = super().clean()
        scope = cleaned_data.get("scope")
        key = cleaned_data.get("key", "").strip()

        if scope == ProjectOption.Scope.DOCKERFILE and key not in DOCKERFILE_OPTION_KEYS:
            self.add_error(
                "key",
                "This key is not used by Dockerfile generation. "
                f"Choose one of: {', '.join(sorted(DOCKERFILE_OPTION_KEYS))}.",
            )
        elif scope == ProjectOption.Scope.DOCKER_COMPOSE and key in DOCKERFILE_OPTION_KEYS:
            self.add_error(
                "key",
                "This is a Dockerfile option key. Change the scope to Dockerfile.",
            )

        if self.project and scope and key:
            matching_options = self.project.options.filter(scope=scope, key=key)
            if self.instance.pk:
                matching_options = matching_options.exclude(pk=self.instance.pk)
            if matching_options.exists():
                self.add_error(
                    "key",
                    "An option with this key and scope already exists.",
                )

        return cleaned_data

    class Meta:
        model = ProjectOption
        fields = ("scope", "key", "value")
        widgets = {
            "scope": forms.Select(attrs={"class": "form-select"}),
            "key": forms.TextInput(attrs={"class": "form-control", "placeholder": "Option key"}),
            "value": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Option value"}),
        }


class NetworkForm(forms.ModelForm):
    labels = KeyValueField(
        help_text="Enter one label per line using KEY=value.",
    )
    driver_opts = KeyValueField(
        label="Driver options",
        help_text="Enter one driver option per line using KEY=value.",
    )
    extra = JSONObjectField(
        help_text="Optional advanced network settings as a JSON object.",
    )

    def __init__(
        self,
        *args: Any,
        project: ConfigProject | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        if project is None and self.instance.pk:
            project = self.instance.project
        self.project = project

    def clean_name(self) -> str:
        name = self.cleaned_data["name"]
        if self.project:
            matching_networks = self.project.networks.filter(name=name)
            if self.instance.pk:
                matching_networks = matching_networks.exclude(pk=self.instance.pk)
            if matching_networks.exists():
                raise forms.ValidationError(
                    "A network with this name already exists in the project."
                )
        return name

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
        }


class NamedVolumeForm(forms.ModelForm):
    labels = KeyValueField(
        help_text="Enter one label per line using KEY=value.",
    )
    driver_opts = KeyValueField(
        label="Driver options",
        help_text="Enter one driver option per line using KEY=value.",
    )
    extra = JSONObjectField(
        help_text="Optional advanced volume settings as a JSON object.",
    )

    def __init__(
        self,
        *args: Any,
        project: ConfigProject | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        if project is None and self.instance.pk:
            project = self.instance.project
        self.project = project

    def clean_name(self) -> str:
        name = self.cleaned_data["name"]
        if self.project:
            matching_volumes = self.project.named_volumes.filter(name=name)
            if self.instance.pk:
                matching_volumes = matching_volumes.exclude(pk=self.instance.pk)
            if matching_volumes.exists():
                raise forms.ValidationError(
                    "A volume with this name already exists in the project."
                )
        return name

    class Meta:
        model = NamedVolume
        fields = ("name", "driver", "external", "labels", "driver_opts", "extra")
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Volume name"}),
            "driver": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g., local"}),
            "external": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
