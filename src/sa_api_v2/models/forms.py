from django.contrib.gis.db import models
from .core import DataSet
from .flavors import Flavor
import logging
from django.core.exceptions import ValidationError
logger = logging.getLogger(__name__)


class Form(models.Model):
    label = models.CharField(max_length=128)
    is_enabled = models.BooleanField(default=True)

    dataset = models.ForeignKey(
        DataSet,
        related_name='+',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

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
        on_delete=models.CASCADE,
    )
    order = models.PositiveSmallIntegerField(default=0, blank=False, null=False)
    visible = models.BooleanField(
        default=True,
        blank=True,
        help_text="Determines whether the module is visible by default.",
    )

    def __unicode__(self):
        related_module = self.get_related_module()
        return 'id: {}, {}'.format(self.id, related_module)

    def get_related_module(self):
        related_modules = self._get_related_modules()
        if len(related_modules) == 0:
            # In Django Admin, a FormModule needs to be created before
            # a RelatedFormModule can be added to it.
            return None
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


class RelatedFormModule(models.Model):

    module = models.OneToOneField(
        FormModule,
        on_delete=models.CASCADE,
    )

    def save(self, *args, **kwargs):
        self.module.clean()
        super(RelatedFormModule, self).save(*args, **kwargs)

    class Meta:
        app_label = 'sa_api_v2'
        abstract = True


class HtmlModule(RelatedFormModule):
    content = models.TextField(blank=True, default=None)

    def __unicode__(self):
        return "html module with content: {}".format(self.content)

    class Meta:
        db_table = 'ms_api_form_module_html'


class FormField(RelatedFormModule):

    key = models.CharField(max_length=128)
    prompt = models.TextField(blank=True, default="")
    private = models.BooleanField(
        default=False,
        blank=True,
        help_text="If true, then the submitted data will be flagged as private.",
    )
    required = models.BooleanField(
        default=False,
        blank=True,
        help_text="If true, then the form cannot be submitted unless this field has received a response.",
    )

    class Meta:
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

    def __unicode__(self):
        return "radio field with prompt: {}".format(self.prompt)

    class Meta:
        db_table = 'ms_api_form_module_field_radio'


class FormFieldOption(models.Model):
    advance_to_next_stage = models.BooleanField(
        default=False,
        blank=True,
        help_text="When this option is selected, the form will advance to the next stage.",
    )

    visibility_triggers = models.ManyToManyField(
        FormModule,
        help_text="If this FormFieldOption is selected, the following FormModules will become visible. Only default invisible modules are selectable here.",
        blank=True,
        related_name='+',
    )

    def clean(self):
        related_field = self.field
        if related_field is None:
            message = '[FORM_FIELD_OPTION] Instance does not have a related `field`: {}'.format(self.id)
            raise ValidationError(message)

    def save(self, *args, **kwargs):
        self.clean()
        super(FormFieldOption, self).save(*args, **kwargs)

    class Meta:
        app_label = 'sa_api_v2'
        abstract = True


class RadioOption(FormFieldOption):
    label = models.CharField(max_length=128)
    value = models.CharField(max_length=128)

    field = models.ForeignKey(
        RadioField,
        related_name="options",
        on_delete=models.CASCADE,
    )

    class Meta:
        db_table = 'ms_api_form_module_option_radio'
