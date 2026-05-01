# dealer_ai/services/inventory_search.py

from dealer_ai.models import Vehicle
from django.db.models import Q


def search_inventory(query):
    words = query.lower().split()

    qs = Vehicle.objects.filter(is_available=True)

    vehicle_filters = Q()

    for word in words:
        vehicle_filters |= Q(model__icontains=word)
        vehicle_filters |= Q(trim__icontains=word)
        vehicle_filters |= Q(body_style__icontains=word)
        vehicle_filters |= Q(description__icontains=word)

    if "truck" in words:
        vehicle_filters |= Q(body_style__icontains="truck")
        vehicle_filters |= Q(model__icontains="f-150")
        vehicle_filters |= Q(model__icontains="ranger")

    if "suv" in words:
        vehicle_filters |= Q(body_style__icontains="suv")
        vehicle_filters |= Q(model__icontains="explorer")
        vehicle_filters |= Q(model__icontains="escape")
        vehicle_filters |= Q(model__icontains="bronco")

    return qs.filter(vehicle_filters).order_by("price")[:10]