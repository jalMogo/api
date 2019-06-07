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
        flavor_slug = self.kwargs['flavor_slug']
        flavor_queryset = self.model\
                              .objects\
                              .filter(slug=flavor_slug)\
                              .prefetch_related(
                                  Prefetch(
                                      'forms__stages__modules',
                                      queryset=models.OrderedModule.objects.select_related(
                                          'skipstagemodule',
                                          'htmlmodule',
                                          'groupmodule',
                                          'filefield',
                                          'numberfield',
                                          'datefield',
                                          'radiofield',
                                          'textfield',
                                          'textareafield',
                                          'checkboxfield',
                                      ),
                                  ),
                              )

        obj = get_object_or_404(flavor_queryset)
        return obj
