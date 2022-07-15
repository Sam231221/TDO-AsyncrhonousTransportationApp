import base64
from io import BytesIO
import json
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from PIL import Image
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase

from trips.caches import make_driver_rating_cache_key
from trips.models import Trip

PASSWORD = 'pAssw0rd!'


def create_user(username='user@example.com', password=PASSWORD, group_name='rider'):
    group, _ = Group.objects.get_or_create(name=group_name)
    user = get_user_model().objects.create_user(
        username=username, password=password)
    user.groups.add(group)
    user.save()
    return user


def create_photo_file():
    data = BytesIO()
    Image.new('RGB', (100, 100)).save(data, 'PNG')
    data.seek(0)
    return SimpleUploadedFile('photo.png', data.getvalue())


class AuthenticationTest(APITestCase):
    def test_user_can_sign_up(self):
        photo_file = create_photo_file()
        response = self.client.post(reverse('sign_up'), data={
            'username': 'user@example.com',
            'first_name': 'Test',
            'last_name': 'User',
            'password1': PASSWORD,
            'password2': PASSWORD,
            'group': 'rider',
            'photo': photo_file,
        })
        user = get_user_model().objects.last()
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)
        self.assertEqual(response.data['id'], user.id)
        self.assertEqual(response.data['username'], user.username)
        self.assertEqual(response.data['first_name'], user.first_name)
        self.assertEqual(response.data['last_name'], user.last_name)
        self.assertEqual(response.data['group'], user.group)
        self.assertIsNotNone(user.photo)

    def test_user_can_log_in(self):
        user = create_user()
        response = self.client.post(reverse('log_in'), data={
            'username': user.username,
            'password': PASSWORD,
        })

        # Parse payload data from access token.
        access = response.data['access']
        header, payload, signature = access.split('.')
        decoded_payload = base64.b64decode(f'{payload}==')
        payload_data = json.loads(decoded_payload)

        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertIsNotNone(response.data['refresh'])
        self.assertEqual(payload_data['id'], user.id)
        self.assertEqual(payload_data['username'], user.username)
        self.assertEqual(payload_data['first_name'], user.first_name)
        self.assertEqual(payload_data['last_name'], user.last_name)


@override_settings(CACHES={
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'
    }
})
class HttpTripTest(APITestCase):
    def setUp(self):
        self.user = create_user()
        self.client.login(username=self.user.username, password=PASSWORD)

    def test_user_can_list_trips(self):
        trips = [
            Trip.objects.create(
                pick_up_address='A', drop_off_address='B', rider=self.user),
            Trip.objects.create(
                pick_up_address='B', drop_off_address='C', rider=self.user),
            Trip.objects.create(
                pick_up_address='C', drop_off_address='D')
        ]
        response = self.client.get(reverse('trip:trip_list'))
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        exp_trip_ids = [str(trip.id) for trip in trips[0:2]]
        act_trip_ids = [trip.get('id') for trip in response.data]
        self.assertCountEqual(act_trip_ids, exp_trip_ids)

    def test_user_can_retrieve_trip_by_id(self):
        trip = Trip.objects.create(
            pick_up_address='A', drop_off_address='B', rider=self.user)
        response = self.client.get(trip.get_absolute_url())
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(str(trip.id), response.data.get('id'))

    def test_rider_can_rate_trip(self):
        # Given
        rating = 5
        driver = create_user(username='driver@example.com', group_name='driver')
        unrated_trip = Trip.objects.create(
            pick_up_address='A', drop_off_address='B', driver=driver, rider=self.user)

        # When
        response = self.client.patch(unrated_trip.get_absolute_url(), {'rating': rating})

        # Then
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(rating, response.data.get('rating'))

    def test_rating_trip_populates_cache_with_average_rating(self):
        # Given
        driver = create_user(username='driver@example.com', group_name='driver')
        Trip.objects.bulk_create([
            Trip(pick_up_address='A', drop_off_address='B', driver=driver, rating=3),
            Trip(pick_up_address='B', drop_off_address='C', driver=driver, rating=3),
            Trip(pick_up_address='C', drop_off_address='D', driver=driver, rating=3),
        ])
        unrated_trip = Trip.objects.create(
            pick_up_address='A', drop_off_address='B', driver=driver, rider=self.user)

        cache_key = make_driver_rating_cache_key(driver.id)
        cache.clear()

        # When
        response = self.client.patch(unrated_trip.get_absolute_url(), {'rating': 5})

        # Then
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        
        # Cached value is (3 + 3 + 3 + 5) / 4 = 3.50
        self.assertEqual('3.50', cache.get(cache_key))


@override_settings(CACHES={
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'
    }
})
class HttpDriverTest(APITestCase):
    def setUp(self):
        self.user = create_user()
        self.client.login(username=self.user.username, password=PASSWORD)

    def test_user_can_get_driver(self):
        driver = create_user(username='driver@example.com', group_name='driver')
        response = self.client.get(reverse('driver', kwargs={'driver_id': driver.id}))
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(driver.id, response.data.get('id'))

    def test_user_cannot_get_rider(self):
        rider = create_user(username='rider@example.com', group_name='rider')
        response = self.client.get(reverse('driver', kwargs={'driver_id': rider.id}))
        self.assertEqual(status.HTTP_404_NOT_FOUND, response.status_code)

    def test_user_can_see_driver_rating(self):
        # Given
        driver = create_user(username='driver@example.com', group_name='driver')
        Trip.objects.bulk_create([
            Trip(pick_up_address='A', drop_off_address='B', driver=driver, rider=self.user, rating=4),
            Trip(pick_up_address='B', drop_off_address='C', driver=driver, rider=self.user, rating=5),
            Trip(pick_up_address='C', drop_off_address='D', driver=driver, rider=self.user, rating=5),
        ])

        cache_key = make_driver_rating_cache_key(driver.id)
        cache.clear()

        # When
        with patch('trips.caches.cache.set', new=Mock(wraps=cache.set)) as mock_cache_set:
            response = self.client.get(reverse('driver', kwargs={'driver_id': driver.id}))
            mock_cache_set.assert_called_once_with(cache_key, '4.67')

        # Then
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual('4.67', str(response.data.get('rating')))

        # Value has been cached
        self.assertEqual('4.67', cache.get(cache_key))

    def test_user_can_see_driver_rating_from_cache(self):
        # Given
        driver = create_user(username='driver@example.com', group_name='driver')
        Trip.objects.bulk_create([
            Trip(pick_up_address='A', drop_off_address='B', driver=driver, rider=self.user, rating=4),
            Trip(pick_up_address='B', drop_off_address='C', driver=driver, rider=self.user, rating=5),
            Trip(pick_up_address='C', drop_off_address='D', driver=driver, rider=self.user, rating=5),
        ])

        cache_key = make_driver_rating_cache_key(driver.id)
        cache.clear()
        cache.set(cache_key, '4.67')

        # When
        with patch('trips.caches.cache.set') as mock_cache_set:
            response = self.client.get(reverse('driver', kwargs={'driver_id': driver.id}))
            mock_cache_set.assert_not_called()

        # Then
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual('4.67', str(response.data.get('rating')))

    def test_user_cannot_see_driver_rating_below_threshold(self):
        # Given
        driver = create_user(username='driver@example.com', group_name='driver')
        Trip.objects.bulk_create([
            Trip(pick_up_address='A', drop_off_address='B', driver=driver, rider=self.user, rating=4),
            Trip(pick_up_address='B', drop_off_address='C', driver=driver, rider=self.user, rating=5),
            Trip(pick_up_address='C', drop_off_address='D', driver=driver, rider=self.user),
        ])

        # When
        response = self.client.get(reverse('driver', kwargs={'driver_id': driver.id}))

        # Then
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual('0', response.data.get('rating'))

    def test_user_can_see_driver_num_trips(self):
        # Given
        driver = create_user(username='driver@example.com', group_name='driver')
        Trip.objects.create(
            pick_up_address='A', drop_off_address='B', driver=driver, rider=self.user)

        # When
        response = self.client.get(reverse('driver', kwargs={'driver_id': driver.id}))

        # Then
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(1, response.data.get('num_trips'))
