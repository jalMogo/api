from django.contrib.gis.db import models
from .core import DataSet
from .flavors import Flavor


class Form(models.Model):
    label = models.CharField(max_length=128)
    is_enabled = models.BooleanField(default=True)

    dataset = models.ForeignKey(DataSet, related_name='+', on_delete=models.CASCADE)

    flavor = models.ForeignKey(
        Flavor,
        related_name='forms',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    def __unicode__(self):
        return self.label

    class Meta:
        app_label = 'sa_api_v2'
        db_table = 'ms_api_form'


class FormModule(models.Model):

    form = models.ForeignKey(
        Form,
        related_name="modules",
    )

    class Meta:
        app_label = 'sa_api_v2'
        db_table = 'ms_api_form_module'


class HtmlModule(FormModule):

    content = models.TextField(blank=True, default=None)

    class Meta:
        app_label = 'sa_api_v2'
        db_table = 'ms_api_form_module_html'


class FormField(FormModule):

    key = models.CharField(max_length=128)
    private = models.BooleanField(default=False, blank=True)
    required = models.BooleanField(default=False, blank=True)

    class Meta:
        app_label = 'sa_api_v2'
        abstract = True


class RadioField(FormField):
    RADIO = "radio"
    DROPDOWN = "dropdown"
    CHOICES = [
        (RADIO, 'a radio selection'),
        (DROPDOWN, 'a dropdown list'),
    ]

    variant = models.CharField(max_length=128, choices=CHOICES, default=RADIO)
    dropdown_placeholder = models.CharField(max_length=128, null=True, blank=True)

    class Meta:
        db_table = 'ms_api_form_module_field_radio'


class RadioOption(models.Model):
    label = models.CharField(max_length=128)
    value = models.CharField(max_length=128)

    field = models.ForeignKey(
        RadioField,
        related_name="options",
    )

    class Meta:
        app_label = 'sa_api_v2'
        db_table = 'ms_api_form_module_option_radio'
