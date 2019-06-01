# -*- coding: utf-8 -*-
# Generated by Django 1.11.20 on 2019-05-28 18:12
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('sa_api_v2', '0015_auto_20190521_2333'),
    ]

    operations = [
        migrations.CreateModel(
            name='TextField',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.CharField(max_length=128)),
                ('prompt', models.TextField(blank=True, default=b'')),
                ('private', models.BooleanField(default=False, help_text=b'If true, then the submitted data will be flagged as private.')),
                ('required', models.BooleanField(default=False, help_text=b'If true, then the form cannot be submitted unless this field has received a response.')),
            ],
            options={
                'db_table': 'ms_api_form_module_field_text',
            },
        ),
        migrations.AddField(
            model_name='htmlmodule',
            name='label',
            field=models.CharField(blank=True, default=b'', help_text=b"For labelling purponses only - won't be used on the form. Use this label to more easily identify this module in the form.", max_length=128),
        ),
        migrations.AlterField(
            model_name='formmodule',
            name='htmlmodule',
            field=models.ForeignKey(blank=True, help_text=b'Choose an html module. Create a new html module, or select an htmlmodule that already exists within this flavor. Only one field/module can be selected for this FormModule.', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='modules', to='sa_api_v2.HtmlModule'),
        ),
        migrations.AlterField(
            model_name='formmodule',
            name='radiofield',
            field=models.ForeignKey(blank=True, help_text=b'Choose a radio field. Create a new radio field, or select a radiofield that already exists within this flavor. Only one field/module can be selected for this FormModule.', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='modules', to='sa_api_v2.RadioField'),
        ),
        migrations.AlterField(
            model_name='htmlmodule',
            name='content',
            field=models.TextField(help_text=b'Add HTML here that will be displayed on the form. Make sure that the html is valid and sanitized!'),
        ),
    ]