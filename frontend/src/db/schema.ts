import { pgTable, uuid, varchar, text, timestamp, boolean, decimal, integer, jsonb, time, date } from 'drizzle-orm/pg-core';
import { relations } from 'drizzle-orm';

// ============================================
// DEPOTS
// ============================================
export const depots = pgTable('depots', {
  id: uuid('id').primaryKey().defaultRandom(),
  name: varchar('name', { length: 255 }).notNull(),
  address: text('address').notNull(),
  latitude: decimal('latitude', { precision: 10, scale: 7 }).notNull(),
  longitude: decimal('longitude', { precision: 10, scale: 7 }).notNull(),
  capacityVehicles: integer('capacity_vehicles').default(50),
  operatingHoursStart: time('operating_hours_start').default('06:00:00'),
  operatingHoursEnd: time('operating_hours_end').default('22:00:00'),
  isActive: boolean('is_active').default(true),
  createdAt: timestamp('created_at', { withTimezone: true }).defaultNow(),
  updatedAt: timestamp('updated_at', { withTimezone: true }).defaultNow(),
});

// ============================================
// DRIVERS
// ============================================
export const drivers = pgTable('drivers', {
  id: uuid('id').primaryKey().defaultRandom(),
  employeeId: varchar('employee_id', { length: 50 }).unique().notNull(),
  firstName: varchar('first_name', { length: 100 }).notNull(),
  lastName: varchar('last_name', { length: 100 }).notNull(),
  email: varchar('email', { length: 255 }).unique().notNull(),
  phone: varchar('phone', { length: 20 }),
  licenseNumber: varchar('license_number', { length: 50 }),
  licenseExpiry: date('license_expiry'),
  preferredDepotId: uuid('preferred_depot_id').references(() => depots.id),
  maxWorkingHoursPerDay: decimal('max_working_hours_per_day', { precision: 4, scale: 2 }).default('8.00'),
  status: varchar('status', { length: 20 }).default('available'),
  rating: decimal('rating', { precision: 3, scale: 2 }).default('5.00'),
  totalDeliveries: integer('total_deliveries').default(0),
  createdAt: timestamp('created_at', { withTimezone: true }).defaultNow(),
  updatedAt: timestamp('updated_at', { withTimezone: true }).defaultNow(),
});

// ============================================
// VEHICLES
// ============================================
export const vehicles = pgTable('vehicles', {
  id: uuid('id').primaryKey().defaultRandom(),
  vehicleNumber: varchar('vehicle_number', { length: 50 }).unique().notNull(),
  type: varchar('type', { length: 50 }).notNull(),
  make: varchar('make', { length: 100 }),
  model: varchar('model', { length: 100 }),
  year: integer('year'),
  capacityKg: decimal('capacity_kg', { precision: 10, scale: 2 }).notNull(),
  capacityCubicM: decimal('capacity_cubic_m', { precision: 10, scale: 2 }),
  fuelType: varchar('fuel_type', { length: 20 }).default('diesel'),
  fuelEfficiencyKmPerL: decimal('fuel_efficiency_km_per_l', { precision: 5, scale: 2 }),
  co2EmissionGPerKm: decimal('co2_emission_g_per_km', { precision: 6, scale: 2 }),
  depotId: uuid('depot_id').references(() => depots.id),
  currentDriverId: uuid('current_driver_id').references(() => drivers.id),
  latitude: decimal('latitude', { precision: 10, scale: 7 }),
  longitude: decimal('longitude', { precision: 10, scale: 7 }),
  status: varchar('status', { length: 20 }).default('available'),
  lastMaintenanceDate: date('last_maintenance_date'),
  nextMaintenanceDate: date('next_maintenance_date'),
  createdAt: timestamp('created_at', { withTimezone: true }).defaultNow(),
  updatedAt: timestamp('updated_at', { withTimezone: true }).defaultNow(),
});

// ============================================
// CUSTOMERS
// ============================================
export const customers = pgTable('customers', {
  id: uuid('id').primaryKey().defaultRandom(),
  externalId: varchar('external_id', { length: 100 }),
  name: varchar('name', { length: 255 }).notNull(),
  email: varchar('email', { length: 255 }),
  phone: varchar('phone', { length: 20 }),
  address: text('address').notNull(),
  latitude: decimal('latitude', { precision: 10, scale: 7 }).notNull(),
  longitude: decimal('longitude', { precision: 10, scale: 7 }).notNull(),
  deliveryInstructions: text('delivery_instructions'),
  preferredTimeWindowStart: time('preferred_time_window_start'),
  preferredTimeWindowEnd: time('preferred_time_window_end'),
  priority: integer('priority').default(1),
  createdAt: timestamp('created_at', { withTimezone: true }).defaultNow(),
  updatedAt: timestamp('updated_at', { withTimezone: true }).defaultNow(),
});

// ============================================
// ORDERS
// ============================================
export const orders = pgTable('orders', {
  id: uuid('id').primaryKey().defaultRandom(),
  orderNumber: varchar('order_number', { length: 50 }).unique().notNull(),
  customerId: uuid('customer_id').references(() => customers.id),
  depotId: uuid('depot_id').references(() => depots.id),
  items: jsonb('items').default([]),
  totalWeightKg: decimal('total_weight_kg', { precision: 10, scale: 2 }).notNull(),
  totalValue: decimal('total_value', { precision: 12, scale: 2 }),
  deliveryDate: date('delivery_date').notNull(),
  timeWindowStart: timestamp('time_window_start', { withTimezone: true }).notNull(),
  timeWindowEnd: timestamp('time_window_end', { withTimezone: true }).notNull(),
  serviceTimeMinutes: integer('service_time_minutes').default(5),
  status: varchar('status', { length: 30 }).default('pending'),
  priority: integer('priority').default(1),
  source: varchar('source', { length: 50 }).default('manual'),
  externalOrderId: varchar('external_order_id', { length: 100 }),
  createdAt: timestamp('created_at', { withTimezone: true }).defaultNow(),
  updatedAt: timestamp('updated_at', { withTimezone: true }).defaultNow(),
});

// ============================================
// ROUTES
// ============================================
export const routes = pgTable('routes', {
  id: uuid('id').primaryKey().defaultRandom(),
  routeDate: date('route_date').notNull(),
  driverId: uuid('driver_id').references(() => drivers.id),
  vehicleId: uuid('vehicle_id').references(() => vehicles.id),
  depotId: uuid('depot_id').references(() => depots.id),
  plannedDistanceKm: decimal('planned_distance_km', { precision: 10, scale: 2 }),
  plannedDurationMinutes: integer('planned_duration_minutes'),
  plannedStops: integer('planned_stops'),
  actualDistanceKm: decimal('actual_distance_km', { precision: 10, scale: 2 }),
  actualDurationMinutes: integer('actual_duration_minutes'),
  completedStops: integer('completed_stops').default(0),
  algorithmUsed: varchar('algorithm_used', { length: 50 }),
  optimizationScore: decimal('optimization_score', { precision: 5, scale: 4 }),
  computationTimeMs: integer('computation_time_ms'),
  status: varchar('status', { length: 20 }).default('planned'),
  startedAt: timestamp('started_at', { withTimezone: true }),
  completedAt: timestamp('completed_at', { withTimezone: true }),
  createdAt: timestamp('created_at', { withTimezone: true }).defaultNow(),
  updatedAt: timestamp('updated_at', { withTimezone: true }).defaultNow(),
});

// ============================================
// ROUTE STOPS
// ============================================
export const routeStops = pgTable('route_stops', {
  id: uuid('id').primaryKey().defaultRandom(),
  routeId: uuid('route_id').references(() => routes.id, { onDelete: 'cascade' }),
  orderId: uuid('order_id').references(() => orders.id),
  stopSequence: integer('stop_sequence').notNull(),
  latitude: decimal('latitude', { precision: 10, scale: 7 }).notNull(),
  longitude: decimal('longitude', { precision: 10, scale: 7 }).notNull(),
  address: text('address').notNull(),
  plannedArrival: timestamp('planned_arrival', { withTimezone: true }),
  plannedDeparture: timestamp('planned_departure', { withTimezone: true }),
  actualArrival: timestamp('actual_arrival', { withTimezone: true }),
  actualDeparture: timestamp('actual_departure', { withTimezone: true }),
  distanceFromPrevKm: decimal('distance_from_prev_km', { precision: 10, scale: 2 }),
  durationFromPrevMinutes: integer('duration_from_prev_minutes'),
  status: varchar('status', { length: 20 }).default('pending'),
  failureReason: text('failure_reason'),
  signatureUrl: text('signature_url'),
  photoUrl: text('photo_url'),
  recipientName: varchar('recipient_name', { length: 255 }),
  createdAt: timestamp('created_at', { withTimezone: true }).defaultNow(),
  updatedAt: timestamp('updated_at', { withTimezone: true }).defaultNow(),
});

// ============================================
// RELATIONS
// ============================================
export const depotsRelations = relations(depots, ({ many }) => ({
  drivers: many(drivers),
  vehicles: many(vehicles),
  orders: many(orders),
  routes: many(routes),
}));

export const driversRelations = relations(drivers, ({ one, many }) => ({
  preferredDepot: one(depots, {
    fields: [drivers.preferredDepotId],
    references: [depots.id],
  }),
  routes: many(routes),
  vehicle: one(vehicles),
}));

export const vehiclesRelations = relations(vehicles, ({ one, many }) => ({
  depot: one(depots, {
    fields: [vehicles.depotId],
    references: [depots.id],
  }),
  currentDriver: one(drivers, {
    fields: [vehicles.currentDriverId],
    references: [drivers.id],
  }),
  routes: many(routes),
}));

export const ordersRelations = relations(orders, ({ one }) => ({
  customer: one(customers, {
    fields: [orders.customerId],
    references: [customers.id],
  }),
  depot: one(depots, {
    fields: [orders.depotId],
    references: [depots.id],
  }),
}));

export const routesRelations = relations(routes, ({ one, many }) => ({
  driver: one(drivers, {
    fields: [routes.driverId],
    references: [drivers.id],
  }),
  vehicle: one(vehicles, {
    fields: [routes.vehicleId],
    references: [vehicles.id],
  }),
  depot: one(depots, {
    fields: [routes.depotId],
    references: [depots.id],
  }),
  stops: many(routeStops),
}));

export const routeStopsRelations = relations(routeStops, ({ one }) => ({
  route: one(routes, {
    fields: [routeStops.routeId],
    references: [routes.id],
  }),
  order: one(orders, {
    fields: [routeStops.orderId],
    references: [orders.id],
  }),
}));
