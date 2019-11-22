from .. import cors

class CorsEnabledMixin (object):
    """
    A view that puts Access-Control headers on the response.
    """
    always_allow_options = True
    SAFE_CORS_METHODS = ('GET', 'HEAD', 'TRACE')

    def finalize_response(self, request, response, *args, **kwargs):
        response = super(CorsEnabledMixin, self).finalize_response(request, response, *args, **kwargs)

        # Allow AJAX requests from anywhere for safe methods. Though OPTIONS
        # is also a safe method in that it does not modify data on the server,
        # it is used in preflight requests to determine whether a client is
        # allowed to make unsafe requests. So, we omit OPTIONS from the safe
        # methods so that clients get an honest answer.
        if request.method in self.SAFE_CORS_METHODS:
            response['Access-Control-Allow-Origin'] = request.META.get('HTTP_ORIGIN')

        # Some views don't do client authentication, but still need to allow
        # OPTIONS requests to return favorably (like the user authentication
        # view).
        elif self.always_allow_options and request.method == 'OPTIONS':
            response['Access-Control-Allow-Origin'] = request.META.get('HTTP_ORIGIN')

        # Allow AJAX requests only from trusted domains for unsafe methods.
        elif isinstance(request.client, cors.models.Origin) or request.user.is_authenticated():
            response['Access-Control-Allow-Origin'] = request.META.get('HTTP_ORIGIN')

        else:
            response['Access-Control-Allow-Origin'] = '*'

        response['Access-Control-Allow-Methods'] = ', '.join(self.allowed_methods)
        response['Access-Control-Allow-Headers'] = request.META.get('HTTP_ACCESS_CONTROL_REQUEST_HEADERS', '')
        response['Access-Control-Allow-Credentials'] = 'true'

        return response

