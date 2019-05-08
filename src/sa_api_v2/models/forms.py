from django.contrib.gis.db import models
from .core import DataSet
from .flavors import Flavor
import logging
from django.core.exceptions import ValidationError
logger = logging.getLogger(__name__)


class Form(models.Model):
    label = models.CharField(max_length=128)
    is_enabled = models.BooleanField(default=True)

    dataset = models.ForeignKey(DataSet, related_name='+', on_delete=models.CASCADE)

    flavor = models.ForeignKey(
        Flavor,
        related_name='forms',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
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
    order = models.PositiveSmallIntegerField(default=0, blank=False, null=False)

    def __unicode__(self):
        return "order: {order}".format(order=self.order)

    def get_related_module(self):
        related_modules = self._get_related_modules()
        if len(related_modules) == 0:
            message = '[FORM_MODULE_MODEL] Instance has no related model: {}'.format(self.id)
            raise ValidationError(message)
        else:
            return related_modules[0]

    def _get_related_modules(self):
        related_modules = []
        if hasattr(self, 'radiofield'):
            related_modules.append(self.radiofield)
        if hasattr(self, 'htmlmodule'):
            related_modules.append(self.htmlmodule)
        return related_modules

    def clean(self):
        related_modules = self._get_related_modules()
        if len(related_modules) > 1:
            message = '[FORM_MODULE_MODEL] Instance has more than one related model: {}'.format(self.id)
            raise ValidationError(message)

    class Meta:
        app_label = 'sa_api_v2'
        db_table = 'ms_api_form_module'
        ordering = ['order']


class HtmlModule(models.Model):

    content = models.TextField(blank=True, default=None)

    module = models.OneToOneField(
        FormModule,
        on_delete=models.CASCADE,
    )

    def save(self, *args, **kwargs):
        self.module.clean()
        super(HtmlModule, self).save(*args, **kwargs)

    class Meta:
        app_label = 'sa_api_v2'
        db_table = 'ms_api_form_module_html'


class FormField(models.Model):

    key = models.CharField(max_length=128)
    prompt = models.TextField(blank=True, default="")
    private = models.BooleanField(default=False, blank=True)
    required = models.BooleanField(default=False, blank=True)

    module = models.OneToOneField(
        FormModule,
        on_delete=models.CASCADE,
    )

    class Meta:
        app_label = 'sa_api_v2'
        abstract = True

    def save(self, *args, **kwargs):
        self.module.clean()
        super(FormField, self).save(*args, **kwargs)


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
        on_delete=models.CASCADE,
    )

    class Meta:
        app_label = 'sa_api_v2'
        db_table = 'ms_api_form_module_option_radio'
