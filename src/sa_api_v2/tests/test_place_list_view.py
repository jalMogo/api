from django.test import TestCase
from django.test.client import RequestFactory
from django.core.urlresolvers import reverse
from django.core.cache import cache as django_cache
import base64
import json
import mock
import csv
from io import StringIO
from ..cors.models import Origin
from ..cache import cache_buffer
from ..models import (
    User,
    DataSet,
    Place,
    Submission,
    DataIndex,
)
from .test_views import APITestMixin
from ..apikey.auth import KEY_HEADER
from ..apikey.models import ApiKey
from ..views import (
    PlaceListView,
)
from ..params import (
    INCLUDE_PRIVATE_FIELDS_PARAM,
    INCLUDE_PRIVATE_PLACES_PARAM,
)
# ./src/manage.py test -s sa_api_v2.tests.test_place_list_view:TestPlaceListView


class TestPlaceListView (APITestMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cache_buffer.reset()
        django_cache.clear()

        cls.owner = User.objects.create_user(username='aaron', password='123', email='abc@example.com')
        cls.submitter = User.objects.create_user(username='mjumbe', password='456', email='123@example.com')
        cls.dataset = DataSet.objects.create(slug='ds', owner=cls.owner)
        cls.place = Place.objects.create(
          dataset=cls.dataset,
          geometry='POINT(2 3)',
          submitter=cls.submitter,
          data=json.dumps({
            'type': 'ATM',
            'name': 'K-Mart',
            'private-secrets': 42
          }),
        )
        cls.invisible_place = Place.objects.create(
          dataset=cls.dataset,
          geometry='POINT(3 4)',
          submitter=cls.submitter,
          visible=False,
          data=json.dumps({
            'type': 'ATM',
            'name': 'Walmart',
          }),
        )
        cls.submissions = [
          Submission.objects.create(place_model=cls.place, set_name='comments', dataset=cls.dataset, data='{}'),
          Submission.objects.create(place_model=cls.place, set_name='comments', dataset=cls.dataset, data='{}'),
          Submission.objects.create(place_model=cls.place, set_name='likes', dataset=cls.dataset, data='{}'),
          Submission.objects.create(place_model=cls.place, set_name='likes', dataset=cls.dataset, data='{}'),
          Submission.objects.create(place_model=cls.place, set_name='likes', dataset=cls.dataset, data='{}'),
        ]

        cls.ds_origin = Origin.objects.create(pattern='http://openplans.github.com', dataset=cls.dataset)

        cls.private_place = Place.objects.create(
            dataset=cls.dataset,
            geometry='POINT(7 8)',
            private=True,
        )

        cls.request_kwargs = {
          'owner_username': cls.owner.username,
          'dataset_slug': cls.dataset.slug
        }

        cls.path = reverse('place-list', kwargs=cls.request_kwargs)

    def setUp(self):
        self.factory = RequestFactory()
        self.view = PlaceListView.as_view()
        self.apikey = ApiKey.objects.create(key='abc', dataset=self.dataset)

    def tearDown(self):
        User.objects.all().delete()
        DataSet.objects.all().delete()
        Place.objects.all().delete()
        Submission.objects.all().delete()
        ApiKey.objects.all().delete()

        cache_buffer.reset()
        django_cache.clear()

    def test_OPTIONS_response(self):
        request = self.factory.options(self.path)
        response = self.view(request, **self.request_kwargs)

        # Check that the request was successful
        self.assertStatusCode(response, 200)

    def test_OPTIONS_response_as_owner(self):
        request = self.factory.options(self.path)
        request.user = self.owner
        response = self.view(request, **self.request_kwargs)

        # Check that the request was successful
        self.assertStatusCode(response, 200)

    def test_GET_response(self):
        request = self.factory.get(self.path)
        response = self.view(request, **self.request_kwargs)
        data = json.loads(response.rendered_content)

        # Check that the request was successful
        self.assertStatusCode(response, 200)

        # Check that it's a feature collection
        self.assertIn('type', data)
        self.assertIn('features', data)
        self.assertIn('metadata', data)

        # Check that the metadata looks right
        self.assertIn('length', data['metadata'])
        self.assertIn('next', data['metadata'])
        self.assertIn('previous', data['metadata'])
        self.assertIn('page', data['metadata'])

        # Check that we have the right number of features
        self.assertEqual(len(data['features']), 1)

        self.assertIn('properties', data['features'][0])
        self.assertIn('geometry', data['features'][0])
        self.assertIn('type', data['features'][0])

        self.assertEqual(
            data['features'][0]['properties']['url'],
            'http://testserver' +
            reverse('place-detail', args=[self.owner.username, self.dataset.slug, self.place.id]),
        )

        # check that a JWT token is not present
        self.assertNotIn('jwt_public', data['features'][0]['properties'])

    def test_GET_response_for_multiple_specific_objects(self):
        places = []
        for _ in range(10):
            places.append(Place.objects.create(
              dataset=self.dataset,
              geometry='POINT(2 3)',
              submitter=self.submitter,
              data=json.dumps({
                'type': 'ATM',
                'name': 'K-Mart',
                'private-secrets': 42
              }),
            ))

        request_kwargs = {
          'owner_username': self.owner.username,
          'dataset_slug': self.dataset.slug,
          'pk_list': ','.join([str(p.pk) for p in places[::2]])
        }

        factory = RequestFactory()
        path = reverse('place-list', kwargs=request_kwargs)
        view = PlaceListView.as_view()

        request = factory.get(path)
        response = view(request, **request_kwargs)
        data = json.loads(response.rendered_content)

        # Check that the request was successful
        self.assertStatusCode(response, 200)

        # Check that it's a feature collection
        self.assertIn('features', data)

        # Check that we have the right number of features
        self.assertEqual(len(data['features']), 5)

        # Check that the pks are correct
        self.assertEqual(
            set([f['id'] for f in data['features']]),
            set([p.pk for p in places[::2]])
        )

    def test_GET_csv_response(self):
        request = self.factory.get(self.path + '?format=csv')
        response = self.view(request, **self.request_kwargs)

        rows = list(csv.reader(StringIO(response.rendered_content)))
        headers = rows[0]

        # Check that the request was successful
        self.assertStatusCode(response, 200)

        # Check that it's got good headers
        self.assertIn('dataset', headers)
        self.assertIn('geometry', headers)
        self.assertIn('name', headers)

        # Check that we have the right number of rows
        self.assertEqual(len(rows), 2)

    def test_GET_text_search_response(self):
        Place.objects.create(dataset=self.dataset, geometry='POINT(0 0)', data=json.dumps({'foo': 'bar', 'name': 1})),
        Place.objects.create(dataset=self.dataset, geometry='POINT(1 0)', data=json.dumps({'foo': 'bar', 'name': 2})),
        Place.objects.create(dataset=self.dataset, geometry='POINT(2 0)', data=json.dumps({'foo': 'baz', 'name': 3})),
        Place.objects.create(dataset=self.dataset, geometry='POINT(3 0)', data=json.dumps({'name': 4})),

        request = self.factory.get(self.path + '?search=bar')
        response = self.view(request, **self.request_kwargs)
        data = json.loads(response.rendered_content)

        # Check that there are ATM features
        self.assertStatusCode(response, 200)
        self.assertTrue(all([feature['properties'].get('foo') == 'bar' for feature in data['features']]))
        self.assertEqual(len(data['features']), 2)

        request = self.factory.get(self.path + '?search=ba')
        response = self.view(request, **self.request_kwargs)
        data = json.loads(response.rendered_content)

        # Check that the request was successful
        self.assertStatusCode(response, 200)
        self.assertTrue(all([feature['properties'].get('foo') in ('bar', 'baz') for feature in data['features']]))
        self.assertEqual(len(data['features']), 3)

        request = self.factory.get(self.path + '?search=bad')
        response = self.view(request, **self.request_kwargs)
        data = json.loads(response.rendered_content)

        # Check that the request was successful
        self.assertStatusCode(response, 200)
        self.assertEqual(len(data['features']), 0)

        request = self.factory.get(self.path + '?search=')
        response = self.view(request, **self.request_kwargs)
        data = json.loads(response.rendered_content)

        # Check that the request was successful
        self.assertStatusCode(response, 200)
        self.assertEqual(
            len(data['features']),
            self.dataset.places.filter(visible=True, private=False).count()
        )

    def test_GET_filtered_response(self):
        Place.objects.create(dataset=self.dataset, geometry='POINT(0 0)', data=json.dumps({'foo': 'bar', 'name': 1})),
        Place.objects.create(dataset=self.dataset, geometry='POINT(1 0)', data=json.dumps({'foo': 'bar', 'name': 2})),
        Place.objects.create(dataset=self.dataset, geometry='POINT(2 0)', data=json.dumps({'foo': 'baz', 'name': 3})),
        Place.objects.create(dataset=self.dataset, geometry='POINT(3 0)', data=json.dumps({'name': 4})),

        request = self.factory.get(self.path + '?foo=bar')
        response = self.view(request, **self.request_kwargs)
        data = json.loads(response.rendered_content)

        # Check that there are ATM features
        self.assertStatusCode(response, 200)
        self.assertTrue(all([feature['properties'].get('foo') == 'bar' for feature in data['features']]))
        self.assertEqual(len(data['features']), 2)

        request = self.factory.get(self.path + '?foo=qux')
        response = self.view(request, **self.request_kwargs)
        data = json.loads(response.rendered_content)

        # Check that the request was successful
        self.assertStatusCode(response, 200)
        self.assertEqual(len(data['features']), 0)

        request = self.factory.get(self.path + '?nonexistent=foo')
        response = self.view(request, **self.request_kwargs)
        data = json.loads(response.rendered_content)

        # Check that the request was successful
        self.assertStatusCode(response, 200)
        self.assertEqual(len(data['features']), 0)

    def test_GET_indexed_response(self):
        Place.objects.create(dataset=self.dataset, geometry='POINT(0 0)', data=json.dumps({'foo': 'bar', 'name': 1})),
        Place.objects.create(dataset=self.dataset, geometry='POINT(1 0)', data=json.dumps({'foo': 'bar', 'name': 2})),
        Place.objects.create(dataset=self.dataset, geometry='POINT(2 0)', data=json.dumps({'foo': 'baz', 'name': 3})),
        Place.objects.create(dataset=self.dataset, geometry='POINT(3 0)', data=json.dumps({'name': 4})),

        self.dataset.indexes.add(DataIndex(attr_name='foo'), bulk=False)

        from sa_api_v2.models.core import GeoSubmittedThingQuerySet
        from django.core import cache
        with mock.patch.object(GeoSubmittedThingQuerySet, 'filter_by_index') as patched_filter:
            # We patch django's caching here because otherwise we attempt to save
            # the filter mock to the cache, which requires pickleability.
            with mock.patch.object(cache, 'cache'):
                request = self.factory.get(self.path + '?foo=bar')
                self.view(request, **self.request_kwargs)
                self.assertEqual(patched_filter.call_count, 1)

    def test_GET_unindexed_response(self):
        Place.objects.create(dataset=self.dataset, geometry='POINT(0 0)', data=json.dumps({'foo': 'bar', 'name': 1})),
        Place.objects.create(dataset=self.dataset, geometry='POINT(1 0)', data=json.dumps({'foo': 'bar', 'name': 2})),
        Place.objects.create(dataset=self.dataset, geometry='POINT(2 0)', data=json.dumps({'foo': 'baz', 'name': 3})),
        Place.objects.create(dataset=self.dataset, geometry='POINT(3 0)', data=json.dumps({'name': 4})),

        self.dataset.indexes.add(DataIndex(attr_name='foo'), bulk=False)

        from sa_api_v2.models.core import GeoSubmittedThingQuerySet
        with mock.patch.object(GeoSubmittedThingQuerySet, 'filter_by_index') as patched_filter:
            request = self.factory.get(self.path + '?name=1')
            self.view(request, **self.request_kwargs)
            self.assertEqual(patched_filter.call_count, 0)

    def test_GET_paginated_response(self):
        # Create a view with pagination configuration set, for consistency
        class OverridePlaceListView (PlaceListView):
            paginate_by = 50
            paginate_by_param = 'page_size'
        self.view = OverridePlaceListView.as_view()

        for _ in range(30):
            Place.objects.create(
                dataset=self.dataset,
                geometry='POINT(0 0)',
                data=json.dumps({
                    'foo': 'bar',
                    'name': 1,
                }),
            ),
            Place.objects.create(
                dataset=self.dataset,
                geometry='POINT(1 0)',
                data=json.dumps({
                    'foo': 'bar',
                    'name': 2,
                }),
            ),
            Place.objects.create(
                dataset=self.dataset,
                geometry='POINT(2 0)',
                data=json.dumps({
                    'foo': 'baz',
                    'name': 3,
                }),
            ),
            Place.objects.create(
                dataset=self.dataset,
                geometry='POINT(3 0)',
                data=json.dumps({'name': 4}),
            ),

        # Check that we have items on the 2nd page
        request = self.factory.get(self.path + '?page=2')
        response = self.view(request, **self.request_kwargs)
        data = json.loads(response.rendered_content)

        self.assertStatusCode(response, 200)
        self.assertIn('features', data)
        self.assertEqual(len(data['features']), 50)  # default, in settings.py

        # Check that we can override the page size
        request = self.factory.get(self.path + '?page_size=3')
        response = self.view(request, **self.request_kwargs)
        data = json.loads(response.rendered_content)

        self.assertStatusCode(response, 200)
        self.assertIn('features', data)
        self.assertEqual(len(data['features']), 3)

    def test_GET_nearby_response(self):
        Place.objects.create(
            dataset=self.dataset, geometry='POINT(0 0)', data=json.dumps({'new_place': 'yes', 'name': 1})),
        Place.objects.create(
            dataset=self.dataset,
            geometry='POINT(10 0)',
            data=json.dumps({
                'new_place': 'yes',
                'name': 2,
            })
        ),
        Place.objects.create(
            dataset=self.dataset,
            geometry='POINT(20 0)',
            data=json.dumps({
                'new_place': 'yes',
                'name': 3,
            })
        ),

        Place.objects.create(
            dataset=self.dataset,
            geometry='POINT(30 0)',
            data=json.dumps({
                'new_place': 'yes',
                'name': 4,
            })
        ),

        request = self.factory.get(self.path + '?near=0,19&new_place=yes')
        response = self.view(request, **self.request_kwargs)
        data = json.loads(response.rendered_content)

        # Check that we have all the places, sorted by distance
        self.assertStatusCode(response, 200)
        self.assertEqual(len(data['features']), 4)
        self.assertEqual([feature['properties']['name'] for feature in data['features']],
                         [3, 2, 4, 1])
        self.assertIn('distance', data['features'][0]['properties'])

    def test_GET_response_with_private_data(self):
        #
        # View should not return private data normally
        #
        request = self.factory.get(self.path)
        response = self.view(request, **self.request_kwargs)
        data = json.loads(response.rendered_content)

        # Check that the request was successful
        self.assertStatusCode(response, 200)

        # Check that the private data is not in the properties
        self.assertNotIn('private-secrets', data['features'][0]['properties'])

        # --------------------------------------------------

        #
        # View should 401 when not allowed to request private data (not authenticated)
        #
        request = self.factory.get(self.path + '?' + INCLUDE_PRIVATE_FIELDS_PARAM)
        response = self.view(request, **self.request_kwargs)
        data = json.loads(response.rendered_content)

        # Check that the request was restricted
        self.assertStatusCode(response, 401)

        # --------------------------------------------------

        #
        # View should 403 when not allowed to request private data (api key)
        #
        request = self.factory.get(self.path + '?' + INCLUDE_PRIVATE_FIELDS_PARAM)
        request.META[KEY_HEADER] = self.apikey.key
        response = self.view(request, **self.request_kwargs)
        data = json.loads(response.rendered_content)

        # Check that the request was restricted
        self.assertStatusCode(response, 403)

        # --------------------------------------------------

        #
        # View should 403 when not allowed to request private data (not owner)
        #
        request = self.factory.get(self.path + '?' + INCLUDE_PRIVATE_FIELDS_PARAM)
        unauthorized_user = User.objects.create(username='new_user', password='password')
        request.user = unauthorized_user
        response = self.view(request, **self.request_kwargs)
        data = json.loads(response.rendered_content)

        # Check that the request was restricted
        self.assertStatusCode(response, 403)

        # --------------------------------------------------

        #
        # View should 403 when not allowed to request private places (not owner)
        #
        request = self.factory.get(self.path + '?' + INCLUDE_PRIVATE_PLACES_PARAM)
        request.user = unauthorized_user
        response = self.view(request, **self.request_kwargs)
        data = json.loads(response.rendered_content)

        # Check that the request was restricted
        self.assertStatusCode(response, 403)

        # --------------------------------------------------

        #
        # View should return private data when owner is logged in (Session Auth)
        #
        request = self.factory.get(self.path + '?' + INCLUDE_PRIVATE_FIELDS_PARAM)
        request.user = self.owner
        response = self.view(request, **self.request_kwargs)
        data = json.loads(response.rendered_content)

        # Check that the request was successful
        self.assertStatusCode(response, 200)

        # Check that the private data is in the properties
        self.assertIn('private-secrets', data['features'][0]['properties'])

        # --------------------------------------------------

        #
        # View should return private data when owner is logged in (Basic Auth)
        #
        request = self.factory.get(self.path + '?' + INCLUDE_PRIVATE_FIELDS_PARAM)
        request.META['HTTP_AUTHORIZATION'] = 'Basic ' + base64.b64encode(':'.join([self.owner.username, '123']))
        response = self.view(request, **self.request_kwargs)
        data = json.loads(response.rendered_content)

        # Check that the request was successful
        self.assertStatusCode(response, 200)

        # Check that the private data is in the properties
        self.assertIn('private-secrets', data['features'][0]['properties'])

    def test_GET_invalid_url(self):
        # Make sure that we respond with 404 if a slug is supplied, but for
        # the wrong dataset or owner.
        request_kwargs = {
          'owner_username': 'mischevious_owner',
          'dataset_slug': self.dataset.slug
        }

        path = reverse('place-list', kwargs=request_kwargs)
        request = self.factory.get(path)
        response = self.view(request, **request_kwargs)

        self.assertStatusCode(response, 404)

    def test_POST_response(self):
        place_data = json.dumps({
            'properties': {
                'submitter_name': 'Andy',
                'type': 'Park Bench',
                'private-secrets': 'The mayor loves this bench',
            },
            'type': 'Feature',
            'geometry': {"type": "Point", "coordinates": [-73.99, 40.75]}
        })
        start_num_places = Place.objects.all().count()

        #
        # View should 401 when trying to create when not authenticated
        #
        request = self.factory.post(self.path, data=place_data, content_type='application/json')
        response = self.view(request, **self.request_kwargs)
        self.assertStatusCode(response, 401)

        #
        # View should create the place when owner is authenticated
        #
        request = self.factory.post(self.path, data=place_data, content_type='application/json')
        request.META[KEY_HEADER] = self.apikey.key
        self.apikey.permissions.all().delete()
        self.apikey.permissions.add_permission('places', True, True, False, False)

        response = self.view(request, **self.request_kwargs)

        data = json.loads(response.rendered_content)

        # Check that the request was successful
        self.assertStatusCode(response, 201)

        #
        # The 201 response should contain a valid JWT token 
        #
        self.assertIn('jwt_public', data['properties'])
        self.assertEqual(data['properties']['jwt_public'], Place.objects.latest('id').make_jwt())
        

        # Check that the data attributes have been incorporated into the
        # properties
        self.assertEqual(data['properties'].get('type'), 'Park Bench')
        self.assertEqual(data['properties'].get('submitter_name'), 'Andy')

        self.assertIn('submitter', data['properties'])
        self.assertIsNone(data['properties']['submitter'])

        # visible should be true by default
        self.assertTrue(data['properties'].get('visible'))

        # Check that geometry exists
        self.assertIn('geometry', data)

        # private-secrets is not special, but is private, so should not come
        # back down
        self.assertNotIn('private-secrets', data['properties'])

        # Check that we actually created a place
        final_num_places = Place.objects.all().count()
        self.assertEqual(final_num_places, start_num_places + 1)

        #
        # View should 401 when api key does not have enough permission
        #
        request = self.factory.post(self.path, data=place_data, content_type='application/json')
        request.META[KEY_HEADER] = self.apikey.key
        self.apikey.permissions.all().delete()
        self.apikey.permissions.add_permission('places', False, True, False, False)
        self.apikey.permissions.add_permission('comments', True, True, False, False)

        response = self.view(request, **self.request_kwargs)
        self.assertStatusCode(response, 403)

    def test_GET_response_with_private_place(self):
        #
        # View should not return private places normally
        #
        request = self.factory.get(self.path)
        response = self.view(request, **self.request_kwargs)
        data = json.loads(response.rendered_content)

        # Check that the request was successful
        self.assertStatusCode(response, 200)

        # Check that the private data is not in the properties
        # self.assertNotIn('private-secrets', data['features'][0]['properties'])
        self.assertEqual(data['features'][0]['id'], self.place.id)

        #
        # View should return private places when user is owner (Session Auth)
        #
        request = self.factory.get(self.path + '?' + INCLUDE_PRIVATE_PLACES_PARAM)
        request.user = self.owner
        response = self.view(request, **self.request_kwargs)
        data = json.loads(response.rendered_content)

        # Check that the request was successful
        self.assertStatusCode(response, 200)

        # Check that the private place
        private_place = next((x for x in data['features'] if x['id'] == self.private_place.id), None)
        self.assertIsNotNone(private_place)

    def test_PUT_creates_in_bulk(self):
        # Create a couple bogus places so that we can be sure we're not
        # inadvertantly deleting them
        Place.objects.create(dataset=self.dataset, geometry='POINT(0 0)')
        Place.objects.create(dataset=self.dataset, geometry='POINT(0 0)')

        # Make some data that will update the place, and create another
        place_data = json.dumps([
            {
                'properties': {
                    'submitter_name': 'Andy',
                    'type': 'Park Bench',
                    'private-secrets': 'The mayor loves this bench',
                },
                'type': 'Feature',
                'geometry': {"type": "Point", "coordinates": [-73.99, 40.75]}
            },
            {
                'properties': {
                    'submitter_name': 'Mjumbe',
                    'type': 'Street Light',
                    'private-secrets': 'Helps with street safety, but not as much as storefronts do.',
                },
                'type': 'Feature',
                'geometry': {"type": "Point", "coordinates": [-73.98, 40.76]}
            },
        ])
        start_num_places = Place.objects.all().count()

        #
        # View should 401 when trying to update when not authenticated
        #
        request = self.factory.put(self.path, data=place_data, content_type='application/json')
        response = self.view(request, **self.request_kwargs)
        self.assertStatusCode(response, 401)

        #
        # View should update the places when owner is authenticated
        #
        request = self.factory.put(self.path, data=place_data, content_type='application/json')
        request.META[KEY_HEADER] = self.apikey.key

        response = self.view(request, **self.request_kwargs)

        data_list = json.loads(response.rendered_content)['features']

        # Check that the request was successful
        self.assertStatusCode(response, 200)
        self.assertEqual(len(data_list), 2)

        # Check that we actually created the places
        final_num_places = Place.objects.all().count()
        self.assertEqual(final_num_places, start_num_places + 2)

    def test_PUT_response_creates_and_updates_at_once(self):
        # Create a couple bogus places so that we can be sure we're not
        # inadvertantly deleting them
        Place.objects.create(dataset=self.dataset, geometry='POINT(0 0)')
        Place.objects.create(dataset=self.dataset, geometry='POINT(0 0)')

        # Create a place
        place = Place.objects.create(dataset=self.dataset, geometry='POINT(0 0)')

        # Make some data that will update the place, and create another
        place_data = json.dumps([
            {
                'properties': {
                    'submitter_name': 'Andy',
                    'type': 'Park Bench',
                    'private-secrets': 'The mayor loves this bench',
                    'id': place.id,
                    'url': 'http://testserver/api/v2/aaron/datasets/ds/places/%s' % (place.id,)
                },
                'type': 'Feature',
                'id': place.id,
                'geometry': {"type": "Point", "coordinates": [-73.99, 40.75]}
            },
            {
                'properties': {
                    'submitter_name': 'Mjumbe',
                    'type': 'Street Light',
                    'private-secrets': 'Helps with street safety, but not as much as storefronts do.',
                },
                'type': 'Feature',
                'geometry': {"type": "Point", "coordinates": [-73.98, 40.76]}
            },
        ])
        start_num_places = Place.objects.all().count()

        #
        # View should 401 when trying to update when not authenticated
        #
        request = self.factory.put(self.path, data=place_data, content_type='application/json')
        response = self.view(request, **self.request_kwargs)
        self.assertStatusCode(response, 401)

        #
        # View should update the places when owner is authenticated
        #
        request = self.factory.put(self.path, data=place_data, content_type='application/json')
        request.META[KEY_HEADER] = self.apikey.key

        response = self.view(request, **self.request_kwargs)

        data_list = json.loads(response.rendered_content)['features']

        # Check that the request was successful
        self.assertStatusCode(response, 200)
        self.assertEqual(len(data_list), 2)

        # Check the updated item
        data = [item for item in data_list if item['id'] == place.id][0]

        # Check that the data attributes have been incorporated into the
        # properties
        self.assertEqual(data['properties'].get('type'), 'Park Bench')
        self.assertEqual(data['properties'].get('submitter_name'), 'Andy')

        self.assertIn('submitter', data['properties'])
        self.assertIsNone(data['properties']['submitter'])

        # visible should be true by default
        self.assertTrue(data['properties'].get('visible'))

        # Check that geometry exists
        self.assertIn('geometry', data)

        # private-secrets is not special, but is private, so should not come
        # back down
        self.assertNotIn('private-secrets', data['properties'])

        # Check that we actually created a place
        final_num_places = Place.objects.all().count()
        self.assertEqual(final_num_places, start_num_places + 1)

        # Check the created item
        data = [item for item in data_list if item['id'] != place.id][0]

        # Check that the data attributes have been incorporated into the
        # properties
        self.assertEqual(data['properties'].get('type'), 'Street Light')
        self.assertEqual(data['properties'].get('submitter_name'), 'Mjumbe')

        # Check that we actually created the places
        final_num_places = Place.objects.all().count()
        self.assertEqual(final_num_places, start_num_places + 1)

    def test_POST_response_with_submitter(self):
        place_data = json.dumps({
            'properties': {
                'type': 'Park Bench',
                'private-secrets': 'The mayor loves this bench',
            },
            'type': 'Feature',
            'geometry': {"type": "Point", "coordinates": [-73.99, 40.75]}
        })
        start_num_places = Place.objects.all().count()

        #
        # View should create the place when owner is authenticated
        #
        request = self.factory.post(self.path, data=place_data, content_type='application/json')
        request.META[KEY_HEADER] = self.apikey.key
        request.user = self.submitter
        request.csrf_processing_done = True

        response = self.view(request, **self.request_kwargs)

        data = json.loads(response.rendered_content)

        # Check that the request was successful
        self.assertStatusCode(response, 201)

        # Check that the data attributes have been incorporated into the
        # properties
        self.assertEqual(data['properties'].get('type'), 'Park Bench')

        self.assertIn('submitter', data['properties'])
        self.assertIsNotNone(data['properties']['submitter'])
        self.assertEqual(data['properties']['submitter']['id'], self.submitter.id)

        # visible should be true by default
        self.assertTrue(data['properties'].get('visible'))

        # Check that geometry exists
        self.assertIn('geometry', data)

        # private-secrets is not special, but is private, so should not come
        # back down
        self.assertNotIn('private-secrets', data['properties'])

        # Check that we actually created a place
        final_num_places = Place.objects.all().count()
        self.assertEqual(final_num_places, start_num_places + 1)

    def test_GET_response_with_invisible_data(self):
        #
        # View should not return invisible data normally
        #
        request = self.factory.get(self.path)
        response = self.view(request, **self.request_kwargs)
        data = json.loads(response.rendered_content)

        # Check that the request was successful
        self.assertStatusCode(response, 200)
        self.assertEqual(len(data['features']), 1)

        # --------------------------------------------------

        #
        # View should 401 when not allowed to request private data (not authenticated)
        #
        request = self.factory.get(self.path + '?include_invisible')
        response = self.view(request, **self.request_kwargs)
        data = json.loads(response.rendered_content)

        # Check that the request was restricted
        self.assertStatusCode(response, 401)

        # --------------------------------------------------

        #
        # View should 403 when not allowed to request private data (api key)
        #
        request = self.factory.get(self.path + '?include_invisible')
        request.META[KEY_HEADER] = self.apikey.key
        response = self.view(request, **self.request_kwargs)
        data = json.loads(response.rendered_content)

        # Check that the request was restricted
        self.assertStatusCode(response, 403)

        # --------------------------------------------------

        #
        # View should 403 when not allowed to request private data (not owner)
        #
        request = self.factory.get(self.path + '?include_invisible')
        request.user = User.objects.create(username='new_user', password='password')
        response = self.view(request, **self.request_kwargs)
        data = json.loads(response.rendered_content)

        # Check that the request was restricted
        self.assertStatusCode(response, 403)

        # --------------------------------------------------

        #
        # View should return private data when allowed (api key)
        #
        request = self.factory.get(self.path + '?include_invisible')
        self.apikey.permissions.add_permission(
            '*',
            can_create=False,
            can_retrieve=True,
            can_update=False,
            can_destroy=False,
            can_access_protected=True)
        request.META[KEY_HEADER] = self.apikey.key
        response = self.view(request, **self.request_kwargs)
        data = json.loads(response.rendered_content)

        # Check that the request was restricted
        self.assertStatusCode(response, 200)

        # --------------------------------------------------

        #
        # View should return private data when owner is logged in (Session Auth)
        #
        request = self.factory.get(self.path + '?include_invisible')
        request.user = self.owner
        response = self.view(request, **self.request_kwargs)
        data = json.loads(response.rendered_content)

        # Check that the request was successful
        self.assertStatusCode(response, 200)
        self.assertEqual(len(data['features']), 2)

        # --------------------------------------------------

        #
        # View should return private data when owner is logged in (Basic Auth)
        #
        request = self.factory.get(self.path + '?include_invisible')
        request.META['HTTP_AUTHORIZATION'] = 'Basic ' + base64.b64encode(':'.join([self.owner.username, '123']))
        response = self.view(request, **self.request_kwargs)
        data = json.loads(response.rendered_content)

        # Check that the request was successful
        self.assertStatusCode(response, 200)
        self.assertEqual(len(data['features']), 2)

    def test_POST_invisible_private_response(self):
        place_data = json.dumps({
            'properties': {
                'submitter_name': 'Andy',
                'type': 'Park Bench',
                'private-secrets': 'The mayor loves this bench',
                'visible': False,
                'private': True
            },
            'type': 'Feature',
            'geometry': {"type": "Point", "coordinates": [-73.99, 40.75]},
        })

        request = self.factory.post(self.path, data=place_data, content_type='application/json')
        request.META[KEY_HEADER] = self.apikey.key
        response = self.view(request, **self.request_kwargs)
        data = json.loads(response.rendered_content)

        # Check that the request was successful
        self.assertStatusCode(response, 201)

        # Check that visible is false
        self.assertEqual(data.get('properties').get('visible'), False)
        self.assertEqual(data.get('properties').get('private'), True)

        # Check that the private place doesn't generate an action:
        place = Place.objects.get(id=data.get('id'))
        self.assertEqual(place.actions.count(), 0)

    def test_POST_response_like_XDomainRequest(self):
        place_data = json.dumps({
            'properties': {
                'submitter_name': 'Andy',
                'type': 'Park Bench',
                'private-secrets': 'The mayor loves this bench',
            },
            'type': 'Feature',
            'geometry': {"type": "Point", "coordinates": [-73.99, 40.75]}
        })

        #
        # View should create the place when origin is supplied, even without a
        # content type.
        #
        request = self.factory.post(self.path, data=place_data, content_type='')
        request.META['HTTP_ORIGIN'] = self.ds_origin.pattern
        response = self.view(request, **self.request_kwargs)

        # Check that the request was successful
        self.assertStatusCode(response, 201)

    def test_model_update_clears_GET_cache_for_multiple_specific_objects(self):
        places = []
        for _ in range(10):
            places.append(Place.objects.create(
              dataset=self.dataset,
              geometry='POINT(2 3)',
              submitter=self.submitter,
              data=json.dumps({
                'type': 'ATM',
                'name': 'K-Mart',
                'private-secrets': 42
              }),
            ))
        cache_buffer.flush()

        request_kwargs = {
          'owner_username': self.owner.username,
          'dataset_slug': self.dataset.slug,
          'pk_list': ','.join([str(p.pk) for p in places[::2]])
        }

        factory = RequestFactory()
        path = reverse('place-list', kwargs=request_kwargs)
        view = PlaceListView.as_view()

        # First call should run queries
        #
        # ---- Check (and cache) permissions
        #
        # - SELECT dataset
        # - SELECT dataset permissions
        # - SELECT keys
        # - SELECT key permissions
        # - SELECT origins
        # - SELECT origin permissions
        #
        # ---- Load the data
        #
        # SELECT COUNT(*) FROM place WHERE (id IN <place ids> AND visible = true AND dataset )
        # SELECT * FROM place INNER JOIN ds ON ( dataset ) LEFT OUTER JOIN user ON ( submitter ) INNER JOIN user ON ( owner ) WHERE (id IN <place ids> AND visible = true AND dataset ) LIMIT 5
        # SELECT * FROM social WHERE user_id IN <place submitters>
        # SELECT * FROM group for users <place submitters>
        # SELECT * FROM sset WHERE place_id IN <place ids>
        # SELECT * FROM att WHERE thing_id IN <place ids>
        #
        request = factory.get(path)

        # TODO: https://github.com/mapseed/api/issues/137
        with self.assertNumQueries(22):
            view(request, **request_kwargs)

        # Second call should hardly hit the database
        request = factory.get(path)
        with self.assertNumQueries(0):
            view(request, **request_kwargs)

        # After we modify one of the places, cache should be invalidated
        places[0].data = json.dumps({
            'type': 'ATM',
            'name': 'K-Mart',
            'private-secrets': 43
        })
        places[0].save()
        cache_buffer.flush()

        # Run same queries as above (except for permissions)
        request = factory.get(path)

        # TODO: https://github.com/mapseed/api/issues/137
        with self.assertNumQueries(16):
            view(request, **request_kwargs)
