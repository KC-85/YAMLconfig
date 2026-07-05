import json
import re
from collections.abc import Iterable, Mapping
from typing import Any

import yaml


DOCKERFILE = "dockerfile"
DOCKER_COMPOSE = "docker-compose"
DEFAULT_BASE_IMAGE = "python:3.12-slim"
DEFAULT_WORKDIR = "/app"
DEFAULT_COPY = ". ."
VALID_EXPOSE_PROTOCOLS = {"tcp", "udp"}

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
            network_data: dict[str, Any] = {}
            _set_if_present(network_data, "driver", _get_value(network, "driver"))
            _set_if_present(network_data, "external", _get_value(network, "external"))
            _set_if_present(network_data, "attachable", _get_value(network, "attachable"))
            _set_if_present(network_data, "internal", _get_value(network, "internal"))
            _set_if_present(network_data, "labels", _get_value(network, "labels"))
            _set_if_present(network_data, "driver_opts", _get_value(network, "driver_opts"))
            extra = _get_value(network, "extra", {})
            if isinstance(extra, Mapping):
                network_data.update(extra)
            data["networks"][network_name] = network_data

    named_volumes = _normalize_collection(_get_value(project, "named_volumes", []))
    if not named_volumes:
        named_volumes = _normalize_collection(_get_value(project, "volumes", []))

    if named_volumes:
        data["volumes"] = {}
        for volume in named_volumes:
            volume_name = _get_value(volume, "name", "")
            if not volume_name:
                continue
            volume_data: dict[str, Any] = {}
            _set_if_present(volume_data, "driver", _get_value(volume, "driver"))
            _set_if_present(volume_data, "external", _get_value(volume, "external"))
            _set_if_present(volume_data, "labels", _get_value(volume, "labels"))
            _set_if_present(volume_data, "driver_opts", _get_value(volume, "driver_opts"))
            extra = _get_value(volume, "extra", {})
            if isinstance(extra, Mapping):
                volume_data.update(extra)
            data["volumes"][volume_name] = volume_data

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


def _single_line_value(value: Any) -> str | None:
    if not isinstance(value, (str, int, float)):
        return None

    text = str(value).strip()
    if not text or len(text.splitlines()) != 1 or "\0" in text:
        return None

    return text


def _first_single_line(*values: Any, default: str) -> str:
    for value in values:
        normalized = _single_line_value(value)
        if normalized is not None:
            return normalized
    return default


def _select_primary_service(
    services: list[Any],
    options: Mapping[str, Any],
) -> Mapping[str, Any] | Any:
    requested_name = _single_line_value(
        options.get("dockerfile_service") or options.get("primary_service")
    )
    if requested_name:
        for service in services:
            if _single_line_value(_get_value(service, "name")) == requested_name:
                return service

    for service in services:
        if _single_line_value(_get_value(service, "image")):
            return service

    return services[0] if services else {}


def _expose_candidates(value: Any) -> list[Any]:
    if isinstance(value, Mapping):
        return [value.get("target")]

    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return []

        try:
            decoded = json.loads(stripped)
        except json.JSONDecodeError:
            decoded = None

        if isinstance(decoded, list):
            return decoded

        # ProjectOption values are text. Accept comma/whitespace-separated ports,
        # JSON-like lists, and Compose host mappings without emitting the host side.
        cleaned = re.sub(r"[\[\]\"']", " ", stripped)
        return [part for part in re.split(r"[\s,]+", cleaned) if part]

    if isinstance(value, Iterable) and not isinstance(value, (bytes, bytearray)):
        candidates: list[Any] = []
        for item in value:
            candidates.extend(_expose_candidates(item))
        return candidates

    return [value]


def _normalize_expose_port(value: Any) -> str | None:
    if isinstance(value, bool):
        return None

    text = _single_line_value(value)
    if text is None:
        return None

    # Compose mappings can include IP:host:container. EXPOSE only accepts the
    # final container port, so discard everything before the final colon.
    text = text.rsplit(":", maxsplit=1)[-1]
    port_text, separator, protocol = text.partition("/")

    if not port_text.isdigit():
        return None

    port = int(port_text)
    if not 1 <= port <= 65535:
        return None

    if not separator:
        return str(port)

    protocol = protocol.lower()
    if protocol not in VALID_EXPOSE_PROTOCOLS:
        return None

    return f"{port}/{protocol}"


def _normalize_expose_ports(value: Any) -> list[str]:
    ports: list[str] = []
    for candidate in _expose_candidates(value):
        port = _normalize_expose_port(candidate)
        if port and port not in ports:
            ports.append(port)
    return ports


def _container_ports_from_service(service: Mapping[str, Any] | Any) -> list[str]:
    return _normalize_expose_ports(_get_value(service, "ports", []))


def _run_commands(value: Any) -> list[str]:
    raw_commands = [value] if isinstance(value, str) else _normalize_collection(value)
    commands: list[str] = []

    for raw_command in raw_commands:
        if not isinstance(raw_command, str):
            continue
        commands.extend(
            line.strip()
            for line in raw_command.splitlines()
            if line.strip()
        )

    return commands


def _cmd_instruction(value: Any) -> str | None:
    if isinstance(value, str):
        command = value.strip()
        if not command:
            return None

        try:
            decoded = json.loads(command)
        except json.JSONDecodeError:
            decoded = None

        if isinstance(decoded, list):
            parts = [str(part) for part in decoded if str(part).strip()]
            return f"CMD {json.dumps(parts)}" if parts else None

        return f"CMD {json.dumps(['sh', '-c', command])}"

    parts = [
        str(part)
        for part in _normalize_collection(value)
        if str(part).strip()
    ]
    return f"CMD {json.dumps(parts)}" if parts else None


def build_dockerfile(project: Mapping[str, Any] | Any) -> str:
    options = _options_to_dict(project)
    services = _normalize_collection(_get_value(project, "services", []))
    primary_service = _select_primary_service(services, options)

    from_image = _first_single_line(
        options.get("dockerfile_from"),
        options.get("base_image"),
        _get_value(primary_service, "image"),
        default=DEFAULT_BASE_IMAGE,
    )
    workdir = _first_single_line(
        options.get("dockerfile_workdir"),
        options.get("workdir"),
        default=DEFAULT_WORKDIR,
    )
    copy_value = _first_single_line(
        options.get("dockerfile_copy"),
        default=DEFAULT_COPY,
    )
    run_value = options.get("dockerfile_run") or options.get("run")
    cmd_value = options.get("dockerfile_cmd") or options.get("cmd") or _get_value(primary_service, "command")

    lines: list[str] = [
        f"FROM {from_image}",
        f"WORKDIR {workdir}",
        f"COPY {copy_value}",
    ]

    for run_command in _run_commands(run_value):
        lines.append(f"RUN {run_command}")

    expose_ports = options.get("dockerfile_expose")
    if expose_ports is None or (
        isinstance(expose_ports, str) and not expose_ports.strip()
    ):
        expose_ports = _container_ports_from_service(primary_service)

    for port in _normalize_expose_ports(expose_ports):
        lines.append(f"EXPOSE {port}")

    cmd_instruction = _cmd_instruction(cmd_value)
    if cmd_instruction:
        lines.append(cmd_instruction)

    return "\n".join(lines) + "\n"


def build_output(project: Mapping[str, Any] | Any, target_type: str | None = None) -> str:
    resolved_target = target_type or _get_value(project, "target_type", DOCKER_COMPOSE)

    if resolved_target == DOCKERFILE:
        return build_dockerfile(project)

    return build_compose_yaml(project)


def build_yaml(project: Mapping[str, Any] | Any) -> str:
    # Backward-compatible alias while callers migrate to build_output/build_compose_yaml.
    return build_compose_yaml(project)
