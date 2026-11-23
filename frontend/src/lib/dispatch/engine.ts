/**
 * FleetFlow Dispatch Lab domain logic.
 *
 * This is an explicitly simulated, deterministic route-planning environment.
 * Distances are great-circle estimates, NOT road routing, live GPS, or OR-Tools
 * results. Production optimization remains in the Python service.
 */
export type Priority = 'express' | 'standard';
export type StopStatus = 'queued' | 'assigned' | 'delivered';

export type Point = { lat: number; lon: number };

export interface DispatchStop {
  id: string;
  recipient: string;
  address: string;
  point: Point;
  weightKg: number;
  priority: Priority;
  status: StopStatus;
  driverId?: string;
}

export interface DispatchDriver {
  id: string;
  name: string;
  vehicle: string;
  capacityKg: number;
  color: string;
  depot: Point;
}

export interface PlannedRoute {
  driverId: string;
  stopIds: string[];
  loadKg: number;
  distanceKm: number;
  manifestOrderKm: number;
}

export interface DispatchPlan {
  routes: PlannedRoute[];
  unassignedIds: string[];
  totalKm: number;
  manifestOrderKm: number;
  assignedCount: number;
}

export const DEPOT: Point = { lat: 40.7413, lon: -73.9897 };

export const DEMO_DRIVERS: DispatchDriver[] = [
  { id: 'V-01', name: 'Avery Cole', vehicle: 'Electric van · 01', capacityKg: 72, color: '#78e1b5', depot: DEPOT },
  { id: 'V-02', name: 'Jordan Lee', vehicle: 'Cargo van · 02', capacityKg: 95, color: '#ffbf7b', depot: DEPOT },
  { id: 'V-03', name: 'Morgan Park', vehicle: 'Light vehicle · 03', capacityKg: 64, color: '#91b9ff', depot: DEPOT },
];

export const SCENARIO_STOPS: DispatchStop[] = [
  { id: 'FF-1042', recipient: 'Bleecker Studio', address: 'West Village', point: { lat: 40.7324, lon: -74.0033 }, weightKg: 18, priority: 'express', status: 'queued' },
  { id: 'FF-1043', recipient: 'The Mercer', address: 'SoHo', point: { lat: 40.7243, lon: -73.9993 }, weightKg: 22, priority: 'standard', status: 'queued' },
  { id: 'FF-1044', recipient: 'Hudson Supply', address: 'Chelsea', point: { lat: 40.7485, lon: -74.0025 }, weightKg: 26, priority: 'express', status: 'queued' },
  { id: 'FF-1045', recipient: 'Cooper Works', address: 'East Village', point: { lat: 40.7293, lon: -73.9858 }, weightKg: 11, priority: 'standard', status: 'queued' },
  { id: 'FF-1046', recipient: 'Parkside Atelier', address: 'Gramercy', point: { lat: 40.7375, lon: -73.9834 }, weightKg: 14, priority: 'standard', status: 'queued' },
  { id: 'FF-1047', recipient: 'Madison Market', address: 'Midtown East', point: { lat: 40.7543, lon: -73.9741 }, weightKg: 20, priority: 'express', status: 'queued' },
  { id: 'FF-1048', recipient: 'Canal Collective', address: 'Chinatown', point: { lat: 40.7169, lon: -73.9981 }, weightKg: 12, priority: 'standard', status: 'queued' },
  { id: 'FF-1049', recipient: 'Union Hardware', address: 'Union Square', point: { lat: 40.7359, lon: -73.9909 }, weightKg: 17, priority: 'standard', status: 'queued' },
  { id: 'FF-1050', recipient: 'Broadway Print', address: 'NoMad', point: { lat: 40.7455, lon: -73.9872 }, weightKg: 24, priority: 'express', status: 'queued' },
];

export const AREA_PRESETS: { name: string; point: Point }[] = [
  { name: 'Chelsea', point: { lat: 40.7492, lon: -74.0017 } },
  { name: 'SoHo', point: { lat: 40.7243, lon: -73.9993 } },
  { name: 'Gramercy', point: { lat: 40.7381, lon: -73.9831 } },
  { name: 'East Village', point: { lat: 40.7286, lon: -73.9829 } },
  { name: 'Midtown', point: { lat: 40.7552, lon: -73.9840 } },
];

/** Great-circle distance for comparison only; it does not follow streets. */
export function straightLineKm(a: Point, b: Point): number {
  const rad = (degrees: number) => degrees * Math.PI / 180;
  const deltaLat = rad(b.lat - a.lat);
  const deltaLon = rad(b.lon - a.lon);
  const value = Math.sin(deltaLat / 2) ** 2
    + Math.cos(rad(a.lat)) * Math.cos(rad(b.lat)) * Math.sin(deltaLon / 2) ** 2;
  return 6371 * 2 * Math.atan2(Math.sqrt(value), Math.sqrt(Math.max(0, 1 - value)));
}

/** Round-trip distance, beginning and ending at the vehicle's depot. */
export function routeDistanceKm(stops: DispatchStop[], depot: Point): number {
  if (!stops.length) return 0;
  let total = 0;
  let previous = depot;
  for (const stop of stops) {
    total += straightLineKm(previous, stop.point);
    previous = stop.point;
  }
  return total + straightLineKm(previous, depot);
}

/** Deterministic nearest-neighbor ordering. Does not promise a global optimum. */
export function orderNearestNeighbor(stops: DispatchStop[], depot: Point): DispatchStop[] {
  const remaining = [...stops];
  const result: DispatchStop[] = [];
  let from = depot;
  while (remaining.length) {
    remaining.sort((a, b) => straightLineKm(from, a.point) - straightLineKm(from, b.point) || a.id.localeCompare(b.id));
    const next = remaining.shift()!;
    result.push(next);
    from = next.point;
  }
  return result;
}

/**
 * Assigns eligible orders to vehicles within their weight capacity.
 * Orders are considered express-first; a minimum incremental-distance heuristic
 * balances proximity and existing stop counts. Unassigned orders remain visible.
 */
export function planDispatch(
  stops: DispatchStop[],
  drivers: DispatchDriver[] = DEMO_DRIVERS,
): DispatchPlan {
  const queued = stops.filter(stop => stop.status === 'queued');
  const ordered = [...queued].sort((a, b) => (
    (a.priority === 'express' ? 0 : 1) - (b.priority === 'express' ? 0 : 1)
    || a.id.localeCompare(b.id)
  ));
  const allocations = new Map(drivers.map(driver => [driver.id, [] as DispatchStop[]]));
  const unassignedIds: string[] = [];

  for (const stop of ordered) {
    const eligible = drivers
      .map(driver => {
        const assigned = allocations.get(driver.id)!;
        const load = assigned.reduce((sum, current) => sum + current.weightKg, 0);
        if (load + stop.weightKg > driver.capacityKg) return null;
        const last = assigned.length ? assigned[assigned.length - 1].point : driver.depot;
        const increment = straightLineKm(last, stop.point) + straightLineKm(stop.point, driver.depot)
          - straightLineKm(last, driver.depot);
        return { driver, score: increment + assigned.length * 0.85 };
      })
      .filter((candidate): candidate is { driver: DispatchDriver; score: number } => candidate !== null)
      .sort((a, b) => a.score - b.score || a.driver.id.localeCompare(b.driver.id));

    if (!eligible.length) {
      unassignedIds.push(stop.id);
      continue;
    }
    allocations.get(eligible[0].driver.id)!.push(stop);
  }

  const routes: PlannedRoute[] = drivers
    .map(driver => {
      const initial = allocations.get(driver.id)!;
      if (!initial.length) return null;
      const sequence = orderNearestNeighbor(initial, driver.depot);
      return {
        driverId: driver.id,
        stopIds: sequence.map(stop => stop.id),
        loadKg: initial.reduce((sum, stop) => sum + stop.weightKg, 0),
        distanceKm: routeDistanceKm(sequence, driver.depot),
        manifestOrderKm: routeDistanceKm(initial, driver.depot),
      };
    })
    .filter((route): route is PlannedRoute => route !== null);

  return {
    routes,
    unassignedIds,
    totalKm: routes.reduce((sum, route) => sum + route.distanceKm, 0),
    manifestOrderKm: routes.reduce((sum, route) => sum + route.manifestOrderKm, 0),
    assignedCount: routes.reduce((sum, route) => sum + route.stopIds.length, 0),
  };
}

export function createScenarioStop(
  id: string,
  recipient: string,
  zone: string,
  weightKg: number,
  priority: Priority,
): DispatchStop {
  const area = AREA_PRESETS.find(item => item.name === zone);
  if (!area) throw new Error('Choose an available delivery zone.');
  const name = recipient.trim();
  if (!name || name.length > 60) throw new Error('Enter a recipient name (1–60 characters).');
  if (!Number.isFinite(weightKg) || weightKg <= 0 || weightKg > 50) throw new Error('Weight must be between 1 and 50 kg.');
  return { id, recipient: name, address: zone, weightKg, point: { ...area.point }, priority, status: 'queued' };
}
