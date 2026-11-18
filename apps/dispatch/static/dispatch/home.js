import * as maplibregl from "https://unpkg.com/maplibre-gl@6.16.0/dist/maplibre-gl.mjs";

(() => {
  const locations = {pickup: null, dropoff: null};
  const hints = {pickup: document.getElementById("pickup-hint"), dropoff: document.getElementById("dropoff-hint")};
  const quoteNode = document.getElementById("quote");
  const bookButton = document.getElementById("book");
  const map = new maplibregl.Map({
    container: "map",
    style: window.TAXI_MAP_STYLE_URL || {version: 8, sources: {}, layers: [{id: "bg", type: "background", paint: {"background-color": "#e3ebe5"}}]},
    center: [74.5698, 42.8746], zoom: 11,
  });
  map.addControl(new maplibregl.NavigationControl(), "top-right");
  let markers = [];
  let latestQuote = null;

  async function responseJson(response) {
    const contentType = response.headers.get("content-type") || "";
    if (!contentType.includes("application/json")) {
      throw new Error(`Сервер вернул HTTP ${response.status} вместо JSON. Проверьте журнал Django.`);
    }
    return response.json();
  }
  function csrf() { return document.querySelector("#csrf-form [name=csrfmiddlewaretoken]").value; }
  function chooseAddress(key, item) {
    locations[key] = {latitude: Number(item.latitude), longitude: Number(item.longitude), label: item.label};
    document.getElementById(key).value = item.label;
    markers.forEach(marker => marker.remove());
    markers = Object.entries(locations).filter(([, point]) => point).map(([name, point]) => new maplibregl.Marker({color: name === "pickup" ? "#087c54" : "#e8774f"}).setLngLat([point.longitude, point.latitude]).setPopup(new maplibregl.Popup().setText(point.label)).addTo(map));
    map.flyTo({center: [locations[key].longitude, locations[key].latitude], zoom: 14});
    latestQuote = null;
    if (bookButton) bookButton.disabled = true;
    quoteNode.textContent = "Адрес выбран. Для уточнения отметьте точку на карте.";
  }
  function drawRoute(geometry) {
    if (!geometry) return;
    const draw = () => {
      if (map.getLayer("ride-route")) map.removeLayer("ride-route");
      if (map.getSource("ride-route")) map.removeSource("ride-route");
      map.addSource("ride-route", {type: "geojson", data: {type: "Feature", properties: {}, geometry}});
      map.addLayer({id: "ride-route", type: "line", source: "ride-route", paint: {"line-color": "#087c54", "line-width": 5, "line-opacity": .85}});
      const bounds = new maplibregl.LngLatBounds();
      geometry.coordinates.forEach(coord => bounds.extend(coord));
      if (!bounds.isEmpty()) map.fitBounds(bounds, {padding: 70, maxZoom: 15});
    };
    if (map.isStyleLoaded()) draw(); else map.once("load", draw);
  }

  document.querySelectorAll("[data-search]").forEach(button => button.addEventListener("click", async () => {
    const key = button.dataset.search;
    const query = document.getElementById(key).value.trim();
    if (!query) { hints[key].textContent = "Введите адрес."; return; }
    hints[key].textContent = "Ищем адрес в Кыргызстане…";
    try {
      const response = await fetch(`/api/geo/search/?q=${encodeURIComponent(query)}`);
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Геокодер недоступен.");
      if (!data.results.length) throw new Error("Адрес не найден. Попробуйте указать населённый пункт и улицу.");
      const selector = document.createElement("select");
      selector.style.maxWidth = "100%";
      data.results.forEach((item, index) => {
        const option = document.createElement("option");
        option.value = String(index);
        option.textContent = item.label;
        selector.append(option);
      });
      hints[key].replaceChildren(selector);
      selector.addEventListener("change", () => chooseAddress(key, data.results[Number(selector.value)]));
      chooseAddress(key, data.results[0]);
      hints[key].replaceChildren(selector, document.createTextNode(" Выберите подходящий вариант из списка."));
    } catch (error) { hints[key].textContent = error.message; }
  }));

  ["pickup", "dropoff"].forEach(key => document.getElementById(key).addEventListener("input", () => {
    locations[key] = null;
    latestQuote = null;
    if (bookButton) bookButton.disabled = true;
  }));

  document.getElementById("estimate").addEventListener("click", async () => {
    if (!locations.pickup || !locations.dropoff) { quoteNode.textContent = "Сначала найдите оба адреса."; return; }
    quoteNode.textContent = "Строим маршрут и рассчитываем цену…";
    const start = locations.pickup, end = locations.dropoff;
    const params = new URLSearchParams({start_lon: start.longitude, start_lat: start.latitude, end_lon: end.longitude, end_lat: end.latitude});
    try {
      const routeResponse = await fetch(`/api/geo/route/?${params}`);
      const route = await responseJson(routeResponse);
      if (!routeResponse.ok) throw new Error(route.detail || "Не удалось построить маршрут.");
      let nearby = null;
      try {
        const nearbyResponse = await fetch(`/api/geo/nearby-drivers/?lat=${start.latitude}&lon=${start.longitude}`);
        const nearbyData = await responseJson(nearbyResponse);
        if (nearbyResponse.ok) nearby = nearbyData;
      } catch (error) {
        console.warn("Не удалось получить число свободных водителей:", error);
      }
      latestQuote = route;
      const km = (route.distance_m / 1000).toFixed(1);
      const mins = Math.max(1, Math.round(route.duration_s / 60));
      const availability = nearby ? `${nearby.available_drivers} свободных машин поблизости` : "наличие свободных машин временно не удалось определить";
      const nearest = !nearby || nearby.nearest_approx_m == null ? "" : ` · ближайшая примерно в ${nearby.nearest_approx_m} м`;
      quoteNode.innerHTML = `<strong>${route.price ? `${route.price} ${route.currency}` : "Цена не настроена"}</strong><br>${km} км · около ${mins} мин · ${availability}${nearest}`;
      if (bookButton) bookButton.disabled = !route.tariff_id;
      drawRoute(route.geometry);
      document.getElementById("mapnote").textContent = "Маршрут построен по дорожной сети";
    } catch (error) { latestQuote = null; quoteNode.textContent = error.message; if (bookButton) bookButton.disabled = true; }
  });

  if (bookButton) bookButton.addEventListener("click", async () => {
    if (!latestQuote) return;
    bookButton.disabled = true;
    quoteNode.textContent = "Создаём заказ и ищем ближайшего свободного водителя…";
    const payload = {
      pickup_latitude: locations.pickup.latitude, pickup_longitude: locations.pickup.longitude,
      dropoff_latitude: locations.dropoff.latitude, dropoff_longitude: locations.dropoff.longitude,
      pickup_address: locations.pickup.label, dropoff_address: locations.dropoff.label, tariff: latestQuote.tariff_id,
    };
    try {
      const response = await fetch("/api/orders/", {method: "POST", headers: {"Content-Type": "application/json", "X-CSRFToken": csrf()}, credentials: "same-origin", body: JSON.stringify(payload)});
      const data = await response.json();
      if (!response.ok) throw new Error(data.route || data.detail || JSON.stringify(data));
      quoteNode.textContent = data.assigned_driver ? `Заказ создан и назначен водителю. Номер: ${data.id}` : `Заказ ${data.id} создан. Пока нет свободного водителя; диспетчерская продолжит поиск.`;
    } catch (error) { quoteNode.textContent = `Не удалось создать заказ: ${error.message}`; bookButton.disabled = false; }
  });

  map.on("click", event => {
    const key = locations.pickup && !locations.dropoff ? "dropoff" : "pickup";
    // Manual map selection is useful when the geocoder has no exact house number.
    locations[key] = {latitude: event.lngLat.lat, longitude: event.lngLat.lng, label: `${event.lngLat.lat.toFixed(5)}, ${event.lngLat.lng.toFixed(5)}`};
    document.getElementById(key).value = locations[key].label;
    hints[key].textContent = "Точка выбрана на карте.";
    markers.forEach(marker => marker.remove());
    markers = Object.entries(locations).filter(([, point]) => point).map(([name, point]) => new maplibregl.Marker({color: name === "pickup" ? "#087c54" : "#e8774f"}).setLngLat([point.longitude, point.latitude]).addTo(map));
    latestQuote = null;
    if (bookButton) bookButton.disabled = true;
  });
})();
