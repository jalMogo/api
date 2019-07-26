from django.contrib.auth.backends import ModelBackend
from .cache import UserCache
from social_core.backends.base import BaseAuth
from social_core.exceptions import AuthException
import hmac
from base64 import b64encode, b64decode
from hashlib import sha256
import urllib
from social_core.utils import parse_qs


class CachedModelBackend (ModelBackend):
    def get_user(self, user_id):
        user = UserCache.get_instance(user_id=user_id)
        if user is None:
            user = super(CachedModelBackend, self).get_user(user_id)
            UserCache.set_instance(user, user_id=user_id)
        return user


class DiscourseSSOAuth(BaseAuth):
    name = 'discourse-hdk'
    EXTRA_DATA = [
        'username',
        'name',
        'avatar_url',
    ]

    def auth_url(self):
        returnUrl = self.redirect_uri
        nonce = str(81098579)
        payload = "nonce="+nonce+"&return_sso_url="+returnUrl
        base64Payload = b64encode(payload)
        payloadSignature = hmac.new("discourseSsoSecret", base64Payload,
                                    sha256).hexdigest()
        encodedParams = urllib.urlencode({'sso': base64Payload, 'sig': payloadSignature})
        return "https://ms-test.trydiscourse.com" + "/session/sso_provider?" + encodedParams

    def get_user_id(self, details, response):
        return response['email']

    def get_user_details(self, response):
        results = {
            'username': response.get('username'),
            'email': response.get('email'),
            'name': response.get('name'),
            'groups': response.get('groups', '').split(','),
            'is_staff': response.get('admin') == 'true' or response.get('moderator') == 'true',
            'is_superuser': response.get('admin') == 'true',
        }
        return results

    def auth_complete(self, request, *args, **kwargs):
        ssoParams = request.GET.get('sso')
        ssoSignature = request.GET.get('sig')
        paramSignature = hmac.new("discourseSsoSecret", ssoParams, sha256).hexdigest()

        if not hmac.compare_digest(str(ssoSignature), str(paramSignature)):
            raise AuthException('Could not verify discourse login')

        decodedParams = b64decode(ssoParams)
        kwargs.update({'sso': '', 'sig': '', 'backend': self, 'response': parse_qs(decodedParams)})

        return self.strategy.authenticate(*args, **kwargs)
