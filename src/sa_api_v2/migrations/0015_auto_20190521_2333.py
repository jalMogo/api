# -*- coding: utf-8 -*-
# Generated by Django 1.11.20 on 2019-05-21 23:33
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('sa_api_v2', '0014_auto_20190406_0412'),
    ]

    operations = [
        migrations.CreateModel(
            name='Flavor',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=128)),
                ('slug', models.SlugField(default='', max_length=128, unique=True)),
            ],
            options={
                'ordering': ['name'],
                'db_table': 'ms_api_flavor',
            },
        ),
        migrations.CreateModel(
            name='Form',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('label', models.CharField(max_length=128)),
                ('is_enabled', models.BooleanField(default=True)),
                ('dataset', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to='sa_api_v2.DataSet')),
                ('flavor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='forms', to='sa_api_v2.Flavor')),
            ],
            options={
                'db_table': 'ms_api_form',
            },
        ),
        migrations.CreateModel(
            name='FormModule',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order', models.PositiveSmallIntegerField(default=0)),
                ('visible', models.BooleanField(default=True, help_text=b'Determines whether the module is visible by default.')),
            ],
            options={
                'ordering': ['order'],
                'db_table': 'ms_api_form_module',
            },
        ),
        migrations.CreateModel(
            name='FormStage',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order', models.PositiveSmallIntegerField(default=0)),
                ('form', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='stages', to='sa_api_v2.Form')),
            ],
            options={
                'ordering': ['order'],
                'db_table': 'ms_api_form_stage',
            },
        ),
        migrations.CreateModel(
            name='HtmlModule',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('content', models.TextField(blank=True, default=None)),
            ],
            options={
                'db_table': 'ms_api_form_module_html',
            },
        ),
        migrations.CreateModel(
            name='LayerGroup',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('label', models.CharField(max_length=128)),
            ],
            options={
                'db_table': 'ms_api_map_layer_group',
            },
        ),
        migrations.CreateModel(
            name='MapViewport',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('zoom', models.PositiveSmallIntegerField()),
                ('latitude', models.FloatField()),
                ('longitude', models.FloatField()),
                ('transition_duration', models.PositiveSmallIntegerField()),
                ('bearing', models.PositiveSmallIntegerField()),
                ('pitch', models.PositiveSmallIntegerField()),
                ('stage', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='map_viewport', to='sa_api_v2.FormStage')),
            ],
            options={
                'db_table': 'ms_api_map_viewport',
            },
        ),
        migrations.CreateModel(
            name='RadioField',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.CharField(max_length=128)),
                ('prompt', models.TextField(blank=True, default=b'')),
                ('private', models.BooleanField(default=False, help_text=b'If true, then the submitted data will be flagged as private.')),
                ('required', models.BooleanField(default=False, help_text=b'If true, then the form cannot be submitted unless this field has received a response.')),
                ('variant', models.CharField(choices=[(b'radio', b'a radio selection'), (b'dropdown', b'a dropdown list')], default=b'radio', max_length=128)),
                ('dropdown_placeholder', models.CharField(blank=True, max_length=128, null=True)),
            ],
            options={
                'db_table': 'ms_api_form_module_field_radio',
            },
        ),
        migrations.CreateModel(
            name='RadioOption',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('advance_to_next_stage', models.BooleanField(default=False, help_text=b'When this option is selected, the form will advance to the next stage.')),
                ('label', models.CharField(max_length=128)),
                ('value', models.CharField(max_length=128)),
                ('field', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='options', to='sa_api_v2.RadioField')),
                ('visibility_triggers', models.ManyToManyField(blank=True, help_text=b'If this FormFieldOption is selected, the following FormModules will become visible. Only default invisible modules are selectable here.', related_name='_radiooption_visibility_triggers_+', to='sa_api_v2.FormModule')),
            ],
            options={
                'db_table': 'ms_api_form_module_option_radio',
            },
        ),
        migrations.AddField(
            model_name='formstage',
            name='visible_layer_groups',
            field=models.ManyToManyField(blank=True, help_text=b'A list of layers that will become visible during this stage.', related_name='_formstage_visible_layer_groups_+', to='sa_api_v2.LayerGroup'),
        ),
        migrations.AddField(
            model_name='formmodule',
            name='htmlmodule',
            field=models.ForeignKey(blank=True, help_text=b'', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='modules', to='sa_api_v2.HtmlModule'),
        ),
        migrations.AddField(
            model_name='formmodule',
            name='radiofield',
            field=models.ForeignKey(blank=True, help_text=b'', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='modules', to='sa_api_v2.RadioField'),
        ),
        migrations.AddField(
            model_name='formmodule',
            name='stage',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='modules', to='sa_api_v2.FormStage'),
        ),
    ]
