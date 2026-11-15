import { expect, test, type WebSocketRoute } from "@playwright/test";

const vehicleId = "11111111-1111-4111-8111-111111111111";
const driverId = "22222222-2222-4222-8222-222222222222";

function gpsPosition(latitude: number, observedAt: string, source: "postgres" | "kafka") {
  return {
    vehicle_id: vehicleId,
    driver_id: driverId,
    event_id: "33333333-3333-4333-8333-333333333333",
    location: { latitude, longitude: -4.26 },
    observed_at: observedAt,
    source,
    speed_kmh: 20,
  };
}

test("shows real GPS updates, ignores older positions and reconnects", async ({ page }) => {
  const sockets: WebSocketRoute[] = [];
  const startingTime = new Date(Date.now() - 10_000).toISOString();
  await page.routeWebSocket("ws://localhost:8000/ws", socket => {
    sockets.push(socket);
    socket.onMessage(message => {
      if (JSON.parse(String(message)).action === "subscribe") {
        socket.send(JSON.stringify({
          type: "vehicle_snapshot",
          data: { vehicles: [gpsPosition(55.86, startingTime, "postgres")] },
        }));
      }
    });
  });

  await page.goto("/tracking");
  await expect(page.getByTestId("tracking-connection")).toContainText("connected");
  await expect(page.getByTestId("tracking-vehicle-count")).toHaveText("1");
  await expect(page.getByTestId("tracking-fresh-count")).toHaveText("1");
  await expect(page.getByTestId("tracking-freshness")).toHaveText("FRESH");
  await expect(page.getByTestId("tracking-vehicle-row")).toContainText("55.86000");

  const newerTime = new Date().toISOString();
  sockets[0].send(JSON.stringify({
    type: "vehicle_update",
    data: gpsPosition(55.8721, newerTime, "kafka"),
  }));
  await expect(page.getByTestId("tracking-vehicle-row")).toContainText("55.87210");

  // A delayed Kafka event and a reconnect snapshot may not roll back position.
  sockets[0].send(JSON.stringify({
    type: "vehicle_update",
    data: gpsPosition(51.5, startingTime, "kafka"),
  }));
  await expect(page.getByTestId("tracking-vehicle-row")).toContainText("55.87210");

  sockets[0].close();
  await expect(page.getByTestId("tracking-connection")).toContainText("reconnecting");
  await expect(page.getByTestId("tracking-connection")).toContainText("connected", {
    timeout: 10_000,
  });
  await expect(page.getByTestId("tracking-vehicle-count")).toHaveText("1");
  await expect(page.getByTestId("tracking-vehicle-row")).toContainText("55.87210");
});

test("marks a connected but old GPS snapshot as stale, never live", async ({ page }) => {
  await page.routeWebSocket("ws://localhost:8000/ws", socket => {
    socket.onMessage(message => {
      if (JSON.parse(String(message)).action === "subscribe") {
        socket.send(JSON.stringify({
          type: "vehicle_snapshot",
          data: {
            vehicles: [
              gpsPosition(55.86, new Date(Date.now() - 5 * 60_000).toISOString(), "postgres"),
            ],
          },
        }));
      }
    });
  });
  await page.goto("/tracking");
  await expect(page.getByTestId("tracking-connection")).toContainText("connected");
  await expect(page.getByTestId("tracking-vehicle-count")).toHaveText("1");
  await expect(page.getByTestId("tracking-fresh-count")).toHaveText("0");
  await expect(page.getByTestId("tracking-freshness")).toContainText("STALE");
});

test("never displays seeded vehicles when the live stream has no data", async ({ page }) => {
  await page.routeWebSocket("ws://localhost:8000/ws", socket => {
    socket.onMessage(message => {
      if (JSON.parse(String(message)).action === "subscribe") {
        socket.send(JSON.stringify({ type: "vehicle_snapshot", data: { vehicles: [] } }));
      }
    });
  });
  await page.goto("/tracking");
  await expect(page.getByTestId("tracking-connection")).toContainText("connected");
  await expect(page.getByTestId("tracking-vehicle-count")).toHaveText("0");
  await expect(page.getByTestId("no-live-vehicles")).toBeVisible();
});
