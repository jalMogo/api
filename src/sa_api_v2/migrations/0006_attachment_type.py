# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ("sa_api_v2", "0005_auto_20171211_0042"),
    ]

    operations = [
        migrations.AddField(
            model_name="attachment",
            name="type",
            field=models.CharField(
                default="CO",
                max_length=2,
                choices=[("CO", "Cover"), ("RT", "Rich Text")],
            ),
            preserve_default=True,
        ),
    ]
