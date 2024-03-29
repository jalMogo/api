from django.conf import settings

# Querystring Parameter Names
# Places marked as 'invisible':
INCLUDE_INVISIBLE_PARAM = "include_invisible"
# Places marked as 'private':
INCLUDE_PRIVATE_PLACES_PARAM = "include_private_places"
# Protected Place fields and User fields:
INCLUDE_PRIVATE_FIELDS_PARAM = "include_private_fields"
INCLUDE_SUBMISSIONS_PARAM = "include_submissions"
INCLUDE_TAGS_PARAM = "include_tags"
NEAR_PARAM = "near"
DISTANCE_PARAM = "distance_lt"
BBOX_PARAM = "bounds"
FORMAT_PARAM = "format"
TEXTSEARCH_PARAM = "search"
JWT_PARAM = "token"

PAGE_PARAM = "page"
PAGE_SIZE_PARAM = lambda: getattr(settings, "REST_FRAMEWORK", {}).get(
    "PAGINATE_BY_PARAM"
)
CALLBACK_PARAM = lambda view: (
    "callback"
    if view.get_content_negotiator()
    .select_renderer(view.request, view.get_renderers(), view.format_kwarg)[0]
    .format
    == "jsonp"
    else None
)
