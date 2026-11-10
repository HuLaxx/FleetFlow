import { test, expect } from '@playwright/test';
import {
  DEMO_DRIVERS, SCENARIO_STOPS, createScenarioStop, orderNearestNeighbor,
  planDispatch, routeDistanceKm, straightLineKm,
} from '../src/lib/dispatch/engine';

test('great-circle distances are symmetric and zero at the same point', () => {
  const origin = { lat: 40.74, lon: -73.99 };
  const destination = { lat: 40.73, lon: -73.98 };
  expect(straightLineKm(origin, origin)).toBe(0);
  expect(straightLineKm(origin, destination)).toBeCloseTo(straightLineKm(destination, origin), 10);
});

test('planner assigns each stop once and respects vehicle weight limits', () => {
  const plan = planDispatch(SCENARIO_STOPS);
  const assigned = plan.routes.flatMap(route => route.stopIds);
  expect(new Set(assigned).size).toBe(assigned.length);
  expect(assigned.length + plan.unassignedIds.length).toBe(SCENARIO_STOPS.length);
  for (const route of plan.routes) {
    const vehicle = DEMO_DRIVERS.find(driver => driver.id === route.driverId)!;
    const actualWeight = SCENARIO_STOPS.filter(stop => route.stopIds.includes(stop.id))
      .reduce((sum, stop) => sum + stop.weightKg, 0);
    expect(route.loadKg).toBe(actualWeight);
    expect(route.loadKg).toBeLessThanOrEqual(vehicle.capacityKg);
    expect(route.distanceKm).toBeGreaterThan(0);
  }
});

test('an overweight delivery stays unassigned, never silently vanishes', () => {
  const heavy = { ...SCENARIO_STOPS[0], id: 'HEAVY', weightKg: 200 };
  const plan = planDispatch([heavy]);
  expect(plan.assignedCount).toBe(0);
  expect(plan.unassignedIds).toEqual(['HEAVY']);
});

test('route planning is repeatable for the same manifest', () => {
  expect(planDispatch(SCENARIO_STOPS)).toEqual(planDispatch(SCENARIO_STOPS));
});

test('nearest-neighbor route visits every input stop exactly once', () => {
  const stops = SCENARIO_STOPS.slice(0, 5);
  const arranged = orderNearestNeighbor(stops, DEMO_DRIVERS[0].depot);
  expect(new Set(arranged.map(stop => stop.id))).toEqual(new Set(stops.map(stop => stop.id)));
  expect(routeDistanceKm([], DEMO_DRIVERS[0].depot)).toBe(0);
});

test('new delivery validation rejects unsupported locations and invalid loads', () => {
  expect(() => createScenarioStop('TEST', 'Acme', 'Atlantis', 20, 'standard')).toThrow();
  expect(() => createScenarioStop('TEST', 'Acme', 'Chelsea', 0, 'standard')).toThrow();
  expect(() => createScenarioStop('TEST', '', 'Chelsea', 10, 'express')).toThrow();
  expect(createScenarioStop('TEST', 'Acme', 'Chelsea', 10, 'express').status).toBe('queued');
});
