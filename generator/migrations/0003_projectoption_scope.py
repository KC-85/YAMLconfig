from django.db import migrations, models


DOCKERFILE_OPTION_KEYS = {
    "base_image",
    "cmd",
    "dockerfile_cmd",
    "dockerfile_copy",
    "dockerfile_expose",
    "dockerfile_from",
    "dockerfile_run",
    "dockerfile_service",
    "dockerfile_workdir",
    "primary_service",
    "run",
    "workdir",
}


def classify_existing_options(apps, schema_editor):
    ProjectOption = apps.get_model("generator", "ProjectOption")
    ProjectOption.objects.filter(
        key__in=DOCKERFILE_OPTION_KEYS,
    ).update(scope="dockerfile")


class Migration(migrations.Migration):

    dependencies = [
        ("generator", "0002_configproject_owner"),
    ]

    operations = [
        migrations.AddField(
            model_name="projectoption",
            name="scope",
            field=models.CharField(
                choices=[
                    ("docker-compose", "Docker Compose"),
                    ("dockerfile", "Dockerfile"),
                ],
                default="docker-compose",
                max_length=32,
            ),
        ),
        migrations.RunPython(
            classify_existing_options,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.RemoveConstraint(
            model_name="projectoption",
            name="uniq_project_option_key",
        ),
        migrations.AddConstraint(
            model_name="projectoption",
            constraint=models.UniqueConstraint(
                fields=("project", "scope", "key"),
                name="uniq_project_option_scope_key",
            ),
        ),
        migrations.AlterModelOptions(
            name="projectoption",
            options={"ordering": ["scope", "key"]},
        ),
    ]
