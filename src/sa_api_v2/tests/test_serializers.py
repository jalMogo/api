# -*- coding:utf-8 -*-
from django.test import TestCase
from django.test.client import RequestFactory
from django.core.files.base import ContentFile
from django.core.urlresolvers import reverse
from django.core.exceptions import (
    ValidationError,
)
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
    OrderedModule,
    NestedOrderedModule,
    FormFieldOption,
    SkipStageModule,
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
    LayerGroupSerializer,
    FormFixtureSerializer,
    FlavorFixtureSerializer,
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

    @classmethod
    def setUpTestData(cls):
        test_dir = path.dirname(__file__)
        fixture_dir = path.join(test_dir, 'fixtures')
        twitter_user_data_file = path.join(fixture_dir, 'twitter_user.json')
        facebook_user_data_file = path.join(fixture_dir, 'facebook_user.json')

        cls.twitter_user = User.objects.create_user(
            username='my_twitter_user', password='mypassword')
        cls.twitter_social_auth = UserSocialAuth.objects.create(
            user=cls.twitter_user, provider='twitter', uid='1234',
            extra_data=json.load(open(twitter_user_data_file)))

        cls.facebook_user = User.objects.create_user(
            username='my_facebook_user', password='mypassword')
        cls.facebook_social_auth = UserSocialAuth.objects.create(
            user=cls.facebook_user, provider='facebook', uid='1234',
            extra_data=json.load(open(facebook_user_data_file)))

        cls.no_social_user = User.objects.create_user(
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

    @classmethod
    def setUpTestData(cls):
        User.objects.all().delete()
        DataSet.objects.all().delete()
        Place.objects.all().delete()
        Submission.objects.all().delete()
        cache_buffer.reset()

        cls.owner = User.objects.create(username='myuser')
        cls.dataset = DataSet.objects.create(slug='data',
                                              owner_id=cls.owner.id)
        cls.place = Place.objects.create(dataset=cls.dataset,
                                          geometry='POINT(2 3)')
        Submission.objects.create(dataset=cls.dataset,
                                  place_model=cls.place,
                                  set_name='comments')
        Submission.objects.create(dataset=cls.dataset,
                                  place_model=cls.place,
                                  set_name='comments')

    def tearDown(self):
        User.objects.all().delete()
        DataSet.objects.all().delete()
        Place.objects.all().delete()
        Submission.objects.all().delete()
        cache_buffer.reset()

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
    def setUpTestData(cls):

        cls.owner = User.objects.create(username='myuser')
        cls.dataset1 = DataSet.objects.create(
            slug='data',
            owner_id=cls.owner.id
        )
        cls.dataset2 = DataSet.objects.create(
            slug='data-2',
            owner_id=cls.owner.id
        )

        cls.flavor = Flavor.objects.create(
            display_name='myflavor',
        )

        cls.form1 = Form.objects.create(
            label='form1',
            dataset=cls.dataset1,
            flavor=cls.flavor,
        )

        cls.stages = [
            FormStage.objects.create(
                order=0,
                form=cls.form1,
            ),
            FormStage.objects.create(
                order=1,
                form=cls.form1,
            )
        ]

        cls.html_module_content = "<p>Hey there!</p>"

        html_module = HtmlModule.objects.create(
            content=cls.html_module_content,
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
        cls.grouped_html_module_content = "<p>html within a group!</p>"
        html_grouped_module = HtmlModule.objects.create(
            content=cls.grouped_html_module_content,
        )
        cls.nested_ordered_modules = [
            NestedOrderedModule.objects.create(
                order=1,
                group=related_group_module,
                htmlmodule=html_grouped_module,
            ),
        ]

        OrderedModule.objects.create(
            order=1,
            stage=cls.stages[0],
            radiofield=radio_field
        ),
        OrderedModule.objects.create(
            order=2,
            stage=cls.stages[0],
            htmlmodule=html_module,
        ),
        OrderedModule.objects.create(
            order=3,
            stage=cls.stages[0],
            groupmodule=related_group_module,
        )
        OrderedModule.objects.create(
            order=0,
            stage=cls.stages[1],
        )

        cls.form2 = Form.objects.create(
            label='form2',
            dataset=cls.dataset2,
            flavor=cls.flavor,
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

        self.assertIn('display_name', serializer.data)

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
        self.assertEqual(
            form1.get('stages')[0].get('modules')[1].get('htmlmodule').get('content'),
            self.html_module_content
        )

    def test_form_modules_group(self):
        serializer = FlavorSerializer(
            self.flavor,
            context={'request': RequestFactory().get('')},
        )
        self.assertEqual(2, len(serializer.data['forms']))

        form1 = next(form for form in serializer.data['forms']
                     if form['label'] == 'form1')
        self.assertEqual(
            form1.get('stages')[0].get('modules')[2].get('groupmodule').get('modules')[0].get('htmlmodule').get('content'),
            self.grouped_html_module_content,
        )


class TestFlavorDeserializer (TestCase):
    @classmethod
    def setUpTestData(cls):
        User.objects.all().delete()
        DataSet.objects.all().delete()
        cls.owner = User.objects.create(username='myuser')
        cls.dataset = DataSet.objects.create(
            slug='test-dataset',
            owner_id=cls.owner.id
        )
        cls.dataset2 = DataSet.objects.create(slug='kittitas-firewise-input',
                                              owner_id=cls.owner.id)
        cls.dataset3 = DataSet.objects.create(slug='bellevue-bike-share',
                                              owner_id=cls.owner.id)
        cls.dataset4 = DataSet.objects.create(slug='spokane-input',
                                              owner_id=cls.owner.id)
        cls.dataset5 = DataSet.objects.create(slug='pbdurham',
                                              owner_id=cls.owner.id)
        cls.dataset6 = DataSet.objects.create(slug='kittitas-vsp-input',
                                              owner_id=cls.owner.id)
        pbdurham_projects = DataSet.objects.create(slug='pbdurham-projects',
                                              owner_id=cls.owner.id)
        Group.objects.create(
            dataset=cls.dataset5,
            name='administrators',
        )
        projects_admin_group = Group.objects.create(
            dataset=pbdurham_projects,
            id=45, # this id is hard-coded into our permitted_group_id field
            name='administrators',
        )
        Group.objects.create(
            dataset=pbdurham_projects,
            id=47, # this id is hard-coded into our permitted_group_id field
            name='delegates',
        )
        Group.objects.create(
            dataset=pbdurham_projects,
            id=48, # this id is hard-coded into our permitted_group_id field
            name='tech-reviewers',
        )

        # creating Groups with duplicate names on different datasets for testing:
        cls.dataset1_admins_group = Group.objects.create(
            id=9999,  # this id is hard-coded into our permitted_group_id field
            dataset=cls.dataset,
            name='administrators',
        )
        Group.objects.create(
            dataset=cls.dataset2,
            name='administrators',
        )

    def test_deserialize_flavor(self):
        test_dir = path.dirname(__file__)
        fixture_dir = path.join(test_dir, 'fixtures')
        flavor_data_file = path.join(fixture_dir, 'test_flavor.json')
        data = json.load(open(flavor_data_file))

        # create our LayerGroup models:
        layer_group_serializer = LayerGroupSerializer(
            data=data['layer_groups'],
            many=True,
        )
        self.assertTrue(layer_group_serializer.is_valid())
        layer_group_serializer.save()

        # create our Form models:
        form_serializer = FormFixtureSerializer(data=data['forms'], many=True)
        if not form_serializer.is_valid():
            raise ValidationError("FormSerializer failed with error{}:".format(form_serializer.errors))
        form_serializer.save()

        # create our group visibility triggers:
        group_triggers = data['group_visibility_triggers']
        FormFieldOption.import_group_triggers(group_triggers)

        # create our staging visibility triggers:
        stage_triggers = data['stage_visibility_triggers']
        FormFieldOption.import_stage_triggers(stage_triggers)

        # create our skip staging modules:
        skip_stage_modules = data['skip_stage_modules']
        SkipStageModule.import_skip_stage_modules(skip_stage_modules)

        # create our Flavor models:
        flavor_serializer = FlavorFixtureSerializer(
            data=data['flavors'],
            many=True,
        )
        if not flavor_serializer.is_valid():
            raise ValidationError("FlavorSerializer failed with error: {}".format(flavor_serializer.errors))
        flavors = flavor_serializer.save()
        forms = flavors[0].forms.all()
        form = forms.first()


        # check that our visibility triggers are valid:
        self.assertEqual(
            [module.order for module in form.stages.get(order=1).modules.get(order=5).groupmodule.modules.get(order=1).radiofield.options.first().group_visibility_triggers.all()],
            [2]
        )

        # check that our staging triggers are valid:
        self.assertEqual(
            [stage.order for stage in form.stages.get(order=1).modules.get(order=2).radiofield.options.last().stage_visibility_triggers.all()],
            [2]
        )

        # assert that our SkipFormStage module is correct
        self.assertEqual(
            form.stages.first().modules.first().skipstagemodule.stage,
            form.stages.get(order=3)
        )

        # assert that our form is valid:
        self.assertEqual(form.dataset.id, self.dataset.id)
        # assert that our form stages are valid:
        self.assertEqual(form.stages.first().visible_layer_groups.first().label, "layer1")
        # assert that our MapViewport is valid:
        self.assertEqual(form.stages.all().get(order=2).map_viewport.zoom, 12)
        self.assertEqual(form.stages.all().get(order=2).map_viewport.transition_duration, None)
        # assert that our ordered modules, and their fields, are valid:
        self.assertEqual(
            form.stages.first().modules.get(order=2).radiofield.label,
            "my project idea is:"
        )
        self.assertEqual(
            form.stages.first().modules.get(order=2).radiofield.options.first().label,
            "Art"
        )

        options = form.stages.first().modules.get(order=3).checkboxfield.options.all()
        self.assertEqual(
            map(lambda option: option.label, options),
            ['White', 'Black']
        )

        self.assertEqual(
            form.stages.first().modules.get(order=4).numberfield.placeholder,
            "enter meters of waterlines here (eg: 32)"
        )

        self.assertEqual(
            form.stages.first().modules.get(order=2).radiofield.info_modal.header,
            "test modal"
        )

        # assert that our permitted_groups have been created properly:
        self.assertEqual(
            form.stages.first().modules.get(order=4).permitted_group,
            self.dataset1_admins_group,
        )

        # assert that our nested modules are valid:
        groupmodule = form.stages.first().modules.get(order=5).groupmodule
        self.assertEqual(
            groupmodule.label,
            "a group module"
        )
        self.assertEqual(
            groupmodule.modules.all().last().htmlmodule.label,
            "end of survey"
        )

    def test_deserialize_staging_flavors(self):
        test_dir = path.dirname(__file__)
        fixture_dir = path.join(test_dir, 'fixtures')
        flavor_data_file = path.join(fixture_dir, 'staging_flavors.json')
        data = json.load(open(flavor_data_file))

        # create our LayerGroup models:
        layer_group_serializer = LayerGroupSerializer(
            data=data['layer_groups'],
            many=True,
        )
        if not layer_group_serializer.is_valid():
            raise AssertionError("LayerGroupSerializer failed with error: {}".format(layer_group_serializer.errors))
        layer_group_serializer.save()

        # create our Form models:
        form_serializer = FormFixtureSerializer(data=data['forms'], many=True)
        if not form_serializer.is_valid():
            raise AssertionError("FormSerializer failed with error: {}".format(form_serializer.errors))

        form_serializer.save()

        # create our Flavor models:
        flavor_serializer = FlavorFixtureSerializer(
            data=data['flavors'],
            many=True
        )
        if not flavor_serializer.is_valid():
            raise AssertionError("FlavorSerializer failed with error: {}".format( flavor_serializer.errors))
        flavors = flavor_serializer.save()

        # create our group visibility triggers:
        group_triggers = data['group_visibility_triggers']
        FormFieldOption.import_group_triggers(group_triggers)

        forms = flavors[1].forms.all()
        form = forms.get(label='kittitas-firewise-input')
        self.assertEqual(
            [module.order for module in form.stages.get(order=9).modules.get(order=2).groupmodule.modules.get(order=1).radiofield.options.first().group_visibility_triggers.all()],
            [2,3,4,5,6]
        )

        # create our stage visibility triggers:
        stage_triggers = data['stage_visibility_triggers']
        FormFieldOption.import_stage_triggers(stage_triggers)

        forms = next(flavor for flavor in flavors if flavor.slug == 'spokane-vsp').forms.all()
        form = forms.get(label='spokane-input')
        self.assertEqual(
            [stage.order for stage in form.stages.get(order=2).modules.get(order=2).checkboxfield.options.first().stage_visibility_triggers.all()],
            [3]
        )

        # create our skip staging modules:
        skip_stage_modules = data['skip_stage_modules']
        SkipStageModule.import_skip_stage_modules(skip_stage_modules)

        bellevue_form = next(flavor for flavor in flavors if flavor.slug == 'bellevue-bike-share').forms.first()
        self.assertEqual(
            bellevue_form.stages.first().modules.first().skipstagemodule.stage,
            bellevue_form.stages.get(order=6)
        )

        # ensure that we aren't creating duplicate stages
        forms = flavors[0].forms.all()
        bellevue_form = forms.first()
        self.assertEqual(len(bellevue_form.stages.all()), 6)
