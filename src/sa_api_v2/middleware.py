import time
import json
import logging


# Request logging examples:
# https://github.com/Rhumbix/django-request-logging/blob/master/request_logging/middleware.py
# https://gist.github.com/SehgalDivij/1ca5c647c710a2c3a0397bce5ec1c1b4
def RequestResponsePayloadLogger(get_response):
    logger = logging.getLogger("ms_api.request")
    request_body_methods = ["post", "put", "patch", "delete"]

    def middleware(request):
        method = request.method.lower()
        if method not in request_body_methods:
            return get_response(request)

        body = ""
        if (
            request.META.get("CONTENT_TYPE") == "application/json"
            and request.body != b""
            and request.body is not None
        ):
            # DELETE often has an empty string as body, so we've checked for that here.
            body = json.dumps(json.loads(request.body.decode()), indent=2)

        response = get_response(request)

        response_content = ""
        if (
            response.get("Content-Type", None) == "application/json"
            and response.content is not None
            and response.content != b""
        ):
            response_content = json.dumps(
                json.loads(response.content.decode()), indent=2
            )
        logger.info(
            '"{} {} {}"\nbody: {}\nresponse: {}'.format(
                request.method,
                response.status_code,
                request.get_full_path(),
                body,
                response_content,
            )
        )
        return response

    return middleware


def RequestTimeLogger(get_response):
    # One-time configuration and initialization.
    logger = logging.getLogger("utils.request_timer")

    def middleware(request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.
        start_time = time.time()

        response = get_response(request)

        duration = time.time() - start_time

        # Log the time information
        logger.debug(
            '(%0.3f) "%s %s" %s'
            % (duration, request.method, request.get_full_path(), response.status_code)
        )

        return response

    return middleware
