from .. import models
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from rest_framework import generics
from .. import serializers


class FlavorInstanceView (generics.RetrieveAPIView):
    """
    GET
    ---
    Get a particular Flavor

    """

    model = models.Flavor
    serializer_class = serializers.FlavorSerializer

    def get_object(self, queryset=None):
        flavor_name = self.kwargs['flavor_name']
        flavor_queryset = self.model\
                              .objects\
                              .filter(name=flavor_name)\
                              .prefetch_related(
                                  Prefetch(
                                      'forms__modules',
                                      queryset=models.FormModule.objects.select_related(
                                          'radiofield',
                                      ),
                                  ),
                              )

        obj = get_object_or_404(flavor_queryset)
        return obj
