"""Deterministic, local OR-Tools CVRPTW planning with documented approximations.

Coordinates originate from related Customer records, not the Order ORM table.
Distance uses Haversine rather than road-network travel; travel time assumes an
illustrative fixed speed of 30 km/h. This is a planning prototype, not live ETA.
"""

import math
from datetime import UTC, date, datetime, timedelta
from typing import Any

import structlog
from ortools.constraint_solver import pywrapcp, routing_enums_pb2

logger = structlog.get_logger()


class VehicleRoutingOptimizer:
    """Capacity-constrained route planning with UTC delivery windows."""

    def __init__(self, planning_time_limit_sec: int = 5):
        self.time_limit_sec = planning_time_limit_sec

    def optimize(
        self,
        orders: list[Any],
        vehicles: list[Any],
        depot: Any,
        route_date: date,
    ) -> list[dict[str, Any]]:
        if not orders or not vehicles:
            return []
        if any(order.customer is None for order in orders):
            raise ValueError("Every order needs a customer delivery location")
        if any(float(order.total_weight_kg) <= 0 for order in orders):
            raise ValueError("Order weights must be positive")
        if any(float(vehicle.capacity_kg) <= 0 for vehicle in vehicles):
            raise ValueError("Vehicle capacities must be positive")

        locations = [
            (float(depot.latitude), float(depot.longitude)),
            *[
                (float(order.customer.latitude), float(order.customer.longitude))
                for order in orders
            ],
        ]
        distances = [
            [round(self._haversine(*origin, *destination)) for destination in locations]
            for origin in locations
        ]
        # Both distance and travel time are approximate, never road-network results.
        travel_seconds = [
            [math.ceil(distance / (30_000 / 3_600)) for distance in row] for row in distances
        ]
        service_seconds = [0] + [int(order.service_time_minutes or 0) * 60 for order in orders]
        demands = [0] + [math.ceil(float(order.total_weight_kg) * 1000) for order in orders]
        capacities = [math.floor(float(vehicle.capacity_kg) * 1000) for vehicle in vehicles]

        depot_start = self._time_to_seconds(depot.operating_hours_start, default=6 * 3600)
        depot_end = self._time_to_seconds(depot.operating_hours_end, default=22 * 3600)
        windows = [(depot_start, depot_end)] + [
            (
                self._datetime_to_seconds(order.time_window_start, route_date),
                self._datetime_to_seconds(order.time_window_end, route_date),
            )
            for order in orders
        ]
        if any(start < 0 or end > 24 * 3600 or start > end for start, end in windows):
            raise ValueError("Time windows must be within the same UTC route date")

        manager = pywrapcp.RoutingIndexManager(len(locations), len(vehicles), 0)
        routing = pywrapcp.RoutingModel(manager)

        def distance_callback(from_index: int, to_index: int) -> int:
            return distances[manager.IndexToNode(from_index)][manager.IndexToNode(to_index)]

        distance_callback_index = routing.RegisterTransitCallback(distance_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(distance_callback_index)

        def demand_callback(from_index: int) -> int:
            return demands[manager.IndexToNode(from_index)]

        demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
        routing.AddDimensionWithVehicleCapacity(
            demand_callback_index, 0, capacities, True, "Capacity"
        )

        def time_callback(from_index: int, to_index: int) -> int:
            source = manager.IndexToNode(from_index)
            destination = manager.IndexToNode(to_index)
            return service_seconds[source] + travel_seconds[source][destination]

        time_callback_index = routing.RegisterTransitCallback(time_callback)
        routing.AddDimension(
            time_callback_index,
            24 * 3600,
            24 * 3600,
            False,
            "Time",
        )
        times = routing.GetDimensionOrDie("Time")

        for node, (earliest, latest) in enumerate(windows):
            if node == 0:
                continue
            times.CumulVar(manager.NodeToIndex(node)).SetRange(earliest, latest)

        for index in range(len(vehicles)):
            times.CumulVar(routing.Start(index)).SetRange(depot_start, depot_end)
            times.CumulVar(routing.End(index)).SetRange(depot_start, depot_end)

        search = pywrapcp.DefaultRoutingSearchParameters()
        search.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        search.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        )
        search.time_limit.seconds = self.time_limit_sec

        solution = routing.SolveWithParameters(search)
        if solution is None:
            logger.info("No feasible FleetFlow route")
            return []

        result = []
        for vehicle_index, vehicle in enumerate(vehicles):
            index = routing.Start(vehicle_index)
            if routing.IsEnd(solution.Value(routing.NextVar(index))):
                continue

            stops = []
            total_meters = 0
            while not routing.IsEnd(index):
                node = manager.IndexToNode(index)
                if node > 0:
                    order = orders[node - 1]
                    arrival = solution.Min(times.CumulVar(index))
                    stops.append(
                        {
                            "sequence": len(stops) + 1,
                            "order_id": order.id,
                            "planned_arrival": self._seconds_to_datetime(arrival, route_date),
                            "location": {
                                "latitude": float(order.customer.latitude),
                                "longitude": float(order.customer.longitude),
                                "address": order.customer.address,
                            },
                            "type": "delivery",
                        }
                    )

                next_index = solution.Value(routing.NextVar(index))
                total_meters += distances[node][manager.IndexToNode(next_index)]
                index = next_index

            start = solution.Min(times.CumulVar(routing.Start(vehicle_index)))
            finish = solution.Min(times.CumulVar(routing.End(vehicle_index)))
            result.append(
                {
                    "vehicle_id": vehicle.id,
                    "driver_id": vehicle.current_driver_id,
                    "depot_id": depot.id,
                    "route_date": route_date,
                    "stops": stops,
                    "metrics": {
                        "total_distance_km": total_meters / 1000,
                        "total_duration_minutes": math.ceil((finish - start) / 60),
                        "total_stops": len(stops),
                    },
                }
            )

        return result

    @staticmethod
    def _time_to_seconds(value: Any, *, default: int = 0) -> int:
        if value is None:
            return default
        return value.hour * 3600 + value.minute * 60 + value.second

    @staticmethod
    def _datetime_to_seconds(value: datetime, route_date: date) -> int:
        if value.tzinfo is not None:
            value = value.astimezone(UTC).replace(tzinfo=None)
        midnight = datetime.combine(route_date, datetime.min.time())
        return int((value - midnight).total_seconds())

    @staticmethod
    def _seconds_to_datetime(value: int, route_date: date) -> datetime:
        # The existing PostgreSQL schema stores UTC as naive timestamps.
        return datetime.combine(route_date, datetime.min.time()) + timedelta(seconds=value)

    @staticmethod
    def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        radius = 6_371_000
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
        return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
