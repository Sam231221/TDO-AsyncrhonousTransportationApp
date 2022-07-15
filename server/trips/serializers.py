from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from django.db.models import Count
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .caches import cache_driver_rating
from .models import Trip


class UserSerializer(serializers.ModelSerializer):
    password1 = serializers.CharField(write_only=True)
    password2 = serializers.CharField(write_only=True)
    group = serializers.CharField()

    def validate(self, data):
        if data['password1'] != data['password2']:
            raise serializers.ValidationError('Passwords must match.')
        return data

    def create(self, validated_data):
        group_data = validated_data.pop('group')
        group, _ = Group.objects.get_or_create(name=group_data)
        data = {
            key: value for key, value in validated_data.items()
            if key not in ('password1', 'password2')
        }
        data['password'] = validated_data['password1']
        user = self.Meta.model.objects.create_user(**data)
        user.groups.add(group)
        user.save()
        return user

    class Meta:
        model = get_user_model()
        fields = (
            'id', 'username', 'password1', 'password2',
            'first_name', 'last_name', 'group',
            'photo',
        )
        read_only_fields = ('id',)


class DriverSerializer(serializers.ModelSerializer):
    group = serializers.CharField()
    rating = serializers.SerializerMethodField()
    num_trips = serializers.SerializerMethodField()

    def get_rating(self, obj):
        return cache_driver_rating(obj.id)

    def get_num_trips(self, obj):
        trips = Trip.objects.filter(
            driver=obj.id
        ).aggregate(
            Count('id')
        )
        return trips['id__count']

    class Meta:
        model = get_user_model()
        fields = (
            'id', 'username', 'first_name', 'last_name', 'group',
            'photo', 'rating', 'num_trips',
        )
        read_only_fields = (
            'id', 'username', 'first_name', 'last_name', 'group',
            'photo', 'rating', 'num_trips',
        )


class LogInSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        user_data = UserSerializer(user).data
        for key, value in user_data.items():
            if key != 'id':
                token[key] = value
        return token


class TripSerializer(serializers.ModelSerializer):
    class Meta:
        model = Trip
        fields = '__all__'
        read_only_fields = ('id', 'created', 'updated',)


class NestedTripSerializer(serializers.ModelSerializer):
    driver = UserSerializer(read_only=True)
    rider = UserSerializer(read_only=True)

    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)

        # Update cache
        cache_driver_rating(instance.driver.id)

        return instance

    class Meta:
        model = Trip
        fields = '__all__'
        read_only_fields = (
            'id', 'created', 'updated', 'pick_up_address', 'drop_off_address',
        )
        depth = 1
