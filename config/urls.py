from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.http import JsonResponse
from django.conf import settings
from django.shortcuts import render
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.dispatch.views import MapSnapshotAPIView, map_dashboard
from apps.geo.api import AddressSearchAPIView, NearbyDriversAPIView, RouteQuoteAPIView
from apps.orders.api import OrderViewSet
from apps.tracking.api import DriverLocationAPIView
from apps.tracking.views import driver_location_page
from apps.accounts.views import signup

router = DefaultRouter()
router.register("orders", OrderViewSet, basename="order")


def health(request):
    return JsonResponse({"status": "ok", "service": "taxi-kg-api"})


def home(request):
    return render(request, "home.html", {"map_style_url": settings.MAP_STYLE_URL})


urlpatterns = [
    path("", home, name="home"),
    path("admin/", admin.site.urls),
    path("accounts/signup/", signup, name="signup"),
    path("accounts/login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(next_page="home"), name="logout"),
    path("health/", health, name="health"),
    path("api/", include(router.urls)),
    path("api/dispatch/map/", MapSnapshotAPIView.as_view(), name="dispatch-map-snapshot"),
    path("api/geo/search/", AddressSearchAPIView.as_view(), name="geo-address-search"),
    path("api/geo/route/", RouteQuoteAPIView.as_view(), name="geo-route-quote"),
    path("api/geo/nearby-drivers/", NearbyDriversAPIView.as_view(), name="geo-nearby-drivers"),
    path("api/tracking/location/", DriverLocationAPIView.as_view(), name="driver-location"),
    path("dispatch/map/", map_dashboard, name="dispatch-map"),
    path("driver/location/", driver_location_page, name="driver-location-page"),
    path("api-auth/", include("rest_framework.urls")),
]
