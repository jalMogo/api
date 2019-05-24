import re
from rest_framework import serializers
from .. import models

from ..params import (
    INCLUDE_PRIVATE_FIELDS_PARAM,
)
###############################################################################
#
# User Data Strategies
# --------------------
# Shims for reading user data from various social authentication provider
# objects.
#


class DefaultUserDataStrategy (object):
    def extract_avatar_url(self, user_info):
        return ''

    def extract_full_name(self, user_info):
        return ''

    def extract_bio(self, user_info):
        return ''


class TwitterUserDataStrategy (object):
    def extract_avatar_url(self, user_info):
        try:
            url = user_info['profile_image_url_https']
        except:
            url = user_info['profile_image_url']

        url_pattern = '^(?P<path>.*?)(?:_normal|_mini|_bigger|)(?P<ext>\.[^\.]*)$'
        match = re.match(url_pattern, url)
        if match:
            return match.group('path') + '_bigger' + match.group('ext')
        else:
            return url

    def extract_full_name(self, user_info):
        return user_info['name']

    def extract_bio(self, user_info):
        return user_info['description']


class FacebookUserDataStrategy (object):
    def extract_avatar_url(self, user_info):
        url = user_info['picture']['data']['url']
        return url

    def extract_full_name(self, user_info):
        return user_info['name']

    def extract_bio(self, user_info):
        return user_info['about']


class GoogleUserDataStrategy (object):
    def extract_avatar_url(self, user_info):
        url = user_info['image']['url']
        return url

    def extract_full_name(self, user_info):
        name = user_info['name']['givenName'] + ' ' + user_info['name']['familyName']
        return name

    def extract_bio(self, user_info):
        return user_info["aboutMe"]


class ShareaboutsUserDataStrategy (object):
    """
    This strategy exists so that we can add avatars and full names to users
    that already exist in the system without them creating a Twitter or
    Facebook account.
    """
    def extract_avatar_url(self, user_info):
        return user_info.get('avatar_url', None)

    def extract_full_name(self, user_info):
        return user_info.get('full_name', None)

    def extract_bio(self, user_info):
        return user_info.get('bio', None)


# User serializers
class BaseUserSerializer (serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()
    provider_type = serializers.SerializerMethodField()
    provider_id = serializers.SerializerMethodField()

    strategies = {
        'twitter': TwitterUserDataStrategy(),
        'facebook': FacebookUserDataStrategy(),
        'google-oauth2': GoogleUserDataStrategy(),
        'shareabouts': ShareaboutsUserDataStrategy()
    }
    default_strategy = DefaultUserDataStrategy()

    class Meta:
        model = models.User
        exclude = ('first_name', 'last_name', 'email', 'password', 'is_staff',
                   'is_active', 'is_superuser', 'last_login', 'date_joined',
                   'user_permissions')

    def get_strategy(self, obj):
        for social_auth in obj.social_auth.all():
            provider = social_auth.provider
            if provider in self.strategies:
                return social_auth.extra_data, self.strategies[provider]

        return None, self.default_strategy

    def get_name(self, obj):
        user_data, strategy = self.get_strategy(obj)
        return strategy.extract_full_name(user_data)

    def get_avatar_url(self, obj):
        user_data, strategy = self.get_strategy(obj)
        return strategy.extract_avatar_url(user_data)

    def get_provider_type(self, obj):
        for social_auth in obj.social_auth.all():
            return social_auth.provider
        else:
            return ''

    def get_provider_id(self, obj):
        for social_auth in obj.social_auth.all():
            return social_auth.uid
        else:
            return None

    def to_representation(self, obj):
        if not obj:
            return {}
        data = {
            "name": self.get_name(obj),
            "avatar_url": self.get_avatar_url(obj),
            "provider_type": self.get_provider_type(obj),
            "provider_id": self.get_provider_id(obj),
            "id": obj.id,
            "username": obj.username
        }

        # provider_id contains email address for Google Oauth, so we
        # consider it a private field:
        if not self.context or not self.context.get(INCLUDE_PRIVATE_FIELDS_PARAM):
            del data["provider_id"]
        return data


class SimpleUserSerializer (BaseUserSerializer):
    """
    Generates a partial user representation, for use as submitter data in bulk
    data calls.
    """
    class Meta (BaseUserSerializer.Meta):
        exclude = BaseUserSerializer.Meta.exclude + ('groups',)


class UserSerializer (BaseUserSerializer):
    """
    Generates a partial user representation, for use as submitter data in API
    calls.
    """
    class Meta (BaseUserSerializer.Meta):
        exclude = BaseUserSerializer.Meta.exclude + ('groups',)
