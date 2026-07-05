# YAMLconfig
An application which will generate Docker Compose files, Ansible playbooks, GitHub Actions workflow builder &amp; more. Starting work on this soon.

## YAML Builder Input

The pure Python builder lives in `generator/yaml_builder.py` and supports these entry points:

- `build_compose_yaml(project)`
- `build_dockerfile(project)`
- `build_output(project, target_type=None)`

`project` can be either:

- A `dict`
- An object with matching attributes

### Required project fields

- `services`: list of services

Each service should include:

- `name` (required): service name used in compose output

### Optional project fields

- `target_type`: `docker-compose` or `dockerfile`
- `version`: compose version (default: `3.8`)
- `networks`: list of network entries
- `named_volumes` or `volumes`: list of named volume entries
- `options`: list of scoped key/value entries

Each option supports:

- `scope`: `docker-compose` or `dockerfile`
- `key`
- `value`

For backward compatibility, dictionary input without `scope` treats known
Dockerfile keys as `dockerfile` and all other keys as `docker-compose`.

### Optional service fields

- `image`
- `build_context`
- `container_name`
- `command`
- `restart_policy`
- `ports` (for example `"8000:80"`)
- `volumes`
- `environment`
- `depends_on`
- `extra` (dict merged directly into the service block)

## Web Form Input

The web editor accepts one value per line for ports, volume mounts, and service
dependencies. Environment variables, labels, and driver options use one
`KEY=value` pair per line. Existing JSON lists and objects remain supported.

The `extra` fields accept JSON objects for advanced settings. Service
dependencies must refer to services that already exist in the same project.

### Option keys used by Dockerfile generation

These are read from options whose scope is `dockerfile`:

- `dockerfile_service` (or `primary_service`) selects the service used for image, port, and command defaults
- `dockerfile_from` (or `base_image`)
- `dockerfile_workdir` (or `workdir`)
- `dockerfile_copy`
- `dockerfile_run` (or `run`); each non-empty line becomes a `RUN` instruction
- `dockerfile_cmd` (or `cmd`)
- `dockerfile_expose`; accepts comma/whitespace-separated ports or a JSON list, with optional `/tcp` or `/udp`

If no service is selected explicitly, Dockerfile generation uses the first
service with a non-empty image. It falls back to `python:3.12-slim` when no
usable image is available.

## Example Input

```python
project = {
	"target_type": "docker-compose",
	"version": "3.8",
	"services": [
		{
			"name": "web",
			"image": "nginx:alpine",
			"ports": ["8080:80"],
			"environment": {"APP_ENV": "dev"},
			"depends_on": ["db"],
		},
		{
			"name": "db",
			"image": "postgres:16",
			"volumes": ["pgdata:/var/lib/postgresql/data"],
		},
	],
	"networks": [{"name": "appnet"}],
	"named_volumes": [{"name": "pgdata"}],
	"options": [
		{"scope": "dockerfile", "key": "dockerfile_from", "value": "python:3.12-slim"},
		{"scope": "dockerfile", "key": "dockerfile_workdir", "value": "/app"},
		{"scope": "dockerfile", "key": "dockerfile_run", "value": "pip install -r requirements.txt"},
		{"scope": "dockerfile", "key": "dockerfile_cmd", "value": "python manage.py runserver 0.0.0.0:8000"},
		{"scope": "docker-compose", "key": "name", "value": "example-project"},
	],
}
```

## Output Selection

Use `build_output(project)` to auto-select by `project.target_type`, or pass an explicit target:

```python
from generator.yaml_builder import build_output

compose_text = build_output(project, target_type="docker-compose")
dockerfile_text = build_output(project, target_type="dockerfile")
```

The web preview and download endpoints generate output from the current project
records on every request. Generated files are derived data and are not cached in
the database.
