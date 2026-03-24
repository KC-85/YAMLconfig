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
- `options`: list of key/value entries used as global options and Dockerfile overrides

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

### Option keys used by Dockerfile generation

These are read from `project.options`:

- `dockerfile_from` (or `base_image`)
- `dockerfile_workdir` (or `workdir`)
- `dockerfile_copy`
- `dockerfile_run` (or `run`)
- `dockerfile_cmd` (or `cmd`)
- `dockerfile_expose`

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
		{"key": "dockerfile_from", "value": "python:3.12-slim"},
		{"key": "dockerfile_workdir", "value": "/app"},
		{"key": "dockerfile_run", "value": "pip install -r requirements.txt"},
		{"key": "dockerfile_cmd", "value": "python manage.py runserver 0.0.0.0:8000"},
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
