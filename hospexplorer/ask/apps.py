from django.apps import AppConfig


# post_migrate signal handler that creates (or updates) the Curators group in admin
# with full CRUD permissions on WebsiteResource. Runs after every migrate so
# the group and its permissions are always in sync.
#
# To give a staff user access to manage WebsiteResource:
#   1. Log in to Django admin as a superuser
#   2. Go to Auth > Users, select the user, and check "Staff status"
#   3. On the same page, under "Groups", add the user to the "Curators" group
#      (this group is created automatically after running migrations)
#   4. Save. The user can now log in to admin and manage only WebsiteResource entries.
def create_curator_group(sender, **kwargs):
    from django.contrib.auth.models import Group, Permission
    from django.contrib.contenttypes.models import ContentType

    from ask.models import WebsiteResource

    ct = ContentType.objects.get_for_model(WebsiteResource)
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


class AskConfig(AppConfig):
    name = "ask"

    def ready(self):
        from django.db.models.signals import post_migrate

        post_migrate.connect(create_curator_group, sender=self)
