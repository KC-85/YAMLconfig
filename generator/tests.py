import json
import zipfile
from io import BytesIO

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.staticfiles import finders
from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.urls import reverse

from .forms import (
    JSONObjectField,
    KeyValueField,
    LineListField,
    NamedVolumeForm,
    NetworkForm,
    ProjectOptionForm,
    ServiceForm,
)
from .models import ConfigProject, Service, Network, NamedVolume, ProjectOption
from .yaml_builder import build_compose_yaml, build_dockerfile, build_output


class FrontendAssetTests(TestCase):
    """Frontend dependencies should be available through Django static files."""

    static_assets = (
        "css/app.css",
        "vendor/alpinejs/alpine.min.js",
        "vendor/codemirror/codemirror.css",
        "vendor/codemirror/codemirror.js",
        "vendor/codemirror/yaml.js",
    )

    def test_built_frontend_assets_are_discoverable(self):
        for asset in self.static_assets:
            with self.subTest(asset=asset):
                self.assertIsNotNone(finders.find(asset))

    def test_dashboard_uses_local_frontend_assets_only(self):
        user = User.objects.create_user(
            username="frontend-user",
            password="password123",
        )
        project = ConfigProject.objects.create(
            name="frontend-project",
            owner=user,
        )
        self.client.force_login(user)

        response = self.client.get(
            reverse("generator:project_detail", args=[project.id])
        )
        html = response.content.decode("utf-8")

        for asset in self.static_assets:
            self.assertContains(response, f"{settings.STATIC_URL}{asset}")
        self.assertNotRegex(
            html,
            r'<(?:script|link)\b[^>]*(?:src|href)="https?://',
        )

    def test_tailwind_build_contains_project_components(self):
        css_path = settings.BASE_DIR / "theme" / "static" / "css" / "app.css"
        css = css_path.read_text(encoding="utf-8")

        self.assertIn(".form-control", css)
        self.assertIn(".bg-cyan-600", css)
        self.assertIn(".lg\\:grid-cols-3", css)


class YamlBuilderComposeTests(TestCase):
    """Unit tests for docker-compose YAML generation."""

    def test_build_compose_yaml_basic_service(self):
        """Test basic service serialization."""
        project = {
            "version": "3.8",
            "services": [
                {"name": "web", "image": "nginx:latest", "ports": ["8080:80"]}
            ],
        }
        output = build_compose_yaml(project)
        self.assertIn("version: '3.8'", output)
        self.assertIn("services:", output)
        self.assertIn("web:", output)
        self.assertIn("image: nginx:latest", output)
        self.assertIn("- 8080:80", output)

    def test_build_compose_yaml_network_metadata(self):
        """Test network metadata is serialized correctly."""
        project = {
            "services": [],
            "networks": [
                {
                    "name": "appnet",
                    "driver": "bridge",
                    "external": False,
                    "labels": {"env": "dev"},
                }
            ],
        }
        output = build_compose_yaml(project)
        self.assertIn("networks:", output)
        self.assertIn("appnet:", output)
        self.assertIn("driver: bridge", output)
        self.assertIn("external: false", output)
        self.assertIn("env: dev", output)

    def test_build_compose_yaml_volume_metadata(self):
        """Test volume metadata is serialized correctly."""
        project = {
            "services": [],
            "named_volumes": [
                {
                    "name": "data",
                    "driver": "local",
                    "external": False,
                    "labels": {"type": "app"},
                }
            ],
        }
        output = build_compose_yaml(project)
        self.assertIn("volumes:", output)
        self.assertIn("data:", output)
        self.assertIn("driver: local", output)
        self.assertIn("external: false", output)
        self.assertIn("type: app", output)

    def test_build_compose_yaml_service_environment(self):
        """Test service environment variables are included."""
        project = {
            "services": [
                {
                    "name": "db",
                    "image": "postgres:16",
                    "environment": {"POSTGRES_PASSWORD": "secret"},
                }
            ],
        }
        output = build_compose_yaml(project)
        self.assertIn("environment:", output)
        self.assertIn("POSTGRES_PASSWORD: secret", output)

    def test_build_compose_yaml_depends_on(self):
        """Test service dependencies are included."""
        project = {
            "services": [
                {"name": "web", "depends_on": ["db"]},
                {"name": "db", "image": "postgres:16"},
            ],
        }
        output = build_compose_yaml(project)
        self.assertIn("depends_on:", output)
        self.assertIn("- db", output)

    def test_build_compose_yaml_skip_services_without_name(self):
        """Test that services without names are skipped."""
        project = {
            "services": [
                {"image": "nginx:latest"},  # no name
                {"name": "web", "image": "nginx:latest"},
            ],
        }
        output = build_compose_yaml(project)
        self.assertIn("web:", output)
        # Should only have one service
        self.assertEqual(output.count("image:"), 1)


class YamlBuilderDockerfileTests(TestCase):
    """Unit tests for Dockerfile generation."""

    def test_build_dockerfile_basic(self):
        """Test basic Dockerfile generation."""
        project = {
            "services": [{"name": "web", "image": "python:3.12-slim"}],
        }
        output = build_dockerfile(project)
        self.assertIn("FROM python:3.12-slim", output)
        self.assertIn("WORKDIR /app", output)
        self.assertIn("COPY . .", output)

    def test_build_dockerfile_with_run_command(self):
        """Test Dockerfile with RUN instruction."""
        project = {
            "services": [],
            "options": [{"key": "dockerfile_run", "value": "pip install -r requirements.txt"}],
        }
        output = build_dockerfile(project)
        self.assertIn("RUN pip install -r requirements.txt", output)

    def test_build_dockerfile_with_expose(self):
        """Test Dockerfile EXPOSE instruction."""
        project = {
            "services": [
                {
                    "name": "web",
                    "ports": ["8000:8000"],
                    "command": "python manage.py runserver",
                }
            ],
        }
        output = build_dockerfile(project)
        self.assertIn("EXPOSE 8000", output)

    def test_build_dockerfile_with_cmd(self):
        """Test Dockerfile CMD instruction."""
        project = {
            "services": [{"name": "web", "command": "python manage.py runserver"}],
        }
        output = build_dockerfile(project)
        self.assertIn('CMD ["sh", "-c", "python manage.py runserver"]', output)

    def test_build_dockerfile_uses_default_image_when_service_image_is_blank(self):
        """A blank service image must not produce an empty FROM instruction."""
        project = {
            "services": [{"name": "web", "image": "   "}],
        }

        output = build_dockerfile(project)

        self.assertIn("FROM python:3.12-slim", output)
        self.assertNotIn("FROM \n", output)

    def test_build_dockerfile_rejects_multiline_single_line_instructions(self):
        """FROM, WORKDIR, and COPY values cannot inject extra instructions."""
        project = {
            "services": [{"name": "web", "image": "python:3.12"}],
            "options": [
                {"key": "dockerfile_from", "value": "alpine:3\nRUN unsafe-from"},
                {"key": "dockerfile_workdir", "value": "/app\nRUN unsafe-workdir"},
                {"key": "dockerfile_copy", "value": ". .\nRUN unsafe-copy"},
            ],
        }

        output = build_dockerfile(project)

        self.assertIn("FROM python:3.12", output)
        self.assertIn("WORKDIR /app", output)
        self.assertIn("COPY . .", output)
        self.assertNotIn("unsafe-", output)

    def test_build_dockerfile_selects_named_primary_service(self):
        """dockerfile_service should control service-derived defaults."""
        project = {
            "services": [
                {
                    "name": "database",
                    "image": "postgres:16",
                    "ports": ["5432:5432"],
                },
                {
                    "name": "web",
                    "image": "python:3.12-slim",
                    "ports": ["8000:8000"],
                    "command": "python app.py",
                },
            ],
            "options": [{"key": "dockerfile_service", "value": "web"}],
        }

        output = build_dockerfile(project)

        self.assertIn("FROM python:3.12-slim", output)
        self.assertIn("EXPOSE 8000", output)
        self.assertIn('CMD ["sh", "-c", "python app.py"]', output)
        self.assertNotIn("postgres:16", output)
        self.assertNotIn("EXPOSE 5432", output)

    def test_build_dockerfile_prefers_a_service_with_an_image(self):
        """Fallback selection should skip services that cannot provide FROM."""
        project = {
            "services": [
                {"name": "empty", "image": ""},
                {"name": "worker", "image": "python:3.13-slim"},
            ],
        }

        output = build_dockerfile(project)

        self.assertIn("FROM python:3.13-slim", output)

    def test_build_dockerfile_parses_expose_option_text(self):
        """Text-backed project options should support multiple exposed ports."""
        project = {
            "services": [],
            "options": [
                {
                    "key": "dockerfile_expose",
                    "value": '8000, 8443/UDP, ["9000", "9001/tcp"]',
                }
            ],
        }

        output = build_dockerfile(project)

        self.assertIn("EXPOSE 8000", output)
        self.assertIn("EXPOSE 8443/udp", output)
        self.assertIn("EXPOSE 9000", output)
        self.assertIn("EXPOSE 9001/tcp", output)

    def test_build_dockerfile_normalizes_and_filters_service_ports(self):
        """Host mappings become container ports and invalid ports are omitted."""
        project = {
            "services": [
                {
                    "name": "web",
                    "image": "python:3.12",
                    "ports": [
                        "127.0.0.1:8080:80/tcp",
                        "8443:443/UDP",
                        {"target": 9000},
                        "70000:70000",
                        "not-a-port",
                        "8080:80/tcp",
                    ],
                }
            ],
        }

        output = build_dockerfile(project)

        self.assertEqual(output.count("EXPOSE 80/tcp"), 1)
        self.assertIn("EXPOSE 443/udp", output)
        self.assertIn("EXPOSE 9000", output)
        self.assertNotIn("EXPOSE 70000", output)
        self.assertNotIn("EXPOSE not-a-port", output)

    def test_build_dockerfile_emits_valid_json_cmd(self):
        """String commands should remain valid JSON after escaping."""
        command = 'python -c "print(\\"ready\\")"\npython app.py'
        project = {
            "services": [{"name": "web", "image": "python:3.12", "command": command}],
        }

        output = build_dockerfile(project)
        cmd_line = next(line for line in output.splitlines() if line.startswith("CMD "))

        self.assertEqual(json.loads(cmd_line.removeprefix("CMD ")), ["sh", "-c", command])

    def test_build_dockerfile_splits_multiline_run_commands(self):
        """Each non-empty line in a text option should become a RUN instruction."""
        project = {
            "services": [],
            "options": [
                {
                    "key": "dockerfile_run",
                    "value": "apt-get update\n\napt-get install -y curl",
                }
            ],
        }

        output = build_dockerfile(project)

        self.assertIn("RUN apt-get update", output)
        self.assertIn("RUN apt-get install -y curl", output)
        self.assertEqual(output.count("RUN "), 2)


class ProjectOptionScopeTests(TestCase):
    """Options should only affect the generator for their declared scope."""

    def test_compose_ignores_dockerfile_options(self):
        project = {
            "services": [],
            "options": [
                {
                    "scope": "dockerfile",
                    "key": "dockerfile_run",
                    "value": "pip install unsafe-in-compose",
                },
                {
                    "scope": "docker-compose",
                    "key": "name",
                    "value": "scoped-compose-project",
                },
            ],
        }

        output = build_compose_yaml(project)

        self.assertIn("name: scoped-compose-project", output)
        self.assertNotIn("dockerfile_run", output)
        self.assertNotIn("unsafe-in-compose", output)

    def test_dockerfile_ignores_compose_options(self):
        project = {
            "services": [{"name": "web", "image": "python:3.13-slim"}],
            "options": [
                {
                    "scope": "docker-compose",
                    "key": "dockerfile_from",
                    "value": "alpine:should-not-be-used",
                },
                {
                    "scope": "dockerfile",
                    "key": "dockerfile_workdir",
                    "value": "/srv/app",
                },
            ],
        }

        output = build_dockerfile(project)

        self.assertIn("FROM python:3.13-slim", output)
        self.assertIn("WORKDIR /srv/app", output)
        self.assertNotIn("alpine:should-not-be-used", output)

    def test_unscoped_dictionary_options_remain_backwards_compatible(self):
        project = {
            "services": [],
            "options": [
                {"key": "dockerfile_run", "value": "echo legacy-dockerfile"},
                {"key": "name", "value": "legacy-compose"},
            ],
        }

        compose_output = build_compose_yaml(project)
        dockerfile_output = build_dockerfile(project)

        self.assertIn("name: legacy-compose", compose_output)
        self.assertNotIn("dockerfile_run", compose_output)
        self.assertIn("RUN echo legacy-dockerfile", dockerfile_output)
        self.assertNotIn("legacy-compose", dockerfile_output)

    def test_same_key_can_exist_once_in_each_scope(self):
        project = ConfigProject.objects.create(name="scoped-options")

        ProjectOption.objects.create(
            project=project,
            scope=ProjectOption.Scope.DOCKER_COMPOSE,
            key="name",
            value="compose-name",
        )
        ProjectOption.objects.create(
            project=project,
            scope=ProjectOption.Scope.DOCKERFILE,
            key="name",
            value="dockerfile-value",
        )

        self.assertEqual(project.options.filter(key="name").count(), 2)


class GeneratorFormUsabilityTests(TestCase):
    """Structured form fields should accept readable text and legacy JSON."""

    @staticmethod
    def service_data(**overrides):
        data = {
            "name": "web",
            "image": "nginx:latest",
            "build_context": "",
            "container_name": "",
            "command": "",
            "restart_policy": "",
            "ports": "",
            "volumes": "",
            "environment": "",
            "depends_on": "",
            "extra": "",
        }
        data.update(overrides)
        return data

    def test_line_list_field_accepts_lines_and_legacy_json(self):
        field = LineListField()

        self.assertEqual(
            field.clean("8000:80\n8443:443\n8000:80"),
            ["8000:80", "8443:443"],
        )
        self.assertEqual(
            field.clean('["8000:80", 443]'),
            ["8000:80", "443"],
        )

    def test_key_value_field_accepts_lines_and_legacy_json(self):
        field = KeyValueField()

        self.assertEqual(
            field.clean("APP_ENV=development\nTOKEN=a=b\nEMPTY="),
            {
                "APP_ENV": "development",
                "TOKEN": "a=b",
                "EMPTY": "",
            },
        )
        self.assertEqual(
            field.clean('{"DEBUG": true, "PORT": 8000}'),
            {"DEBUG": True, "PORT": 8000},
        )

    def test_json_object_field_rejects_non_object_json(self):
        field = JSONObjectField()

        with self.assertRaisesMessage(
            ValidationError,
            "Enter a JSON object using curly braces",
        ):
            field.clean('["not", "an", "object"]')

    def test_service_form_parses_readable_fields_and_validates_dependencies(self):
        project = ConfigProject.objects.create(name="forms-project")
        Service.objects.create(project=project, name="database")
        form = ServiceForm(
            data=self.service_data(
                ports="8000:80\n8443:443",
                volumes="./data:/app/data\ncache:/app/cache",
                environment="APP_ENV=development\nDEBUG=true",
                depends_on="database",
                extra='{"healthcheck": {"test": ["CMD", "curl", "localhost"]}}',
            ),
            project=project,
        )

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["ports"], ["8000:80", "8443:443"])
        self.assertEqual(
            form.cleaned_data["volumes"],
            ["./data:/app/data", "cache:/app/cache"],
        )
        self.assertEqual(
            form.cleaned_data["environment"],
            {"APP_ENV": "development", "DEBUG": "true"},
        )
        self.assertEqual(form.cleaned_data["depends_on"], ["database"])

    def test_service_form_rejects_unknown_and_self_dependencies(self):
        project = ConfigProject.objects.create(name="forms-project")

        unknown_form = ServiceForm(
            data=self.service_data(depends_on="missing-service"),
            project=project,
        )
        self.assertFalse(unknown_form.is_valid())
        self.assertIn("Unknown service(s): missing-service", unknown_form.errors["depends_on"][0])

        self_form = ServiceForm(
            data=self.service_data(depends_on="web"),
            project=project,
        )
        self.assertFalse(self_form.is_valid())
        self.assertIn("cannot depend on itself", self_form.errors["depends_on"][0])

    def test_service_form_rejects_duplicate_names_before_database_save(self):
        project = ConfigProject.objects.create(name="forms-project")
        Service.objects.create(project=project, name="web")
        form = ServiceForm(data=self.service_data(), project=project)

        self.assertFalse(form.is_valid())
        self.assertIn("already exists", form.errors["name"][0])

    def test_network_and_volume_forms_parse_key_value_fields(self):
        project = ConfigProject.objects.create(name="forms-project")
        network_form = NetworkForm(
            data={
                "name": "frontend",
                "driver": "bridge",
                "external": False,
                "attachable": False,
                "internal": False,
                "labels": "environment=development",
                "driver_opts": "com.docker.network.driver.mtu=1450",
                "extra": "{}",
            },
            project=project,
        )
        volume_form = NamedVolumeForm(
            data={
                "name": "data",
                "driver": "local",
                "external": False,
                "labels": "backup=daily",
                "driver_opts": "type=none",
                "extra": "{}",
            },
            project=project,
        )

        self.assertTrue(network_form.is_valid(), network_form.errors)
        self.assertEqual(
            network_form.cleaned_data["labels"],
            {"environment": "development"},
        )
        self.assertTrue(volume_form.is_valid(), volume_form.errors)
        self.assertEqual(
            volume_form.cleaned_data["driver_opts"],
            {"type": "none"},
        )

    def test_project_option_form_rejects_keys_in_the_wrong_scope(self):
        project = ConfigProject.objects.create(name="forms-project")
        compose_form = ProjectOptionForm(
            data={
                "scope": ProjectOption.Scope.DOCKER_COMPOSE,
                "key": "dockerfile_run",
                "value": "echo no",
            },
            project=project,
        )
        dockerfile_form = ProjectOptionForm(
            data={
                "scope": ProjectOption.Scope.DOCKERFILE,
                "key": "unknown_key",
                "value": "unused",
            },
            project=project,
        )

        self.assertFalse(compose_form.is_valid())
        self.assertIn("Change the scope to Dockerfile", compose_form.errors["key"][0])
        self.assertFalse(dockerfile_form.is_valid())
        self.assertIn("not used by Dockerfile generation", dockerfile_form.errors["key"][0])


class ProjectCrudTests(TestCase):
    """Integration tests for CRUD operations."""

    def setUp(self):
        self.client = Client()
        self.user1 = User.objects.create_user(
            username="user1", password="password123"
        )
        self.user2 = User.objects.create_user(
            username="user2", password="password123"
        )
        self.client.login = lambda *args, **kwargs: self.client.force_login(self.user1)

    def _get_live_output(self, project: ConfigProject) -> str:
        response = self.client.get(
            reverse("generator:project_detail", args=[project.id])
        )
        self.assertEqual(response.status_code, 200)
        return response.context["generated_output"]

    def test_project_create_requires_login(self):
        """Test that project creation requires authentication."""
        response = self.client.get(reverse("generator:project_create"))
        self.assertEqual(response.status_code, 302)  # redirect to login

    def test_project_create_sets_owner(self):
        """Test that created projects are owned by the logged-in user."""
        self.client.force_login(self.user1)
        response = self.client.post(
            reverse("generator:project_create"),
            {"name": "test-project", "target_type": "docker-compose"},
        )
        self.assertEqual(response.status_code, 302)  # redirect after success
        project = ConfigProject.objects.get(name="test-project")
        self.assertEqual(project.owner, self.user1)

    def test_project_list_only_shows_owned_projects(self):
        """Test that users only see their own projects."""
        project1 = ConfigProject.objects.create(
            name="project1", owner=self.user1
        )
        project2 = ConfigProject.objects.create(
            name="project2", owner=self.user2
        )

        self.client.login(username="user1", password="password123")
        response = self.client.get(reverse("generator:project_list"))
        self.assertContains(response, "project1")
        self.assertNotContains(response, "project2")

    def test_project_detail_requires_ownership(self):
        """Test that users cannot access projects they don't own."""
        project = ConfigProject.objects.create(
            name="project", owner=self.user2
        )
        self.client.force_login(self.user1)
        response = self.client.get(
            reverse("generator:project_detail", args=[project.id])
        )
        self.assertEqual(response.status_code, 404)

    def test_project_detail_lists_saved_service(self):
        """A saved service should be rendered with its edit action."""
        project = ConfigProject.objects.create(
            name="service-list-project", owner=self.user1
        )
        service = Service.objects.create(
            project=project,
            name="visible-service",
            image="regression/service:1",
        )

        self.client.force_login(self.user1)
        response = self.client.get(
            reverse("generator:project_detail", args=[project.id])
        )

        self.assertContains(response, "visible-service")
        self.assertContains(response, "regression/service:1")
        self.assertContains(
            response,
            reverse("generator:service_edit", args=[project.id, service.id]),
        )
        self.assertNotContains(response, "No services yet")

    def test_project_detail_lists_saved_option(self):
        """A saved project option should be rendered with its edit action."""
        project = ConfigProject.objects.create(
            name="option-list-project", owner=self.user1
        )
        option = ProjectOption.objects.create(
            project=project,
            scope=ProjectOption.Scope.DOCKERFILE,
            key="dockerfile_run",
            value="regression-install-command",
        )

        self.client.force_login(self.user1)
        response = self.client.get(
            reverse("generator:project_detail", args=[project.id])
        )

        self.assertContains(response, "dockerfile_run")
        self.assertContains(response, "regression-install-command")
        self.assertContains(
            response,
            reverse("generator:option_edit", args=[project.id, option.id]),
        )
        self.assertNotContains(response, "No build options configured")

    def test_project_detail_lists_saved_network(self):
        """A saved network should be rendered with its edit action."""
        project = ConfigProject.objects.create(
            name="network-list-project", owner=self.user1
        )
        network = Network.objects.create(
            project=project,
            name="visible-network",
            driver="regression-network-driver",
        )

        self.client.force_login(self.user1)
        response = self.client.get(
            reverse("generator:project_detail", args=[project.id])
        )

        self.assertContains(response, "visible-network")
        self.assertContains(response, "regression-network-driver")
        self.assertContains(
            response,
            reverse("generator:network_edit", args=[project.id, network.id]),
        )
        self.assertNotContains(response, "No networks defined yet")

    def test_project_detail_lists_saved_volume(self):
        """A saved named volume should be rendered with its edit action."""
        project = ConfigProject.objects.create(
            name="volume-list-project", owner=self.user1
        )
        volume = NamedVolume.objects.create(
            project=project,
            name="visible-volume",
            driver="regression-volume-driver",
        )

        self.client.force_login(self.user1)
        response = self.client.get(
            reverse("generator:project_detail", args=[project.id])
        )

        self.assertContains(response, "visible-volume")
        self.assertContains(response, "regression-volume-driver")
        self.assertContains(
            response,
            reverse("generator:volume_edit", args=[project.id, volume.id]),
        )
        self.assertNotContains(response, "No volumes defined yet")

    def test_project_list_shows_component_counts(self):
        """Project cards should show counts from the named relationships."""
        project = ConfigProject.objects.create(
            name="counted-project", owner=self.user1
        )
        Service.objects.create(project=project, name="service-one")
        Service.objects.create(project=project, name="service-two")
        Network.objects.create(project=project, name="network-one")
        NamedVolume.objects.create(project=project, name="volume-one")

        self.client.force_login(self.user1)
        response = self.client.get(reverse("generator:project_list"))
        html = response.content.decode("utf-8")

        self.assertRegex(
            html,
            r"Services:</span>\s*<span[^>]*>\s*2\s*</span>",
        )
        self.assertRegex(
            html,
            r"Networks:</span>\s*<span[^>]*>\s*1\s*</span>",
        )
        self.assertRegex(
            html,
            r"Volumes:</span>\s*<span[^>]*>\s*1\s*</span>",
        )

    def test_service_create_is_reflected_in_live_output(self):
        """Creating a service should be reflected without a cached output write."""
        project = ConfigProject.objects.create(
            name="project", owner=self.user1, target_type="docker-compose"
        )
        self.client.login(username="user1", password="password123")
        
        self.client.post(
            reverse("generator:service_create", args=[project.id]),
            {
                "name": "web",
                "image": "nginx:latest",
                "ports": '["8080:80"]',
                "build_context": "",
                "container_name": "",
                "command": "",
                "restart_policy": "",
                "volumes": "[]",
                "environment": "{}",
                "depends_on": "[]",
                "extra": "{}",
            },
        )
        
        output = self._get_live_output(project)
        self.assertIn("web:", output)
        self.assertIn("nginx:latest", output)

    def test_service_create_accepts_line_based_structured_fields(self):
        """The service view should save readable list and key-value input."""
        project = ConfigProject.objects.create(
            name="project", owner=self.user1, target_type="docker-compose"
        )
        Service.objects.create(project=project, name="database")
        self.client.force_login(self.user1)

        response = self.client.post(
            reverse("generator:service_create", args=[project.id]),
            {
                "name": "web",
                "image": "nginx:latest",
                "build_context": "",
                "container_name": "",
                "command": "",
                "restart_policy": "",
                "ports": "8000:80\n8443:443",
                "volumes": "./data:/usr/share/nginx/html",
                "environment": "APP_ENV=development\nDEBUG=true",
                "depends_on": "database",
                "extra": "{}",
            },
        )

        self.assertEqual(response.status_code, 302)
        service = project.services.get(name="web")
        self.assertEqual(service.ports, ["8000:80", "8443:443"])
        self.assertEqual(
            service.environment,
            {"APP_ENV": "development", "DEBUG": "true"},
        )
        self.assertEqual(service.depends_on, ["database"])

    def test_duplicate_service_name_returns_a_form_error(self):
        """Duplicate names should not reach the database constraint."""
        project = ConfigProject.objects.create(
            name="project", owner=self.user1, target_type="docker-compose"
        )
        Service.objects.create(project=project, name="web")
        self.client.force_login(self.user1)

        response = self.client.post(
            reverse("generator:service_create", args=[project.id]),
            {
                "name": "web",
                "image": "nginx:latest",
                "build_context": "",
                "container_name": "",
                "command": "",
                "restart_policy": "",
                "ports": "",
                "volumes": "",
                "environment": "",
                "depends_on": "",
                "extra": "",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already exists in the project")
        self.assertEqual(project.services.filter(name="web").count(), 1)

    def test_service_edit_is_reflected_in_live_output(self):
        """Editing a service should be reflected in the next preview."""
        project = ConfigProject.objects.create(
            name="project", owner=self.user1, target_type="docker-compose"
        )
        service = Service.objects.create(
            project=project, name="web", image="nginx:latest"
        )
        self.client.login(username="user1", password="password123")
        
        self.client.post(
            reverse("generator:service_edit", args=[project.id, service.id]),
            {
                "name": "web",
                "image": "nginx:alpine",
                "ports": [],
                "build_context": "",
                "container_name": "",
                "command": "",
                "restart_policy": "",
                "volumes": [],
                "environment": {},
                "depends_on": [],
                "extra": {},
            },
        )
        
        output = self._get_live_output(project)
        self.assertIn("nginx:alpine", output)
        self.assertNotIn("nginx:latest", output)

    def test_service_delete_is_reflected_in_live_output(self):
        """Deleting a service should be reflected in the next preview."""
        project = ConfigProject.objects.create(
            name="project", owner=self.user1, target_type="docker-compose"
        )
        service = Service.objects.create(project=project, name="web")
        self.client.login(username="user1", password="password123")
        
        self.client.post(
            reverse("generator:service_delete", args=[project.id, service.id])
        )
        
        output = self._get_live_output(project)
        self.assertNotIn("web:", output)

    def test_network_metadata_in_output(self):
        """Test that network metadata is included in generated output."""
        project = ConfigProject.objects.create(
            name="project", owner=self.user1, target_type="docker-compose"
        )
        Network.objects.create(
            project=project, name="appnet", driver="bridge", external=False
        )
        self.client.login(username="user1", password="password123")

        output = self._get_live_output(project)
        self.assertIn("networks:", output)
        self.assertIn("appnet:", output)
        self.assertIn("bridge", output)

    def test_volume_metadata_in_output(self):
        """Test that volume metadata is included in generated output."""
        project = ConfigProject.objects.create(
            name="project", owner=self.user1, target_type="docker-compose"
        )
        NamedVolume.objects.create(
            project=project, name="data", driver="local", external=False
        )
        self.client.login(username="user1", password="password123")

        output = self._get_live_output(project)
        self.assertIn("volumes:", output)
        self.assertIn("data:", output)
        self.assertIn("local", output)

    def test_delete_confirmation_view_has_flag(self):
        """Test that delete confirmation views pass is_delete_confirm flag."""
        project = ConfigProject.objects.create(
            name="project", owner=self.user1
        )
        self.client.login(username="user1", password="password123")
        
        response = self.client.get(
            reverse("generator:project_delete", args=[project.id])
        )
        self.assertContains(response, "Delete Confirmation")
        self.assertContains(response, "This action cannot be undone")

    def test_project_detail_shows_yaml_ide_preview(self):
        """Test that the project detail page includes the YAML IDE preview."""
        project = ConfigProject.objects.create(
            name="project", owner=self.user1, target_type="docker-compose"
        )
        Service.objects.create(project=project, name="web", image="nginx:latest")

        self.client.force_login(self.user1)
        response = self.client.get(
            reverse("generator:project_detail", args=[project.id])
        )

        self.assertContains(response, "YAML IDE Preview")
        self.assertContains(response, 'id="yaml-ide-source"')
        self.assertContains(response, "codemirror")
        self.assertIn("nginx:latest", response.context["generated_output"])

    def test_project_detail_reflects_direct_database_changes(self):
        """Direct ORM changes should appear without an explicit refresh step."""
        project = ConfigProject.objects.create(
            name="project", owner=self.user1, target_type="docker-compose"
        )
        service = Service.objects.create(
            project=project,
            name="web",
            image="nginx:before",
        )
        self.client.force_login(self.user1)

        before = self._get_live_output(project)
        service.image = "nginx:after"
        service.save(update_fields=["image"])
        after = self._get_live_output(project)

        self.assertIn("nginx:before", before)
        self.assertIn("nginx:after", after)
        self.assertNotIn("nginx:before", after)

    def test_compose_preview_matches_compose_download(self):
        """The Compose preview and download should use identical live output."""
        project = ConfigProject.objects.create(
            name="project", owner=self.user1, target_type="docker-compose"
        )
        Service.objects.create(project=project, name="web", image="nginx:latest")
        self.client.force_login(self.user1)

        preview = self._get_live_output(project)
        download = self.client.get(
            reverse("generator:project_download_compose", args=[project.id])
        )

        self.assertEqual(preview, download.content.decode("utf-8"))

    def test_dockerfile_preview_matches_dockerfile_download(self):
        """The Dockerfile preview and download should use identical live output."""
        project = ConfigProject.objects.create(
            name="project", owner=self.user1, target_type="dockerfile"
        )
        Service.objects.create(
            project=project,
            name="app",
            image="python:3.13-slim",
            command="python app.py",
        )
        self.client.force_login(self.user1)

        preview = self._get_live_output(project)
        download = self.client.get(
            reverse("generator:project_download_dockerfile", args=[project.id])
        )

        self.assertEqual(preview, download.content.decode("utf-8"))

    def test_option_create_is_reflected_in_live_dockerfile_output(self):
        """Dockerfile options should appear in the next live preview."""
        project = ConfigProject.objects.create(
            name="project", owner=self.user1, target_type="dockerfile"
        )
        Service.objects.create(project=project, name="app", image="python:3.12")
        self.client.login(username="user1", password="password123")
        
        self.client.post(
            reverse("generator:option_create", args=[project.id]),
            {
                "scope": ProjectOption.Scope.DOCKERFILE,
                "key": "dockerfile_run",
                "value": "pip install -r requirements.txt",
            },
        )
        
        output = self._get_live_output(project)
        self.assertIn("RUN pip install -r requirements.txt", output)
        self.assertEqual(
            project.options.get(key="dockerfile_run").scope,
            ProjectOption.Scope.DOCKERFILE,
        )

    def test_project_download_compose_returns_attachment(self):
        """Compose download should return attachment for owned project."""
        project = ConfigProject.objects.create(
            name="project", owner=self.user1, target_type="docker-compose"
        )
        Service.objects.create(project=project, name="web", image="nginx:latest")

        self.client.login(username="user1", password="password123")
        response = self.client.get(
            reverse("generator:project_download_compose", args=[project.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment;", response["Content-Disposition"])
        self.assertIn("docker-compose.yml", response["Content-Disposition"])
        self.assertIn("services:", response.content.decode("utf-8"))

    def test_project_download_dockerfile_returns_attachment(self):
        """Dockerfile download should return attachment for owned project."""
        project = ConfigProject.objects.create(
            name="project", owner=self.user1, target_type="dockerfile"
        )
        Service.objects.create(project=project, name="app", image="python:3.12")

        self.client.login(username="user1", password="password123")
        response = self.client.get(
            reverse("generator:project_download_dockerfile", args=[project.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment;", response["Content-Disposition"])
        self.assertIn("Dockerfile", response["Content-Disposition"])
        self.assertIn("FROM python:3.12", response.content.decode("utf-8"))

    def test_project_download_bundle_includes_expected_files(self):
        """Bundle download should include docker-compose and Dockerfile files."""
        project = ConfigProject.objects.create(
            name="project", owner=self.user1, target_type="docker-compose"
        )
        Service.objects.create(project=project, name="web", image="nginx:latest")

        self.client.login(username="user1", password="password123")
        response = self.client.get(
            reverse("generator:project_download_bundle", args=[project.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/zip")
        self.assertIn("docker-config.zip", response["Content-Disposition"])

        with zipfile.ZipFile(BytesIO(response.content), "r") as archive:
            names = archive.namelist()
            self.assertIn("docker-compose.yml", names)
            self.assertIn("Dockerfile", names)

    def test_project_download_requires_ownership(self):
        """Users should not download files from projects they do not own."""
        project = ConfigProject.objects.create(name="private", owner=self.user2)
        self.client.login(username="user1", password="password123")

        response = self.client.get(
            reverse("generator:project_download_bundle", args=[project.id])
        )
        self.assertEqual(response.status_code, 404)


class BuildOutputSelectionTests(TestCase):
    """Tests for build_output target selection."""

    def test_build_output_defaults_to_compose(self):
        """Test that build_output defaults to docker-compose."""
        project = {
            "services": [{"name": "web", "image": "nginx:latest"}],
        }
        output = build_output(project)
        self.assertIn("services:", output)
        self.assertIn("version:", output)

    def test_build_output_dockerfile_target(self):
        """Test that build_output respects dockerfile target."""
        project = {
            "target_type": "dockerfile",
            "services": [{"name": "web", "image": "python:3.12"}],
        }
        output = build_output(project, target_type="dockerfile")
        self.assertIn("FROM python:3.12", output)

    def test_build_output_respects_project_target_type(self):
        """Test that build_output uses project.target_type when no override."""
        project = {
            "target_type": "dockerfile",
            "services": [{"name": "web", "image": "python:3.12"}],
        }
        output = build_output(project)
        self.assertIn("FROM python:3.12", output)
