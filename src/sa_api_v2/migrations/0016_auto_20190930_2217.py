# -*- coding: utf-8 -*-
# Generated by Django 1.11.22 on 2019-09-30 22:17
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sa_api_v2', '0015_dataset_auth_required'),
    ]

    operations = [
        migrations.AddField(
            model_name='placeemailtemplate',
            name='default_recipient_email',
            field=models.EmailField(blank=True, default=b'', help_text=b'A "Default recipient email" will take precedence             over a Submission\'s "Recipient email field".', max_length=254),
        ),
        migrations.AlterField(
            model_name='placeemailtemplate',
            name='bcc_email_1',
            field=models.EmailField(blank=True, default=b'', max_length=254),
        ),
        migrations.AlterField(
            model_name='placeemailtemplate',
            name='bcc_email_2',
            field=models.EmailField(blank=True, default=b'', max_length=254),
        ),
        migrations.AlterField(
            model_name='placeemailtemplate',
            name='bcc_email_3',
            field=models.EmailField(blank=True, default=b'', max_length=254),
        ),
        migrations.AlterField(
            model_name='placeemailtemplate',
            name='bcc_email_4',
            field=models.EmailField(blank=True, default=b'', max_length=254),
        ),
        migrations.AlterField(
            model_name='placeemailtemplate',
            name='bcc_email_5',
            field=models.EmailField(blank=True, default=b'', max_length=254),
        ),
        migrations.AlterField(
            model_name='placeemailtemplate',
            name='body_html',
            field=models.TextField(blank=True, default=b''),
        ),
        migrations.AlterField(
            model_name='placeemailtemplate',
            name='recipient_email_field',
            field=models.CharField(blank=True, default=b'', max_length=128),
        ),
    ]
