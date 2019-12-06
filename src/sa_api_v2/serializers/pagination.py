from rest_framework import pagination
from rest_framework.response import Response

###############################################################################
#
# Pagination Serializers
# ----------------------
#


class MetadataPagination(pagination.PageNumberPagination):
    page_size_query_param = "page_size"
    page_size = 50

    def get_paginated_response(self, data):
        return Response(
            {
                "metadata": {
                    "length": self.page.paginator.count,
                    "page": self.page.number,
                    "next": self.get_next_link(),
                    "previous": self.get_previous_link(),
                },
                "results": data,
            }
        )


class FeatureCollectionPagination(pagination.PageNumberPagination):
    page_size_query_param = "page_size"
    page_size = 50

    def get_paginated_response(self, data):
        return Response(
            {
                "metadata": {
                    "length": self.page.paginator.count,
                    "page": self.page.number,
                    "next": self.get_next_link(),
                    "previous": self.get_previous_link(),
                },
                "type": "FeatureCollection",
                "features": data,
            }
        )
