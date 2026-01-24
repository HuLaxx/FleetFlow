import { z } from 'zod';
import { createTRPCRouter, publicProcedure } from '../trpc';
import { fastApiClient } from '@/lib/fastapi-client';

export const vehiclesRouter = createTRPCRouter({
    /**
     * Get all vehicles
     */
    getAll: publicProcedure
        .input(
            z.object({
                status: z.enum(['available', 'in_use', 'maintenance', 'out_of_service']).optional(),
                depot_id: z.string().uuid().optional(),
                limit: z.number().min(1).max(100).default(50),
            }).optional()
        )
        .query(async ({ input }) => {
            const response = await fastApiClient.listVehicles({
                status: input?.status,
                depot_id: input?.depot_id,
            });

            const vehicles = response.vehicles || [];
            return input?.limit ? vehicles.slice(0, input.limit) : vehicles;
        }),

    /**
     * Get vehicle by ID
     */
    getById: publicProcedure
        .input(z.object({ id: z.string().uuid() }))
        .query(async ({ input }) => {
            return await fastApiClient.getVehicle(input.id);
        }),

    /**
     * Get vehicle location
     */
    getLocation: publicProcedure
        .input(z.object({ id: z.string().uuid() }))
        .query(async ({ input }) => {
            return await fastApiClient.getVehicleLocation(input.id);
        }),

    /**
     * Get vehicle stats
     */
    getStats: publicProcedure
        .query(async () => {
            const stats = await fastApiClient.getStats();
            return stats.vehicles || {};
        }),
});
