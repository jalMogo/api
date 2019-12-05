from __future__ import print_function
from django.core.management.base import BaseCommand
from django.core.exceptions import ValidationError
from django.db import transaction
from sa_api_v2 import models
from sa_api_v2.serializers import (
    FlavorSerializer,
    LayerGroupSerializer,
    FormFixtureSerializer,
    FlavorFixtureSerializer,
)
from os import path
import re
import json


class Command(BaseCommand):
    help = """
    Deletes all Flavors, Forms, LayerGroups, and their submodels. Re-creates them from our json fixtures file.
    
    This command is idempotent.
    """

    def handle(self, *args, **options):
        print("parsing json files")
        curr_dir = path.dirname(__file__)
        test_fixture_dir = path.join(curr_dir, "..", "..", "tests", "fixtures")
        flavor_data_file = path.join(test_fixture_dir, "staging_flavors.json")
        data = json.load(open(flavor_data_file))
        with transaction.atomic():
            # This should delete all forms, modules, etc.
            # delete all LayerGroups
            models.LayerGroup.objects.all().delete()

            # delete all Flavors
            models.Flavor.objects.all().delete()

            # delete all Forms
            models.Form.objects.all().delete()
            print("models deleted!")

            # create our LayerGroup models:
            layer_group_serializer = LayerGroupSerializer(
                data=data["layer_groups"], many=True,
            )
            if layer_group_serializer.is_valid() is not True:
                raise ValidationError(
                    "layer_group_serializer is not valid:",
                    layer_group_serializer.errors,
                )

            layer_group_serializer.save()
            print("layerGroups created!")

            # create our Form models:
            form_serializer = FormFixtureSerializer(data=data["forms"], many=True)
            if form_serializer.is_valid() is not True:
                raise ValidationError(
                    "form_serializer is not valid:", form_serializer.errors
                )

            form_serializer.save()
            print("forms created!")

            # create our group visibility triggers:
            group_triggers = data["group_visibility_triggers"]
            models.FormFieldOption.import_group_triggers(group_triggers)
            print("group triggers created!")

            # create our stage visibility triggers:
            stage_triggers = data["stage_visibility_triggers"]
            models.FormFieldOption.import_stage_triggers(stage_triggers)
            print("stage triggers created!")

            # create our skip staging modules:
            skip_stage_modules = data["skip_stage_modules"]
            models.SkipStageModule.import_skip_stage_modules(skip_stage_modules)
            print("skip stage module relationships created!")

            # create our Flavor models:
            flavor_serializer = FlavorFixtureSerializer(
                data=data["flavors"], many=True,
            )
            if flavor_serializer.is_valid() is not True:
                raise ValidationError(
                    "flavor_serializer is not valid:", flavor_serializer.errors
                )

            flavors = flavor_serializer.save()
            print("flavors created!")
