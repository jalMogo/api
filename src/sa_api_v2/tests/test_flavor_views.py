from django.test import TestCase
from django.test.client import RequestFactory
from django.core.urlresolvers import reverse
from django.core.cache import cache as django_cache
import json
from ..cache import cache_buffer
from ..models import (
    User,
    DataSet,
    Flavor,
    Form,
    FormStage,
    OrderedModule,
    RadioField,
    RadioOption,
)
from .test_views import APITestMixin
from ..views import FlavorInstanceView


# ./src/manage.py test -s sa_api_v2.tests.test_flavor_views:TestFlavorInstanceView
class TestFlavorInstanceView(APITestMixin, TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view = FlavorInstanceView.as_view()

        cache_buffer.reset()
        django_cache.clear()

    @classmethod
    def setUpTestData(self):

        self.owner = User.objects.create_user(
            username="aaron", password="123", email="abc@example.com"
        )
        self.dataset = DataSet.objects.create(slug="ds", owner=self.owner)

        self.flavor = Flavor.objects.create(display_name="myflavor", slug="myflavor",)

        self.form1 = Form.objects.create(
            label="form1", dataset=self.dataset, flavor=self.flavor,
        )

        self.form1_stages = [
            FormStage.objects.create(order=0, form=self.form1,),
            FormStage.objects.create(order=1, form=self.form1,),
        ]

        radio_field = RadioField.objects.create(
            key="ward", variant="dropdown", dropdown_placeholder="testing",
        )

        RadioOption.objects.create(
            label="Ward 1", value="ward_1", field=radio_field,
        )
        RadioOption.objects.create(
            label="Ward 2", value="ward_2", field=radio_field,
        )
        RadioOption.objects.create(
            label="Ward 3", value="ward_3", field=radio_field,
        )

        OrderedModule.objects.create(
            order=0, stage=self.form1_stages[0], radiofield=radio_field,
        )

        dataset2 = DataSet.objects.create(slug="ds2", owner=self.owner)
        Form.objects.create(
            label="form2", dataset=dataset2, flavor=self.flavor,
        )

        self.request_kwargs = {
            "flavor_slug": self.flavor.slug,
        }
        self.path = reverse("flavor-detail", kwargs=self.request_kwargs)

    def tearDown(self):
        User.objects.all().delete()
        DataSet.objects.all().delete()
        Flavor.objects.all().delete()
        Form.objects.all().delete()

        cache_buffer.reset()
        django_cache.clear()

    def test_GET_response(self):
        request = self.factory.get(self.path)
        response = self.view(request, **self.request_kwargs)
        data = json.loads(response.rendered_content)

        # Check that the request was successful
        self.assertStatusCode(response, 200)

        # Check that the appropriate attributes are in the properties
        self.assertIn("forms", data)
        self.assertIn("display_name", data)
        self.assertIn("slug", data)

        # Check that the data attributes have been incorporated into the
        # properties
        self.assertEqual(len(data.get("forms")), 2)
        form1 = next(form for form in data.get("forms") if form["label"] == "form1")
        self.assertEqual(len(form1.get("stages")), 2)

    def test_GET_invalid_url(self):
        # Make sure that we respond with 404 if a flavor's slug is supplied, but it doesn't match to any flavor
        request_kwargs = {
            "flavor_slug": "wrong_slug",
        }

        path = reverse("flavor-detail", kwargs=request_kwargs)
        request = self.factory.get(path)
        response = self.view(request, **request_kwargs)

        self.assertStatusCode(response, 404)
