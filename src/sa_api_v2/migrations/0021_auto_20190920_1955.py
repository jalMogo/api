# -*- coding: utf-8 -*-
# Generated by Django 1.11.22 on 2019-09-20 19:55
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sa_api_v2', '0020_auto_20190920_1950'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='LatLngField',
            new_name='LngLatField',
        ),
        migrations.RenameField(
            model_name='nestedorderedmodule',
            old_name='latlngfield',
            new_name='lnglatfield',
        ),
        migrations.RenameField(
            model_name='orderedmodule',
            old_name='latlngfield',
            new_name='lnglatfield',
        ),
        migrations.AlterModelTable(
            name='lnglatfield',
            table='ms_api_form_module_field_lnglat',
        ),
    ]
