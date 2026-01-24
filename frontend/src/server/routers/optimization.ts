import { z } from 'zod';
import { createTRPCRouter, publicProcedure } from '../trpc';
import { fastApiClient } from '@/lib/fastapi-client';

export const optimizationRouter = createTRPCRouter({
    /**
     * Optimize routes for a given date and depot
     */
    optimizeRoutes: publicProcedure
        .input(
            z.object({
                date: z.string(), // YYYY-MM-DD format
                depot_id: z.string().uuid(),
            })
        )
        .mutation(async ({ input }) => {
            return await fastApiClient.optimizeRoutes(input);
        }),
});
