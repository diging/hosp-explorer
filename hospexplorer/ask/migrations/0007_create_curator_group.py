from django.db import migrations


def create_curator_group(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")

    ct = ContentType.objects.get(app_label="ask", model="websiteresource")
    perms = Permission.objects.filter(
        content_type=ct,
        codename__in=[
            "add_websiteresource",
            "change_websiteresource",
            "delete_websiteresource",
            "view_websiteresource",
        ],
    )

    group, _ = Group.objects.get_or_create(name="Curators")
    group.permissions.set(perms)


def remove_curator_group(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name="Curators").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("ask", "0006_merge_0005_merge_20260304_2256_0005_websiteresource"),
        ("auth", "0012_alter_user_first_name_max_length"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.RunPython(create_curator_group, remove_curator_group),
    ]
