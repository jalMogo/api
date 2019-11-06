from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.contrib.gis.db import models
from .core import DataSet
from .profiles import (
    Group,
)
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
    'SkipStageModule',
    'SubmitButtonModule',
    'Modal',
    'FormFieldOption',
    'CheckboxOption',
    'AddressField',
    'DateField',
    'NumberField',
    'FileField',
    'RadioField',
    'RadioOption',
    'TextField',
    'TextAreaField',
    'CheckboxField',
    'RELATED_MODULES',
]

RELATED_MODULES = [
    "htmlmodule",
    "skipstagemodule",
    "radiofield",
    "numberfield",
    "filefield",
    "datefield",
    "checkboxfield",
    "textfield",
    "addressfield",
    "textareafield",
    "submitbuttonmodule",
]

class Form(models.Model):
    label = models.CharField(
        max_length=127
    )
    is_enabled = models.BooleanField(default=True)

    engagement_text = models.CharField(
        max_length=255, 
        blank=True,
        help_text="When multiple forms are available to select, this text will help describe this form.",
    )

    image = models.CharField(
        max_length=127,
        blank=True,
        help_text="An URL for the location of this forms's image. Useful when selecting one of multiple forms on a flavor. This field is optional.",
    )

    dataset = models.OneToOneField(
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
    label = models.CharField(max_length=127, unique=True)

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

    header_text = models.CharField(
        blank=True,
        max_length=512,
        help_text="Use this when adding a header to the Form Stage. Usually used to summarize this section of the form.",
    )

    label = models.CharField(
        blank=True,
        max_length=255,
        help_text="An option label that can be used to describe the form stage. Currently it is only used internally.",
    )

    visible = models.BooleanField(
        default=True,
        blank=True,
        help_text="Determines whether the stage is visible by default.",
    )

    validate_geometry = models.BooleanField(
        default=False,
        blank=True,
        help_text="Determines whether we should validate whether a correct lng/lat has been entered at this stage.",
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
    zoom = models.FloatField(null=True, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    transition_duration = models.PositiveSmallIntegerField(null=True, blank=True)
    bearing = models.PositiveSmallIntegerField(null=True, blank=True)
    pitch = models.PositiveSmallIntegerField(null=True, blank=True)

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

    # If the model's cache has a (nested)OrderedModule, then verify with the db
    # and return if that's true
    def _has_ordered_module(self):
        return (hasattr(self, 'orderedmodule')) and \
            OrderedModule.objects.filter(id=self.orderedmodule.id).exists()    

    def _has_nested_ordered_module(self):
        return (hasattr(self, 'nestedorderedmodule')) and \
            NestedOrderedModule.objects.filter(id=self.nestedorderedmodule.id).exists()    

    # returns whether the instances has ordered_module or
    # nested_ordered_module pointing to it.
    def has_any_ordered_module(self):
        return self._has_ordered_module() or self._has_nested_ordered_module()

    # returns the (nested)ordered module
    def get_ordered_module(self):
        if self._has_ordered_module(): 
            return self.orderedmodule
        elif self._has_nested_ordered_module():
            return self.nestedorderedmodule
        else:
            return None

    def validate(self, ordered_module):
        pass

    def __unicode__(self):
        if not self.has_any_ordered_module():
            return "{} (unnattached)".format(self.summary())
        else:
            return self.summary()


class GroupModule(RelatedFormModule):
    label = models.CharField(
        help_text="For naming purposes only - this won't be displayed to end users. Use this label to more easily identify this module whle building the form.",
        max_length=127,
        blank=True,
    )

    def summary(self):
        return "group module, with label: \"{}\"".format(self.label) if self.label else "group module, id: {}".format(self.id)

    class Meta:
        db_table = 'ms_api_form_module_group'


class HtmlModule(RelatedFormModule):
    label = models.CharField(
        help_text="For naming purposes only - this won't be displayed to end users. Use this label to more easily identify this module whle building the form.",
        max_length=127,
        blank=True,
    )
    content = models.TextField(
        help_text="Add HTML here that will be displayed on the form. Make sure that the html is valid and sanitized!",
    )

    def summary(self):
        return "html module, with label: \"{}\"".format(self.label)

    class Meta:
        db_table = 'ms_api_form_module_html'


class SkipStageModule(RelatedFormModule):
    label = models.TextField(
        help_text="The message to be displayed on the form. When clicked, it will skip to the appropriate FormStage. Note that all modules within this FormStage should be optional for this to work properly. (eg: \"This section is not relevant to me.\")",
        blank=True,
        default='',
    )

    stage = models.ForeignKey(
        FormStage,
        on_delete=models.SET_NULL,
        help_text="If null, skip to the next stage. Otherwise, we skip to the associated FormStage.",
        blank=True,
        null=True,
    )

    def validate(self, ordered_module):
        if self.stage is not None and \
            ordered_module.stage.form != self.stage.form:
            raise ValidationError("[SkipStageModule] self.stage has a different Form than this module: {}".format(self.stage))


    # This is only used for importing SkipStageModules relationships from a JSON
    # source

    # NOTE: imports are limited to SkipStageModules that are NOT inside of a
    # group
    @staticmethod
    def import_skip_stage_modules(skip_stage_modules):
        for module_data in skip_stage_modules:
            module = SkipStageModule.objects.get(
                orderedmodule__stage__form__label=module_data['form'],
                orderedmodule__order=module_data['module_order'],
            )
            stage = FormStage.objects.get(
                form__label=module_data['form'],
                order=module_data['destination_stage_order']
            )
            module.stage = stage
            module.save()

    def summary(self):
        return "skip stage module with label: \"{}\"".format(self.label[:40])

    class Meta:
        db_table = 'ms_api_form_module_skip_stage'


class SubmitButtonModule(RelatedFormModule):
    label = models.CharField(
        help_text="This is the label that the submit button will have",
        default='Submit',
        max_length=127,
    )

    def summary(self):
        return "submit button with label: \"{}\"".format(self.label[:40])

    class Meta:
        db_table = 'ms_api_form_module_submit_button'


class Modal(models.Model):
    # We are assuming that these fields must be filled out.
    header = models.CharField(
        help_text="This is the label that the submit button will have",
        max_length=127,
    )

    content = models.TextField(
        help_text="Add HTML here that will be displayed as a modal alongside the FormField. Make sure that the html is valid and sanitized!",
    )

    class Meta:
        app_label = 'sa_api_v2'
        db_table = 'ms_api_form_field_modal'

    def __unicode__(self):
        return "header: {}, content: {}".format(self.header[0:20], self.content[0:20])

class FormField(RelatedFormModule):
    key = models.CharField(
        max_length=127,
        help_text="The key onto which the field's response will be saved",
    )
    label = models.CharField(
        blank=True,
        max_length=127,
        help_text="This label will be used when displaying the submitted form field (eg: \"My project idea is:\")",
    )
    prompt = models.CharField(
        blank=True,
        max_length=512,
        help_text="Some helpful text to guide the user on how to fill out this field (eg: \"What is your project idea?\")",
    )
    private = models.BooleanField(
        default=False,
        blank=True,
        help_text="If true, then the submitted data will be flagged as private",
    )
    required = models.BooleanField(
        default=False,
        blank=True,
        help_text="If true, then the form cannot be submitted unless this field has received a response",
    )
    info_modal = models.OneToOneField(
        Modal,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    class Meta:
        abstract = True

    def delete(self, *args, **kwargs):
        if self.info_modal is not None:
            self.info_modal.delete()
        super(FormField, self).delete(*args, **kwargs)


# Used for CharField:
placeholder_kwargs = {
    "max_length": 255,
    "blank": True,
    "help_text": "Used to help guide users on what to type into the form's input box (eg: \"Enter your email here\", \"joe@example.com\")",
}

# Used for CharField:
units_kwargs = {
    "max_length": 127,
    "blank": True,
    "help_text": "Units are used for labelling numerical submissions (eg: \"13 acres\")",
}


class DateField(FormField):
    placeholder = models.CharField(**placeholder_kwargs)
    include_ongoing = models.BooleanField(default=False)
    # TODO: enforce only date-related regexes for model save:
    label_format = models.CharField(
        blank=True,
        help_text="Formatting of the date that will be used on the label",
        max_length=24,
    )

    form_format = models.CharField(
        blank=True,
        help_text="Formatting of the date that will be required for the input form",
        max_length=24,
    )

    def summary(self):
        return "date field with prompt: \"{}\"".format(self.prompt)

    class Meta:
        db_table = 'ms_api_form_module_field_date'


class NumberField(FormField):
    placeholder = models.CharField(**placeholder_kwargs)
    minimum = models.IntegerField(blank=True, null=True)
    units = models.CharField(**units_kwargs)

    def summary(self):
        return "number field with prompt: \"{}\"".format(self.prompt)

    class Meta:
        db_table = 'ms_api_form_module_field_number'


class FileField(FormField):

    def summary(self):
        return "file field with prompt: \"{}\"".format(self.prompt)

    class Meta:
        db_table = 'ms_api_form_module_field_file'


class AddressField(FormField):
    """
    Saves the address from the map's lng/lat values
    """
    placeholder = models.CharField(**placeholder_kwargs)
    reverse_geocode = models.BooleanField(
        default=True,
        blank=True,
        help_text="Inidicates whether the field will auto-update with a new address based on the map's location.",
    )

    def summary(self):
        return "address field with prompt: \"{}\"".format(self.prompt)

    class Meta:
        db_table = 'ms_api_form_module_field_address'


class RadioField(FormField):
    RADIO = "RA"
    DROPDOWN = "DR"
    AUTOCOMPLETE_DROPDOWN = "AD"
    TOGGLE = "TO"
    CHOICES = [
        (RADIO, 'a radio selection'),
        (DROPDOWN, 'a dropdown list'),
        (TOGGLE, 'a toggle switch, choosing one of 2 choices'),
        (AUTOCOMPLETE_DROPDOWN, 'a dropdown list that allows fuzzy searching through the items'),
    ]

    variant = models.CharField(max_length=127, choices=CHOICES, default=RADIO)
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
    rich_text = models.BooleanField(
        default=False,
        blank=True,
        help_text="Determines whether the field allows for rich text input.",
    )

    def summary(self):
        return "textarea field with prompt: \"{}\"".format(self.prompt)

    class Meta:
        db_table = 'ms_api_form_module_field_textarea'


class TextField(FormField):
    EMAIL = "EM"
    PHONE = "PH"
    ADDRESS = "AD"
    TEXT_FIELD_VARIANTS = (
        (EMAIL, 'Email'),
        (PHONE, 'Phone'),
        (ADDRESS, 'Address'),
    )
    variant = models.CharField(
        max_length=127,
        blank=True,
        choices=TEXT_FIELD_VARIANTS,
    )

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
    HELP_TEXT = "Choose a {} by creating a new one, or selecting one that already exists within this flavor. Only one field/module can be selected for this OrderedModule."

    numberfield = models.OneToOneField(
        NumberField,
        on_delete=models.SET_NULL,
        help_text=HELP_TEXT.format("number"),
        blank=True,
        null=True,
    )

    filefield = models.OneToOneField(
        FileField,
        on_delete=models.SET_NULL,
        help_text=HELP_TEXT.format("file"),
        blank=True,
        null=True,
    )

    datefield = models.OneToOneField(
        DateField,
        on_delete=models.SET_NULL,
        help_text=HELP_TEXT.format("date"),
        blank=True,
        null=True,
    )

    radiofield = models.OneToOneField(
        RadioField,
        on_delete=models.SET_NULL,
        help_text=HELP_TEXT.format("radio"),
        blank=True,
        null=True,
    )

    addressfield = models.OneToOneField(
        AddressField,
        on_delete=models.SET_NULL,
        help_text=HELP_TEXT.format("address field"),
        blank=True,
        null=True,
    )
    checkboxfield = models.OneToOneField(
        CheckboxField,
        on_delete=models.SET_NULL,
        help_text=HELP_TEXT.format("checkbox field"),
        blank=True,
        null=True,
    )

    textareafield = models.OneToOneField(
        TextAreaField,
        on_delete=models.SET_NULL,
        help_text=HELP_TEXT.format("textarea field"),
        blank=True,
        null=True,
    )

    textfield = models.OneToOneField(
        TextField,
        on_delete=models.SET_NULL,
        help_text=HELP_TEXT.format("text field"),
        blank=True,
        null=True,
    )

    htmlmodule = models.OneToOneField(
        HtmlModule,
        on_delete=models.SET_NULL,
        help_text=HELP_TEXT.format("html module"),
        blank=True,
        null=True,
    )

    skipstagemodule = models.OneToOneField(
        SkipStageModule,
        on_delete=models.SET_NULL,
        help_text=HELP_TEXT.format("skip stage module"),
        blank=True,
        null=True,
    )

    submitbuttonmodule = models.OneToOneField(
        SubmitButtonModule,
        on_delete=models.SET_NULL,
        help_text=HELP_TEXT.format("submit button module"),
        blank=True,
        null=True,
    )

    def __unicode__(self):
        related_module = self.get_related_module()
        return 'order: {order}, with Related Module: {related}'.format(related=related_module, order=self.order)

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
        for related_module_name in RELATED_MODULES:
            related_module = getattr(self, related_module_name)
            if related_module:
                # if the related_module field is instantiated, then add it to
                # our collection
                related_modules.append(related_module)
        return related_modules

    def clean(self):
        related_modules = self._get_related_modules()
        if len(related_modules) > 1:
            message = '[FormModuleModel] Instance has more than one related model: {}'.format([related_modules])
            raise ValidationError(message)
        # Validate permitted_group on OrderedModule:
        if hasattr(self, 'permitted_group') and self.permitted_group is not None:
            # every OrderedModule has a stage, and every stage has a form.
            if self.stage.form.dataset is None:
                raise ValidationError("[FormModuleModel] Dataset must be assigned before adding Restrcted Group to module: {}".format(self))
            dataset = self.stage.form.dataset
            if self.permitted_group.dataset != dataset:
                raise ValidationError("[FormModuleModel] permitted_group is not within this form's dataset: {}".format(dataset))
        if len(related_modules) == 1:
            related_module = related_modules[0]
            related_ordered_module = related_module.get_ordered_module()
            # check to ensure that the (nested)ordered modules are the same:
            if related_ordered_module and \
                related_ordered_module != self:
                raise ValidationError("[FormModuleModel] RelatedModule cannot have more than one (Nested)OrderedModules pointing to it: {}".format(related_modules[0]))
            # Perform validation specific to the related module.
            related_module.validate(self)


    def save(self, *args, **kwargs):
        self.clean()
        super(RelatedFormModule, self).save(*args, **kwargs)


    def save(self, *args, **kwargs):
        self.clean()
        super(AbstractOrderedModule, self).save(*args, **kwargs)

    class Meta:
        app_label = 'sa_api_v2'
        ordering = ['order']
        abstract = True


class OrderedModule(AbstractOrderedModule):
    stage = models.ForeignKey(
        FormStage,
        help_text="Every OrderedModule must belong to a FormStage.",
        related_name="modules",
        on_delete=models.CASCADE,
    )

    groupmodule = models.OneToOneField(
        GroupModule,
        on_delete=models.SET_NULL,
        help_text=AbstractOrderedModule.HELP_TEXT.format("group module"),
        blank=True,
        null=True,
    )

    # This can only be added if the OrderedModule is associated with a Form.
    permitted_group = models.ForeignKey(
        Group,
        on_delete=models.SET_NULL,
        help_text="Only this Group is allowed to edit this module's field. If null, any group can edit.",
        related_name="+",
        blank=True,
        null=True,
    )
    include_on_list = models.BooleanField(
        default=False,
        blank=True,
        help_text="If true, then include this field when rendering list items.",
    )

    def _get_related_modules(self):
        related_modules = super(OrderedModule, self)._get_related_modules()
        if self.groupmodule:
            related_modules.append(self.groupmodule)
        return related_modules

    class Meta(AbstractOrderedModule.Meta):
        db_table = 'ms_api_form_ordered_module'


class NestedOrderedModule(AbstractOrderedModule):
    group = models.ForeignKey(
        GroupModule,
        related_name="modules",
        on_delete=models.CASCADE,
    )

    class Meta(AbstractOrderedModule.Meta):
        db_table = 'ms_api_form_nested_ordered_module'


@receiver(post_delete, sender=OrderedModule)
@receiver(post_delete, sender=NestedOrderedModule)
def delete_ordered_module(sender, instance, using, **kwargs):
    # Delete any "dangling" RelatedModules that have no
    # OrderedModule or NestedOrderedModule reference.
    for related_module in instance._get_related_modules():
        if related_module is None:
            return
        if not related_module.has_any_ordered_module():
            related_module.delete()


class FormFieldOption(models.Model):

    stage_visibility_triggers = models.ManyToManyField(
        FormStage,
        help_text="Triggers an update to make the following FormStages visible. Only default invisible stages are within this module's Form are selectable here",
        blank=True,
        related_name='+',
    )

    group_visibility_triggers = models.ManyToManyField(
        # Triggers are constrained to NestedOrderedModules within the GroupModule.
        NestedOrderedModule,
        help_text="Triggers an update to make the following NestedOrderedModules visible. Only default invisible modules are within this module's group are selectable here.",
        blank=True,
        related_name='+',
    )

    default = models.BooleanField(
        default=False,
        blank=True,
        help_text="If true, then this field will be selected by default.",
    )

    make_private = models.BooleanField(
        default=False,
        blank=True,
        help_text="If true, then the Place's 'private' field will be set to true when this option is selected.",
    )

    icon = models.CharField(
        max_length=127,
        blank=True,
        help_text="An URL for the location of this option's icon. This field is optional.",
    )

    order = models.PositiveSmallIntegerField(default=0, blank=False, null=False)

    def clean(self):
        if not hasattr(self, 'field') or self.field is None:
            message = '[FORM_FIELD_OPTION] Instance does not have a related `field`: {}'.format(self)
            raise ValidationError(message)

    def save(self, *args, **kwargs):
        self.clean()
        super(FormFieldOption, self).save(*args, **kwargs)

    # This is only used for importing visibility trigger relationships from a
    # JSON source
    @staticmethod
    def import_group_triggers(field_data):
        for field in field_data:
            # First get the field option to which we'll add the group triggers:
            FieldOption = RadioOption if field['type'] == 'radiofield' else CheckboxOption
            field_option = FieldOption.objects.get(
                value=field['option_value'],
                field__nestedorderedmodule__order=field['field_order'],
                field__nestedorderedmodule__group__orderedmodule__order=field['group_order'],
                field__nestedorderedmodule__group__orderedmodule__stage__order=field['stage_order'],
                field__nestedorderedmodule__group__orderedmodule__stage__form__label=field['form'],
            )
            # get the GroupModule that contains the field_option:
            group = GroupModule.objects.get(
                modules=field_option.field.nestedorderedmodule
            )
            # get the hidden modules that we want to trigger when this field
            # option is selected:
            nested_ordered_modules_to_trigger = NestedOrderedModule.objects.filter(
                order__in=field['group_visibility_triggers'],
                group_id=group.id,
            )
            field_option.group_visibility_triggers.add(
                *[module for module in nested_ordered_modules_to_trigger.all()]
            )
            field_option.save()

    # This is only used for importing visibility trigger relationships from a
    # JSON source

    # NOTE: imports are limited to FormFieldOptions that are NOT inside of a
    # group
    @staticmethod
    def import_stage_triggers(field_data):
        for field in field_data:
            # First get the field option to which we'll add the stage triggers:
            FieldOption = RadioOption if field['type'] == 'radiofield' else CheckboxOption
            field_option = FieldOption.objects.get(
                value=field['option_value'],
                field__orderedmodule__order=field['field_order'],
                field__orderedmodule__stage__order=field['stage_order'],
                field__orderedmodule__stage__form__label=field['form'],
            )
            stages_to_trigger = FormStage.objects.filter(
                order__in=field['stage_visibility_triggers'],
                form__label=field['form']
            )
            field_option.stage_visibility_triggers.add(
                *[stage for stage in stages_to_trigger.all()]
            )
            field_option.save()

    class Meta:
        app_label = 'sa_api_v2'
        abstract = True
        ordering = ['order']


class CheckboxOption(FormFieldOption):
    label = models.CharField(
        max_length=127,
        help_text="For display purposes only. This is how the option will be presented on the form, or labelled in a submission summary.",

    )
    value = models.CharField(
        max_length=127,
        help_text="This is the value that will be associated with the field's key.",
    )

    field = models.ForeignKey(
        CheckboxField,
        related_name="options",
        on_delete=models.CASCADE,
    )

    def __unicode__(self):
        return "CheckboxOption with label: {} on field: {}".format(self.label, self.field)

    class Meta(FormFieldOption.Meta):
        db_table = 'ms_api_form_module_option_checkbox'


class RadioOption(FormFieldOption):
    label = models.CharField(
        max_length=255,
        help_text="For display purposes only. This is how the option will be presented on the form, or labelled in a submission summary.",
    )
    value = models.CharField(
        max_length=127,
        help_text="This is the value that will be associated with the field's key.",
    )

    field = models.ForeignKey(
        RadioField,
        related_name="options",
        on_delete=models.CASCADE,
    )

    def __unicode__(self):
        return "RadioOption with label: '{}' and order: {} on field: {}".format(self.label, self.order, self.field)

    class Meta(FormFieldOption.Meta):
        db_table = 'ms_api_form_module_option_radio'
