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
    'OrderedModule',
    'NestedOrderedModule',
    'GroupModule',
    'HtmlModule',
    'FormFieldOption',
    'CheckboxOption',
    'GeocodingField',
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
        return "\"{}\" on dataset: {}".format(self.label, self.dataset)

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
        return 'order: {}, containing {} modules, on form: \"{}\"'.format(
            self.order,
            len(self.modules.all()),
            self.form.label,
        )

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

    # returns whether the instances has ordered_modules or
    # nested_ordered_modules pointing to it.
    def has_any_ordered_modules(self):
        # Note that GroupModule doesn't have a
        # 'nested_ordered_modules' attribute, so we check that
        # explicitly:
        return len(self.ordered_modules.all()) > 0 or \
           (hasattr(self, 'nested_ordered_modules') and len(self.nested_ordered_modules.all()) > 0)

    def __unicode__(self):
        if not self.has_any_ordered_modules():
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


placeholder_kwargs = {
    "max_length": 255,
    "default": "",
    "blank": True,
}


class GeocodingField(FormField):
    placeholder = models.CharField(**placeholder_kwargs)

    def summary(self):
        return "geocoding field with prompt: \"{}\"".format(self.prompt)

    class Meta:
        db_table = 'ms_api_form_module_field_geocoding'


class RadioField(FormField):
    RADIO = "radio"
    DROPDOWN = "dropdown"
    CHOICES = [
        (RADIO, 'a radio selection'),
        (DROPDOWN, 'a dropdown list'),
    ]

    variant = models.CharField(max_length=128, choices=CHOICES, default=RADIO)
    dropdown_placeholder = models.CharField(**placeholder_kwargs)

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
    placeholder = models.CharField(**placeholder_kwargs)

    def summary(self):
        return "textarea field with prompt: \"{}\"".format(self.prompt)

    class Meta:
        db_table = 'ms_api_form_module_field_textarea'


class TextField(FormField):
    placeholder = models.CharField(**placeholder_kwargs)

    def summary(self):
        return "text field with prompt: \"{}\"".format(self.prompt)

    class Meta:
        db_table = 'ms_api_form_module_field_text'


class AbstractOrderedModule(models.Model):
    order = models.PositiveSmallIntegerField(default=0, blank=False, null=False)
    visible = models.BooleanField(
        default=True,
        blank=True,
        help_text="Determines whether the module is visible by default.",
    )
    HELP_TEXT = "Choose a {} by creating a new one, or selecting one that already exists within this flavor. Only one field or one module can be selected for this OrderedModule."

    radiofield = models.ForeignKey(
        RadioField,
        on_delete=models.SET_NULL,
        help_text=HELP_TEXT.format("radio"),
        blank=True,
        null=True,
    )

    geocodingfield = models.ForeignKey(
        GeocodingField,
        on_delete=models.SET_NULL,
        help_text=HELP_TEXT.format("geocoding field"),
        blank=True,
        null=True,
    )
    checkboxfield = models.ForeignKey(
        CheckboxField,
        on_delete=models.SET_NULL,
        help_text=HELP_TEXT.format("checkbox field"),
        blank=True,
        null=True,
    )

    textareafield = models.ForeignKey(
        TextAreaField,
        on_delete=models.SET_NULL,
        help_text=HELP_TEXT.format("textarea field"),
        blank=True,
        null=True,
    )

    textfield = models.ForeignKey(
        TextField,
        on_delete=models.SET_NULL,
        help_text=HELP_TEXT.format("text field"),
        blank=True,
        null=True,
    )

    htmlmodule = models.ForeignKey(
        HtmlModule,
        on_delete=models.SET_NULL,
        help_text=HELP_TEXT.format("html module"),
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
        if self.geocodingfield:
            related_modules.append(self.geocodingfield)
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
        super(AbstractOrderedModule, self).save(*args, **kwargs)

    class Meta:
        abstract = True


class OrderedModule(AbstractOrderedModule):
    stage = models.ForeignKey(
        FormStage,
        help_text="Every OrderedModule must belong to a FormStage.",
        related_name="modules",
        on_delete=models.CASCADE,
    )

    groupmodule = models.ForeignKey(
        GroupModule,
        on_delete=models.SET_NULL,
        help_text=AbstractOrderedModule.HELP_TEXT.format("group module"),
        blank=True,
        null=True,
    )

    def _get_related_modules(self):
        related_modules = super(OrderedModule, self)._get_related_modules()
        if self.groupmodule:
            related_modules.append(self.groupmodule)
        return related_modules

    class Meta:
        app_label = 'sa_api_v2'
        db_table = 'ms_api_form_ordered_module'
        ordering = ['order']
        default_related_name = "ordered_modules"


class NestedOrderedModule(AbstractOrderedModule):
    group = models.ForeignKey(
        GroupModule,
        related_name="modules",
        on_delete=models.CASCADE,
    )

    class Meta:
        app_label = 'sa_api_v2'
        db_table = 'ms_api_form_nested_ordered_module'
        ordering = ['order']
        default_related_name = "nested_ordered_modules"


@receiver(post_delete, sender=OrderedModule)
@receiver(post_delete, sender=NestedOrderedModule)
def delete(sender, instance, using, **kwargs):
    # Delete any "dangling" RelatedModules that have no
    # OrderedModule or NestedOrderedModule references.
    for related_module in instance._get_related_modules():
        if related_module is None:
            return
        if not related_module.has_any_ordered_modules():
            related_module.delete()


class FormFieldOption(models.Model):
    advance_to_next_stage = models.BooleanField(
        default=False,
        blank=True,
        help_text="When this option is selected, the form will advance to the next stage.",
    )

    visibility_triggers = models.ManyToManyField(
        # Triggers are constrained to NestedOrderedModules only.
        NestedOrderedModule,
        help_text="Triggers an update to make the following NestedOrderedModules visible. Only default invisible modules are within this module's group are selectable here.",
        blank=True,
        related_name='+',
    )

    def clean(self):
        if not hasattr(self, 'field') or self.field is None:
            message = '[FORM_FIELD_OPTION] Instance does not have a related `field`: {}'.format(self)
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

    def __unicode__(self):
        return "CheckboxOption with label: {} on field: {}".format(self.label, self.field)

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

    def __unicode__(self):
        return "RadioOption with label: {} on field: {}".format(self.label, self.field)

    class Meta:
        db_table = 'ms_api_form_module_option_radio'
