# -*- coding: utf-8 -*-
# Generated by Django 1.11.22 on 2019-09-24 21:26
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('sa_api_v2', '0019_auto_20190923_2026'),
    ]

    operations = [
        migrations.AddField(
            model_name='orderedmodule',
            name='permitted_group',
            field=models.ForeignKey(blank=True, help_text=b"Only this Group is allowed to edit this module's field. If null, any group can edit.", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='sa_api_v2.Group'),
        ),
    ]
