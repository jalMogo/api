# -*- coding: utf-8 -*-
# Generated by Django 1.11.22 on 2019-11-06 20:48
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sa_api_v2', '0017_auto_20191016_2342'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='form',
            name='icon',
        ),
        migrations.AddField(
            model_name='form',
            name='engagement_text',
            field=models.CharField(blank=True, help_text=b'When multiple forms are available to select, this text will help describe this form.', max_length=255),
        ),
        migrations.AddField(
            model_name='form',
            name='image',
            field=models.CharField(blank=True, help_text=b"An URL for the location of this forms's image. Useful when selecting one of multiple forms on a flavor. This field is optional.", max_length=127),
        ),
        migrations.AlterField(
            model_name='addressfield',
            name='label',
            field=models.CharField(blank=True, help_text=b'This label will be used when displaying the submitted form field (eg: "My project idea is:")', max_length=127),
        ),
        migrations.AlterField(
            model_name='addressfield',
            name='placeholder',
            field=models.CharField(blank=True, help_text=b'Used to help guide users on what to type into the form\'s input box (eg: "Enter your email here", "joe@example.com")', max_length=255),
        ),
        migrations.AlterField(
            model_name='addressfield',
            name='prompt',
            field=models.CharField(blank=True, help_text=b'Some helpful text to guide the user on how to fill out this field (eg: "What is your project idea?")', max_length=512),
        ),
        migrations.AlterField(
            model_name='checkboxfield',
            name='label',
            field=models.CharField(blank=True, help_text=b'This label will be used when displaying the submitted form field (eg: "My project idea is:")', max_length=127),
        ),
        migrations.AlterField(
            model_name='checkboxfield',
            name='prompt',
            field=models.CharField(blank=True, help_text=b'Some helpful text to guide the user on how to fill out this field (eg: "What is your project idea?")', max_length=512),
        ),
        migrations.AlterField(
            model_name='checkboxoption',
            name='icon',
            field=models.CharField(blank=True, help_text=b"An URL for the location of this option's icon. This field is optional.", max_length=127),
        ),
        migrations.AlterField(
            model_name='datefield',
            name='form_format',
            field=models.CharField(blank=True, help_text=b'Formatting of the date that will be required for the input form', max_length=24),
        ),
        migrations.AlterField(
            model_name='datefield',
            name='include_ongoing',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='datefield',
            name='label',
            field=models.CharField(blank=True, help_text=b'This label will be used when displaying the submitted form field (eg: "My project idea is:")', max_length=127),
        ),
        migrations.AlterField(
            model_name='datefield',
            name='label_format',
            field=models.CharField(blank=True, help_text=b'Formatting of the date that will be used on the label', max_length=24),
        ),
        migrations.AlterField(
            model_name='datefield',
            name='placeholder',
            field=models.CharField(blank=True, help_text=b'Used to help guide users on what to type into the form\'s input box (eg: "Enter your email here", "joe@example.com")', max_length=255),
        ),
        migrations.AlterField(
            model_name='datefield',
            name='prompt',
            field=models.CharField(blank=True, help_text=b'Some helpful text to guide the user on how to fill out this field (eg: "What is your project idea?")', max_length=512),
        ),
        migrations.AlterField(
            model_name='filefield',
            name='label',
            field=models.CharField(blank=True, help_text=b'This label will be used when displaying the submitted form field (eg: "My project idea is:")', max_length=127),
        ),
        migrations.AlterField(
            model_name='filefield',
            name='prompt',
            field=models.CharField(blank=True, help_text=b'Some helpful text to guide the user on how to fill out this field (eg: "What is your project idea?")', max_length=512),
        ),
        migrations.AlterField(
            model_name='formstage',
            name='label',
            field=models.CharField(blank=True, help_text=b'An option label that can be used to describe the form stage. Currently it is only used internally.', max_length=255),
        ),
        migrations.AlterField(
            model_name='groupmodule',
            name='label',
            field=models.CharField(blank=True, help_text=b"For naming purposes only - this won't be displayed to end users. Use this label to more easily identify this module whle building the form.", max_length=127),
        ),
        migrations.AlterField(
            model_name='htmlmodule',
            name='label',
            field=models.CharField(blank=True, help_text=b"For naming purposes only - this won't be displayed to end users. Use this label to more easily identify this module whle building the form.", max_length=127),
        ),
        migrations.AlterField(
            model_name='numberfield',
            name='label',
            field=models.CharField(blank=True, help_text=b'This label will be used when displaying the submitted form field (eg: "My project idea is:")', max_length=127),
        ),
        migrations.AlterField(
            model_name='numberfield',
            name='placeholder',
            field=models.CharField(blank=True, help_text=b'Used to help guide users on what to type into the form\'s input box (eg: "Enter your email here", "joe@example.com")', max_length=255),
        ),
        migrations.AlterField(
            model_name='numberfield',
            name='prompt',
            field=models.CharField(blank=True, help_text=b'Some helpful text to guide the user on how to fill out this field (eg: "What is your project idea?")', max_length=512),
        ),
        migrations.AlterField(
            model_name='numberfield',
            name='units',
            field=models.CharField(blank=True, help_text=b'Units are used for labelling numerical submissions (eg: "13 acres")', max_length=127),
        ),
        migrations.AlterField(
            model_name='radiofield',
            name='dropdown_placeholder',
            field=models.CharField(blank=True, help_text=b'Used to help guide users on what to type into the form\'s input box (eg: "Enter your email here", "joe@example.com")', max_length=255),
        ),
        migrations.AlterField(
            model_name='radiofield',
            name='label',
            field=models.CharField(blank=True, help_text=b'This label will be used when displaying the submitted form field (eg: "My project idea is:")', max_length=127),
        ),
        migrations.AlterField(
            model_name='radiofield',
            name='prompt',
            field=models.CharField(blank=True, help_text=b'Some helpful text to guide the user on how to fill out this field (eg: "What is your project idea?")', max_length=512),
        ),
        migrations.AlterField(
            model_name='radiooption',
            name='icon',
            field=models.CharField(blank=True, help_text=b"An URL for the location of this option's icon. This field is optional.", max_length=127),
        ),
        migrations.AlterField(
            model_name='textareafield',
            name='label',
            field=models.CharField(blank=True, help_text=b'This label will be used when displaying the submitted form field (eg: "My project idea is:")', max_length=127),
        ),
        migrations.AlterField(
            model_name='textareafield',
            name='placeholder',
            field=models.CharField(blank=True, help_text=b'Used to help guide users on what to type into the form\'s input box (eg: "Enter your email here", "joe@example.com")', max_length=255),
        ),
        migrations.AlterField(
            model_name='textareafield',
            name='prompt',
            field=models.CharField(blank=True, help_text=b'Some helpful text to guide the user on how to fill out this field (eg: "What is your project idea?")', max_length=512),
        ),
        migrations.AlterField(
            model_name='textfield',
            name='label',
            field=models.CharField(blank=True, help_text=b'This label will be used when displaying the submitted form field (eg: "My project idea is:")', max_length=127),
        ),
        migrations.AlterField(
            model_name='textfield',
            name='placeholder',
            field=models.CharField(blank=True, help_text=b'Used to help guide users on what to type into the form\'s input box (eg: "Enter your email here", "joe@example.com")', max_length=255),
        ),
        migrations.AlterField(
            model_name='textfield',
            name='prompt',
            field=models.CharField(blank=True, help_text=b'Some helpful text to guide the user on how to fill out this field (eg: "What is your project idea?")', max_length=512),
        ),
    ]