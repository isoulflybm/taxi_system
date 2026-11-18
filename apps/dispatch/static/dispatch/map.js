import * as maplibregl from "https://unpkg.com/maplibre-gl@6.16.0/dist/maplibre-gl.mjs";

(() => {
  const center = [74.5698, 42.8746];
  const fallbackStyle = {version: 8, sources: {}, layers: [{id: "background", type: "background", paint: {"background-color": "#e8eee9"}}]};
  const configuredStyle = (window.TAXI_MAP_STYLE_URL || "").trim();
  const map = new maplibregl.Map({container: "map", style: configuredStyle || fallbackStyle, center, zoom: 12});
  map.addControl(new maplibregl.NavigationControl(), "top-right");
  const notice = document.getElementById("map-notice");
  if (!configuredStyle) notice.hidden = true;
  const driverMarkers = new Map();
  let orderMarkers = [];
  const ordersNode = document.getElementById("orders");
  const driversNode = document.getElementById("drivers");
  const connection = document.getElementById("connection");
  const searchForm = document.getElementById("address-search");
  const searchInput = document.getElementById("address-query");
  const searchResult = document.getElementById("search-result");
  let searchMarker = null;

  function addPopup(marker, title, detail) {
    const box = document.createElement("div");
    const heading = document.createElement("strong");
    heading.textContent = title;
    const text = document.createElement("div");
    text.textContent = detail || "";
    box.append(heading, text);
    marker.setPopup(new maplibregl.Popup({offset: 14}).setDOMContent(box));
  }

  function renderOrders(items) {
    orderMarkers.forEach(marker => marker.remove());
    orderMarkers = [];
    const routeCollection = {type: "FeatureCollection", features: items.filter(order => order.route_geojson).map(order => ({type: "Feature", properties: {order_id: order.id}, geometry: order.route_geojson}))};
    const updateRoutes = () => {
      if (map.getSource("order-routes")) map.getSource("order-routes").setData(routeCollection);
      else {
        map.addSource("order-routes", {type: "geojson", data: routeCollection});
        map.addLayer({id: "order-routes-line", type: "line", source: "order-routes", paint: {"line-color": "#087c54", "line-width": 3, "line-opacity": .65}});
      }
    };
    if (map.isStyleLoaded()) updateRoutes(); else map.once("load", updateRoutes);
    ordersNode.replaceChildren();
    document.getElementById("order-count").textContent = items.length;
    if (!items.length) ordersNode.innerHTML = '<div class="muted">Активных заказов нет</div>';
    items.forEach(order => {
      const card = document.createElement("div");
      card.className = "item";
      const heading = document.createElement("strong");
      heading.textContent = `Заказ ${order.id.slice(0, 8)} · ${order.status_label}`;
      const text = document.createElement("div");
      text.className = "muted";
      text.textContent = `${order.pickup_address || "Подача отмечена на карте"} → ${order.dropoff_address || "точка назначения"}`;
      card.append(heading, text);
      ordersNode.append(card);
      const el = document.createElement("div");
      el.className = "pickup-marker";
      const marker = new maplibregl.Marker({element: el}).setLngLat([order.pickup.longitude, order.pickup.latitude]).addTo(map);
      orderMarkers.push(marker);
      addPopup(marker, `Подача · ${order.id.slice(0, 8)}`, `${order.status_label}; клиент: ${order.client}`);
      if (order.pickup_address) marker.setPopup(new maplibregl.Popup({offset: 14}).setText(`Подача: ${order.pickup_address}`));
      const destination = document.createElement("div");
      destination.className = "dropoff-marker";
      const destinationMarker = new maplibregl.Marker({element: destination}).setLngLat([order.dropoff.longitude, order.dropoff.latitude]).addTo(map);
      orderMarkers.push(destinationMarker);
      destinationMarker.setPopup(new maplibregl.Popup({offset: 14}).setText(`Назначение: ${order.dropoff_address || "адрес не указан"}`));
    });
  }

  function updateDriver(driver) {
    const key = String(driver.driver_id);
    let entry = driverMarkers.get(key);
    if (!entry) {
      const el = document.createElement("div");
      el.className = "driver-marker";
      const icon = document.createElement("span");
      icon.textContent = "↗";
      el.append(icon);
      entry = {marker: new maplibregl.Marker({element: el}).setLngLat([driver.longitude, driver.latitude]).addTo(map), element: icon};
      driverMarkers.set(key, entry);
    } else {
      entry.marker.setLngLat([driver.longitude, driver.latitude]);
    }
    if (driver.heading != null) entry.element.style.transform = `rotate(${driver.heading}deg)`;
    addPopup(entry.marker, `Водитель: ${driver.username}`, `Обновлено: ${new Date(driver.recorded_at).toLocaleTimeString()}`);
    const card = document.createElement("div");
    card.className = "item";
    const heading = document.createElement("strong");
    heading.textContent = driver.username;
    const sub = document.createElement("div");
    sub.className = "muted";
    sub.textContent = `На связи · ${new Date(driver.recorded_at).toLocaleTimeString()}`;
    card.append(heading, sub);
    const old = driversNode.querySelector(`[data-driver-id="${key}"]`);
    card.dataset.driverId = key;
    if (old) old.replaceWith(card); else driversNode.append(card);
    document.getElementById("driver-count").textContent = driverMarkers.size;
  }

  async function loadSnapshot() {
    const response = await fetch("/api/dispatch/map/", {credentials: "same-origin"});
    if (response.status === 401 || response.status === 403) throw new Error("Нет доступа к диспетчерской карте. Войдите под диспетчером.");
    if (!response.ok) throw new Error(`Не удалось загрузить данные (${response.status})`);
    const data = await response.json();
    renderOrders(data.orders);
    data.drivers.forEach(updateDriver);
  }

  function connectSocket() {
    const scheme = location.protocol === "https:" ? "wss:" : "ws:";
    const socket = new WebSocket(`${scheme}//${location.host}/ws/dispatch/locations/`);
    socket.onopen = () => { connection.textContent = "Обновления в реальном времени подключены"; connection.className = "connection online"; };
    socket.onmessage = event => { const data = JSON.parse(event.data); if (data.event === "driver_location") updateDriver(data); };
    socket.onclose = () => { connection.textContent = "Связь потеряна, переподключаемся…"; connection.className = "connection offline"; setTimeout(connectSocket, 2500); };
    socket.onerror = () => socket.close();
  }

  if (searchForm) {
    searchForm.addEventListener("submit", async event => {
      event.preventDefault();
      const query = searchInput.value.trim();
      if (!query) return;
      searchResult.textContent = "Ищем адрес…";
      try {
        const response = await fetch(`/api/geo/search/?q=${encodeURIComponent(query)}`, {credentials: "same-origin"});
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || "Не удалось найти адрес.");
        if (!data.results.length) { searchResult.textContent = "Ничего не найдено."; return; }
        const result = data.results[0];
        const point = [Number(result.longitude), Number(result.latitude)];
        if (searchMarker) searchMarker.remove();
        searchMarker = new maplibregl.Marker({color: "#7c3aed"}).setLngLat(point).setPopup(new maplibregl.Popup().setText(result.label)).addTo(map);
        map.flyTo({center: point, zoom: 15});
        searchMarker.togglePopup();
        searchResult.textContent = result.label;
      } catch (error) { searchResult.textContent = error.message; }
    });
  }

  loadSnapshot().then(() => {
    connectSocket();
    window.setInterval(() => loadSnapshot().catch(error => { connection.textContent = error.message; connection.className = "connection offline"; }), 15000);
  }).catch(error => {
    connection.textContent = error.message;
    connection.className = "connection offline";
  });
})();
