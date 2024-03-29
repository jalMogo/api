import ujson as json
from rest_framework import serializers, fields
from collections import OrderedDict
from rest_framework.relations import PKOnlyObject
from rest_framework.fields import SkipField
from ..params import INCLUDE_PRIVATE_FIELDS_PARAM

###############################################################################
#
# Serializer Mixins
# -----------------
#


class ActivityGenerator(object):
    def save(self, silent=False, **kwargs):
        request = self.context["request"]
        silent_header = request.META.get("HTTP_X_SHAREABOUTS_SILENT", "False")
        if not silent:
            silent = silent_header.lower() in ("true", "t", "yes", "y")
        request_source = request.META.get("HTTP_REFERER", "")
        return super(ActivityGenerator, self).save(
            silent=silent, source=request_source, **kwargs
        )


class EmptyModelSerializer(object):
    """
    A simple mixin that constructs an in-memory model when None is passed in
    as the object to to_representation.
    """

    def ensure_obj(self, obj):
        if obj is None:
            obj = self.opts.model()
        return obj


class DataBlobProcessor(EmptyModelSerializer):
    """
    Like ModelSerializer, but automatically serializes/deserializes a
    'data' JSON blob of arbitrary key/value pairs.
    """

    def to_internal_value(self, data):
        """
        Dict of native values <- Dict of primitive datatypes.
        """
        known_fields_object = super(DataBlobProcessor, self).to_internal_value(data)

        model = self.Meta.model
        blob = json.loads(self.instance.data) if self.partial else {}
        data_copy = OrderedDict()

        # Pull off any fields that the model doesn't know about directly
        # and put them into the data blob.
        known_fields = set([f.name for f in model._meta.get_fields()])

        # Also ignore the following field names (treat them like reserved
        # words).
        known_fields.update(list(self.fields.keys()))

        # And allow an arbitrary value field named 'data' (don't let the
        # data blob get in the way).
        known_fields.remove("data")

        # Split the incoming data into stuff that will be set straight onto
        # preexisting fields, and stuff that will go into the data blob.
        for key in data:
            if key not in known_fields:
                blob[key] = data[key]

        for key in known_fields_object:
            data_copy[key] = known_fields_object[key]

        data_copy["data"] = json.dumps(blob)

        if not self.partial:
            for field_name, field in list(self.fields.items()):
                if (
                    not field.read_only
                    and field_name not in data_copy
                    and field.default is not fields.empty
                ):
                    data_copy[field_name] = field.default

        return data_copy

    # TODO: What is this replaced with?
    def convert_object(self, obj):
        attrs = super(DataBlobProcessor, self).convert_object(obj)

        data = json.loads(obj.data)
        del attrs["data"]
        attrs.update(data)

        return attrs

    def explode_data_blob(self, data):
        blob = data.pop("data")

        blob_data = json.loads(blob)

        # Did the user not ask for private data? Remove it!
        if not self.is_flag_on(INCLUDE_PRIVATE_FIELDS_PARAM):
            for key in list(blob_data.keys()):
                if key.startswith("private"):
                    del blob_data[key]

        data.update(blob_data)
        return data

    def to_representation(self, obj):
        obj = self.ensure_obj(obj)
        # data = super(DataBlobProcessor, self).to_representation(obj, None, None)
        data = super(DataBlobProcessor, self).to_representation(obj)
        self.explode_data_blob(data)
        return data


class AttachmentSerializerMixin(EmptyModelSerializer, serializers.ModelSerializer):
    def to_representation(self, instance):
        # add an 'id', which is the primary key
        ret = super(AttachmentSerializerMixin, self).to_representation(instance)
        ret["id"] = instance.pk
        return ret


class FormFieldOptionsCreator(object):
    def create(self, validated_data):
        options_data = validated_data.pop("options", None)
        field = super(FormFieldOptionsCreator, self).create(validated_data)
        # ensure that no order has been supplied, because we auto-generate it
        # upon creation:
        order = 1

        for option_data in options_data:
            if "order" in list(option_data.keys()):
                raise serializers.ValidationError(
                    "Order should not be supplied when creating a FormField option"
                )

            option_data["order"] = order
            order += 1
            # read from our custom attrs:
            self.Meta.options_model.objects.create(field=field, **option_data)
        return field


class FormModulesValidator(object):
    def validate(self, data):
        if hasattr(self, "initial_data"):
            unknown_keys = set(self.initial_data.keys()) - set(data.keys())
            if unknown_keys:
                raise serializers.ValidationError(
                    "Got unknown fields: {}".format(list(unknown_keys))
                )
        return data


class OmitNullFieldsFromRepr(object):
    # removes "null" fields, based on our configured fields in
    # 'self.Meta.fields_to_omit`:
    def to_representation(self, instance):
        """
        Object instance -> Dict of primitive datatypes.
        """
        ret = OrderedDict()
        fields = self._readable_fields

        for field in fields:
            try:
                attribute = field.get_attribute(instance)
            except SkipField:
                continue

            # We skip `to_representation` for `None` values so that fields do
            # not have to explicitly deal with that case.
            #
            # For related fields with `use_pk_only_optimization` we need to
            # resolve the pk value.
            attribute_or_pk = (
                attribute.pk if isinstance(attribute, PKOnlyObject) else attribute
            )

            # Skip the fields here, if needed:
            if not attribute_or_pk and (
                "*" in self.Meta.fields_to_omit
                or field.field_name in self.Meta.fields_to_omit
            ):
                continue

            if attribute_or_pk is None:
                ret[field.field_name] = None
            else:
                ret[field.field_name] = field.to_representation(attribute)

        return ret
