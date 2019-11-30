import ujson as json
from django.utils.http import urlquote_plus
from rest_framework.reverse import reverse
from django.contrib.gis.geos import GEOSGeometry
from django.core.exceptions import ValidationError
from rest_framework import serializers
from .. import models

###############################################################################
#
# Geo-related fields
# ------------------
#


class GeometryField(serializers.Field):
    def __init__(self, format='dict', *args, **kwargs):
        self.format = format

        if self.format not in ('json', 'wkt', 'dict'):
            raise ValueError('Invalid format: %s' % self.format)

        super(GeometryField, self).__init__(*args, **kwargs)

    def to_representation(self, obj):
        if self.format == 'json':
            return obj.json
        elif self.format == 'wkt':
            return obj.wkt
        elif self.format == 'dict':
            return json.loads(obj.json)
        else:
            raise ValueError('Cannot output as %s' % self.format)

    def to_internal_value(self, data):
        if not isinstance(data, str):
            data = json.dumps(data)

        try:
            return GEOSGeometry(data)
        except Exception as exc:
            raise ValidationError('Problem converting native data to Geometry: %s' % (exc,))

###############################################################################
#
# Shareabouts-specific fields
# ---------------------------
#


class ShareaboutsFieldMixin (object):

    # These names should match the names of the cache parameters, and should be
    # in the same order as the corresponding URL arguments.
    url_arg_names = ()

    def get_url_kwargs(self, obj):
        """
        Pull the appropriate arguments off of the cache to construct the URL.
        """
        if isinstance(obj, models.User):
            instance_kwargs = {'owner_username': obj.username}
        else:
            instance_kwargs = obj.cache.get_cached_instance_params(obj.pk,
                                                                   lambda: obj)

        url_kwargs = {}
        for arg_name in self.url_arg_names:
            arg_value = instance_kwargs.get(arg_name, None)
            if arg_value is None:
                try:
                    arg_value = getattr(obj, arg_name)
                except AttributeError:
                    raise KeyError('No arg named %r in %r' % (arg_name,
                                                              instance_kwargs))
            url_kwargs[arg_name] = arg_value
        return url_kwargs


def api_reverse(view_name, kwargs={}, request=None, format=None):
    """
    A special case of URL reversal where we know we're getting an API URL. This
    can be much faster than Django's built-in general purpose regex resolver.

    """
    if request:
        url = '{}://{}/api/v2'.format(request.scheme, request.get_host())
    else:
        url = '/api/v2'

    route_template_strings = {
        'submission-detail': '/{owner_username}/datasets/{dataset_slug}/places/{place_id}/{submission_set_name}/{submission_id}',
        'submission-list': '/{owner_username}/datasets/{dataset_slug}/places/{place_id}/{submission_set_name}',

        'place-detail':
        '/{owner_username}/datasets/{dataset_slug}/places/{place_id}',
        'place-list': '/{owner_username}/datasets/{dataset_slug}/places',
        'place-tag-list': '/{owner_username}/datasets/{dataset_slug}/places/{place_id}/tags',

        'dataset-detail': '/{owner_username}/datasets/{dataset_slug}',
        'user-detail': '/{owner_username}',
        'dataset-submission-list': '/{owner_username}/datasets/{dataset_slug}/{submission_set_name}',
        'attachment-detail': '/{owner_username}/datasets/{dataset_slug}/places/{place_id}/attachments/{attachment_id}',
    }

    try:
        route_template_string = route_template_strings[view_name]
    except KeyError:
        raise ValueError('No API route named {} formatted.'.format(view_name))

    url_params = dict([(key, urlquote_plus(val))
                       for key, val in kwargs.items()])
    url += route_template_string.format(**url_params)

    if format is not None:
        url += '.' + format

    return url


class ShareaboutsRelatedField (ShareaboutsFieldMixin,
                               serializers.HyperlinkedRelatedField):
    """
    Represents a Shareabouts relationship using hyperlinking.
    """
    read_only = True
    view_name = None

    def __init__(self, *args, **kwargs):
        if self.view_name is not None:
            kwargs['view_name'] = self.view_name
        if self.queryset is not None:
            kwargs['queryset'] = self.queryset
        super(ShareaboutsRelatedField, self).__init__(*args, **kwargs)

    def get_attribute(self, obj):
        # Pass the entire object through to `to_representation()`,
        # instead of the standard attribute lookup. Otherwise,
        # obj is just a DRF relations.PKOnlyObject.
        return obj

    def to_representation(self, obj, request=None, format=None):
        view_name = self.view_name
        request = request if request else self.context.get('request', None)
        format = format if format else self.format or self.context.get('format', None)

        pk = getattr(obj, 'pk', None)
        if pk is None:
            return

        kwargs = self.get_url_kwargs(obj)
        return api_reverse(view_name, kwargs=kwargs, request=request,
                           format=format)


# If we want to make this field writeable, we'll need to implement a get_object as well.
class DataSetHyperlinkedField (serializers.HyperlinkedRelatedField):
    view_name = 'dataset-detail'
    queryset = models.DataSet.objects.all()
    lookup_field = 'id'

    def get_url(self, obj, view_name, request, format):
        url_kwargs = {
            'owner_username': obj.owner.username,
            'dataset_slug': obj.slug,
        }
        return reverse(self.view_name, kwargs=url_kwargs, request=request)


class DataSetRelatedField (ShareaboutsRelatedField):
    view_name = 'dataset-detail'
    url_arg_names = ('owner_username', 'dataset_slug')

    def get_url(self, obj, request):
        url_kwargs = {
            'owner_username': obj.owner.username,
            'dataset_slug': obj.slug,
        }
        return reverse(self.view_name, kwargs=url_kwargs, request=request)

    def get_object(self, view_name, view_args, view_kwargs):
        lookup_kwargs = {
            'display_name': view_kwargs['dataset_slug'],
            'owner__username': view_kwargs['owner_username'],
        }
        return self.get_queryset().get(**lookup_kwargs)


# class DataSetKeysRelatedField (ShareaboutsRelatedField):
#     view_name = 'apikey-list'
#     url_arg_names = ('owner_username', 'dataset_slug')


class UserRelatedField (ShareaboutsRelatedField):
    view_name = 'user-detail'
    url_arg_names = ('owner_username',)


class PlaceRelatedField (ShareaboutsRelatedField):
    view_name = 'place-detail'
    url_arg_names = ('owner_username', 'dataset_slug', 'place_id')
    queryset = models.Place.objects.all()

    def get_object(self, view_name, view_args, view_kwargs):
        lookup_kwargs = {
            'id': view_kwargs['place_id'],
        }
        return self.get_queryset().get(**lookup_kwargs)


class SubmissionSetRelatedField (ShareaboutsRelatedField):
    view_name = 'submission-list'
    url_arg_names = ('owner_username', 'dataset_slug', 'place_id',
                     'submission_set_name')


# TODO: enable this with caching
class TagRelatedField (serializers.HyperlinkedRelatedField):
    view_name = 'tag-detail'
    queryset = models.Tag.objects.all()
    lookup_field = 'id'

    def get_url(self, obj, view_name, request, format):
        url_kwargs = {
            'owner_username': obj.dataset.owner.get_username(),
            'dataset_slug': obj.dataset.slug,
            'tag_id': obj.pk
        }
        return reverse(self.view_name, kwargs=url_kwargs, request=request, format=format)

    # TODO: do we need this?
    def get_object(self, view_name, view_args, view_kwargs):
        lookup_kwargs = {
           'dataset__slug': view_kwargs['dataset_slug'],
           'id': view_kwargs['tag_id']
        }
        return self.get_queryset().get(**lookup_kwargs)


class ShareaboutsIdentityField (ShareaboutsFieldMixin,
                                serializers.HyperlinkedIdentityField):
    read_only = True

    def __init__(self, *args, **kwargs):
        view_name = kwargs.pop('view_name', None) or getattr(self, 'view_name',
                                                             None)
        super(ShareaboutsIdentityField, self).__init__(view_name=view_name,
                                                       *args, **kwargs)

    def get_attribute(self, obj):
        # Pass the entire object through to `to_representation()`,
        # instead of the standard attribute lookup. Otherwise,
        # obj is just a DRF relations.PKOnlyObject.
        return obj

    def to_representation(self, obj, request=None, format=None):
        if obj.pk is None:
            return None

        request = request if request else self.context.get('request', None)
        format = format if format else self.context.get('format', None)

        view_name = self.view_name or self.parent.opts.view_name

        kwargs = self.get_url_kwargs(obj)

        if format and self.format and self.format != format:
            format = self.format

        return api_reverse(view_name, kwargs=kwargs, request=request,
                           format=format)


class PlaceIdentityField (ShareaboutsIdentityField):
    url_arg_names = ('owner_username', 'dataset_slug', 'place_id')
    view_name = 'place-detail'


class AttachmentIdentityField (ShareaboutsIdentityField):
    url_arg_names = ('owner_username', 'dataset_slug', 'place_id', 'attachment_id')
    view_name = 'attachment-detail'


class SubmissionSetIdentityField (ShareaboutsIdentityField):
    url_arg_names = ('owner_username', 'dataset_slug', 'place_id',
                     'submission_set_name')
    view_name = 'submission-list'


class DataSetPlaceSetIdentityField (ShareaboutsIdentityField):
    url_arg_names = ('owner_username', 'dataset_slug')
    view_name = 'place-list'


class DataSetSubmissionSetIdentityField (ShareaboutsIdentityField):
    url_arg_names = ('owner_username', 'dataset_slug', 'submission_set_name')
    view_name = 'dataset-submission-list'


class SubmissionIdentityField (ShareaboutsIdentityField):
    url_arg_names = ('owner_username', 'dataset_slug', 'place_id',
                     'submission_set_name', 'submission_id')
    view_name = 'submission-detail'


class TagIdentityField (serializers.HyperlinkedIdentityField):
    lookup_field = 'id'

    def __init__(self, *args, **kwargs):
        super(TagIdentityField, self).__init__(view_name='tag-detail', *args, **kwargs)

    def get_url(self, obj, view_name, request, format):
        url_kwargs = {
            'owner_username': obj.dataset.owner.get_username(),
            'dataset_slug': obj.dataset.slug,
            'tag_id': obj.pk
        }
        return reverse(view_name, kwargs=url_kwargs, request=request, format=format)


class PlaceTagListIdentityField (ShareaboutsIdentityField):
    url_arg_names = ('owner_username', 'dataset_slug', 'place_id',)
    view_name = 'place-tag-list'


class PlaceTagIdentityField (serializers.HyperlinkedIdentityField):
    lookup_field = 'id'

    def __init__(self, *args, **kwargs):
        super(PlaceTagIdentityField, self).__init__(view_name='place-tag-detail', *args, **kwargs)

    def get_url(self, obj, view_name, request, format):
        url_kwargs = {
            'owner_username': obj.tag.dataset.owner.get_username(),
            'dataset_slug': obj.tag.dataset.slug,
            'place_id': obj.place.id,
            'place_tag_id': obj.pk
        }
        return reverse(view_name, kwargs=url_kwargs, request=request, format=format)


class DataSetIdentityField (ShareaboutsIdentityField):
    url_arg_names = ('owner_username', 'dataset_slug')
    view_name = 'dataset-detail'


# class AttachmentFileField (serializers.FileField):
#     def to_representation(self, obj):
#         return obj.storage.url(obj.name)
