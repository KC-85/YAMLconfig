from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
import zipfile
from io import BytesIO

from .models import ConfigProject, Service, Network, NamedVolume, ProjectOption
from .yaml_builder import build_compose_yaml, build_dockerfile, build_output


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

    def test_service_create_generates_output(self):
        """Test that creating a service regenerates project output."""
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
        
        project.refresh_from_db()
        self.assertIn("web:", project.output_text)
        self.assertIn("nginx:latest", project.output_text)

    def test_service_edit_regenerates_output(self):
        """Test that editing a service regenerates project output."""
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
        
        project.refresh_from_db()
        self.assertIn("nginx:alpine", project.output_text)
        self.assertNotIn("nginx:latest", project.output_text)

    def test_service_delete_regenerates_output(self):
        """Test that deleting a service regenerates project output."""
        project = ConfigProject.objects.create(
            name="project", owner=self.user1, target_type="docker-compose"
        )
        service = Service.objects.create(project=project, name="web")
        self.client.login(username="user1", password="password123")
        
        self.client.post(
            reverse("generator:service_delete", args=[project.id, service.id])
        )
        
        project.refresh_from_db()
        self.assertNotIn("web:", project.output_text)

    def test_network_metadata_in_output(self):
        """Test that network metadata is included in generated output."""
        project = ConfigProject.objects.create(
            name="project", owner=self.user1, target_type="docker-compose"
        )
        Network.objects.create(
            project=project, name="appnet", driver="bridge", external=False
        )
        self.client.login(username="user1", password="password123")
        
        # Refresh output by editing project
        self.client.post(
            reverse("generator:project_edit", args=[project.id]),
            {"name": "project", "target_type": "docker-compose"},
        )
        
        project.refresh_from_db()
        self.assertIn("networks:", project.output_text)
        self.assertIn("appnet:", project.output_text)
        self.assertIn("bridge", project.output_text)

    def test_volume_metadata_in_output(self):
        """Test that volume metadata is included in generated output."""
        project = ConfigProject.objects.create(
            name="project", owner=self.user1, target_type="docker-compose"
        )
        NamedVolume.objects.create(
            project=project, name="data", driver="local", external=False
        )
        self.client.login(username="user1", password="password123")
        
        # Refresh output by editing project
        self.client.post(
            reverse("generator:project_edit", args=[project.id]),
            {"name": "project", "target_type": "docker-compose"},
        )
        
        project.refresh_from_db()
        self.assertIn("volumes:", project.output_text)
        self.assertIn("data:", project.output_text)
        self.assertIn("local", project.output_text)

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

    def test_option_create_updates_dockerfile_output(self):
        """Test that options affecting Dockerfile are reflected in output."""
        project = ConfigProject.objects.create(
            name="project", owner=self.user1, target_type="dockerfile"
        )
        Service.objects.create(project=project, name="app", image="python:3.12")
        self.client.login(username="user1", password="password123")
        
        self.client.post(
            reverse("generator:option_create", args=[project.id]),
            {"key": "dockerfile_run", "value": "pip install -r requirements.txt"},
        )
        
        project.refresh_from_db()
        self.assertIn("RUN pip install -r requirements.txt", project.output_text)

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
