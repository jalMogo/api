from .. import models
from django.db.models import Prefetch
from rest_framework import generics
from .. import serializers
from django.http import Http404


class FlavorInstanceView (generics.RetrieveAPIView):
    """
    GET
    ---
    Get a particular Flavor

    **Authentication**: Basic, session, or key auth *(optional)*

    """

    model = models.Flavor
    serializer_class = serializers.FlavorSerializer

    # TODO: rename this to slug
    # TODO: refacto this to use django's shortcuts
    def get_object_or_404(self, name):
        try:
            return self.model.objects\
                .filter(name=name)\
                .prefetch_related(
                    Prefetch(
                        'forms__modules',
                        queryset=models.FormModule.objects.select_related(
                            'radiofield',
                            # 'checkboxfield',
                        ),
                    ),
                )\
                .get()
        except self.model.DoesNotExist:
            raise Http404

    def get_object(self, queryset=None):
        flavor_slug = self.kwargs['flavor_name']
        obj = self.get_object_or_404(flavor_slug)
        return obj
