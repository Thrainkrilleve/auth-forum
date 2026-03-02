from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("auth_forum", "0001_initial"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="general",
            options={
                "managed": False,
                "default_permissions": (),
                "permissions": (
                    ("basic_access", "Can access the forum"),
                    ("manage_forum", "Can moderate the forum (lock/pin/delete)"),
                    (
                        "bypass_board_restrictions",
                        "Can access boards regardless of group/state restrictions",
                    ),
                ),
            },
        ),
    ]
