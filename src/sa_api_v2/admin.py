"""
Basic behind-the-scenes maintenance for superusers,
via django.contrib.admin.
"""

import itertools
import json
import models
from django.contrib.admin import SimpleListFilter
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserChangeForm as BaseUserChangeForm
from django.contrib.gis import admin
from django.contrib import messages
from django.core.exceptions import FieldDoesNotExist
from django.core.urlresolvers import reverse
from django.forms import (
    ValidationError,
    ModelForm,
    CheckboxSelectMultiple,
    ModelMultipleChoiceField,
)
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.utils.html import escape
from django_ace import AceWidget
from django_object_actions import DjangoObjectActions
from django.utils.html import format_html

from .apikey.models import ApiKey
from .cors.models import Origin
from .cors.admin import OriginAdmin

from adminsortable2.admin import SortableInlineAdminMixin
from .tasks import clone_related_dataset_data
import nested_admin

__all__ = []


class HiddenModelAdmin (admin.ModelAdmin):
    def get_model_perms(self, request):
        """
        Return empty perms dict thus hiding the model from admin index.
        """
        return {}


class SubmissionSetFilter (SimpleListFilter):
    """
    Used to filter a list of submissions by type (set name).
    """
    title = 'Submission Set'
    parameter_name = 'set'

    def lookups(self, request, model_admin):
        qs = model_admin.get_queryset(request)
        qs = qs.order_by('set_name').distinct('set_name').values('set_name')
        return [(elem['set_name'], elem['set_name']) for elem in qs]

    def queryset(self, request, qs):
        set_name = self.value()
        if set_name:
            qs = qs.filter(set_name=set_name)
        return qs


class DataSetFilter (SimpleListFilter):
    """
    Used to filter a list of submitted things by dataset slug.
    """
    title = 'Dataset'
    parameter_name = 'dataset'

    def lookups(self, request, model_admin):
        qs = model_admin.get_queryset(request)
        qs = qs.order_by('dataset__slug').distinct('dataset__slug').values('dataset__slug')
        return [(elem['dataset__slug'], elem['dataset__slug']) for elem in qs]

    def queryset(self, request, qs):
        dataset__slug = self.value()
        if dataset__slug:
            qs = qs.filter(dataset__slug=dataset__slug)
        return qs


class InlineAttachmentAdmin(admin.StackedInline):
    model = models.Attachment
    extra = 0


class PrettyAceWidget (AceWidget):
    def render(self, name, value, attrs=None):
        if value:
            try:
                # If we can prettify the JSON, we should
                value = json.dumps(json.loads(value), indent=2)
            except ValueError:
                # If we cannot, then we should still display the value
                pass
        return super(PrettyAceWidget, self).render(name, value, attrs=attrs)


class SubmittedThingAdmin(admin.OSMGeoAdmin):
    date_hierarchy = 'created_datetime'
    inlines = (InlineAttachmentAdmin,)
    list_display = ('id', 'created_datetime', 'submitter_name', 'dataset', 'visible', 'data')
    list_editable = ('visible',)
    list_filter = (DataSetFilter,)
    search_fields = ('submitter__username', 'data',)

    openlayers_url = 'https://cdnjs.cloudflare.com/ajax/libs/openlayers/2.13.1/OpenLayers.js'
    raw_id_fields = ('submitter', 'dataset')
    readonly_fields = ('api_path',)

    def submitter_name(self, obj):
        return obj.submitter.username if obj.submitter else None

    def get_queryset(self, request):
        qs = super(SubmittedThingAdmin, self).get_queryset(request)
        user = request.user
        if not user.is_superuser:
            qs = qs.filter(dataset__owner=user)
        return qs

    def get_form(self, request, obj=None, **kwargs):
        FormWithJSONCleaning = super(SubmittedThingAdmin, self).get_form(request, obj=obj, **kwargs)

        def clean_json_blob(form):
            data = form.cleaned_data['data']
            try:
                json.loads(data)
            except ValueError as e:
                raise ValidationError(e)
            return data

        FormWithJSONCleaning.clean_data = clean_json_blob
        FormWithJSONCleaning.base_fields['data'].widget = PrettyAceWidget(mode='json', width='100%', wordwrap=True, theme='jsoneditor')
        return FormWithJSONCleaning

    def save_model(self, request, obj, form, change):
        # Make changes through the admin silently.
        obj.save(silent=True)


class InlineApiKeyAdmin(admin.StackedInline):
    model = ApiKey
    # raw_id_fields = ['apikey']
    extra = 0
    readonly_fields = ('edit_url',)

    def permissions_list(self, instance):
        if instance.pk:
            return '<ul>%s</ul>' % ''.join(['<li>%s</li>' % (escape(permission),) for permission in instance.permissions.all()])
        else:
            return ''

    def edit_url(self, instance):
        if instance.pk is None:
            return '(You must save your dataset before you can edit the permissions on your API key.)'
        else:
            return (
                # '<a href="%s"><strong>Edit permissions</strong></a>' % (reverse('admin:sa_api_v2_apikey_change', args=[instance.pk]))
                # + self.permissions_list(instance)

                # temp workaround for https://github.com/jalMogo/mgmt/issues/204:
                '<a><strong>Edit permissions (disabled for API keys)</strong></a>'
                + self.permissions_list(instance)
            )
    edit_url.allow_tags = True


class InlineTagAdmin(admin.StackedInline):
    model = models.Tag


class InlineOriginAdmin(admin.StackedInline):
    model = Origin
    raw_id_fields = ['place_email_template']
    extra = 0
    readonly_fields = ('edit_url',)

    def permissions_list(self, instance):
        if instance.pk:
            return '<ul>%s</ul>' % ''.join(['<li>%s</li>' % (escape(permission),) for permission in instance.permissions.all()])
        else:
            return ''

    def edit_url(self, instance):
        if instance.pk is None:
            return '(You must save your dataset before you can edit the permissions on your origin.)'
        else:
            return (
                '<a href="%s"><strong>Edit permissions</strong></a>' % (reverse('admin:sa_api_v2_origin_change', args=[instance.pk]))
                + self.permissions_list(instance)
            )
    edit_url.allow_tags = True


class InlineGroupAdmin(admin.StackedInline):
    model = models.Group
    filter_horizontal = ('submitters',)
    extra = 0
    readonly_fields = ('edit_url',)

    def permissions_list(self, instance):
        if instance.pk:
            return '<ul>%s</ul>' % ''.join(['<li>%s</li>' % (escape(permission),) for permission in instance.permissions.all()])
        else:
            return ''

    def edit_url(self, instance):
        if instance.pk is None:
            return '(You must save your dataset before you can edit the permissions on your API key.)'
        else:
            return (
                '<a href="%s"><strong>Edit permissions</strong></a>' % (reverse('admin:sa_api_v2_group_change', args=[instance.pk]))
                + self.permissions_list(instance)
            )
    edit_url.allow_tags = True


class InlineDataSetPermissionAdmin(admin.TabularInline):
    model = models.DataSetPermission
    extra = 0


class InlineDataIndexAdmin(admin.TabularInline):
    model = models.DataIndex
    extra = 0


class InlineWebhookAdmin(admin.StackedInline):
    model = models.Webhook
    extra = 0


class WebhookAdmin(admin.ModelAdmin):
    list_display = ('id', 'dataset', 'submission_set', 'event', 'url',)
    raw_id_fields = ('dataset',)
    # list_filter = ('name',)

    def get_queryset(self, request):
        qs = super(WebhookAdmin, self).get_queryset(request)
        user = request.user
        if not user.is_superuser:
            qs = qs.filter(dataset__owner=user)
        return qs


class PlaceEmailTemplateAdmin(admin.ModelAdmin):
    list_display = ('id', 'submission_set', 'event', 'subject', 'body_text', 'body_html',)
    # list_filter = ('name',)

    def get_queryset(self, request):
        qs = super(PlaceEmailTemplateAdmin, self).get_queryset(request)
        user = request.user
        if not user.is_superuser:
            qs = qs.filter(dataset__owner=user)
        return qs


class DataSetAdmin(DjangoObjectActions, admin.ModelAdmin):
    list_display = ('display_name', 'slug', 'owner')
    prepopulated_fields = {'slug': ['display_name']}
    search_fields = ('display_name', 'slug', 'owner__username')

    change_actions = ('clone_dataset', 'clear_cache')
    raw_id_fields = ('owner',)
    readonly_fields = ('api_path',)
    inlines = [
        InlineDataIndexAdmin,
        InlineDataSetPermissionAdmin,
        InlineApiKeyAdmin,
        InlineOriginAdmin,
        InlineGroupAdmin,
        InlineTagAdmin,
        InlineWebhookAdmin
    ]

    def clear_cache(self, request, obj):
        obj.clear_instance_cache()

    def clone_dataset(self, request, obj):
        siblings = models.DataSet.objects.filter(owner=obj.owner)
        slugs = set([ds.slug for ds in siblings])

        for uniquifier in itertools.count(2):
            unique_slug = '-'.join([obj.slug, str(uniquifier)])
            if unique_slug not in slugs: break

        try:
            new_obj = obj.clone(overrides={'slug': unique_slug}, commit=False)
            new_obj.save()
            clone_related_dataset_data.apply_async(args=[obj.id, new_obj.id])

            new_obj_edit_url = reverse('admin:sa_api_v2_dataset_change', args=[new_obj.pk])
            messages.success(request, 'Cloning dataset. Please give it a few moments.')
            return HttpResponseRedirect(new_obj_edit_url)
        except Exception as e:
            messages.error(request, 'Failed to clone dataset: %s (%s)' % (e, type(e).__name__))

    def api_path(self, instance):
        path = reverse('dataset-detail', args=[instance.owner, instance.slug])
        return '<a href="{0}">{0}</a>'.format(path)
    api_path.allow_tags = True

    def get_queryset(self, request):
        qs = super(DataSetAdmin, self).get_queryset(request)
        user = request.user
        if not user.is_superuser:
            qs = qs.filter(owner=user)
        return qs

    def get_form(self, request, obj=None, **kwargs):
        # Hide the owner field from non-superusers. All objects visible to the
        # user should be assumed to be owned by themselves.
        if not request.user.is_superuser:
            self.exclude = (self.exclude or ()) + ('owner',)
        return super(DataSetAdmin, self).get_form(request, obj, **kwargs)

    def save_model(self, request, obj, form, change):
        # Set the current user as the owner if the object has no owner and the
        # user is not a superuser.
        user = request.user
        if not user.is_superuser:
            if obj.owner_id is None:
                obj.owner = user
        super(DataSetAdmin, self).save_model(request, obj, form, change)


class InlinePlaceTagAdmin(admin.StackedInline):
    model = models.PlaceTag

    def get_formset(self, request, obj=None, **kwargs):
        self.parent_obj = obj
        return super(InlinePlaceTagAdmin, self).get_formset(request, obj, **kwargs)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "tag":
            kwargs["queryset"] = models.Tag.objects.filter(dataset=self.parent_obj.dataset)
            return super(InlinePlaceTagAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)


class PlaceAdmin(SubmittedThingAdmin):
    model = models.Place
    inlines = [
        InlinePlaceTagAdmin,
        InlineAttachmentAdmin
    ]
    readonly_fields = ('jwt_public_token', 'api_path')

    def jwt_public_token(self, instance):
        return instance.make_jwt()

    def api_path(self, instance):
        path = reverse('place-detail', args=[instance.dataset.owner, instance.dataset.slug, instance.id])
        return '<a href="{0}">{0}</a>'.format(path)
    api_path.allow_tags = True


class SubmissionAdmin(SubmittedThingAdmin):
    model = models.Submission

    list_display = SubmittedThingAdmin.list_display[:-1] + ('place_model', 'set_',) \
        + SubmittedThingAdmin.list_display[-1:] # keep the 'data' column at the end
    list_filter = (SubmissionSetFilter,) + SubmittedThingAdmin.list_filter
    search_fields = ('set_name',) + SubmittedThingAdmin.search_fields

    raw_id_fields = ('submitter', 'dataset', 'place_model')

    def set_(self, obj):
        return obj.set_name
    set_.short_description = 'Set'
    set_.admin_order_field = 'set_name'

    def place_model(self, obj):
        return obj.place_model_id
    place_model.short_description = 'Place'
    place_model.admin_order_field = 'place_model__id'

    def api_path(self, instance):
        path = reverse('submission-detail', args=[instance.dataset.owner, instance.dataset.slug, instance.place_model.id, instance.set_name, instance.id])
        return '<a href="{0}">{0}</a>'.format(path)
    api_path.allow_tags = True


class FormFieldOptionInlineForm(ModelForm):
    group_visibility_triggers = ModelMultipleChoiceField(
        widget=CheckboxSelectMultiple,
        queryset=models.NestedOrderedModule.objects.none(),
        help_text=unicode(models.FormFieldOption._meta.get_field('group_visibility_triggers').help_text),
        required=False,
    )
    fields = ('group_visibility_triggers',)

    def __init__(self, *args, **kwargs):
        super(FormFieldOptionInlineForm, self).__init__(*args, **kwargs)
        # Only add visibility triggers if we are inside of a
        # GroupModule. If so, only allow trigger onto modules that are
        # within the same GroupModule as this Option's FormField
        group_module_id = self.instance.field.nestedorderedmodule.group.id
        if group_module_id is not None:

            # limit the selectable group_visibility_triggers to
            # NestedOrderedModules that belong to the same form, and are not
            # visible by default
            nested_ordered_module_id = self.instance.field.nestedorderedmodule.id
            self.fields['group_visibility_triggers'].queryset = models.\
                NestedOrderedModule.objects.select_related('group').\
                filter(
                    # filter out this option's OrderedModule, because we
                    # don't want to trigger our own field:
                    ~Q(id=nested_ordered_module_id),
                    # Only select NestedOrderedModules under the same
                    # GroupModule as this instance's field:
                    group_id=group_module_id,
                    visible=False,
                )


class CheckboxOptionInline(nested_admin.NestedTabularInline):
    model = models.CheckboxOption
    form = FormFieldOptionInlineForm

    fields = ('label', 'value') + FormFieldOptionInlineForm.fields


class CheckboxFieldAdmin(HiddenModelAdmin, nested_admin.NestedModelAdmin):
    model = models.CheckboxField
    inlines = [
        CheckboxOptionInline
    ]


class RadioOptionInline(nested_admin.NestedTabularInline):
    model = models.RadioOption
    form = FormFieldOptionInlineForm

    fields = ('label', 'value') + FormFieldOptionInlineForm.fields


class RadioFieldAdmin(HiddenModelAdmin, nested_admin.NestedModelAdmin):
    model = models.RadioField
    inlines = [
        RadioOptionInline
    ]


class AbstractFormModuleAdmin (HiddenModelAdmin, admin.ModelAdmin):
    model = models.GroupModule
    fields = ['visible'] + models.RELATED_MODULES

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        Model = None
        # TODO: update models.RELATED_MODULES and make this read from it:
        if db_field.name == "radiofield":
            Model = models.RadioField
        elif db_field.name == "filefield":
            Model = models.FileField
        elif db_field.name == "numberfield":
            Model = models.NumberField
        elif db_field.name == "datefield":
            Model = models.DateField
        elif db_field.name == "addressfield":
            Model = models.AddressField
        elif db_field.name == "textfield":
            Model = models.TextField
        elif db_field.name == "textareafield":
            Model = models.TextAreaField
        elif db_field.name == "checkboxfield":
            Model = models.CheckboxField
        # NOTE: groupmodule is an exception:
        elif db_field.name == "groupmodule":
            Model = models.GroupModule
        elif db_field.name == "htmlmodule":
            Model = models.HtmlModule
        elif db_field.name == "skipstagemodule":
            Model = models.SkipStageModule
        elif db_field.name == "submitbuttonmodule":
            Model = models.SubmitButtonModule
        else:
            raise FieldDoesNotExist("db_field name does not exist: {}".format(db_field.name))

        # Filter our related modules to only those that unattached or
        # within this flavor:
        kwargs["queryset"] = self._get_related_queryset(Model.objects)

        return super(AbstractFormModuleAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)


class OrderedModuleAdmin(AbstractFormModuleAdmin):
    model = models.OrderedModule
    readonly_fields = ('formstage', 'order')
    fields = ['formstage'] + AbstractFormModuleAdmin.fields + ["groupmodule"]

    def _get_related_queryset(self, queryset):
        # include only in the queryset RelatedModules that are within this Flavor, or unattached:
        return queryset.prefetch_related('orderedmodule').filter(
            Q(orderedmodule__id=self.orderedmodule) | Q(orderedmodule=None),
        )

    def get_form(self, request, obj=None, **kwargs):
        # filter RadioFields that have ALL modules within the same flavor as this module:
        # https://www.agiliq.com/blog/2014/04/django-backward-relationship-lookup/
        self.orderedmodule = models.OrderedModule.objects.select_related('stage__form__flavor').filter(
            stage__form__flavor__id=obj.stage.form.flavor.id,
        )
        form = super(OrderedModuleAdmin, self).get_form(request, obj, **kwargs)
        return form

    def formstage(self, instance):
            return format_html(
                '<a href="{}"><strong>{}</strong></a>',
                reverse('admin:sa_api_v2_formstage_change', args=[instance.stage.pk]),
                instance.stage,
            )


class NestedOrderedModuleAdmin(AbstractFormModuleAdmin):
    model = models.NestedOrderedModule
    readonly_fields = ('parent_group_module', 'order')
    fields = ['parent_group_module'] + AbstractFormModuleAdmin.fields

    def _get_related_queryset(self, queryset):
        # include only in the queryset RelatedModules that are within
        # this Flavor, or unattached:
        # (It's helpful to link multiple FormModule to a RelatedModule when we are cloning/tweaking
        # forms...)
        return queryset.prefetch_related('nestedorderedmodule').filter(
            Q(nestedorderedmodule__id__in=self.nestedorderedmodule_id) | Q(nestedorderedmodule=None),
        )

    def get_form(self, request, obj=None, **kwargs):
        # Get all NestedOrderedModules within this flavor:
        # First, get the flavor id:
        flavor_id = obj.group.orderedmodule.stage.form.flavor.id
        self.nestedorderedmodule_id = models.NestedOrderedModule.objects.prefetch_related('group__orderedmodule__stage__form__flavor').values_list('id', flat=True)
        form = super(NestedOrderedModuleAdmin, self).get_form(request, obj, **kwargs)
        return form

    def parent_group_module(self, instance):
            return format_html(
                '<a href="{}"><strong>{}</strong></a>',
                reverse('admin:sa_api_v2_groupmodule_change', args=[instance.group.pk]),
                instance.group,
            )


# Allows us to save FormStage and FormModules that have been created
# inline.
class AlwaysChangedModelForm(ModelForm):
    def has_changed(self, *args, **kwargs):
        if self.instance.pk is None:
            return True
        return super(AlwaysChangedModelForm, self).has_changed(*args, **kwargs)


class OrderedModuleInline(SortableInlineAdminMixin, admin.StackedInline):
    model = models.OrderedModule
    extra = 0
    form = AlwaysChangedModelForm
    fields = ['visible', 'edit_url']

    readonly_fields = ['edit_url']

    def edit_url(self, instance):
        if instance.pk is None:
            return '(You must save your form before you can edit this form module.)'
        else:
            return format_html(
                '<a href="{}"><strong>Edit Ordered Module</strong></a>',
                reverse('admin:sa_api_v2_orderedmodule_change', args=[instance.pk])
            )


class NestedOrderedModuleInline(SortableInlineAdminMixin, admin.StackedInline):
    model = models.NestedOrderedModule
    extra = 0
    form = AlwaysChangedModelForm
    fields = ['visible', 'edit_url']

    readonly_fields = ['edit_url']

    def edit_url(self, instance):
        if instance.pk is None:
            return '(You must save your form before you can edit this form module.)'
        else:
            return format_html(
                '<a href="{}"><strong>Edit Nested Ordered Module</strong></a>',
                reverse('admin:sa_api_v2_nestedorderedmodule_change', args=[instance.pk])
            )


class MapViewportInline(nested_admin.NestedStackedInline):
    model = models.MapViewport
    extra = 0


class GroupModuleAdmin(HiddenModelAdmin, nested_admin.NestedModelAdmin):
    model = models.GroupModule
    inlines = [
        NestedOrderedModuleInline,
    ]


class FormStageAdmin(HiddenModelAdmin, nested_admin.NestedModelAdmin):
    model = models.FormStage
    readonly_fields = ('link_to_form', 'order')
    fields = ('link_to_form', 'order', 'visible_layer_groups')
    exclude = ("form",)
    inlines = [
        MapViewportInline,
        OrderedModuleInline,
    ]

    def link_to_form(self, instance):
        return format_html(
            '<a href="{}"><strong>{}</strong></a>',
            reverse('admin:sa_api_v2_form_change', args=[instance.form.pk]),
            instance.form,
        )


class FormStageInline(SortableInlineAdminMixin, admin.StackedInline):
    model = models.FormStage
    extra = 0
    form = AlwaysChangedModelForm

    readonly_fields = ['edit_url', 'summary']

    def edit_url(self, instance):
        if instance.pk is None:
            return '(You must save your form before you can edit this form stage.)'
        else:
            return format_html(
                '<a href="{}"><strong>Edit Form Stage</strong></a>',
                reverse('admin:sa_api_v2_formstage_change', args=[instance.pk])
            )

    def summary(self, instance):
        related_module = instance.get_related_module()
        if related_module is None:
            return "module id: {}".format(instance.id)
        else:
            return "module id: {}, {}".format(
                instance.id,
                related_module,
            )


class FormAdmin(admin.ModelAdmin):
    model = models.Form
    inlines = [
        FormStageInline
    ]


class FlavorAdmin(admin.ModelAdmin):
    model = models.Flavor
    prepopulated_fields = {'slug': ['display_name']}


class ActionAdmin(admin.ModelAdmin):
    date_hierarchy = 'created_datetime'
    list_display = ('id', 'created_datetime', 'action', 'type_of_thing', 'submitter_name', 'source')
    raw_id_fields = ('thing',)

    # Django 1.6+
    def get_queryset(self, request):
        qs = super(ActionAdmin, self).get_queryset(request)
        user = request.user
        if not user.is_superuser:
            qs = qs.filter(thing__dataset__owner=user)
        return qs.select_related('thing', 'thing__place', 'thing__submitter')

    def submitter_name(self, obj):
        return obj.submitter.username if obj.submitter else None

    def type_of_thing(self, obj):
        try:
            if obj.thing.place is not None:
                return 'place'
        except models.Place.DoesNotExist:
            return obj.thing.submission.set_name


class InlineGroupPermissionAdmin(admin.TabularInline):
    model = models.GroupPermission
    extra = 0


class GroupAdmin(admin.ModelAdmin):
    raw_id_fields = ('dataset',)
    filter_horizontal = ('submitters',)
    inlines = [InlineGroupPermissionAdmin]

    class Media:
        js = (
            'admin/js/jquery-1.11.0.min.js',
            'admin/js/jquery-ui-1.10.4.min.js',
            'admin/js/admin-list-reorder.js',
        )

    def get_queryset(self, request):
        qs = super(GroupAdmin, self).get_queryset(request)
        user = request.user
        if not user.is_superuser:
            qs = qs.filter(dataset__owner=user)
        return qs


class UserChangeForm(BaseUserChangeForm):
    class Meta(BaseUserChangeForm.Meta):
        model = models.User


class UserAdmin(BaseUserAdmin):
    form = UserChangeForm
    change_form_template = 'loginas/change_form.html'

    fieldsets = BaseUserAdmin.fieldsets + (
            # (None, {'fields': ('some_extra_data',)}),
    )

    def get_queryset(self, request):
        qs = super(UserAdmin, self).get_queryset(request)
        user = request.user
        if not user.is_superuser:
            # Only show users that have contributed to the owner's datasets
            qs = qs.filter(things__dataset__owner=user)
        return qs


admin.site.register(models.User, UserAdmin)
admin.site.register(models.DataSet, DataSetAdmin)
admin.site.register(models.Place, PlaceAdmin)
admin.site.register(models.Submission, SubmissionAdmin)
admin.site.register(models.Action, ActionAdmin)
admin.site.register(models.Group, GroupAdmin)
admin.site.register(models.Webhook, WebhookAdmin)
admin.site.register(models.PlaceEmailTemplate, PlaceEmailTemplateAdmin)
admin.site.register(models.Flavor, FlavorAdmin)
admin.site.register(models.Form, FormAdmin)
admin.site.register(models.FormStage, FormStageAdmin)
admin.site.register(models.OrderedModule, OrderedModuleAdmin)
admin.site.register(models.NestedOrderedModule, NestedOrderedModuleAdmin)
admin.site.register(models.LayerGroup, admin.ModelAdmin)
admin.site.register(models.MapViewport, HiddenModelAdmin)
admin.site.register(models.RadioField, RadioFieldAdmin)
admin.site.register(models.HtmlModule, HiddenModelAdmin)
admin.site.register(models.SkipStageModule, HiddenModelAdmin)
admin.site.register(models.SubmitButtonModule, HiddenModelAdmin)
admin.site.register(models.TextField, HiddenModelAdmin)
admin.site.register(models.TextAreaField, HiddenModelAdmin)
admin.site.register(models.DateField, HiddenModelAdmin)
admin.site.register(models.NumberField, HiddenModelAdmin)
admin.site.register(models.FileField, HiddenModelAdmin)
admin.site.register(models.CheckboxField, CheckboxFieldAdmin)
admin.site.register(models.AddressField, HiddenModelAdmin)
admin.site.register(models.GroupModule, GroupModuleAdmin)

admin.site.site_header = 'Mapseed API Server Administration'
admin.site.site_title = 'Mapseed API Server'
