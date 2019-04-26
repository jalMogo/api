"""
DjangoRestFramework resources for the Shareabouts REST API.
"""
from django.utils import six
from collections import defaultdict
from django.core.exceptions import ValidationError
from rest_framework import serializers

from .mixins import (
    ActivityGenerator,
    EmptyModelSerializer,
    DataBlobProcessor,
    AttachmentSerializerMixin,
)

from .fields import (
    GeometryField,
    DataSetRelatedField,
    DataSetHyperlinkedField,
    UserRelatedField,
    PlaceRelatedField,
    SubmissionSetRelatedField,
    TagRelatedField,
    PlaceIdentityField,
    AttachmentIdentityField,
    SubmissionSetIdentityField,
    DataSetPlaceSetIdentityField,
    DataSetSubmissionSetIdentityField,
    SubmissionIdentityField,
    TagIdentityField,
    PlaceTagListIdentityField,
    PlaceTagIdentityField,
    DataSetIdentityField,
)

from .user import (
    BaseUserSerializer,
    UserSerializer,
    SimpleUserSerializer,
)
from .. import apikey
from .. import cors
from .. import models
from ..models import check_data_permission
from ..params import (
    INCLUDE_PRIVATE_FIELDS_PARAM,
    INCLUDE_INVISIBLE_PARAM,
    INCLUDE_TAGS_PARAM,
    INCLUDE_SUBMISSIONS_PARAM,
)

import logging
logger = logging.getLogger(__name__)

###############################################################################
#
# Serializers
# -----------
#
# Many of the serializers below come in two forms:
#
# 1) A hyperlinked serializer -- this form includes URLs to the object's
#    related fields, as well as the object's own URL. This is useful for the
#    self-describing nature of the web API.
#
# 2) A simple serializer -- this form does not include any of the URLs in the
#    hyperlinked serializer. This is more useful for bulk data dumps where all
#    of the related data is included in a package.
#


class AttachmentListSerializer (AttachmentSerializerMixin):
    url = AttachmentIdentityField()

    class Meta:
        model = models.Attachment
        exclude = ('thing', 'id')


class AttachmentInstanceSerializer (AttachmentSerializerMixin):
    url = AttachmentIdentityField()

    class Meta:
        model = models.Attachment
        exclude = ('thing', 'id')

class DataSetPermissionSerializer (serializers.ModelSerializer):
    class Meta:
        model = models.DataSetPermission
        exclude = ('id', 'dataset')

class GroupPermissionSerializer (serializers.ModelSerializer):
    class Meta:
        model = models.GroupPermission
        exclude = ('id', 'group')

class KeyPermissionSerializer (serializers.ModelSerializer):
    class Meta:
        model = models.KeyPermission
        exclude = ('id', 'key')

class OriginPermissionSerializer (serializers.ModelSerializer):
    class Meta:
        model = models.OriginPermission
        exclude = ('id', 'origin')

class ApiKeySerializer (serializers.ModelSerializer):
    permissions = KeyPermissionSerializer(many=True)

    class Meta:
        model = apikey.models.ApiKey
        exclude = ('id', 'dataset', 'logged_ip', 'last_used')

class OriginSerializer (serializers.ModelSerializer):
    permissions = OriginPermissionSerializer(many=True)

    class Meta:
        model = cors.models.Origin
        exclude = ('id', 'dataset', 'logged_ip', 'last_used')


# Group serializers
class BaseGroupSerializer (serializers.ModelSerializer):
    class Meta:
        model = models.Group
        exclude = ('submitters', 'id')


class SimpleGroupSerializer (BaseGroupSerializer):
    permissions = GroupPermissionSerializer(many=True)

    class Meta (BaseGroupSerializer.Meta):
        exclude = ('id', 'dataset', 'submitters')


class GroupSerializer (BaseGroupSerializer):
    dataset = DataSetRelatedField(queryset=models.DataSet.objects.all())

    class Meta (BaseGroupSerializer.Meta):
        pass

    def to_representation(self, obj):
        ret = {}
        ret['dataset'] = six.text_type(self.fields['dataset']
                                       .to_representation(obj.dataset))
        ret['name'] = obj.name
        ret['dataset_slug'] = obj.dataset.slug
        ret['permissions'] = [] 

        for permission in obj.permissions.all():
            ret['permissions'].append({
                'abilities': permission.get_abilities(),
                'submission_set': permission.submission_set
            })

        return ret


class FullUserSerializer (BaseUserSerializer):
    """
    Generates a representation of the current user. Since it's only for the
    current user, it should have all the user's information on it (all that
    the user would need).
    """
    groups = GroupSerializer(many=True, source='_groups', read_only=True)

    class Meta (BaseUserSerializer.Meta):
        pass

    def to_representation(self, obj):
        data = super(FullUserSerializer, self).to_representation(obj)
        if obj:
            group_serializer = self.fields['groups']
            groups_field = obj.get_groups()
            data['groups'] = group_serializer.to_representation(groups_field)
        return data


# DataSet place set serializer
class DataSetPlaceSetSummarySerializer (serializers.HyperlinkedModelSerializer):
    length = serializers.IntegerField(source='places_length')
    url = DataSetPlaceSetIdentityField()

    class Meta:
        model = models.DataSet
        fields = ('length', 'url')

    def get_place_counts(self, obj):
        """
        Return a dictionary whose keys are dataset ids and values are the
        corresponding count of places in that dataset.
        """
        # This will currently do a query for every dataset, not a single query
        # for all datasets. Generally a bad idea, but not a huge problem
        # considering the number of datasets at the moment. In the future,
        # we should perhaps use some kind of many_to_representation function.

        # if self.many:
        #     include_invisible = INCLUDE_INVISIBLE_PARAM in self.context['request'].GET
        #     places = models.Place.objects.filter(dataset__in=obj)
        #     if not include_invisible:
        #         places = places.filter(visible=True)

        #     # Unset any default ordering
        #     places = places.order_by()

        #     places = places.values('dataset').annotate(length=Count('dataset'))
        #     return dict([(place['dataset'], place['length']) for place in places])

        # else:
        include_invisible = INCLUDE_INVISIBLE_PARAM in self.context['request'].GET
        places = obj.places
        if not include_invisible:
            places = places.filter(visible=True)
        return {obj.pk: places.count()}

    def to_representation(self, obj):
        place_count_map = self.get_place_counts(obj)
        obj.places_length = place_count_map.get(obj.pk, 0)
        data = super(DataSetPlaceSetSummarySerializer, self).to_representation(obj)
        return data


# DataSet submission set serializer
class DataSetSubmissionSetSummarySerializer (serializers.HyperlinkedModelSerializer):
    length = serializers.IntegerField(source='submission_set_length')
    url = DataSetSubmissionSetIdentityField()

    class Meta:
        model = models.DataSet
        fields = ('length', 'url')

    def is_flag_on(self, flagname):
        request = self.context['request']
        param = request.GET.get(flagname, 'false')
        return param.lower() not in ('false', 'no', 'off')

    def get_submission_sets(self, dataset):
        include_invisible = self.is_flag_on(INCLUDE_INVISIBLE_PARAM)
        submission_sets = defaultdict(list)
        for submission in dataset.submissions.all():
            if include_invisible or submission.visible:
                set_name = submission.set_name
                submission_sets[set_name].append(submission)
        return {dataset.id: submission_sets}

    def to_representation(self, obj):
        request = self.context['request']
        submission_sets_map = self.get_submission_sets(obj)
        sets = submission_sets_map.get(obj.id, {})
        summaries = {}
        for set_name, submission_set in sets.iteritems():
            # Ensure the user has read permission on the submission set.
            user = getattr(request, 'user', None)
            client = getattr(request, 'client', None)
            dataset = obj
            if not check_data_permission(user, client, None, 'retrieve', dataset, set_name):
                continue

            obj.submission_set_name = set_name
            obj.submission_set_length = len(submission_set)
            summaries[set_name] = super(DataSetSubmissionSetSummarySerializer, self).to_representation(obj)
        return summaries


class SubmittedThingSerializer (ActivityGenerator, DataBlobProcessor):
    def is_flag_on(self, flagname):
        request = self.context['request']
        param = request.GET.get(flagname, 'false')
        return param.lower() not in ('false', 'no', 'off')


# Place serializers
class BasePlaceSerializer (SubmittedThingSerializer,
                           serializers.ModelSerializer):
    geometry = GeometryField(format='wkt')
    attachments = AttachmentListSerializer(read_only=True, many=True)
    submitter = SimpleUserSerializer(required=False, allow_null=True)
    private = serializers.BooleanField(required=False, default=False)

    class Meta:
        model = models.Place

    def get_submission_sets(self, place):
        include_invisible = self.is_flag_on(INCLUDE_INVISIBLE_PARAM)
        submission_sets = defaultdict(list)
        for submission in place.submissions.all():
            if include_invisible or submission.visible:
                set_name = submission.set_name
                submission_sets[set_name].append(submission)
        return submission_sets

    def summary_to_native(self, set_name, submissions):
        return {
            'name': set_name,
            'length': len(submissions)
        }

    def get_submission_set_summaries(self, place):
        """
        Get a mapping from place id to a submission set summary dictionary.
        Get this for the entire dataset at once.
        """
        request = self.context['request']

        submission_sets = self.get_submission_sets(place)
        summaries = {}
        for set_name, submissions in submission_sets.iteritems():
            # Ensure the user has read permission on the submission set.
            user = getattr(request, 'user', None)
            client = getattr(request, 'client', None)
            dataset = getattr(request, 'get_dataset', lambda: None)()

            if not check_data_permission(user, client, None, 'retrieve', dataset, set_name):
                continue

            summaries[set_name] = self.summary_to_native(set_name, submissions)

        return summaries

    def get_tag_summary(self, place):
        """
        Get a mapping from place id to a tag summary dictionary.
        Get this for the entire dataset at once.
        """
        url_field = PlaceTagListIdentityField()
        url = url_field.to_representation(
            place,
            request=self.context.get('request', None),
            format=self.context.get('format', None)
        )
        return {
            'url': url,
            'length': place.tags.count()
        }

    def get_detailed_tags(self, place):
        """
        Get a mapping from place id to an array of place tag details.
        TODO: Get this for the entire dataset at once.
        """
        request = self.context['request']

        tags = place.tags.all()

        return [PlaceTagSerializer(context={'request': request})
                .to_representation(tag) for tag in tags]

    def set_to_native(self, set_name, submissions):
        serializer = SimpleSubmissionSerializer(submissions, many=True, context=self.context)
        return serializer.data

    def get_detailed_submission_sets(self, place):
        """
        Get a mapping from place id to a detiled submission set dictionary.
        Get this for the entire dataset at once.
        """
        request = self.context['request']

        submission_sets = self.get_submission_sets(place)
        details = {}
        for set_name, submissions in submission_sets.iteritems():
            # Ensure the user has read permission on the submission set.
            user = getattr(request, 'user', None)
            client = getattr(request, 'client', None)
            dataset = getattr(request, 'get_dataset', lambda: None)()

            if not check_data_permission(user, client, None, 'retrieve', dataset, set_name):
                continue

            # We know that the submission datasets will be the same as the
            # place dataset, so say so and avoid an extra query for each.
            for submission in submissions:
                submission.dataset = place.dataset

            details[set_name] = self.set_to_native(set_name, submissions)

        return details

    def attachments_to_native(self, obj):
        return [AttachmentListSerializer(a, context=self.context).data for a in obj.attachments.filter(visible=True)]

    def submitter_to_native(self, obj):
        return SimpleUserSerializer(obj.submitter).data if obj.submitter else None

    def to_representation(self, obj):
        obj = self.ensure_obj(obj)
        fields = self.get_fields()

        request = self.context.get('request', None)

        dataset_field = fields['dataset']
        data = {
            'id': obj.pk,  # = serializers.PrimaryKeyRelatedField(read_only=True)
            'geometry': str(obj.geometry or 'POINT(0 0)'),  # = GeometryField(format='wkt')
            'dataset': dataset_field.get_url(
                obj.dataset,
                request,
            ),
            'attachments': self.attachments_to_native(obj),  # = AttachmentSerializer(read_only=True)
            'submitter': self.submitter_to_native(obj),
            'data': obj.data,
            'visible': obj.visible,
            'created_datetime': obj.created_datetime.isoformat() if obj.created_datetime else None,
            'updated_datetime': obj.updated_datetime.isoformat() if obj.updated_datetime else None,
        }

        # If the place is public, don't inlude the 'private' attribute
        # in the serialized representation. This minimizes the JSON
        # payload:
        if obj.private:
            data['private'] = obj.private

        if self.context.get('include_jwt'):
            data['jwt_public'] = obj.make_jwt()

        # For use in PlaceSerializer:
        if 'url' in fields:
            field = fields['url']
            data['url'] = field.to_representation(
                obj,
                request=request,
                format=self.context.get('format', None)
            )

        data = self.explode_data_blob(data)

        # data = super(PlaceSerializer, self).to_representation(obj)

        # TODO: Put this flag value directly in to the serializer context,
        #       instead of relying on the request query parameters.
        if not self.is_flag_on(INCLUDE_SUBMISSIONS_PARAM):
            submission_sets_getter = self.get_submission_set_summaries
        else:
            submission_sets_getter = self.get_detailed_submission_sets

        if not self.is_flag_on(INCLUDE_TAGS_PARAM):
            tags_getter = self.get_tag_summary
        else:
            tags_getter = self.get_detailed_tags

        data['submission_sets'] = submission_sets_getter(obj)
        data['tags'] = tags_getter(obj)

        if hasattr(obj, 'distance'):
            data['distance'] = str(obj.distance)

        return data


class SimplePlaceSerializer (BasePlaceSerializer):
    class Meta (BasePlaceSerializer.Meta):
        read_only_fields = ('dataset',)
        fields = '__all__'


class PlaceListSerializer(serializers.ListSerializer):
    def update(self, instance, validated_data):
        place_mapping = {place.id: place for place in instance}

        ret = []
        for item in validated_data:
            place_id = item['id'] if 'id' in item else None
            place = None
            if place_id is not None:
                place = place_mapping.get(place_id, None)
            update_or_create_data = item.copy()
            url_kwargs = self.context['view'].kwargs
            dataset = models.DataSet.objects.get(slug=url_kwargs['dataset_slug'])
            update_or_create_data['dataset_id'] = dataset.id
            if place is None:
                ret.append(self.child.create(update_or_create_data))
            else:
                ret.append(self.child.update(place, update_or_create_data))

        return ret


class PlaceSerializer (BasePlaceSerializer,
                       serializers.HyperlinkedModelSerializer):
    id = serializers.IntegerField(required=False)
    url = PlaceIdentityField()
    dataset = DataSetRelatedField(queryset=models.DataSet.objects.all(), required=False)
    submitter = UserSerializer(required=False, allow_null=True)

    class Meta (BasePlaceSerializer.Meta):
        list_serializer_class = PlaceListSerializer
        fields = '__all__'

    def summary_to_native(self, set_name, submissions):
        url_field = SubmissionSetIdentityField()
        set_url = url_field.to_representation(
            submissions[0],
            request=self.context.get('request', None),
            format=self.context.get('format', None)
        )

        return {
            'name': set_name,
            'length': len(submissions),
            'url': set_url,
        }

    def set_to_native(self, set_name, submissions):
        serializer = SubmissionSerializer(submissions, many=True, context=self.context)
        return serializer.data

    def submitter_to_native(self, obj):
        return UserSerializer(obj.submitter, context={
            INCLUDE_PRIVATE_FIELDS_PARAM: self.is_flag_on(INCLUDE_PRIVATE_FIELDS_PARAM)
        }).data if obj.submitter else None


# Submission serializers
class BaseSubmissionSerializer (SubmittedThingSerializer, serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    attachments = AttachmentListSerializer(read_only=True, many=True)
    submitter = SimpleUserSerializer(required=False, allow_null=True)

    class Meta:
        model = models.Submission
        exclude = ('set_name',)


class SimpleSubmissionSerializer (BaseSubmissionSerializer):
    class Meta (BaseSubmissionSerializer.Meta):
        read_only_fields = ('dataset', 'place_model')


class SubmissionListSerializer(serializers.ListSerializer):
    def update(self, instance, validated_data):
        submission_mapping = {submission.id: submission for submission in instance}

        ret = []
        for item in validated_data:
            submission_id = item['id'] if 'id' in item else None
            submission = None
            if submission_id is not None:
                submission = submission_mapping.get(submission_id, None)
            update_or_create_data = item.copy()
            url_kwargs = self.context['view'].kwargs
            dataset = models.DataSet.objects.get(slug=url_kwargs['dataset_slug'])
            update_or_create_data['dataset_id'] = dataset.id
            update_or_create_data['place_model_id'] = url_kwargs['place_id']
            update_or_create_data['set_name'] = url_kwargs['submission_set_name']
            if submission is None:
                ret.append(self.child.create(update_or_create_data))
            else:
                ret.append(self.child.update(submission, update_or_create_data))

        return ret


class SubmissionSerializer (BaseSubmissionSerializer,
                            serializers.HyperlinkedModelSerializer):
    id = serializers.IntegerField(required=False)
    url = SubmissionIdentityField()
    dataset = DataSetRelatedField(queryset=models.DataSet.objects.all(), required=False)
    set = SubmissionSetRelatedField(source='*', required=False, read_only=True)
    place = PlaceRelatedField(required=False, source='place_model')
    submitter = UserSerializer(required=False, allow_null=True)

    class Meta (BaseSubmissionSerializer.Meta):
        model = models.Submission
        list_serializer_class = SubmissionListSerializer
        exclude = BaseSubmissionSerializer.Meta.exclude + ('place_model',)


class TagSerializer (serializers.ModelSerializer):
    url = TagIdentityField()

    class Meta:
        model = models.Tag
        fields = ['id', 'url', 'name', 'parent', 'color', 'is_enabled', 'children']


class PlaceTagSerializer (serializers.ModelSerializer):
    url = PlaceTagIdentityField()
    id = serializers.IntegerField(read_only=True, required=False)
    place = PlaceRelatedField()
    submitter = SimpleUserSerializer(required=False, allow_null=True)
    note = serializers.CharField(allow_blank=True)
    tag = TagRelatedField()
    created_datetime = serializers.DateTimeField(required=False)
    updated_datetime = serializers.DateTimeField(required=False)

    class Meta:
        model = models.PlaceTag
        fields = ('url', 'id', 'place', 'submitter', 'note', 'tag', 'created_datetime', 'updated_datetime')


# DataSet serializers
class BaseDataSetSerializer (EmptyModelSerializer,
                             serializers.ModelSerializer):
    class Meta:
        model = models.DataSet

    # TODO: We may need to re-implement this if want support for serving HTML
    # in the browseable api form
    # def to_representation(self, obj):
    #     obj = self.ensure_obj(obj)
    #     fields = self.get_fields()

    #     data = {
    #         'id': obj.pk,
    #         'slug': obj.slug,
    #         'display_name': obj.display_name,
    #         'owner': fields['owner'].to_representation(obj) if obj.owner_id else None,
    #     }

    #     if 'places' in fields:
    #         fields['places'].context = self.context
    #         data['places'] = fields['places'].to_representation(obj)

    #     if 'submission_sets' in fields:
    #         fields['submission_sets'].context = self.context
    #         data['submission_sets'] = fields['submission_sets'].to_representation(obj)

    #     if 'url' in fields:
    #         data['url'] = fields['url'].to_representation(obj)

    #     if 'keys' in fields: data['keys'] = fields['keys'].to_representation(obj)
    #     if 'origins' in fields: data['origins'] = fields['origins'].to_representation(obj)
    #     if 'groups' in fields: data['groups'] = fields['groups'].to_representation(obj)
    #     if 'permissions' in fields: data['permissions'] = fields['permissions'].to_representation(obj)

    #     # Construct a SortedDictWithMetaData to get the brosable API form
    #     ret = self._dict_class(data)
    #     ret.fields = self._dict_class()
    #     for field_name, field in fields.iteritems():
    #         default = getattr(field, 'get_default_value', lambda: None)()
    #         value = data.get(field_name, default)
    #         ret.fields[field_name] = self.augment_field(field, field_name, field_name, value)
    #     return ret

class SimpleDataSetSerializer (BaseDataSetSerializer, serializers.ModelSerializer):
    keys = ApiKeySerializer(many=True, read_only=False)
    origins = OriginSerializer(many=True, read_only=False)
    groups = SimpleGroupSerializer(many=True, read_only=False)
    permissions = DataSetPermissionSerializer(many=True, read_only=False)

    class Meta (BaseDataSetSerializer.Meta):
        pass


class DataSetSerializer (BaseDataSetSerializer, serializers.HyperlinkedModelSerializer):
    url = DataSetIdentityField()
    owner = UserRelatedField(read_only=True)

    places = DataSetPlaceSetSummarySerializer(source='*', read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    submission_sets = DataSetSubmissionSetSummarySerializer(source='*', read_only=True)

    load_from_url = serializers.URLField(write_only=True, required=False)

    class Meta (BaseDataSetSerializer.Meta):
        validators = []
        fields = '__all__'
        pass

    def validate_load_from_url(self, attrs, source):
        url = attrs.get(source)
        if url:
            # Verify that at least a head request on the given URL is valid.
            import requests
            head_response = requests.head(url)
            if head_response.status_code != 200:
                raise ValidationError('There was an error reading from the URL: %s' % head_response.content)
        return attrs

    # NOTE: as part of the DRF3 upgrade we're commenting this method out pending
    #       further investigation. DRF3 has replaced save_object() with other
    #       methods, but the correct refactor of the below method is unclear at
    #       the moment. Major functionality of the API does not seem to be
    #       affected by removing this method however.
    # def save_object(self, obj, **kwargs):
    #     obj.save(**kwargs)

    #     # Load any bulk dataset definition supplied
    #     if hasattr(self, 'load_url') and self.load_url:
    #         # Somehow, make sure there's not already some loading going on.
    #         # Then, do:
    #         from .tasks import load_dataset_archive
    #         load_dataset_archive.apply_async(args=(obj.id, self.load_url,))

    def to_internal_value(self, data):
        if data and 'load_from_url' in data:
            self.load_url = data.pop('load_from_url')
            if self.load_url and isinstance(self.load_url, list):
                self.load_url = unicode(self.load_url[0])
        return super(DataSetSerializer, self).to_internal_value(data)


# Action serializer
class ActionSerializer (EmptyModelSerializer, serializers.ModelSerializer):
    target_type = serializers.SerializerMethodField()
    target = serializers.SerializerMethodField()

    class Meta:
        model = models.Action
        exclude = ('thing', 'source')

    def get_target_type(self, obj):
        try:
            if obj.thing.place is not None:
                return u'place'
        except models.Place.DoesNotExist:
            pass

        return obj.thing.submission.set_name

    def get_target(self, obj):
        try:
            if obj.thing.place is not None:
                serializer = PlaceSerializer(obj.thing.place, context=self.context)
            else:
                serializer = SubmissionSerializer(obj.thing.submission, context=self.context)
        except models.Place.DoesNotExist:
            serializer = SubmissionSerializer(obj.thing.submission, context=self.context)

        return serializer.data


class FormSerializer (serializers.ModelSerializer):
    dataset = DataSetHyperlinkedField()

    class Meta:
        model = models.Form
        fields = '__all__'


class FlavorSerializer (serializers.ModelSerializer):
    forms = FormSerializer(many=True, read_only=True)

    class Meta:
        model = models.Flavor
        fields = '__all__'
