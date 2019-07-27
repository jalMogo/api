from django.contrib.auth.backends import ModelBackend
from .cache import UserCache
from social_core.backends.base import BaseAuth
from social_core.exceptions import (AuthException, AuthTokenError)
import hmac
from base64 import b64encode, b64decode
from hashlib import sha256
import urllib
from social_core.utils import parse_qs
import time


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
    SERVER_URL = "https://ms-test.trydiscourse.com"

    def auth_url(self):
        """Return redirect url"""
        returnUrl = self.redirect_uri
        nonce = self.strategy.random_string(64)
        self.add_nonce(nonce)

        payload = "nonce="+nonce+"&return_sso_url="+returnUrl
        base64Payload = b64encode(payload)
        payloadSignature = hmac.new(self.setting("SOCIAL_AUTH_DISCOURSE_SSO_SECRET"), base64Payload,
                                    sha256).hexdigest()
        encodedParams = urllib.urlencode({'sso': base64Payload, 'sig': payloadSignature})
        return self.SERVER_URL + "/session/sso_provider?" + encodedParams

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

    def add_nonce(self, nonce):
        self.strategy.storage.nonce.use(self.SERVER_URL, time.time(), nonce)

    def get_nonce(self, nonce):
        try:
            return self.strategy.storage.nonce.objects.get(
                server_url=self.SERVER_URL,
                salt=nonce
            )
        except IndexError:
            pass

    def auth_complete(self, request, *args, **kwargs):
        ssoParams = request.GET.get('sso')
        ssoSignature = request.GET.get('sig')
        paramSignature = hmac.new(self.setting("SOCIAL_AUTH_DISCOURSE_SSO_SECRET"), ssoParams, sha256).hexdigest()

        if not hmac.compare_digest(str(ssoSignature), str(paramSignature)):
            raise AuthException('Could not verify discourse login')

        decodedParams = b64decode(ssoParams)

        # Validate the nonce to ensure the request was not modified
        response = parse_qs(decodedParams)
        nonce_obj = self.get_nonce(response.get('nonce'))
        if nonce_obj:
            nonce_obj.delete()
        else:
            raise AuthTokenError(self, 'Incorrect id_token: nonce')

        kwargs.update({'sso': '', 'sig': '', 'backend': self, 'response': response})

        return self.strategy.authenticate(*args, **kwargs)
