from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.contrib.gis.db import models
from .core import DataSet
from .flavors import Flavor
import logging
from django.core.exceptions import ValidationError
logger = logging.getLogger(__name__)

__all__ = [
    'Form',
    'FormStage',
    'LayerGroup',
    'MapViewport',
    'FormStageModule',
    'FormGroupModule',
    'GroupModule',
    'HtmlModule',
    'FormFieldOption',
    'CheckboxOption',
    'RadioField',
    'RadioOption',
    'TextField',
    'TextAreaField',
    'CheckboxField',
]


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
        return "{} on dataset: {}".format(self.label, self.dataset.display_name)

    class Meta:
        app_label = 'sa_api_v2'
        db_table = 'ms_api_form'


class LayerGroup(models.Model):
    label = models.CharField(max_length=128)

    class Meta:
        app_label = 'sa_api_v2'
        db_table = 'ms_api_map_layer_group'

    def __unicode__(self):
        return self.label


class FormStage(models.Model):
    form = models.ForeignKey(
        Form,
        related_name="stages",
        on_delete=models.CASCADE,
    )
    order = models.PositiveSmallIntegerField(default=0, blank=False, null=False)

    visible_layer_groups = models.ManyToManyField(
        LayerGroup,
        help_text="A list of layers that will become visible during this stage.",
        blank=True,
        related_name='+',
    )

    def __unicode__(self):
        return '{}, order: {}'.format(self.form, self.order)

    class Meta:
        app_label = 'sa_api_v2'
        db_table = 'ms_api_form_stage'
        ordering = ['order']


class MapViewport(models.Model):
    zoom = models.PositiveSmallIntegerField(null=False, blank=False)
    latitude = models.FloatField(null=False, blank=False)
    longitude = models.FloatField(null=False, blank=False)
    transition_duration = models.PositiveSmallIntegerField(null=False, blank=False)
    bearing = models.PositiveSmallIntegerField(null=False, blank=False)
    pitch = models.PositiveSmallIntegerField(null=False, blank=False)

    stage = models.OneToOneField(
        FormStage,
        related_name='map_viewport',
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )

    class Meta:
        app_label = 'sa_api_v2'
        db_table = 'ms_api_map_viewport'


class RelatedFormModule(models.Model):

    class Meta:
        app_label = 'sa_api_v2'
        abstract = True

    def __unicode__(self):
        if len(self.stage_modules.all()) == 0 and \
           (hasattr(self, 'group_modules') and len(self.group_modules.all()) == 0):
            return "{} (unnattached)".format(self.summary())
        else:
            return self.summary()


class GroupModule(RelatedFormModule):
    label = models.CharField(
        help_text="For labelling purposes only - won't be used on the form. Use this label to more easily identify this module in the form.",
        max_length=128,
        blank=True,
        default='',
    )

    def summary(self):
        return "group module, with label: \"{}\"".format(self.label)

    class Meta:
        db_table = 'ms_api_form_module_group'


class HtmlModule(RelatedFormModule):
    label = models.CharField(
        help_text="For labelling purposes only - won't be used on the form. Use this label to more easily identify this module in the form.",
        max_length=128,
        blank=True,
        default='',
    )
    content = models.TextField(
        help_text="Add HTML here that will be displayed on the form. Make sure that the html is valid and sanitized!",
    )

    def summary(self):
        return "html module, with label: \"{}\"".format(self.label)

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


placeholder_field = models.CharField(max_length=255, default="", blank=True)


class RadioField(FormField):
    RADIO = "radio"
    DROPDOWN = "dropdown"
    CHOICES = [
        (RADIO, 'a radio selection'),
        (DROPDOWN, 'a dropdown list'),
    ]

    variant = models.CharField(max_length=128, choices=CHOICES, default=RADIO)
    dropdown_placeholder = placeholder_field

    def summary(self):
        return "radio field with prompt: \"{}\"".format(self.prompt)

    class Meta:
        db_table = 'ms_api_form_module_field_radio'


class CheckboxField(FormField):
    def summary(self):
        return "checkbox field with prompt: \"{}\"".format(self.prompt)

    class Meta:
        db_table = 'ms_api_form_module_field_checkbox'


class TextAreaField(FormField):
    placeholder = placeholder_field

    def summary(self):
        return "textarea field with prompt: \"{}\"".format(self.prompt)

    class Meta:
        db_table = 'ms_api_form_module_field_textarea'


class TextField(FormField):
    placeholder = placeholder_field

    def summary(self):
        return "text field with prompt: \"{}\"".format(self.prompt)

    class Meta:
        db_table = 'ms_api_form_module_field_text'


class AbstractFormModule(models.Model):
    order = models.PositiveSmallIntegerField(default=0, blank=False, null=False)
    visible = models.BooleanField(
        default=True,
        blank=True,
        help_text="Determines whether the module is visible by default.",
    )

    radiofield = models.ForeignKey(
        RadioField,
        on_delete=models.SET_NULL,
        help_text="Choose a radio field. Create a new radio field, or select a radiofield that already exists within this flavor. Only one field/module can be selected for this FormModule.",
        blank=True,
        null=True,
    )

    checkboxfield = models.ForeignKey(
        CheckboxField,
        on_delete=models.SET_NULL,
        help_text="Choose a checkbox field. Create a new checkbox field, or select a radiofield that already exists within this flavor. Only one field/module can be selected for this FormModule.",
        blank=True,
        null=True,
    )

    textareafield = models.ForeignKey(
        TextAreaField,
        on_delete=models.SET_NULL,
        help_text="Choose a textarea field. Create a new textarea field, or select one that already exists within this flavor. Only one field/module can be selected for this FormModule.",
        blank=True,
        null=True,
    )

    textfield = models.ForeignKey(
        TextField,
        on_delete=models.SET_NULL,
        help_text="Choose a text field. Create a new text field, or select one that already exists within this flavor. Only one field/module can be selected for this FormModule.",
        blank=True,
        null=True,
    )

    htmlmodule = models.ForeignKey(
        HtmlModule,
        on_delete=models.SET_NULL,
        help_text="Choose an html module. Create a new html module, or select an htmlmodule that already exists within this flavor. Only one field/module can be selected for this FormModule.",
        blank=True,
        null=True,
    )

    def __unicode__(self):
        related_module = self.get_related_module()
        return 'order: {order}, with related module: {related}'.format(related=related_module, order=self.order)

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
        if self.radiofield:
            related_modules.append(self.radiofield)
        if self.htmlmodule:
            related_modules.append(self.htmlmodule)
        if self.textfield:
            related_modules.append(self.textfield)
        if self.textareafield:
            related_modules.append(self.textareafield)
        if self.checkboxfield:
            related_modules.append(self.checkboxfield)
        return related_modules

    def clean(self):
        related_modules = self._get_related_modules()
        if len(related_modules) > 1:
            message = '[FORM_MODULE_MODEL] Instance has more than one related model: {}'.format([related_modules])
            raise ValidationError(message)

    def save(self, *args, **kwargs):
        self.clean()
        super(AbstractFormModule, self).save(*args, **kwargs)

    class Meta:
        abstract = True


class FormStageModule(AbstractFormModule):
    stage = models.ForeignKey(
        FormStage,
        help_text="Every FormStageModule must belong to a FormStage.",
        related_name="modules",
        on_delete=models.CASCADE,
    )

    groupmodule = models.ForeignKey(
        GroupModule,
        on_delete=models.SET_NULL,
        help_text="Choose a group. Create a new radio field, or select a radiofield that already exists within this flavor. Only one field/module can be selected for this FormModule.",
        blank=True,
        null=True,
    )

    def _get_related_modules(self):
        related_modules = super(FormStageModule, self)._get_related_modules()
        if self.groupmodule:
            related_modules.append(self.radiofield)
        return related_modules

    class Meta:
        app_label = 'sa_api_v2'
        db_table = 'ms_api_form_stage_module'
        ordering = ['order']
        default_related_name = "stage_modules"


class FormGroupModule(AbstractFormModule):
    group = models.ForeignKey(
        GroupModule,
        related_name="modules",
        on_delete=models.CASCADE,
    )

    class Meta:
        app_label = 'sa_api_v2'
        db_table = 'ms_api_form_group_module'
        ordering = ['order']
        default_related_name = "group_modules"


@receiver(post_delete, sender=FormStageModule)
@receiver(post_delete, sender=FormGroupModule)
def delete(sender, instance, using, **kwargs):
    # Delete any "dangling" RelatedModules that have no
    # FormStageModule or FormGroupModule references.
    for related_module in instance._get_related_modules():
        if related_module is None:
            return
        if len(related_module.stage_modules.all()) == 0 \
           and len(related_module.group_modules.all()) == 0:
            related_module.delete()


class FormFieldOption(models.Model):
    advance_to_next_stage = models.BooleanField(
        default=False,
        blank=True,
        help_text="When this option is selected, the form will advance to the next stage.",
    )

    visibility_triggers = models.ManyToManyField(
        # Triggers are constrained to FormGroupModules only.
        FormGroupModule,
        help_text="If this FormFieldOption is selected, the following FormGroupModules will become visible. Only default invisible modules are selectable here.",
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


class CheckboxOption(FormFieldOption):
    label = models.CharField(max_length=128)
    value = models.CharField(max_length=128)

    field = models.ForeignKey(
        CheckboxField,
        related_name="options",
        on_delete=models.CASCADE,
    )

    class Meta:
        db_table = 'ms_api_form_module_option_checkbox'


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
