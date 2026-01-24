import { z } from 'zod';
import { createTRPCRouter, publicProcedure } from '../trpc';
import { fastApiClient } from '@/lib/fastapi-client';

export const driversRouter = createTRPCRouter({
    /**
     * Get all drivers with optional status filter
     */
    getAll: publicProcedure
        .input(
            z.object({
                status: z.enum(['available', 'on_route', 'on_break', 'offline']).optional(),
                limit: z.number().min(1).max(100).default(50),
                depot_id: z.string().uuid().optional(),
            }).optional()
        )
        .query(async ({ input }) => {
            const response = await fastApiClient.listDrivers({
                status: input?.status,
                depot_id: input?.depot_id,
            });

            const drivers = response.drivers || [];
            return input?.limit ? drivers.slice(0, input.limit) : drivers;
        }),

    /**
     * Get driver by ID
     */
    getById: publicProcedure
        .input(z.object({ id: z.string().uuid() }))
        .query(async ({ input }) => {
            return await fastApiClient.getDriver(input.id);
        }),

    /**
     * Get driver's current location (from vehicle)
     */
    getLocation: publicProcedure
        .input(z.object({ driverId: z.string().uuid() }))
        .query(async ({ input }) => {
            const driver = await fastApiClient.getDriver(input.driverId);

            // Return vehicle location if available
            if (driver.vehicle) {
                return {
                    latitude: driver.vehicle.latitude,
                    longitude: driver.vehicle.longitude,
                    status: driver.vehicle.status,
                };
            }

            return null;
        }),

    /**
     * Update driver location (GPS tracking)
     */
    updateLocation: publicProcedure
        .input(
            z.object({
                id: z.string().uuid(),
                latitude: z.number(),
                longitude: z.number(),
                speed_kmh: z.number().optional(),
                heading: z.number().optional(),
            })
        )
        .mutation(async ({ input }) => {
            const { id, ...location } = input;
            return await fastApiClient.updateDriverLocation(id, location);
        }),

    /**
     * Get driver stats
     */
    getStats: publicProcedure
        .query(async () => {
            const stats = await fastApiClient.getStats();
            return stats.drivers || {};
        }),
});
