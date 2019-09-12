from __future__ import print_function
from django.core.management.base import BaseCommand
from django.core.exceptions import ValidationError
from django.db import transaction
from sa_api_v2 import models as sa_models
from sa_api_v2.serializers import (
    FlavorSerializer,
    LayerGroupSerializer,
    FormFixtureSerializer,
    FlavorFixtureSerializer,
)
from os import path
import re
import logging
import json

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class Command(BaseCommand):
    help = """
    Deletes all Flavors, Forms, LayerGroups, and their submodels. Re-creates them from our json fixtures file.
    
    This command is idempotent.
    """

    def handle(self, *args, **options):
        logger.debug('parsing json files')
        test_dir = path.dirname(__file__)
        fixture_dir = path.join(test_dir, 'fixtures')
        flavor_data_file = path.join(
            fixture_dir, 'initial_flavors_and_forms.json'
        )
        data = json.load(open(flavor_data_file))
        with transaction.atomic():
            # This should delete all forms, modules, etc.
            # delete all LayerGroups
            sa_models.LayerGroup.objects.all().delete()

            # delete all Flavors
            sa_models.Flavor.objects.all().delete()

            # delete all Forms
            sa_models.Form.objects.all().delete()
            logger.debug('models deleted!')

            # create our LayerGroup models:
            layer_group_serializer = LayerGroupSerializer(
                data=data['layer_groups'],
                many=True,
            )
            if layer_group_serializer.is_valid() is not True:
                raise ValidationError("layer_group_serializer is not valid:", layer_group_serializer.errors)

            layer_group_serializer.save()
            logger.debug('layerGroups created!')

            # create our Form models:
            form_serializer = FormFixtureSerializer(data=data['forms'], many=True)
            if form_serializer.is_valid() is not True:
                raise ValidationError("form_serializer is not valid:", form_serializer.errors)

            form_serializer.save()
            logger.debug('forms created!')

            # create our Flavor models:
            flavor_serializer = FlavorFixtureSerializer(data=data['flavor'])
            if flavor_serializer.is_valid() is not True:
                raise ValidationError("flavor_serializer is not valid:", flavor_serializer.errors)

            flavor = flavor_serializer.save()
            logger.debug('flavor created!')