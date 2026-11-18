from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import render

from apps.accounts.models import UserProfile


@login_required
def driver_location_page(request):
    profile = getattr(request.user, "taxi_profile", None)
    if not profile or profile.role != UserProfile.Role.DRIVER:
        return HttpResponseForbidden("Страница доступна только водителю.")
    return render(request, "tracking/driver_location.html")
