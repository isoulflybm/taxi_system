import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings


class GeoServiceError(Exception):
    pass


def _get_json(url, *, user_agent=None, timeout=8):
    headers = {"Accept": "application/json"}
    if user_agent:
        headers["User-Agent"] = user_agent
    request = Request(url, headers=headers)
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, ValueError) as exc:
        raise GeoServiceError("Внешний геосервис временно недоступен.") from exc


def search_addresses(query, *, limit=5):
    if not settings.NOMINATIM_BASE_URL:
        raise GeoServiceError("Геокодер не настроен. Укажите NOMINATIM_BASE_URL.")
    params = urlencode({"q": query, "format": "jsonv2", "countrycodes": "kg", "limit": limit})
    payload = _get_json(
        f"{settings.NOMINATIM_BASE_URL}/search?{params}",
        user_agent=settings.NOMINATIM_USER_AGENT,
    )
    return [{
        "label": item.get("display_name", ""),
        "latitude": float(item["lat"]),
        "longitude": float(item["lon"]),
    } for item in payload if item.get("lat") is not None and item.get("lon") is not None]


def get_driving_route(start_lon, start_lat, end_lon, end_lat):
    if not settings.OSRM_BASE_URL:
        raise GeoServiceError("Маршрутизатор не настроен. Укажите OSRM_BASE_URL.")
    coordinates = f"{start_lon},{start_lat};{end_lon},{end_lat}"
    params = urlencode({"overview": "full", "geometries": "geojson", "steps": "false", "alternatives": "false"})
    payload = _get_json(f"{settings.OSRM_BASE_URL}/route/v1/driving/{coordinates}?{params}")
    routes = payload.get("routes") or []
    if payload.get("code") != "Ok" or not routes:
        raise GeoServiceError("Дорожный маршрут между точками не найден.")
    route = routes[0]
    return {
        "distance_m": int(round(route["distance"])),
        "duration_s": int(round(route["duration"])),
        "geometry": route.get("geometry"),
    }
