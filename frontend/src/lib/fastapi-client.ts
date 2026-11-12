/**
 * FastAPI Backend Client
 * Proxy layer to call the Python backend from tRPC
 */


/** Wire-format projections: optional fields reflect partial API responses. */
export type BackendOrder = {
    id: string;
    order_number?: string;
    status: string;
    priority?: number;
    customer?: { name?: string } | null;
    delivery_address?: string;
    time_window_start?: string;
};
export type BackendDriver = {
    id: string;
    employee_id?: string;
    name?: string;
    status: string;
    rating?: number | string | null;
    vehicle?: { vehicle_number?: string; latitude?: number; longitude?: number; status?: string } | null;
    depot?: { name?: string } | null;
};
export type BackendVehicle = {
    id: string;
    status?: string;
    latitude?: number;
    longitude?: number;
    vehicle_number?: string;
};
export type BackendRoute = {
    id: string;
    status?: string;
    planned_stops?: number;
    completed_stops?: number;
    planned_distance_km?: number;
    actual_distance_km?: number;
    planned_duration_minutes?: number;
    vehicle?: BackendVehicle | null;
};
export type BackendStats = Record<string, number>;
export type BackendMutationResponse = Record<string, unknown>;
export type RouteOptimizationResponse = {
    status: string;
    message?: string;
    routes: Array<Record<string, unknown>>;
    metrics?: {
        total_vehicles_used: number;
        total_orders_scheduled: number;
        total_distance_km: number;
    };
};

const FASTAPI_BASE_URL = process.env.FASTAPI_URL || 'http://localhost:8000/api/v1';

export class FastAPIClient {
    private baseUrl: string;

    constructor(baseUrl: string = FASTAPI_BASE_URL) {
        this.baseUrl = baseUrl;
    }

    private async request<T>(endpoint: string, options?: RequestInit): Promise<T> {
        const url = `${this.baseUrl}${endpoint}`;

        const response = await fetch(url, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...options?.headers,
            },
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Request failed' }));
            throw new Error(error.detail || `HTTP ${response.status}: ${response.statusText}`);
        }

        return response.json();
    }

    // Drivers
    async listDrivers(params?: { status?: string; depot_id?: string }) {
        const queryParams = new URLSearchParams();
        if (params?.status) queryParams.append('status', params.status);
        if (params?.depot_id) queryParams.append('depot_id', params.depot_id);

        const query = queryParams.toString();
        return this.request<{ drivers: BackendDriver[] }>(`/drivers${query ? `?${query}` : ''}`);
    }

    async getDriver(id: string) {
        return this.request<BackendDriver>(`/drivers/${id}`);
    }

    async updateDriverLocation(id: string, data: {
        latitude: number;
        longitude: number;
        speed_kmh?: number;
        heading?: number;
    }) {
        return this.request<BackendMutationResponse>(`/drivers/${id}/location`, {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    // Orders
    async listOrders(params?: { status?: string; date?: string; limit?: number }) {
        const queryParams = new URLSearchParams();
        if (params?.status) queryParams.append('status', params.status);
        if (params?.date) queryParams.append('date', params.date);
        if (params?.limit) queryParams.append('limit', params.limit.toString());

        const query = queryParams.toString();
        return this.request<{ orders: BackendOrder[] }>(`/orders${query ? `?${query}` : ''}`);
    }

    async getOrder(id: string) {
        return this.request<BackendOrder>(`/orders/${id}`);
    }

    async createOrder(data: unknown) {
        return this.request<BackendMutationResponse>('/orders', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    async cancelOrder(id: string, reason?: string) {
        return this.request<BackendMutationResponse>(`/orders/${id}/cancel`, {
            method: 'POST',
            body: JSON.stringify({ reason }),
        });
    }

    // Routes
    async listRoutes(params?: { date?: string; status?: string; driver_id?: string }) {
        const queryParams = new URLSearchParams();
        if (params?.date) queryParams.append('date', params.date);
        if (params?.status) queryParams.append('status', params.status);
        if (params?.driver_id) queryParams.append('driver_id', params.driver_id);

        const query = queryParams.toString();
        return this.request<{ routes: BackendRoute[] }>(`/routes${query ? `?${query}` : ''}`);
    }

    async getRoute(id: string) {
        return this.request<BackendRoute>(`/routes/${id}`);
    }

    async startRoute(id: string) {
        return this.request<BackendMutationResponse>(`/routes/${id}/start`, {
            method: 'POST',
        });
    }

    async completeStop(routeId: string, stopId: string, data?: unknown) {
        return this.request<BackendMutationResponse>(`/routes/${routeId}/stops/${stopId}/complete`, {
            method: 'POST',
            body: JSON.stringify(data || {}),
        });
    }

    // Vehicles
    async listVehicles(params?: { status?: string; depot_id?: string }) {
        const queryParams = new URLSearchParams();
        if (params?.status) queryParams.append('status', params.status);
        if (params?.depot_id) queryParams.append('depot_id', params.depot_id);

        const query = queryParams.toString();
        return this.request<{ vehicles: BackendVehicle[] }>(`/vehicles${query ? `?${query}` : ''}`);
    }

    async getVehicle(id: string) {
        return this.request<BackendVehicle>(`/vehicles/${id}`);
    }

    async getVehicleLocation(id: string) {
        return this.request<BackendVehicle>(`/vehicles/${id}/location`);
    }

    // Optimization
    async optimizeRoutes(data: { date: string; depot_id: string }) {
        return this.request<RouteOptimizationResponse>('/optimization/routes/optimize', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    // Stats
    async getStats() {
        return Promise.all([
            this.request<BackendStats>('/orders/stats'),
            this.request<BackendStats>('/drivers/stats'),
            this.request<BackendStats>('/routes/stats'),
            this.request<BackendStats>('/vehicles/stats'),
        ]).then(([orders, drivers, routes, vehicles]) => ({
            orders,
            drivers,
            routes,
            vehicles,
        }));
    }
}

export const fastApiClient = new FastAPIClient();
