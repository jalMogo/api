# -*- coding: utf-8 -*-
# Generated by Django 1.11.22 on 2019-11-06 20:55
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sa_api_v2', '0018_auto_20191106_2048'),
    ]

    operations = [
        migrations.AddField(
            model_name='formstage',
            name='header_text',
            field=models.CharField(blank=True, help_text=b'Use this when adding a header to the Form Stage. Usually used to summarize this section of the form.', max_length=512),
        ),
    ]
