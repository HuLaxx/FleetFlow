/**
 * FastAPI Backend Client
 * Proxy layer to call the Python backend from tRPC
 */

import { toDisplayDriver, toDisplayOrder } from './fleet-adapters';

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
                ...(process.env.FASTAPI_API_KEY ? { 'X-API-Key': process.env.FASTAPI_API_KEY } : {}),
                ...options?.headers,
            },
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Request failed' }));
            throw new Error(error.detail || `HTTP ${response.status}: ${response.statusText}`);
        }

        return response.json();
    }

    // Active depots for validated route optimization requests
    async listDepots(): Promise<{ depots: { id: string; name: string; address: string; latitude: number; longitude: number }[] }> {
        return this.request('/depots');
    }

    // Drivers
    async listDrivers(params?: { status?: string; depot_id?: string }) {
        const queryParams = new URLSearchParams();
        if (params?.status) queryParams.append('status', params.status);
        if (params?.depot_id) queryParams.append('depot_id', params.depot_id);

        const query = queryParams.toString();
        const response = await this.request<{ drivers?: Parameters<typeof toDisplayDriver>[0][]; total?: number }>(`/drivers${query ? `?${query}` : ''}`);
        return { ...response, drivers: (response.drivers || []).map(toDisplayDriver) };
    }

    async getDriver(id: string) {
        return this.request<any>(`/drivers/${id}`);
    }

    async updateDriverLocation(id: string, data: {
        latitude: number;
        longitude: number;
        speed_kmh?: number;
        heading?: number;
    }) {
        return this.request<any>(`/drivers/${id}/location`, {
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
        const response = await this.request<{ orders?: Parameters<typeof toDisplayOrder>[0][]; total?: number }>(`/orders${query ? `?${query}` : ''}`);
        return { ...response, orders: (response.orders || []).map(toDisplayOrder) };
    }

    async getOrder(id: string) {
        return this.request<any>(`/orders/${id}`);
    }

    async createOrder(data: any) {
        return this.request<any>('/orders', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    async cancelOrder(id: string, reason?: string) {
        return this.request<any>(`/orders/${id}/cancel`, {
            method: 'POST',
            body: JSON.stringify({ reason: reason?.trim() || 'Cancelled by dispatcher' }),
        });
    }

    // Routes
    async listRoutes(params?: { date?: string; status?: string; driver_id?: string }) {
        const queryParams = new URLSearchParams();
        if (params?.date) queryParams.append('date', params.date);
        if (params?.status) queryParams.append('status', params.status);
        if (params?.driver_id) queryParams.append('driver_id', params.driver_id);

        const query = queryParams.toString();
        return this.request<any>(`/routes${query ? `?${query}` : ''}`);
    }

    async getRoute(id: string) {
        return this.request<any>(`/routes/${id}`);
    }

    async startRoute(id: string) {
        return this.request<any>(`/routes/${id}/start`, {
            method: 'POST',
        });
    }

    async completeStop(routeId: string, stopId: string, data?: any) {
        return this.request<any>(`/routes/${routeId}/stops/${stopId}/complete`, {
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
        return this.request<any>(`/vehicles${query ? `?${query}` : ''}`);
    }

    async getVehicle(id: string) {
        return this.request<any>(`/vehicles/${id}`);
    }

    async getVehicleLocation(id: string) {
        return this.request<any>(`/vehicles/${id}/location`);
    }

    // Optimization
    async optimizeRoutes(data: { date: string; depot_id: string }) {
        return this.request<any>('/optimization/routes/optimize', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    // Stats
    async getStats() {
        return Promise.all([
            this.request<any>('/orders/stats/summary'),
            this.request<any>('/drivers/stats/summary'),
            this.request<any>('/routes/stats/summary'),
            this.request<any>('/vehicles/stats/summary'),
        ]).then(([orders, drivers, routes, vehicles]) => ({
            orders,
            drivers,
            routes,
            vehicles,
        }));
    }
}

export const fastApiClient = new FastAPIClient();
