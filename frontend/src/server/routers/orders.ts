import { z } from 'zod';
import { createTRPCRouter, publicProcedure } from '../trpc';
import { fastApiClient } from '@/lib/fastapi-client';

export const ordersRouter = createTRPCRouter({
    /**
     * Get all orders with optional filters
     */
    getAll: publicProcedure
        .input(
            z.object({
                status: z.enum(['pending', 'assigned', 'in_transit', 'delivered', 'cancelled']).optional(),
                date: z.string().optional(),
                limit: z.number().min(1).max(100).default(50),
            }).optional()
        )
        .query(async ({ input }) => {
            const response = await fastApiClient.listOrders({
                status: input?.status,
                date: input?.date,
                limit: input?.limit,
            });
            return response.orders || [];
        }),

    /**
     * Get order by ID
     */
    getById: publicProcedure
        .input(z.object({ id: z.string().uuid() }))
        .query(async ({ input }) => {
            return await fastApiClient.getOrder(input.id);
        }),

    /**
     * Create new order
     */
    create: publicProcedure
        .input(
            z.object({
                customer_name: z.string(),
                customer_phone: z.string().optional(),
                delivery_address: z.string(),
                delivery_latitude: z.number(),
                delivery_longitude: z.number(),
                delivery_date: z.string(),
                time_window_start: z.string(),
                time_window_end: z.string(),
                items: z.array(z.object({
                    name: z.string(),
                    quantity: z.number(),
                    weight_kg: z.number(),
                })),
                priority: z.number().min(1).max(5).default(2),
                notes: z.string().optional(),
            })
        )
        .mutation(async ({ input }) => {
            return await fastApiClient.createOrder(input);
        }),

    /**
     * Cancel order
     */
    cancel: publicProcedure
        .input(
            z.object({
                id: z.string().uuid(),
                reason: z.string().optional(),
            })
        )
        .mutation(async ({ input }) => {
            return await fastApiClient.cancelOrder(input.id, input.reason);
        }),

    /**
     * Get order stats
     */
    getStats: publicProcedure
        .query(async () => {
            const stats = await fastApiClient.getStats();
            return stats.orders || {};
        }),
});
