import { expect, test } from "@playwright/test";

// REAL infrastructure acceptance. No page.routeWebSocket(), no mocked HTTP.
// Run only on isolated CI PostGIS and a disposable Redpanda broker with the
// seed_gps_browser_ci.py fixtures. This does not require a cloud deployment.
test("authenticated browser receives API -> outbox -> Kafka -> PostGIS -> WebSocket GPS", async ({
  page,
  request,
}) => {
  const email = process.env.GPS_E2E_EMAIL;
  const password = process.env.GPS_E2E_PASSWORD;
  const driverId = process.env.GPS_E2E_DRIVER_ID;
  const vehicleId = process.env.GPS_E2E_VEHICLE_ID;
  if (!email || !password || !driverId || !vehicleId) {
    throw new Error("Missing isolated GPS E2E fixture credentials and IDs");
  }
  const api = "http://localhost:8000";
  await page.goto("/tracking");
  await expect(page.getByTestId("no-live-vehicles")).toBeVisible();
  await expect(page.getByTestId("tracking-connection")).toContainText("Sign in required");

  await page.getByTestId("tracking-email").fill(email);
  await page.getByTestId("tracking-password").fill(password);
  await page.getByTestId("tracking-log-in").click();
  await expect(page.getByTestId("tracking-connection")).toContainText("connected", {
    timeout: 20000,
  });
  await expect(page.getByTestId("tracking-vehicle-count")).toHaveText("0");

  // API login through the real server. The JWT is never copied into the
  // browser URL, cookies or localStorage.
  const login = await request.post(`${api}/api/v1/auth/login`, {
    form: { username: email, password },
  });
  expect(login.status()).toBe(200);
  const { access_token: token } = await login.json();
  expect(token).toBeTruthy();

  const submitted = await request.post(
    `${api}/api/v1/drivers/${driverId}/location`,
    {
      headers: { Authorization: `Bearer ${token}` },
      data: { latitude: 55.8721, longitude: -4.2582, speed_kmh: 18.5 },
    },
  );
  expect(submitted.status()).toBe(202);
  const queued = await submitted.json();
  expect(queued.status).toBe("queued");
  expect(queued.delivery_status).toBe("pending");
  expect(queued.vehicle_id).toBe(vehicleId);

  // A real background worker publishes the row to Redpanda. FastAPI's real
  // consumer commits the geolocation before sending a same-process socket
  // broadcast to the already authenticated/subscribed Chromium page.
  const row = page.getByTestId("tracking-vehicle-row");
  await expect(row).toContainText("55.87210, -4.25820", { timeout: 45000 });
  await expect(row).toContainText("Kafka GPS event");
  await expect(page.getByTestId("tracking-vehicle-count")).toHaveText("1");
  await expect(page.getByTestId("tracking-fresh-count")).toHaveText("1");
  await expect(page.getByTestId("tracking-freshness")).toHaveText("FRESH");

  // Independently read the database-backed vehicle endpoint. It is scoped
  // by the same current linked-driver identity, not public.
  await expect.poll(async () => {
    const location = await request.get(
      `${api}/api/v1/vehicles/${vehicleId}/location`,
      { headers: { Authorization: `Bearer ${token}` } },
    );
    if (location.status() !== 200) return null;
    return (await location.json()).location;
  }, { timeout: 20000 }).toEqual({
    latitude: 55.8721,
    longitude: -4.2582,
  });

  const blocked = await request.get(`${api}/api/v1/vehicles/${vehicleId}/location`);
  expect(blocked.status()).toBe(401);

  // Logout closes the socket and clears every location from the browser.
  await page.getByTestId("tracking-sign-out").click();
  await expect(page.getByTestId("tracking-connection")).toContainText("Sign in required");
  await expect(page.getByTestId("tracking-vehicle-count")).toHaveText("0");
});
