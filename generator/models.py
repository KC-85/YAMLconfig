from django.db import models


class ConfigProject(models.Model):
	class TargetType(models.TextChoices):
		DOCKERFILE = "dockerfile", "Dockerfile"
		DOCKER_COMPOSE = "docker-compose", "Docker Compose"

	name = models.CharField(max_length=120)
	target_type = models.CharField(
		max_length=32,
		choices=TargetType.choices,
		default=TargetType.DOCKER_COMPOSE,
	)
	output_text = models.TextField(blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ["-updated_at"]

	def __str__(self) -> str:
		return f"{self.name} ({self.target_type})"


class Service(models.Model):
	project = models.ForeignKey(
		ConfigProject,
		on_delete=models.CASCADE,
		related_name="services",
	)
	name = models.CharField(max_length=120)
	image = models.CharField(max_length=255, blank=True)
	build_context = models.CharField(max_length=255, blank=True)
	container_name = models.CharField(max_length=120, blank=True)
	command = models.CharField(max_length=255, blank=True)
	restart_policy = models.CharField(max_length=50, blank=True)
	ports = models.JSONField(default=list, blank=True)
	volumes = models.JSONField(default=list, blank=True)
	environment = models.JSONField(default=dict, blank=True)
	depends_on = models.JSONField(default=list, blank=True)
	extra = models.JSONField(default=dict, blank=True)

	class Meta:
		ordering = ["name"]
		constraints = [
			models.UniqueConstraint(fields=["project", "name"], name="uniq_service_per_project"),
		]

	def __str__(self) -> str:
		return f"{self.project.name}: {self.name}"


class ProjectOption(models.Model):
	project = models.ForeignKey(
		ConfigProject,
		on_delete=models.CASCADE,
		related_name="options",
	)
	key = models.CharField(max_length=100)
	value = models.TextField(blank=True)

	class Meta:
		ordering = ["key"]
		constraints = [
			models.UniqueConstraint(fields=["project", "key"], name="uniq_project_option_key"),
		]

	def __str__(self) -> str:
		return f"{self.project.name}: {self.key}"


class Network(models.Model):
	project = models.ForeignKey(
		ConfigProject,
		on_delete=models.CASCADE,
		related_name="networks",
	)
	name = models.CharField(max_length=120)
	driver = models.CharField(max_length=100, blank=True)
	external = models.BooleanField(default=False)
	attachable = models.BooleanField(default=False)
	internal = models.BooleanField(default=False)
	labels = models.JSONField(default=dict, blank=True)
	driver_opts = models.JSONField(default=dict, blank=True)
	extra = models.JSONField(default=dict, blank=True)

	class Meta:
		ordering = ["name"]
		constraints = [
			models.UniqueConstraint(fields=["project", "name"], name="uniq_network_per_project"),
		]

	def __str__(self) -> str:
		return f"{self.project.name}: network/{self.name}"


class NamedVolume(models.Model):
	project = models.ForeignKey(
		ConfigProject,
		on_delete=models.CASCADE,
		related_name="named_volumes",
	)
	name = models.CharField(max_length=120)
	driver = models.CharField(max_length=100, blank=True)
	external = models.BooleanField(default=False)
	labels = models.JSONField(default=dict, blank=True)
	driver_opts = models.JSONField(default=dict, blank=True)
	extra = models.JSONField(default=dict, blank=True)

	class Meta:
		ordering = ["name"]
		constraints = [
			models.UniqueConstraint(fields=["project", "name"], name="uniq_named_volume_per_project"),
		]

	def __str__(self) -> str:
		return f"{self.project.name}: volume/{self.name}"
