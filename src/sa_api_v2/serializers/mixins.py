import ujson as json
from rest_framework import serializers, fields
from collections import OrderedDict
from ..params import (
    INCLUDE_PRIVATE_FIELDS_PARAM,
)

###############################################################################
#
# Serializer Mixins
# -----------------
#


class ActivityGenerator (object):
    def save(self, silent=False, **kwargs):
        request = self.context['request']
        silent_header = request.META.get('HTTP_X_SHAREABOUTS_SILENT', 'False')
        if not silent:
            silent = silent_header.lower() in ('true', 't', 'yes', 'y')
        request_source = request.META.get('HTTP_REFERER', '')
        return super(ActivityGenerator, self).save(
            silent=silent,
            source=request_source,
            **kwargs
        )


class EmptyModelSerializer (object):
    """
    A simple mixin that constructs an in-memory model when None is passed in
    as the object to to_representation.
    """
    def ensure_obj(self, obj):
        if obj is None:
            obj = self.opts.model()
        return obj


class DataBlobProcessor (EmptyModelSerializer):
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
        known_fields.update(self.fields.keys())

        # And allow an arbitrary value field named 'data' (don't let the
        # data blob get in the way).
        known_fields.remove('data')

        # Split the incoming data into stuff that will be set straight onto
        # preexisting fields, and stuff that will go into the data blob.
        for key in data:
            if key not in known_fields:
                blob[key] = data[key]

        for key in known_fields_object:
            data_copy[key] = known_fields_object[key]

        data_copy['data'] = json.dumps(blob)

        if not self.partial:
            for field_name, field in self.fields.items():
                if (not field.read_only and field_name not in data_copy and field.default is not fields.empty):
                    data_copy[field_name] = field.default

        return data_copy

    # TODO: What is this replaced with?
    def convert_object(self, obj):
        attrs = super(DataBlobProcessor, self).convert_object(obj)

        data = json.loads(obj.data)
        del attrs['data']
        attrs.update(data)

        return attrs

    def explode_data_blob(self, data):
        blob = data.pop('data')

        blob_data = json.loads(blob)

        # Did the user not ask for private data? Remove it!
        if not self.is_flag_on(INCLUDE_PRIVATE_FIELDS_PARAM):
            for key in blob_data.keys():
                if key.startswith('private'):
                    del blob_data[key]

        data.update(blob_data)
        return data

    def to_representation(self, obj):
        obj = self.ensure_obj(obj)
        # data = super(DataBlobProcessor, self).to_representation(obj, None, None)
        data = super(DataBlobProcessor, self).to_representation(obj)
        self.explode_data_blob(data)
        return data


class AttachmentSerializerMixin (EmptyModelSerializer, serializers.ModelSerializer):
    def to_representation(self, instance):
        # add an 'id', which is the primary key
        ret = super(AttachmentSerializerMixin, self).to_representation(instance)
        ret['id'] = instance.pk
        return ret


class FormModulesSerializer (serializers.ModelSerializer):
    def validate(self, data):
        if hasattr(self, 'initial_data'):
            unknown_keys = set(self.initial_data.keys()) - set(data.keys())
            if unknown_keys:
                raise serializers.ValidationError("Got unknown fields: {}".format(unknown_keys))
        return data
