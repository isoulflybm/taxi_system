from django.urls import path
from .consumers import DispatchMapConsumer

websocket_urlpatterns = [
    path("ws/dispatch/locations/", DispatchMapConsumer.as_asgi()),
]
