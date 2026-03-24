from collections.abc import Iterable, Mapping
from typing import Any

import yaml


DOCKERFILE = "dockerfile"
DOCKER_COMPOSE = "docker-compose"

def _get_value(source: Mapping[str, Any] | Any, key: str, default: Any = None) -> Any:
    if isinstance(source, Mapping):
        return source.get(key, default)
    return getattr(source, key, default)


def _normalize_collection(value: Any) -> list[Any]:
    if value is None:
        return []

    all_method = getattr(value, "all", None)
    if callable(all_method):
        value = all_method()

    if isinstance(value, Mapping):
        return list(value.values())

    if isinstance(value, (str, bytes)):
        return []

    if isinstance(value, Iterable):
        return list(value)

    return []


def _set_if_present(target: dict[str, Any], key: str, value: Any) -> None:
    if value in (None, "", [], {}):
        return
    target[key] = value


def _compose_dict(project: Mapping[str, Any] | Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "version": _get_value(project, "version", "3.8"),
        "services": {},
    }

    services = _normalize_collection(_get_value(project, "services", []))
    for service in services:
        service_name = _get_value(service, "name", "")
        if not service_name:
            continue

        service_data: dict[str, Any] = {}
        _set_if_present(service_data, "image", _get_value(service, "image"))
        _set_if_present(service_data, "build", _get_value(service, "build_context"))
        _set_if_present(service_data, "container_name", _get_value(service, "container_name"))
        _set_if_present(service_data, "command", _get_value(service, "command"))
        _set_if_present(service_data, "restart", _get_value(service, "restart_policy"))
        _set_if_present(service_data, "ports", _get_value(service, "ports"))
        _set_if_present(service_data, "volumes", _get_value(service, "volumes"))
        _set_if_present(service_data, "environment", _get_value(service, "environment"))
        _set_if_present(service_data, "depends_on", _get_value(service, "depends_on"))

        extra = _get_value(service, "extra", {})
        if isinstance(extra, Mapping):
            service_data.update(extra)

        data["services"][service_name] = service_data

    networks = _normalize_collection(_get_value(project, "networks", []))
    if networks:
        data["networks"] = {}
        for network in networks:
            network_name = _get_value(network, "name", "")
            if not network_name:
                continue
            data["networks"][network_name] = {}

    named_volumes = _normalize_collection(_get_value(project, "named_volumes", []))
    if not named_volumes:
        named_volumes = _normalize_collection(_get_value(project, "volumes", []))

    if named_volumes:
        data["volumes"] = {}
        for volume in named_volumes:
            volume_name = _get_value(volume, "name", "")
            if not volume_name:
                continue
            data["volumes"][volume_name] = {}

    options = _normalize_collection(_get_value(project, "options", []))
    for option in options:
        option_key = _get_value(option, "key", "")
        if not option_key:
            continue
        data[option_key] = _get_value(option, "value", "")

    return data


def build_compose_yaml(project: Mapping[str, Any] | Any) -> str:
    return yaml.safe_dump(_compose_dict(project), sort_keys=False)


def _options_to_dict(project: Mapping[str, Any] | Any) -> dict[str, Any]:
    options_dict: dict[str, Any] = {}
    options = _normalize_collection(_get_value(project, "options", []))
    for option in options:
        key = _get_value(option, "key", "")
        if not key:
            continue
        options_dict[str(key)] = _get_value(option, "value", "")
    return options_dict


def _container_ports_from_service(service: Mapping[str, Any] | Any) -> list[str]:
    ports = _normalize_collection(_get_value(service, "ports", []))
    container_ports: list[str] = []

    for port in ports:
        if isinstance(port, int):
            container_ports.append(str(port))
            continue

        if not isinstance(port, str):
            continue

        # Handles formats like "8000:80" or "127.0.0.1:8000:80" by taking the last segment.
        container_port = port.split(":")[-1].strip()
        if container_port:
            container_ports.append(container_port)

    return container_ports


def build_dockerfile(project: Mapping[str, Any] | Any) -> str:
    options = _options_to_dict(project)
    services = _normalize_collection(_get_value(project, "services", []))
    primary_service = services[0] if services else {}

    from_image = options.get("dockerfile_from") or options.get("base_image") or _get_value(primary_service, "image", "python:3.12-slim")
    workdir = options.get("dockerfile_workdir") or options.get("workdir") or "/app"
    copy_value = options.get("dockerfile_copy") or ". ."
    run_value = options.get("dockerfile_run") or options.get("run")
    cmd_value = options.get("dockerfile_cmd") or options.get("cmd") or _get_value(primary_service, "command")

    lines: list[str] = [
        f"FROM {from_image}",
        f"WORKDIR {workdir}",
        f"COPY {copy_value}",
    ]

    if run_value:
        if isinstance(run_value, str):
            lines.append(f"RUN {run_value}")
        else:
            for run_cmd in _normalize_collection(run_value):
                if run_cmd:
                    lines.append(f"RUN {run_cmd}")

    expose_ports = options.get("dockerfile_expose")
    if expose_ports is None:
        expose_ports = _container_ports_from_service(primary_service)

    for port in _normalize_collection(expose_ports):
        if port:
            lines.append(f"EXPOSE {port}")

    if cmd_value:
        if isinstance(cmd_value, str):
            escaped = cmd_value.replace('"', '\\"')
            lines.append(f'CMD ["sh", "-c", "{escaped}"]')
        else:
            cmd_parts = [str(part) for part in _normalize_collection(cmd_value) if part]
            if cmd_parts:
                encoded = ", ".join(f'"{part}"' for part in cmd_parts)
                lines.append(f"CMD [{encoded}]")

    return "\n".join(lines) + "\n"


def build_output(project: Mapping[str, Any] | Any, target_type: str | None = None) -> str:
    resolved_target = target_type or _get_value(project, "target_type", DOCKER_COMPOSE)

    if resolved_target == DOCKERFILE:
        return build_dockerfile(project)

    return build_compose_yaml(project)


def build_yaml(project: Mapping[str, Any] | Any) -> str:
    # Backward-compatible alias while callers migrate to build_output/build_compose_yaml.
    return build_compose_yaml(project)