/**
 * Anti-corruption layer between the Python REST contract and the operator UI.
 * Preserve the backend's field names at the network boundary and normalize
 * them in one place instead of scattering `any` field fallbacks across views.
 */
export interface ApiOrder {
  id?: string;
  order_id?: string;
  order_number?: string;
  status?: string;
  customer_name?: string;
  customer?: { name?: string } | null;
  address?: string | { street?: string } | null;
  delivery_address?: string;
  time_window?: string | { start?: string; end?: string } | null;
  priority?: number;
  total_weight_kg?: number;
}

export interface DisplayOrder {
  id: string;
  order_number: string;
  status: string;
  customer: { name: string };
  delivery_address: string;
  time_window: string;
  priority: number;
  total_weight_kg: number;
}

export function toDisplayOrder(order: ApiOrder): DisplayOrder {
  const address = typeof order.address === 'string'
    ? order.address
    : order.address?.street ?? '';
  const windowText = typeof order.time_window === 'string'
    ? order.time_window
    : order.time_window && typeof order.time_window === 'object'
      ? [order.time_window.start, order.time_window.end].filter(Boolean).join(' – ')
      : '';
  const id = order.id || order.order_id || '';
  return {
    id,
    order_number: order.order_number || id || 'Unknown order',
    status: order.status || 'pending',
    customer: { name: order.customer?.name || order.customer_name || 'Unknown customer' },
    delivery_address: order.delivery_address || address || 'Address unavailable',
    time_window: windowText,
    priority: Number.isFinite(order.priority) ? Number(order.priority) : 2,
    total_weight_kg: Number.isFinite(order.total_weight_kg) ? Number(order.total_weight_kg) : 0,
  };
}

export interface ApiDriver {
  id?: string;
  employee_id?: string;
  name?: string;
  status?: string;
  rating?: number;
  vehicle?: { number?: string; vehicle_number?: string } | null;
  preferred_depot?: { name?: string } | null;
  depot?: { name?: string } | null;
}

export interface DisplayDriver {
  id: string;
  employee_id: string;
  name: string;
  status: string;
  rating: number | null;
  vehicle: { vehicle_number: string } | null;
  depot: { name: string } | null;
}

export function toDisplayDriver(driver: ApiDriver): DisplayDriver {
  return {
    id: driver.id || '',
    employee_id: driver.employee_id || '',
    name: driver.name || 'Unknown driver',
    status: driver.status || 'offline',
    rating: typeof driver.rating === 'number' && Number.isFinite(driver.rating) ? driver.rating : null,
    vehicle: driver.vehicle ? { vehicle_number: driver.vehicle.vehicle_number || driver.vehicle.number || 'Unknown vehicle' } : null,
    depot: driver.depot?.name || driver.preferred_depot?.name
      ? { name: driver.depot?.name || driver.preferred_depot?.name || '' }
      : null,
  };
}
