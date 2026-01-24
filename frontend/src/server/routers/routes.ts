import { z } from 'zod';
import { createTRPCRouter, publicProcedure } from '../trpc';
import { fastApiClient } from '@/lib/fastapi-client';

export const routesRouter = createTRPCRouter({
    /**
     * Get all routes for a specific date
     */
    getByDate: publicProcedure
        .input(
            z.object({
                date: z.string(), // ISO date string
                status: z.enum(['planned', 'in_progress', 'completed', 'cancelled']).optional(),
            })
        )
        .query(async ({ input }) => {
            const response = await fastApiClient.listRoutes({
                date: input.date,
                status: input.status,
            });
            return response.routes || [];
        }),

    /**
     * Get route by ID with all stops
     */
    getById: publicProcedure
        .input(z.object({ id: z.string().uuid() }))
        .query(async ({ input }) => {
            return await fastApiClient.getRoute(input.id);
        }),

    /**
     * Get driver's current route
     */
    getDriverCurrentRoute: publicProcedure
        .input(z.object({ driverId: z.string().uuid() }))
        .query(async ({ input }) => {
            const response = await fastApiClient.listRoutes({
                driver_id: input.driverId,
                status: 'in_progress',
            });

            // Return first in-progress route
            return response.routes?.[0] || null;
        }),

    /**
     * Start a route
     */
    startRoute: publicProcedure
        .input(z.object({ routeId: z.string().uuid() }))
        .mutation(async ({ input }) => {
            return await fastApiClient.startRoute(input.routeId);
        }),

    /**
     * Complete a stop
     */
    completeStop: publicProcedure
        .input(
            z.object({
                routeId: z.string().uuid(),
                stopId: z.string().uuid(),
                signature: z.string().optional(),
                photo: z.string().optional(),
                notes: z.string().optional(),
            })
        )
        .mutation(async ({ input }) => {
            const { routeId, stopId, ...data } = input;
            return await fastApiClient.completeStop(routeId, stopId, data);
        }),

    /**
     * Get route progress/metrics
     */
    getProgress: publicProcedure
        .input(z.object({ routeId: z.string().uuid() }))
        .query(async ({ input }) => {
            // Get full route details which includes progress
            const route = await fastApiClient.getRoute(input.routeId);

            return {
                total_stops: route.planned_stops || 0,
                completed_stops: route.completed_stops || 0,
                planned_distance_km: route.planned_distance_km || 0,
                actual_distance_km: route.actual_distance_km || 0,
                planned_duration_minutes: route.planned_duration_minutes || 0,
                current_location: route.vehicle?.latitude && route.vehicle?.longitude
                    ? { latitude: route.vehicle.latitude, longitude: route.vehicle.longitude }
                    : null,
            };
        }),

    /**
     * Get route stats
     */
    getStats: publicProcedure
        .query(async () => {
            const stats = await fastApiClient.getStats();
            return stats.routes || {};
        }),
});
