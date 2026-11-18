(() => {
  const start = document.getElementById("start");
  const stop = document.getElementById("stop");
  const status = document.getElementById("status");
  const coordinates = document.getElementById("coordinates");
  const ordersNode = document.getElementById("driver-orders");
  const csrf = document.querySelector("input[name=csrfmiddlewaretoken]").value;
  let watchId = null;
  let lastSentAt = 0;

  async function send(position) {
    const now = Date.now();
    if (now - lastSentAt < 2500) return;
    lastSentAt = now;
    const {latitude, longitude, heading, speed, accuracy} = position.coords;
    coordinates.textContent = `${latitude.toFixed(6)}, ${longitude.toFixed(6)} · ${new Date(now).toLocaleTimeString()}`;
    try {
      const response = await fetch("/api/tracking/location/", {
        method: "POST",
        credentials: "same-origin",
        headers: {"Content-Type": "application/json", "X-CSRFToken": csrf},
        body: JSON.stringify({latitude, longitude, heading, speed_mps: speed, accuracy_m: accuracy, recorded_at: new Date(position.timestamp).toISOString()})
      });
      if (!response.ok) throw new Error(response.status === 403 ? "Сессия водителя не активна." : `Ошибка отправки: ${response.status}`);
      status.textContent = "Геолокация передаётся диспетчеру.";
    } catch (error) {
      status.textContent = error.message;
    }
  }

  function handleError(error) {
    status.textContent = error.code === 1 ? "Разреши браузеру доступ к геолокации." : `Не удалось получить координаты: ${error.message}`;
  }

  async function loadOrders() {
    if (!ordersNode) return;
    try {
      const response = await fetch("/api/orders/", {credentials: "same-origin"});
      const data = await response.json();
      if (!response.ok) throw new Error("Не удалось загрузить заказы.");
      const active = data.filter(order => ["assigned", "driver_arriving", "in_progress"].includes(order.status));
      ordersNode.replaceChildren();
      if (!active.length) { ordersNode.textContent = "Назначенных активных заказов пока нет."; return; }
      active.forEach(order => {
        const card = document.createElement("article");
        card.className = "order-card";
        const title = document.createElement("strong");
        title.textContent = `Заказ ${order.id.slice(0, 8)} · ${order.status_label || order.status}`;
        const details = document.createElement("div");
        details.className = "order-muted";
        const amount = order.final_price || order.estimated_price || "—";
        details.textContent = `${order.pickup_address || "Подача"} → ${order.dropoff_address || "Назначение"} · ${amount} ${order.currency} · клиент: ${order.client_username || "—"}${order.client_phone ? ` · ${order.client_phone}` : ""}`;
        card.append(title, details);
        const actions = [];
        if (order.status === "assigned") actions.push(["Я приехал", "driver-arriving"]);
        if (["assigned", "driver_arriving"].includes(order.status)) actions.push(["Начать поездку", "start"]);
        if (["assigned", "driver_arriving"].includes(order.status)) actions.push(["Отказаться — передать дальше", "decline"]);
        if (order.status === "in_progress") actions.push(["Завершить поездку", "complete"]);
        actions.forEach(([label, action]) => {
          const button = document.createElement("button");
          button.type = "button";
          button.textContent = label;
          button.addEventListener("click", async () => {
            button.disabled = true;
            try {
              const result = await fetch(`/api/orders/${order.id}/${action}/`, {method: "POST", credentials: "same-origin", headers: {"X-CSRFToken": csrf}});
              const body = await result.json();
              if (!result.ok) throw new Error(body.detail || body.status || "Ошибка обновления заказа.");
              if (action === "decline" && body.detail) status.textContent = body.detail;
              await loadOrders();
            } catch (error) { status.textContent = error.message; button.disabled = false; }
          });
          card.append(button);
        });
        ordersNode.append(card);
      });
    } catch (error) { ordersNode.textContent = error.message; }
  }

  loadOrders();

  start.addEventListener("click", () => {
    if (!navigator.geolocation) { status.textContent = "Этот браузер не поддерживает геолокацию."; return; }
    watchId = navigator.geolocation.watchPosition(send, handleError, {enableHighAccuracy: true, maximumAge: 2000, timeout: 15000});
    start.disabled = true;
    stop.disabled = false;
    status.textContent = "Ожидаю разрешение и координаты…";
  });

  stop.addEventListener("click", () => {
    if (watchId !== null) navigator.geolocation.clearWatch(watchId);
    watchId = null;
    start.disabled = false;
    stop.disabled = true;
    status.textContent = "Передача остановлена.";
  });

  window.setInterval(loadOrders, 15000);
})();
