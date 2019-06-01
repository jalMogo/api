# -*- coding:utf-8 -*-
from django.test import TestCase
from django.test.client import RequestFactory
from django.core.files.base import ContentFile
from django.core.urlresolvers import reverse
from nose.tools import istest
from sa_api_v2.cache import cache_buffer
from sa_api_v2.models import (
    Attachment,
    Action,
    User,
    DataSet,
    Place,
    Submission,
    Group,
    Flavor,
    Form,
    FormStage,
    FormStageModule,
    FormGroupModule,
    RadioField,
    RadioOption,
    HtmlModule,
    GroupModule,
)
from sa_api_v2.serializers import (
    AttachmentListSerializer,
    AttachmentInstanceSerializer,
    ActionSerializer,
    UserSerializer,
    FullUserSerializer,
    PlaceSerializer,
    DataSetSerializer,
    SubmissionSerializer,
    FlavorSerializer,
)
from social_django.models import UserSocialAuth
import json
from os import path
from mock import patch


class TestAttachmentListSerializer (TestCase):

    def setUp(self):
        f = ContentFile('this is a test')
        f.name = 'my_file.txt'
        self.attachment_model = Attachment(name='my_file', file=f, type='RT')

    def test_attributes(self):
        serializer = AttachmentListSerializer(self.attachment_model)
        self.assertNotIn('thing', serializer.data)

        self.assertIn('created_datetime', serializer.data)
        self.assertIn('updated_datetime', serializer.data)
        self.assertIn('file', serializer.data)
        self.assertIn('name', serializer.data)
        self.assertIn('type', serializer.data)
        self.assertIn('id', serializer.data)

    def test_can_serlialize_a_null_instance(self):
        serializer = AttachmentListSerializer(None)
        data = serializer.data
        self.assertIsInstance(data, dict)


class TestAttachmentInstanceSerializer (TestCase):

    def setUp(self):
        f = ContentFile('this is a test')
        f.name = 'my_file.txt'
        self.attachment_model = Attachment(name='my_file', file=f, type='RT')

    def test_attributes(self):
        serializer = AttachmentInstanceSerializer(self.attachment_model)
        self.assertNotIn('thing', serializer.data)

        self.assertIn('created_datetime', serializer.data)
        self.assertIn('updated_datetime', serializer.data)
        self.assertIn('file', serializer.data)
        self.assertIn('name', serializer.data)
        self.assertIn('type', serializer.data)
        self.assertIn('id', serializer.data)

    def test_can_serlialize_a_null_instance(self):
        serializer = AttachmentInstanceSerializer(None)
        data = serializer.data
        self.assertIsInstance(data, dict)


class TestActionSerializer (TestCase):

    def setUp(self):
        User.objects.all().delete()
        DataSet.objects.all().delete()
        Place.objects.all().delete()
        Action.objects.all().delete()

        owner = User.objects.create(username='myuser')
        dataset = DataSet.objects.create(slug='data',
                                         owner_id=owner.id)
        place = Place.objects.create(dataset=dataset, geometry='POINT(2 3)')
        comment = Submission.objects.create(dataset=dataset,
                                            place_model=place,
                                            set_name='comments')

        self.place_action = Action.objects.create(
            thing=place.submittedthing_ptr)
        self.comment_action = Action.objects.create(
            thing=comment.submittedthing_ptr)

    def test_place_action_attributes(self):
        serializer = ActionSerializer(
            self.place_action,
            context={'request': RequestFactory().get('')},
        )

        self.assertIn('id', serializer.data)
        self.assertEqual(serializer.data.get('action'), 'create')
        self.assertEqual(serializer.data.get('target_type'), 'place')
        self.assertIn('target', serializer.data)
        self.assertNotIn('thing', serializer.data)

    def test_submission_action_attributes(self):
        serializer = ActionSerializer(
            self.comment_action,
            context={'request': RequestFactory().get('')},
        )

        self.assertIn('id', serializer.data)
        self.assertEqual(serializer.data.get('action'), 'create')
        self.assertEqual(serializer.data.get('target_type'), 'comments')
        self.assertIn('target', serializer.data)
        self.assertNotIn('thing', serializer.data)

    def test_prejoined_place_action_attributes(self):
        action = Action.objects.all()\
                               .select_related('thing__place', 'thing__submission')\
                               .filter(thing=self.place_action.thing)[0]

        serializer = ActionSerializer(
            action,
            context={'request': RequestFactory().get('')},
        )

        self.assertIn('id', serializer.data)
        self.assertEqual(serializer.data.get('action'), 'create')
        self.assertEqual(serializer.data.get('target_type'), 'place')
        self.assertIn('target', serializer.data)
        self.assertNotIn('thing', serializer.data)

    def test_prejoined_submission_action_attributes(self):
        action = Action.objects.all()\
            .select_related('thing__place' ,'thing__submission')\
            .filter(thing=self.comment_action.thing)[0]

        serializer = ActionSerializer(
            action,
            context={'request': RequestFactory().get('')},
        )

        self.assertIn('id', serializer.data)
        self.assertEqual(serializer.data.get('action'), 'create')
        self.assertEqual(serializer.data.get('target_type'), 'comments')
        self.assertIn('target', serializer.data)
        self.assertNotIn('thing', serializer.data)


class TestSocialUserSerializer (TestCase):

    def setUp(self):
        test_dir = path.dirname(__file__)
        fixture_dir = path.join(test_dir, 'fixtures')
        twitter_user_data_file = path.join(fixture_dir, 'twitter_user.json')
        facebook_user_data_file = path.join(fixture_dir, 'facebook_user.json')

        self.twitter_user = User.objects.create_user(
            username='my_twitter_user', password='mypassword')
        self.twitter_social_auth = UserSocialAuth.objects.create(
            user=self.twitter_user, provider='twitter', uid='1234',
            extra_data=json.load(open(twitter_user_data_file)))

        self.facebook_user = User.objects.create_user(
            username='my_facebook_user', password='mypassword')
        self.facebook_social_auth = UserSocialAuth.objects.create(
            user=self.facebook_user, provider='facebook', uid='1234',
            extra_data=json.load(open(facebook_user_data_file)))

        self.no_social_user = User.objects.create_user(
            username='my_antisocial_user', password='password')

    def tearDown(self):
        User.objects.all().delete()
        UserSocialAuth.objects.all().delete()

    def test_twitter_user_attributes(self):
        serializer = UserSerializer(self.twitter_user)
        self.assertNotIn('password', serializer.data)
        self.assertIn('name', serializer.data)
        self.assertIn('avatar_url', serializer.data)

        self.assertEqual(serializer.data['name'], 'Mjumbe Poe')
        self.assertEqual(serializer.data['avatar_url'],
                         'https://si0.twimg.com/profile_images/1101892515/dreadlocked_browntwitterbird-248x270_bigger.png')

    def test_facebook_user_attributes(self):
        serializer = UserSerializer(self.facebook_user)
        self.assertNotIn('password', serializer.data)
        self.assertIn('name', serializer.data)
        self.assertIn('avatar_url', serializer.data)

        self.assertEqual(serializer.data['name'], 'Mjumbe Poe')
        self.assertEqual(serializer.data['avatar_url'],
                         'https://fbcdn-profile-a.akamaihd.net/hprofile-ak-ash4/c17.0.97.97/55_512302020614_7565_s.jpg')

    def test_no_social_user_attributes(self):
        serializer = UserSerializer(self.no_social_user)
        self.assertNotIn('password', serializer.data)
        self.assertIn('name', serializer.data)
        self.assertIn('avatar_url', serializer.data)

        self.assertEqual(serializer.data['name'], '')
        self.assertEqual(serializer.data['avatar_url'], '')


class TestUserSerializer (TestCase):

    def setUp(self):
        self.owner = User.objects.create_user(
            username='my_owning_user', password='mypassword')
        self.normal_user = User.objects.create_user(
            username='my_normal_user', password='password')
        self.special_user = User.objects.create_user(
            username='my_special_user', password='password')

        self.datasets = [
            DataSet.objects.create(owner=self.owner, slug='ds1'),
            DataSet.objects.create(owner=self.owner, slug='ds2')
        ]
        self.groups = [
            Group.objects.create(dataset=self.datasets[0],
                                 name='special users')
        ]

        self.special_user._groups.add(self.groups[0])

    def tearDown(self):
        User.objects.all().delete()
        UserSocialAuth.objects.all().delete()
        Group.objects.all().delete()
        DataSet.objects.all().delete()

    def test_partial_serializer_does_not_return_a_users_groups(self):
        serializer = UserSerializer(self.special_user)
        self.assertNotIn('groups', serializer.data)

    def test_full_serializer_returns_an_empty_list_of_groups_for_normal_users(self):
        serializer = FullUserSerializer(self.normal_user)
        self.assertIn('groups', serializer.data)
        self.assertEqual(serializer.data['groups'], [])

    def test_full_serializer_returns_a_users_groups(self):
        serializer = FullUserSerializer(self.special_user)
        self.assertIn('groups', serializer.data)
        self.assertEqual(
            serializer.data['groups'],
            [{'dataset': reverse('dataset-detail',
                                 kwargs={'dataset_slug': 'ds1',
                                         'owner_username': 'my_owning_user'}),
              'name': 'special users',
              'dataset_slug': 'ds1',
              'permissions': []}])


class TestPlaceSerializer (TestCase):

    def setUp(self):
        User.objects.all().delete()
        DataSet.objects.all().delete()
        Place.objects.all().delete()
        Submission.objects.all().delete()
        cache_buffer.reset()

        self.owner = User.objects.create(username='myuser')
        self.dataset = DataSet.objects.create(slug='data',
                                              owner_id=self.owner.id)
        self.place = Place.objects.create(dataset=self.dataset,
                                          geometry='POINT(2 3)')
        Submission.objects.create(dataset=self.dataset,
                                  place_model=self.place,
                                  set_name='comments')
        Submission.objects.create(dataset=self.dataset,
                                  place_model=self.place,
                                  set_name='comments')

    def test_can_serlialize_a_null_instance(self):
        request = RequestFactory().get('')
        request.get_dataset = lambda: self.dataset

        serializer = PlaceSerializer(None)

        data = serializer.data
        self.assertIsInstance(data, dict)

    def test_place_has_right_number_of_submissions(self):
        request = RequestFactory().get('')
        request.get_dataset = lambda: self.dataset

        serializer = PlaceSerializer(self.place, context={'request': request})

        self.assertEqual(
            serializer.data['submission_sets']['comments']['length'], 2)


class TestSubmissionSerializer (TestCase):

    def setUp(self):
        User.objects.all().delete()
        DataSet.objects.all().delete()
        Place.objects.all().delete()
        Submission.objects.all().delete()
        cache_buffer.reset()

    def test_can_serlialize_a_null_instance(self):
        serializer = SubmissionSerializer(
            None,
            context={'request': RequestFactory().get('')},
        )

        data = serializer.data
        self.assertIsInstance(data, dict)


class TestDataSetSerializer (TestCase):

    def setUp(self):
        User.objects.all().delete()
        DataSet.objects.all().delete()
        Place.objects.all().delete()
        Submission.objects.all().delete()
        cache_buffer.reset()

        self.owner = User.objects.create(username='myuser')
        self.dataset = DataSet.objects.create(slug='data',
                                              owner_id=self.owner.id)
        self.place = Place.objects.create(dataset=self.dataset,
                                          geometry='POINT(2 3)')
        Submission.objects.create(dataset=self.dataset,
                                  place_model=self.place,
                                  set_name='comments')
        Submission.objects.create(dataset=self.dataset,
                                  place_model=self.place,
                                  set_name='comments')

    def test_can_serlialize_a_null_instance(self):
        serializer = DataSetSerializer(
            None,
            context={
                'request': RequestFactory().get(''),
                'place_count_map_getter': (lambda: {}),
                'submission_sets_map_getter': (lambda: {})
            }
        )

        data = serializer.data
        self.assertIsInstance(data, dict)


class TestFlavorSerializer (TestCase):

    # ./src/manage.py test -s sa_api_v2.tests.test_serializers:TestFlavorSerializer
    @classmethod
    def setUpTestData(self):
        User.objects.all().delete()
        DataSet.objects.all().delete()
        Place.objects.all().delete()
        Submission.objects.all().delete()
        cache_buffer.reset()

        self.owner = User.objects.create(username='myuser')
        self.dataset1 = DataSet.objects.create(
            slug='data',
            owner_id=self.owner.id
        )

        self.flavor = Flavor.objects.create(
            name='myflavor',
        )

        self.form1 = Form.objects.create(
            label='form1',
            dataset=self.dataset1,
            flavor=self.flavor,
        )

        self.stages = [
            FormStage.objects.create(
                order=0,
                form=self.form1,
            ),
            FormStage.objects.create(
                order=1,
                form=self.form1,
            )
        ]

        self.html_module_content = "<p>Hey there!</p>"

        html_module = HtmlModule.objects.create(
            content=self.html_module_content,
        )

        radio_field = RadioField.objects.create(
            key="ward",
            prompt="where is your ward?",
        )
        RadioOption.objects.create(
            label="Ward 1",
            value="ward_1",
            field=radio_field,
        )
        RadioOption.objects.create(
            label="Ward 2",
            value="ward_2",
            field=radio_field,
        )
        RadioOption.objects.create(
            label="Ward 3",
            value="ward_3",
            field=radio_field,
        )

        related_group_module = GroupModule.objects.create(
            label="This is a group",
        )
        self.grouped_html_module_content = "<p>Inside a group!</p>"
        html_grouped_module = HtmlModule.objects.create(
            content="<p>html within a group!</p>",
        )
        self.group_form_modules = [
            FormGroupModule.objects.create(
                order=1,
                group=related_group_module,
                htmlmodule=html_grouped_module,
            ),
        ]

        # TODO: consider creating a 'save' utility method on
        # the FormStageModule model to make this easier
        FormStageModule.objects.create(
            order=1,
            stage=self.stages[0],
            radiofield=radio_field
        ),
        FormStageModule.objects.create(
            order=2,
            stage=self.stages[0],
            htmlmodule=html_module,
        ),
        FormStageModule.objects.create(
            order=3,
            stage=self.stages[0],
            groupmodule=related_group_module,
        )
        FormStageModule.objects.create(
            order=0,
            stage=self.stages[1],
        )

        self.form2 = Form.objects.create(
            label='form2',
            dataset=self.dataset1,
            flavor=self.flavor,
        )

    def tearDown(self):
        Flavor.objects.all().delete()
        Form.objects.all().delete()
        DataSet.objects.all().delete()
        User.objects.all().delete()
        cache_buffer.reset()

    def test_attributes(self):
        serializer = FlavorSerializer(
            self.flavor,
            context={'request': RequestFactory().get('')},
        )

        self.assertIn('name', serializer.data)

    def test_forms(self):
        serializer = FlavorSerializer(
            self.flavor,
            context={'request': RequestFactory().get('')},
        )
        self.assertEqual(2, len(serializer.data['forms']))

        form1 = next(form for form in serializer.data['forms']
                     if form['label'] == 'form1')
        self.assertTrue(form1.get('label'), self.form1.label)

        form2 = next(form for form in serializer.data['forms']
                     if form['label'] == 'form2')
        self.assertTrue(form2.get('label'), self.form2.label)
        self.assertIn('is_enabled', form2)
        self.assertIn('dataset', form1)
        self.assertIn('dataset', form2)

    # TODO: add tests here for FormStage MapViewPort and layer groups

    def test_form_modules_radiofield(self):
        serializer = FlavorSerializer(
            self.flavor,
            context={'request': RequestFactory().get('')},
        )
        self.assertEqual(2, len(serializer.data['forms']))

        form1 = next(form for form in serializer.data['forms']
                     if form['label'] == 'form1')
        self.assertTrue(len(form1.get('stages')[0].get('modules')[0].get('radiofield').get('options')), 3)

    def test_form_modules_html(self):
        serializer = FlavorSerializer(
            self.flavor,
            context={'request': RequestFactory().get('')},
        )

        form1 = next(form for form in serializer.data['forms']
                     if form['label'] == 'form1')
        self.assertTrue(
            form1.get('stages')[0].get('modules')[1].get('htmlmodule').get('content'),
            self.html_module_content
        )
