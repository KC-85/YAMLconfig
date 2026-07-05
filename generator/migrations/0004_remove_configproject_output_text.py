from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("generator", "0003_projectoption_scope"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="configproject",
            name="output_text",
        ),
    ]
