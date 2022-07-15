from decimal import Decimal, ROUND_UP

from django.core.cache import cache
from django.db.models import Avg, Count

from .models import Trip


def make_driver_rating_cache_key(driver_id):
    return f'driver:{driver_id}:rating'


def cache_driver_rating(driver_id):
    cache_key = make_driver_rating_cache_key(driver_id)
    rating = cache.get(cache_key)
    if rating is None:
        trips = Trip.objects.filter(
            driver=driver_id, rating__isnull=False
        ).aggregate(
            Avg('rating'), Count('rating')
        )
        if trips['rating__count'] >= 3:
            new_rating = Decimal(trips['rating__avg']).quantize(Decimal('.01'), rounding=ROUND_UP)
            cache.set(cache_key, str(new_rating))
            return str(new_rating)
        else:
            cache.set(cache_key, '0')
            return '0'
    else:
        return rating