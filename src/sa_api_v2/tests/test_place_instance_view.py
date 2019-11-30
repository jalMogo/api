from django.test import TestCase
from django.test.client import RequestFactory
from django.core.urlresolvers import reverse
from django.core.cache import cache as django_cache
from django.core.files import File
from django.contrib.auth.models import AnonymousUser
from django.conf import settings
import base64
import json
import jwt
from io import StringIO
from ..cors.models import Origin
from ..cache import cache_buffer
from ..models import (
    User,
    DataSet,
    Place,
    Submission,
    Attachment,
    Group,
    GroupPermission,
)
from .test_views import APITestMixin
from ..apikey.auth import KEY_HEADER
from ..apikey.models import ApiKey
from ..views import (
    PlaceInstanceView,
)
from ..params import (
    INCLUDE_PRIVATE_FIELDS_PARAM,
    INCLUDE_PRIVATE_PLACES_PARAM,
    JWT_PARAM
)
# ./src/manage.py test -s sa_api_v2.tests.test_place_instance_view:TestPlaceInstanceView


class TestPlaceInstanceView (APITestMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
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
        f = StringIO('This is test content in a "file"')
        f.name = 'myfile.txt'
        f.size = 20
        cls.attachments = Attachment.objects.create(
            file=File(f, 'myfile.txt'), name='my_file_name', thing=cls.place)
        cls.submissions = [
            Submission.objects.create(
                place_model=cls.place,
                set_name='comments',
                dataset=cls.dataset, data='{"foo": 3}',
            ),
            Submission.objects.create(
                place_model=cls.place,
                set_name='comments',
                dataset=cls.dataset,
                data='{"foo": 3}',
            ),
            Submission.objects.create(
                place_model=cls.place,
                set_name='comments',
                dataset=cls.dataset,
                data='{"foo": 3}',
                visible=False,
            ),
            Submission.objects.create(
                place_model=cls.place,
                set_name='likes',
                dataset=cls.dataset,
                data='{"bar": 3}',
            ),
            Submission.objects.create(
                place_model=cls.place,
                set_name='likes',
                dataset=cls.dataset,
                data='{"bar": 3}',
            ),
            Submission.objects.create(
                place_model=cls.place,
                set_name='likes',
                dataset=cls.dataset,
                data='{"bar": 3}',
            ),
            Submission.objects.create(
                place_model=cls.place,
                set_name='likes',
                dataset=cls.dataset,
                data='{"bar": 3}',
                visible=False,
            ),
        ]

        cls.invisible_place = Place.objects.create(
          dataset=cls.dataset,
          geometry='POINT(3 4)',
          submitter=cls.submitter,
          visible=False,
          data=json.dumps({
            'type': 'ATM',
            'name': 'K-Mart',
          }),
        )

        cls.apikey = ApiKey.objects.create(key='abc', dataset=cls.dataset)
        cls.ds_origin = Origin.objects.create(pattern='http://openplans.github.com', dataset=cls.dataset)

        cls.request_kwargs = {
          'owner_username': cls.owner.username,
          'dataset_slug': cls.dataset.slug,
          'place_id': cls.place.id
        }

        cls.invisible_request_kwargs = {
          'owner_username': cls.owner.username,
          'dataset_slug': cls.dataset.slug,
          'place_id': cls.invisible_place.id
        }

        cls.path = reverse('place-detail', kwargs=cls.request_kwargs)
        cls.invisible_path = reverse('place-detail', kwargs=cls.invisible_request_kwargs)

    def setUp(self):
        self.factory = RequestFactory()
        self.view = PlaceInstanceView.as_view()
        cache_buffer.reset()
        django_cache.clear()

    def tearDown(self):
        User.objects.all().delete()
        DataSet.objects.all().delete()
        Place.objects.all().delete()
        Submission.objects.all().delete()
        ApiKey.objects.all().delete()

        cache_buffer.reset()
        django_cache.clear()

    def test_GET_response_with_invalid_JWT_payload(self):
        """
        View should 401 when a GET request is made with a valid JWT whose
        payload does not match the requested Place.
        """
        valid_jwt_public_incorrect_payload = jwt.encode({ 'place_id': 99999999 }, settings.JWT_SECRET, algorithm='HS256').decode()
        request = self.factory.get(
            f"{self.path}?{INCLUDE_PRIVATE_FIELDS_PARAM}&{INCLUDE_PRIVATE_PLACES_PARAM}&{JWT_PARAM}={valid_jwt_public_incorrect_payload}"
        )
        response = self.view(request, **self.request_kwargs)
        data = json.loads(response.rendered_content)

        # Check that the request was restricted
        self.assertStatusCode(response, 401)

    def test_GET_response_with_invalid_JWT_secret(self):
        """
        View should 401 when a GET request is made with an invalid JWT, signed with the wrong secret.
        """
        invalid_jwt_public = jwt.encode({ 'place_id': self.place.id }, 'invalid-secret-oh-no', algorithm='HS256').decode()
        request = self.factory.get(
            f"{self.path}?{INCLUDE_PRIVATE_FIELDS_PARAM}&{INCLUDE_PRIVATE_PLACES_PARAM}&{JWT_PARAM}={ invalid_jwt_public}"
        )
        response = self.view(request, **self.request_kwargs)
        data = json.loads(response.rendered_content)

        # Check that the request was restricted
        self.assertStatusCode(response, 401)

    def test_GET_response_with_valid_JWT(self):
        """
        # View should return private data when a GET request is made with a valid JWT.
        """
        valid_jwt_public_correct_payload = self.place.make_jwt().decode()
        request = self.factory.get(
            f"{self.path}?{INCLUDE_PRIVATE_FIELDS_PARAM}&{INCLUDE_PRIVATE_PLACES_PARAM}&{JWT_PARAM}={valid_jwt_public_correct_payload}" 
            )
        response = self.view(request, **self.request_kwargs)
        data = json.loads(response.rendered_content)

        # Check that the request was successful
        self.assertStatusCode(response, 200)

        # Check that the private data is in the properties
        self.assertIn('private-secrets', data['properties'])

    def test_OPTIONS_response(self):
        request = self.factory.options(self.path)
        response = self.view(request, **self.request_kwargs)

        # Check that the request was successful
        self.assertStatusCode(response, 200)

    def test_GET_response(self):
        request = self.factory.get(self.path)
        response = self.view(request, **self.request_kwargs)
        data = json.loads(response.rendered_content)

        # Check that the request was successful
        self.assertStatusCode(response, 200)

        # Check that it's a feature
        self.assertIn('type', data)
        self.assertIn('geometry', data)
        self.assertIn('properties', data)
        self.assertIn('id', data)

        # Check that data attribute is not present
        self.assertNotIn('data', data['properties'])

        # Check that the data attributes have been incorporated into the
        # properties
        self.assertEqual(data['properties'].get('type'), 'ATM')
        self.assertEqual(data['properties'].get('name'), 'K-Mart')

        # Check that the geometry attribute looks right
        self.assertIsInstance(data['geometry'], dict)
        self.assertIn('type', data['geometry'])
        self.assertIn('coordinates', data['geometry'])

        # Check that the appropriate attributes are in the properties
        self.assertIn('url', data['properties'])
        self.assertIn('dataset', data['properties'])
        self.assertIn('attachments', data['properties'])
        self.assertIn('submission_sets', data['properties'])
        self.assertIn('submitter', data['properties'])

        self.assertIn('provider_type', data.get('properties').get('submitter'))
        self.assertNotIn('provider_id', data.get('properties').get('submitter'))

        # Check that the URL is right
        self.assertEqual(
            data['properties']['url'],
            'http://testserver' +
            reverse(
                'place-detail',
                args=[self.owner.username, self.dataset.slug, self.place.id]
            )
        )

        # Check that the submission sets look right
        self.assertEqual(len(data['properties']['submission_sets']), 2)
        self.assertIn('comments', list(data['properties']['submission_sets'].keys()))
        self.assertIn('likes', list(data['properties']['submission_sets'].keys()))
        self.assertNotIn('applause', list(data['properties']['submission_sets'].keys()))

        # Check that the submitter looks right
        self.assertIsNotNone(data['properties']['submitter'])
        self.assertIn('id', data['properties']['submitter'])
        self.assertIn('name', data['properties']['submitter'])
        self.assertIn('avatar_url', data['properties']['submitter'])

        # Check that only the visible comments were counted
        self.assertEqual(data['properties']['submission_sets']['comments']['length'], 2)

        # --------------------------------------------------

        #
        # View should include submissions when requested
        #
        request = self.factory.get(self.path + '?include_submissions')
        response = self.view(request, **self.request_kwargs)
        data = json.loads(response.rendered_content)

        # Check that the submission_sets are in the properties
        self.assertIn('submission_sets', data['properties'])

        # Check that the submission sets look right
        comments_set = data['properties']['submission_sets'].get('comments')
        self.assertIsInstance(comments_set, list)
        self.assertEqual(len(comments_set), 2)
        self.assertIn('foo', comments_set[0])
        self.assertTrue(all([comment['visible'] for comment in comments_set]))

        # --------------------------------------------------

        #
        # View should not include submissions when explicitly false
        #
        request = self.factory.get(self.path + '?include_submissions=false')
        response = self.view(request, **self.request_kwargs)
        data = json.loads(response.rendered_content)

        # Check that the submission_sets are in the properties
        self.assertIn('submission_sets', data['properties'])

        # Check that the submission sets look right
        comments_set = data['properties']['submission_sets'].get('comments')
        self.assertIsInstance(comments_set, dict)
        self.assertIn('length', comments_set)
        self.assertEqual(comments_set['length'], 2)

        # --------------------------------------------------

        #
        # View should include invisible submissions when requested and allowed
        #

        # - - - - - Not logged in  - - - - - - - - - - - - -
        request = self.factory.get(self.path + '?include_submissions&include_invisible')
        response = self.view(request, **self.request_kwargs)
        data = json.loads(response.rendered_content)

        self.assertStatusCode(response, 401)

        # - - - - - Authenticated as owner - - - - - - - - -
        request = self.factory.get(self.path + '?include_submissions&include_invisible')
        request.user = self.owner
        response = self.view(request, **self.request_kwargs)
        data = json.loads(response.rendered_content)

        # Check that the submission_sets are in the properties
        self.assertIn('submission_sets', data['properties'])

        # Check that the invisible submissions are included
        comments_set = data['properties']['submission_sets'].get('comments')
        self.assertEqual(len(comments_set), 3)
        self.assertTrue(not all([comment['visible'] for comment in comments_set]))

    def test_GET_response_with_attachment(self):
        request = self.factory.get(self.path)
        response = self.view(request, **self.request_kwargs)
        data = json.loads(response.rendered_content)

        # Check that the attachment looks right
        self.assertIn('file', data['properties']['attachments'][0])
        self.assertIn('name', data['properties']['attachments'][0])

        self.assertEqual(len(data['properties']['attachments']), 1)
        self.assertEqual(data['properties']['attachments'][0]['name'], 'my_file_name')

        a = self.place.attachments.all()[0]
        self.assertEqual(a.file.read(), b'This is test content in a "file"')

    def test_new_attachment_clears_GET_cache(self):
        request = self.factory.get(self.path)
        response = self.view(request, **self.request_kwargs)
        initial_data = json.loads(response.rendered_content)

        # Create a dummy view instance so that we can call get_cache_key
        temp_view = PlaceInstanceView()
        temp_view.request = request

        # Check that the response is cached
        cache_key = temp_view.get_cache_key(request)
        self.assertIsNotNone(django_cache.get(cache_key))

        # Save another attachment
        Attachment.objects.create(file=None, name='my_new_file_name', thing=self.place)
        cache_buffer.flush()

        # Check that the response cache was cleared
        cache_key = temp_view.get_cache_key(request)
        self.assertIsNone(django_cache.get(cache_key))

        # Check that the we get a different response
        response = self.view(request, **self.request_kwargs)
        new_data = json.loads(response.rendered_content)
        self.assertNotEqual(initial_data, new_data)

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
        self.assertNotIn('private-secrets', data['properties'])

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
        # View should 403 when not allowed to request private data (origin)
        #
        request = self.factory.get(self.path + '?' + INCLUDE_PRIVATE_FIELDS_PARAM)
        request.META['HTTP_ORIGIN'] = self.ds_origin.pattern
        response = self.view(request, **self.request_kwargs)
        data = json.loads(response.rendered_content)

        # Check that the request was restricted
        self.assertStatusCode(response, 403)

        # --------------------------------------------------

        #
        # View should 403 when not allowed to request private data (not owner)
        #
        request = self.factory.get(self.path + '?' + INCLUDE_PRIVATE_FIELDS_PARAM)
        request.user = User.objects.create(username='new_user', password='password')
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
        self.assertIn('provider_id', data.get('properties').get('submitter'))

        self.assertIn('private-secrets', data['properties'])

        # --------------------------------------------------

        #
        # View should return private data when owner is logged in (Basic Auth)
        #
        request = self.factory.get(self.path + '?' + INCLUDE_PRIVATE_FIELDS_PARAM)
        request.META['HTTP_AUTHORIZATION'] = b'Basic ' + base64.b64encode(b':'.join([self.owner.username.encode('utf-8'), b'123']))
        response = self.view(request, **self.request_kwargs)
        data = json.loads(response.rendered_content)

        # Check that the request was successful
        self.assertStatusCode(response, 200)

        # Check that the private data is in the properties
        self.assertIn('private-secrets', data['properties'])

    def test_GET_response_with_invisible_data(self):
        #
        # View should not return invisible data normally
        #
        request = self.factory.get(self.invisible_path)
        response = self.view(request, **self.invisible_request_kwargs)
        data = json.loads(response.rendered_content)

        # Check that the request was successful
        self.assertStatusCode(response, 400)

        # --------------------------------------------------

        #
        # View should 401 when not allowed to request private data (not authenticated)
        #
        request = self.factory.get(self.invisible_path + '?include_invisible')
        response = self.view(request, **self.invisible_request_kwargs)
        data = json.loads(response.rendered_content)

        # Check that the request was restricted
        self.assertStatusCode(response, 401)

        # --------------------------------------------------

        #
        # View should 403 when not allowed to request private data (api key)
        #
        request = self.factory.get(self.invisible_path + '?include_invisible')
        request.META[KEY_HEADER] = self.apikey.key
        response = self.view(request, **self.invisible_request_kwargs)
        data = json.loads(response.rendered_content)

        # Check that the request was restricted
        self.assertStatusCode(response, 403)

        # --------------------------------------------------

        #
        # View should 403 when not allowed to request private data (api key)
        #
        request = self.factory.get(self.invisible_path + '?include_invisible')
        request.META['HTTP_ORIGIN'] = self.ds_origin.pattern
        response = self.view(request, **self.invisible_request_kwargs)
        data = json.loads(response.rendered_content)

        # Check that the request was restricted
        self.assertStatusCode(response, 403)

        # --------------------------------------------------

        #
        # View should 403 when not allowed to request private data (not owner)
        #
        request = self.factory.get(self.invisible_path + '?include_invisible')
        request.user = User.objects.create(username='new_user', password='password')
        response = self.view(request, **self.invisible_request_kwargs)
        data = json.loads(response.rendered_content)

        # Check that the request was restricted
        self.assertStatusCode(response, 403)

        # --------------------------------------------------

        #
        # View should return private data when owner is logged in (Session Auth)
        #
        request = self.factory.get(self.invisible_path + '?include_invisible')
        request.user = self.owner
        response = self.view(request, **self.invisible_request_kwargs)
        data = json.loads(response.rendered_content)

        # Check that the request was successful
        self.assertStatusCode(response, 200)

        # --------------------------------------------------

        #
        # View should return private data when owner is logged in (Basic Auth)
        #
        request = self.factory.get(self.invisible_path + '?include_invisible')
        request.META['HTTP_AUTHORIZATION'] = b'Basic ' + base64.b64encode(b':'.join([self.owner.username.encode('utf-8'), b'123']))
        response = self.view(request, **self.invisible_request_kwargs)
        data = json.loads(response.rendered_content)

        # Check that the request was successful
        self.assertStatusCode(response, 200)

        # --------------------------------------------------

        #
        # View should 400 when owner is logged in but doesn't request invisible
        #
        request = self.factory.get(self.invisible_path)
        request.user = self.owner
        response = self.view(request, **self.invisible_request_kwargs)
        data = json.loads(response.rendered_content)

        # Check that the request was successful
        self.assertStatusCode(response, 400)

    def test_GET_invalid_url(self):
        # Make sure that we respond with 404 if a place_id is supplied, but for
        # the wrong dataset or owner.
        request_kwargs = {
          'owner_username': 'mischevious_owner',
          'dataset_slug': self.dataset.slug,
          'place_id': self.place.id
        }

        path = reverse('place-detail', kwargs=request_kwargs)
        request = self.factory.get(path)
        response = self.view(request, **request_kwargs)

        self.assertStatusCode(response, 404)

    def test_GET_from_cache(self):
        path = reverse('place-detail', kwargs=self.request_kwargs)
        request = self.factory.get(path)

        # Check that we make a finite number of queries
        #
        # ---- Checking data access permissions:
        #
        # - SELECT requested dataset and owner
        # - SELECT dataset permissions
        # - SELECT keys
        # - SELECT key permissions
        # - SELECT origins
        # - SELECT origin permissions
        #
        # ---- Building the data
        #
        # - SELECT * FROM sa_api_place AS p
        #     JOIN sa_api_submittedthing AS t ON (p.submittedthing_ptr_id = t.id)
        #     JOIN sa_api_dataset AS ds ON (t.dataset_id = ds.id)
        #     JOIN auth_user as u1 ON (t.submitter_id = u1.id)
        #     JOIN auth_user as u2 ON (ds.owner_id = u2.id)
        #    WHERE t.id = <self.place.id>;
        #
        # - SELECT * FROM social_auth_usersocialauth
        #    WHERE user_id IN (<self.owner.id>)
        #
        # - SELECT * FROM sa_api_submission AS s
        #     JOIN sa_api_submittedthing AS t ON (s.submittedthing_ptr_id = t.id)
        #    WHERE s.parent_id IN (<self.comments.id>, <self.likes.id>, <self.applause.id>);
        #
        # - SELECT * FROM sa_api_attachment AS a
        #    WHERE a.thing_id IN (<[each submission id]>);
        #
        # - SELECT * FROM sa_api_attachment AS a
        #    WHERE a.thing_id IN (<self.place.id>);
        #

        # TODO: https://github.com/mapseed/api/issues/137
        with self.assertNumQueries(16):
            response = self.view(request, **self.request_kwargs)
            self.assertStatusCode(response, 200)

        path = reverse('place-detail', kwargs=self.request_kwargs)
        request = self.factory.get(path)

        # Check that this performs no more queries, since it's all cached
        with self.assertNumQueries(0):
            response = self.view(request, **self.request_kwargs)
            self.assertStatusCode(response, 200)

    def test_GET_from_cache_with_api_key(self):
        # Modify the dataset permissions
        ds_perm = self.dataset.permissions.all()[0]
        ds_perm.can_retrieve = False
        ds_perm.save()

        key_perm = self.apikey.permissions.all()[0]
        key_perm.can_retrieve = True
        key_perm.save()

        # Set up the initial request
        path = reverse('place-detail', kwargs=self.request_kwargs)
        request = self.factory.get(path)
        request.META[KEY_HEADER] = self.apikey.key

        # Check that we make a finite number of queries
        #
        # ---- Checking data access permissions:
        #
        # - SELECT requested dataset and owner
        # - SELECT dataset permissions
        # - SELECT keys
        # - SELECT key permissions
        # - SELECT origins
        # - SELECT origin permissions
        #
        # ---- Building the data
        #
        # - SELECT * FROM sa_api_place AS p
        #     JOIN sa_api_submittedthing AS t ON (p.submittedthing_ptr_id = t.id)
        #     JOIN sa_api_dataset AS ds ON (t.dataset_id = ds.id)
        #     JOIN auth_user as u1 ON (t.submitter_id = u1.id)
        #     JOIN auth_user as u2 ON (ds.owner_id = u2.id)
        #    WHERE t.id = <self.place.id>;
        #
        # - SELECT * FROM social_auth_usersocialauth
        #    WHERE user_id IN (<self.owner.id>)
        #
        # - SELECT * FROM sa_api_submission AS s
        #     JOIN sa_api_submittedthing AS t ON (s.submittedthing_ptr_id = t.id)
        #    WHERE s.parent_id IN (<self.comments.id>, <self.likes.id>, <self.applause.id>);
        #
        # - SELECT * FROM sa_api_attachment AS a
        #    WHERE a.thing_id IN (<[each submission id]>);
        #
        # - SELECT * FROM sa_api_attachment AS a
        #    WHERE a.thing_id IN (<self.place.id>);
        #

        # TODO: https://github.com/mapseed/api/issues/137
        with self.assertNumQueries(16):
            response = self.view(request, **self.request_kwargs)
            self.assertStatusCode(response, 200)

        path = reverse('place-detail', kwargs=self.request_kwargs)
        request = self.factory.get(path)
        request.META[KEY_HEADER] = self.apikey.key

        # Check that this performs no more queries, since it's all cached
        with self.assertNumQueries(0):
            response = self.view(request, **self.request_kwargs)
            self.assertStatusCode(response, 200)

    def test_GET_differently_from_cache_by_user_group(self):
        user = User.objects.create_user(username='temp_user', password='lkjasdf')
        group = Group.objects.create(dataset=self.dataset, name='mygroup')
        group.submitters.add(user)

        path = reverse('place-detail', kwargs=self.request_kwargs)
        anon_request = self.factory.get(path)
        anon_request.user = AnonymousUser()
        auth_request = self.factory.get(path)
        auth_request.user = User.objects.get(username=user.username)

        # Check that we make a finite number of queries
        #
        # ---- Checking data access permissions (only when authed):
        #
        # - SELECT requested dataset
        # - SELECT dataset permissions
        # - SELECT keys
        # - SELECT key permissions
        # - SELECT origins
        # - SELECT origin permissions
        #
        # ---- Building the data (each time)
        #
        # - SELECT * FROM sa_api_place AS p
        #     JOIN sa_api_submittedthing AS t ON (p.submittedthing_ptr_id = t.id)
        #     JOIN sa_api_dataset AS ds ON (t.dataset_id = ds.id)
        #     JOIN auth_user as u1 ON (t.submitter_id = u1.id)
        #     JOIN auth_user as u2 ON (ds.owner_id = u2.id)
        #    WHERE t.id = <self.place.id>;
        #
        # - SELECT * FROM social_auth_usersocialauth
        #    WHERE user_id IN (<self.owner.id>)
        #
        # - SELECT * FROM sa_api_submission AS s
        #     JOIN sa_api_submittedthing AS t ON (s.submittedthing_ptr_id = t.id)
        #    WHERE s.parent_id IN (<self.comments.id>, <self.likes.id>, <self.applause.id>);
        #
        # - SELECT * FROM sa_api_attachment AS a
        #    WHERE a.thing_id IN (<[each submission id]>);
        #
        # - SELECT * FROM sa_api_attachment AS a
        #    WHERE a.thing_id IN (<self.place.id>);
        #

        # TODO: https://github.com/mapseed/api/issues/137
        with self.assertNumQueries(26):
            response = self.view(anon_request, **self.request_kwargs)
            self.assertStatusCode(response, 200)
            response = self.view(auth_request, **self.request_kwargs)
            self.assertStatusCode(response, 200)

        path = reverse('place-detail', kwargs=self.request_kwargs)
        anon_request = self.factory.get(path)
        anon_request.user = AnonymousUser()
        auth_request = self.factory.get(path)
        auth_request.user = User.objects.get(username=user.username)

        # Check that this performs no more queries, since it's all cached
        with self.assertNumQueries(0):
            response = self.view(anon_request, **self.request_kwargs)
            self.assertStatusCode(response, 200)
            response = self.view(auth_request, **self.request_kwargs)
            self.assertStatusCode(response, 200)

    def test_DELETE_response(self):
        #
        # View should 401 when trying to delete when not authenticated
        #
        request = self.factory.delete(self.path)
        response = self.view(request, **self.request_kwargs)
        self.assertStatusCode(response, 401)

    def test_DELETE_response_with_apikey(self):
        #
        # View should delete the place when owner is authenticated
        #
        request = self.factory.delete(self.path)
        request.META[KEY_HEADER] = self.apikey.key
        response = self.view(request, **self.request_kwargs)

        # Check that the request was successful
        self.assertStatusCode(response, 204)

        # Check that no data was returned
        self.assertIsNone(response.data)

    def test_DELETE_response_with_origin(self):
        #
        # View should delete the place when owner is authenticated
        #
        request = self.factory.delete(self.path)
        request.META['HTTP_ORIGIN'] = self.ds_origin.pattern
        response = self.view(request, **self.request_kwargs)

        # Check that the request was successful
        self.assertStatusCode(response, 204)

        # Check that no data was returned
        self.assertIsNone(response.data)

    def test_PUT_response_as_owner(self):
        place_data = json.dumps({
            'type': 'Feature',
            'properties': {
                'type': 'Park Bench',
                'private-secrets': 'The mayor loves this bench',
                'submitter': None,
            },
            'geometry': {"type": "Point", "coordinates": [-73.99, 40.75]},
        })

        #
        # View should 401 when trying to update when not authenticated
        #
        request = self.factory.put(self.path, data=place_data, content_type='application/json')
        response = self.view(request, **self.request_kwargs)
        self.assertStatusCode(response, 401)

        # TODO: Use the SubmittedThingSerializer to implement the commented
        #       out permission structure instead.
        #

        #
        # View should update the place when client is authenticated (apikey)
        #
        request = self.factory.put(self.path, data=place_data, content_type='application/json')
        request.META[KEY_HEADER] = self.apikey.key
        response = self.view(request, **self.request_kwargs)
        self.assertStatusCode(response, 200)

        #
        # View should update the place when client is authenticated (origin)
        #
        request = self.factory.put(self.path, data=place_data, content_type='application/json')
        request.META['HTTP_ORIGIN'] = self.ds_origin.pattern
        response = self.view(request, **self.request_kwargs)
        self.assertStatusCode(response, 200)

        # #
        # # View should 401 when authenticated as client
        # #
        # request = self.factory.put(self.path, data=place_data, content_type='application/json')
        # request.META[KEY_HEADER] = self.apikey.key
        # response = self.view(request, **self.request_kwargs)
        # self.assertStatusCode(response, 401)

        # #
        # # View should update the place when owner is authenticated
        # #
        # request = self.factory.put(self.path, data=place_data, content_type='application/json')
        # request.user = self.owner
        # response = self.view(request, **self.request_kwargs)
        # self.assertStatusCode(response, 200)

        data = json.loads(response.rendered_content)

        # Check that the data attributes have been incorporated into the
        # properties
        self.assertEqual(data['properties'].get('type'), 'Park Bench')
        self.assertIsNone(data['properties']['submitter'])

        # name is not special (lives in the data blob), so should just be unset
        self.assertNotIn('name', data['properties'])

        # private-secrets is not special, but is private, so should not come
        # back down
        self.assertNotIn('private-secrets', data['properties'])

    def test_PUT_response_as_group_submitter(self):
        place_data = json.dumps({
            'type': 'Feature',
            'properties': {
                'type': 'Illegal Dumping',
                'private-secrets': 'The mayor should know about this.',
                'submitter': None
            },
            'geometry': {"type": "Point", "coordinates": [-74.98, 41.76]},
        })
        user = User.objects.create_user(username='temp_user',
                                        password='lkjasdf')
        group = Group.objects.create(dataset=self.dataset,
                                     name='mygroup')
        group.submitters.add(user)
        GroupPermission.objects.create(group=group,
                                       submission_set='places',
                                       can_update=True)

        request = self.factory.put(self.path, data=place_data,
                                   content_type='application/json')
        request.user = user
        response = self.view(request, **self.request_kwargs)
        self.assertStatusCode(response, 200)

        data = json.loads(response.rendered_content)

        # Check that our data attributes are correct:
        self.assertEqual(data['properties'].get('type'), 'Illegal Dumping')
        self.assertIsNone(data['properties']['submitter'])
        self.assertNotIn('name', data['properties'])
        self.assertNotIn('private-secrets', data['properties'])

    def test_PATCH_response_as_owner(self):
        place_data = json.dumps({
          'type': 'Feature',
          'properties': {
            'type': 'Park Bench',
            'meal-preference': 'vegan',
            'private-email': 'test@example.com',
          },
          'geometry': {"type": "Point", "coordinates": [-80, 40]},
        })

        #
        # View should update the place when client is authenticated (apikey)
        #
        request = self.factory.patch(self.path, data=place_data, content_type='application/json')
        request.META[KEY_HEADER] = self.apikey.key
        response = self.view(request, **self.request_kwargs)
        self.assertStatusCode(response, 200)

        data = json.loads(response.rendered_content)

        # Check that the data attributes have been incorporated into the
        # properties
        self.assertEqual(data['properties'].get('type'), 'Park Bench')
        self.assertEqual(data['properties'].get('meal-preference'), 'vegan')
        self.assertEqual(data['geometry'], {"type": "Point", "coordinates": [-80, 40]})

        # Check that previous data is all still there
        self.assertEqual(data['properties'].get('name'), 'K-Mart')

        # private-secrets is not special, but is private, so should not come
        # back down
        self.assertNotIn('private-secrets', data['properties'])
        self.assertNotIn('private-email', data['properties'])

    def test_PUT_response_as_owner_doesnt_change_submitter(self):
        place_data = json.dumps({
          'type': 'Feature',
          'properties': {
            'type': 'Park Bench',
            'private-secrets': 'The mayor loves this bench'
          },
          'geometry': {"type": "Point", "coordinates": [-73.99, 40.75]},
        })

        request = self.factory.put(self.path, data=place_data, content_type='application/json')
        request.user = self.owner
        response = self.view(request, **self.request_kwargs)

        self.assertStatusCode(response, 200)
        data = json.loads(response.rendered_content)

        # Check that the submitter is still the original
        self.assertEqual(data['properties'].get('submitter', {}).get('id'), self.submitter.id)

    def test_PUT_to_invisible_place(self):
        place_data = json.dumps({
            'type': 'Feature',
            'properties': {
                'type': 'Park Bench',
                'private-secrets': 'The mayor loves this bench',
                'submitter': None
            },
            'geometry': {"type": "Point", "coordinates": [-73.99, 40.75]}
        })

        #
        # View should 401 when trying to update when not authenticated
        #
        request = self.factory.put(
            self.invisible_path + '?include_invisible',
            data=place_data,
            content_type='application/json',
        )
        response = self.view(request, **self.invisible_request_kwargs)
        self.assertStatusCode(response, 401)

        #
        # View should 403 when owner is authenticated through api key
        #
        request = self.factory.put(
            self.invisible_path + '?include_invisible',
            data=place_data,
            content_type='application/json',
        )
        request.META[KEY_HEADER] = self.apikey.key
        response = self.view(request, **self.invisible_request_kwargs)
        self.assertStatusCode(response, 403)

        #
        # View should update the place when owner is directly authenticated
        #
        request = self.factory.put(
            self.invisible_path + '?include_invisible',
            data=place_data,
            content_type='application/json',
        )
        request.META['HTTP_AUTHORIZATION'] = b'Basic ' + base64.b64encode(b':'.join([self.owner.username.encode('utf-8'), b'123']))
        response = self.view(request, **self.invisible_request_kwargs)

        data = json.loads(response.rendered_content)

        # Check that the request was successful
        self.assertStatusCode(response, 200)

        # Check that the data attributes have been incorporated into the
        # properties
        self.assertEqual(data['properties'].get('type'), 'Park Bench')

        # submitter is special, and so should be present and None
        self.assertIsNone(data['properties']['submitter'])

        # name is not special (lives in the data blob), so should just be unset
        self.assertNotIn('name', data['properties'])

        # private-secrets is not special, but is private, so should not come
        # back down
        self.assertNotIn('private-secrets', data['properties'])
