import { createTRPCRouter } from './trpc';
import { driversRouter } from './routers/drivers';
import { ordersRouter } from './routers/orders';
import { routesRouter } from './routers/routes';
import { vehiclesRouter } from './routers/vehicles';
import { optimizationRouter } from './routers/optimization';

/**
 * Main tRPC router - combines all sub-routers
 * Now proxies to FastAPI backend instead of direct DB queries
 */
export const appRouter = createTRPCRouter({
    drivers: driversRouter,
    orders: ordersRouter,
    routes: routesRouter,
    vehicles: vehiclesRouter,
    optimization: optimizationRouter,
});

export type AppRouter = typeof appRouter;
