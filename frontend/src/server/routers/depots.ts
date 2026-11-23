import { createTRPCRouter, publicProcedure } from '../trpc';
import { fastApiClient } from '@/lib/fastapi-client';

export const depotsRouter = createTRPCRouter({
  getAll: publicProcedure.query(async () => {
    const response = await fastApiClient.listDepots();
    return response.depots;
  }),
});
