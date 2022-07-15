from django.contrib.auth import get_user_model
from django.db.models import FilteredRelation, Q
from rest_framework import generics, mixins, permissions, viewsets
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import Trip
from .serializers import DriverSerializer, LogInSerializer, NestedTripSerializer, UserSerializer


class SignUpView(generics.CreateAPIView):
    queryset = get_user_model().objects.all()
    serializer_class = UserSerializer


class LogInView(TokenObtainPairView):
    serializer_class = LogInSerializer


class TripView(
    mixins.ListModelMixin, 
    mixins.RetrieveModelMixin, 
    mixins.UpdateModelMixin, 
    viewsets.GenericViewSet,
):
    lookup_field = 'id'
    lookup_url_kwarg = 'trip_id'
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = NestedTripSerializer

    def get_queryset(self):
        user = self.request.user
        if user.group == 'driver':
            return Trip.objects.filter(
                Q(status=Trip.REQUESTED) | Q(driver=user)
            )
        if user.group == 'rider':
            return Trip.objects.filter(rider=user)
        return Trip.objects.none()


class DriverView(generics.RetrieveAPIView):
    lookup_field = 'id'
    lookup_url_kwarg = 'driver_id'
    permission_classes = (permissions.IsAuthenticated,)
    queryset = get_user_model().objects.annotate(
        user_groups=FilteredRelation('groups')
    ).filter(
        user_groups__name='driver'
    )
    serializer_class = DriverSerializer
