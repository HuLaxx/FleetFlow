"""
Vehicle Routing Problem (VRP) Optimizer using Google OR-Tools.

Implements Capacitated Vehicle Routing Problem with Time Windows (CVRPTW).
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID
import math

from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
import structlog

# Type hints for ORM models - these are passed in from the API layer
# from src.models import Order, Vehicle, Depot, Route (if running integrated)
# When running standalone, define data classes or use duck-typing

logger = structlog.get_logger()

class VehicleRoutingOptimizer:
    """
    Optimizer for Vehicle Routing Problem with Time Windows and Capacity constraints.
    """

    def __init__(self, planning_time_limit_sec: int = 30):
        self.time_limit_sec = planning_time_limit_sec
        self.scaling_factor = 1000  # To handle float coordinates/distances as integers

    def optimize(
        self,
        orders: List[Any],  # List[Order]
        vehicles: List[Any],  # List[Vehicle]
        depot: Any,  # Depot
        route_date: datetime.date
    ) -> List[Dict[str, Any]]:
        """
        Run VRP optimization.

        Args:
            orders: List of Order objects with location, weight, and time windows.
            vehicles: List of Vehicle objects with capacity.
            depot: Depot object with location and operating hours.
            route_date: Date for the routes.

        Returns:
            List of route plans (dictionaries) suitable for creating Route objects.
        """
        if not orders or not vehicles:
            logger.warning("No orders or vehicles provided for optimization")
            return []

        # A failed relation is a data-quality error, not a zero-distance destination.
        if any(order.customer is None for order in orders):
            raise ValueError("Every order must have a valid customer delivery location")
        if any(float(order.total_weight_kg) <= 0 for order in orders):
            raise ValueError("Order weight must be positive")
        if any(float(vehicle.capacity_kg) <= 0 for vehicle in vehicles):
            raise ValueError("Vehicle capacity must be positive")

        # 1. Create Data Model
        data = self._create_data_model(orders, vehicles, depot, route_date)
        
        # 2. Create Routing Manager
        manager = pywrapcp.RoutingIndexManager(
            len(data['time_matrix']),
            data['num_vehicles'],
            data['depot_index']
        )

        # 3. Create Routing Model
        routing = pywrapcp.RoutingModel(manager)

        # 4. Define Weight/Distance Callback
        def distance_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return data['distance_matrix'][from_node][to_node]

        transit_callback_index = routing.RegisterTransitCallback(distance_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

        # 5. Add Capacity Constraint
        def demand_callback(from_index):
            from_node = manager.IndexToNode(from_index)
            return data['demands'][from_node]

        demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
        routing.AddDimensionWithVehicleCapacity(
            demand_callback_index,
            0,  # null capacity slack
            data['vehicle_capacities'],  # vehicle maximum capacities
            True,  # start cumul to zero
            'Capacity'
        )

        # 6. Add Time Window Constraint
        def time_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            # Service time + Travel time
            service_time = data['service_times'][from_node]
            travel_time = data['time_matrix'][from_node][to_node]
            return service_time + travel_time

        time_callback_index = routing.RegisterTransitCallback(time_callback)
        routing.AddDimension(
            time_callback_index,
            30 * 60,  # allow waiting time (30 mins max waiting at a stop before window opens?) - actually usually larger
            data['horizon'],  # maximum time per vehicle
            False,  # Don't force start cumul to zero
            'Time'
        )
        time_dimension = routing.GetDimensionOrDie('Time')
        
        # Add time window constraints for each location
        for location_idx, time_window in enumerate(data['time_windows']):
            if location_idx == data['depot_index']:
                continue
            index = manager.NodeToIndex(location_idx)
            time_dimension.CumulVar(index).SetRange(time_window[0], time_window[1])

        # Add time window constraints for depot (start and end times)
        depot_idx = data['depot_index']
        for vehicle_id in range(data['num_vehicles']):
            index = routing.Start(vehicle_id)
            time_dimension.CumulVar(index).SetRange(
                data['time_windows'][depot_idx][0],
                data['time_windows'][depot_idx][1]
            )
            index = routing.End(vehicle_id)
            time_dimension.CumulVar(index).SetRange(
                data['time_windows'][depot_idx][0],
                data['time_windows'][depot_idx][1]
            )

        # 7. Set Search Parameters
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        )
        search_parameters.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        )
        search_parameters.time_limit.seconds = self.time_limit_sec

        # 8. Solve
        solution = routing.SolveWithParameters(search_parameters)

        # 9. Format Solution
        if solution:
            return self._format_solution(data, manager, routing, solution, orders, vehicles, depot, route_date)
        else:
            logger.warning("No solution found for VRP")
            return []

    def _create_data_model(self, orders, vehicles, depot, route_date):
        """Prepares data model for OR-Tools."""
        data = {}
        
        # Combine depot and orders into a single list of locations
        # Index 0 is Depot
        all_locations = [depot] + [order.customer for order in orders]
        data['locations'] = [(float(loc.latitude), float(loc.longitude)) for loc in all_locations]
        
        # Distance and Time Matrices
        # In production, use OSRM or Valhalla. Here using Haversine/Euclidean approximation for simplicity/demo
        data['distance_matrix'] = self._compute_distance_matrix(data['locations'])
        data['time_matrix'] = self._compute_time_matrix(data['distance_matrix']) # simple avg speed assumption
        
        # Demands (Weight)
        # Depot has 0 demand
        data['demands'] = [0] + [math.ceil(float(order.total_weight_kg) * 1000) for order in orders]
        
        # Vehicle Capacities
        data['vehicle_capacities'] = [math.floor(float(v.capacity_kg) * 1000) for v in vehicles]
        data['num_vehicles'] = len(vehicles)
        data['depot_index'] = 0
        
        # Service Times (seconds)
        # Depot: 0, Orders: usually defined in order or default to 5-10 mins
        data['service_times'] = [0] + [getattr(o, 'service_time_minutes', 10) * 60 for o in orders]
        
        # Time Windows (seconds from midnight)
        # Normalize everything to seconds from route_date midnight
        data['time_windows'] = []
        
        # Depot window
        depot_start = self._time_to_seconds(depot.operating_hours_start) if depot.operating_hours_start else 8 * 3600
        depot_end = self._time_to_seconds(depot.operating_hours_end) if depot.operating_hours_end else 20 * 3600
        data['time_windows'].append((depot_start, depot_end))
        
        # Order windows
        for order in orders:
            start = self._datetime_to_seconds(order.time_window_start, route_date)
            end = self._datetime_to_seconds(order.time_window_end, route_date)
            data['time_windows'].append((start, end))
            
        data['horizon'] = 24 * 3600 # Max horizon is end of day
        
        return data

    def _format_solution(self, data, manager, routing, solution, orders, vehicles, depot, route_date):
        routes = []
        time_dimension = routing.GetDimensionOrDie('Time')
        
        for vehicle_id in range(data['num_vehicles']):
            index = routing.Start(vehicle_id)
            
            # Skip unused vehicles
            if routing.IsEnd(solution.Value(routing.NextVar(index))):
                continue
                
            vehicle = vehicles[vehicle_id]
            route_plan = {
                "vehicle_id": vehicle.id,
                "driver_id": vehicle.current_driver_id,
                "depot_id": depot.id,
                "route_date": route_date,
                "stops": [],
                "metrics": {
                    "total_distance_km": 0,
                    "total_duration_minutes": 0,
                    "total_stops": 0
                }
            }
            
            route_distance = 0
            route_duration = 0
            stop_sequence = 1
            
            while not routing.IsEnd(index):
                node_index = manager.IndexToNode(index)
                time_var = time_dimension.CumulVar(index)
                
                # Retrieve order if not depot
                order = None
                if node_index > 0:
                    order = orders[node_index - 1]
                    
                    arrival_seconds = solution.Min(time_var)
                    arrival_time = self._seconds_to_datetime(arrival_seconds, route_date)
                    
                    stop_data = {
                        "sequence": stop_sequence,
                        "order_id": order.id,
                        "planned_arrival": arrival_time,
                        # "planned_departure": ... 
                        "location": {
                            "latitude": float(order.customer.latitude),
                            "longitude": float(order.customer.longitude),
                            "address": order.customer.address
                        },
                        "type": "delivery"
                    }
                    route_plan["stops"].append(stop_data)
                    stop_sequence += 1

                previous_index = index
                index = solution.Value(routing.NextVar(index))
                
                # Metrics
                route_distance += data['distance_matrix'][manager.IndexToNode(previous_index)][manager.IndexToNode(index)]
                # Time calc approximation
                
            # Finalize metrics from the solver's actual start/end time variables.
            start_seconds = solution.Min(time_dimension.CumulVar(routing.Start(vehicle_id)))
            finish_seconds = solution.Min(time_dimension.CumulVar(routing.End(vehicle_id)))
            route_plan["metrics"]["total_duration_minutes"] = math.ceil((finish_seconds - start_seconds) / 60)
            route_plan["metrics"]["total_stops"] = len(route_plan["stops"])
            # Provide distance in km (matrix is in metres)
            route_plan["metrics"]["total_distance_km"] = route_distance / 1000.0 if route_distance > 0 else 0
            
            routes.append(route_plan)
            
        return routes

    def _compute_distance_matrix(self, locations):
        """
        Computes distance matrix using Haversine formula (approximation).
        In production, call OSRM/Google Maps API.
        Returns distances in meters.
        """
        matrix = []
        for from_node in locations:
            row = []
            for to_node in locations:
                if from_node == to_node:
                    row.append(0)
                else:
                    dist = self._haversine(from_node[0], from_node[1], to_node[0], to_node[1])
                    row.append(int(dist)) # meters
            matrix.append(row)
        return matrix

    def _compute_time_matrix(self, distance_matrix):
        """
        Computes time matrix based on average speed (e.g., 30 km/h in city).
        Returns time in seconds.
        """
        avg_speed_mps = 30 * 1000 / 3600  # ~8.33 m/s
        matrix = []
        for row in distance_matrix:
            time_row = [int(dist / avg_speed_mps) for dist in row]
            matrix.append(time_row)
        return matrix

    def _haversine(self, lat1, lon1, lat2, lon2):
        """
        Calculate the great circle distance between two points 
        on the earth (specified in decimal degrees).
        """
        R = 6371000  # Radius of earth in meters
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        
        a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c

    def _time_to_seconds(self, t):
        if not t: return 0
        return t.hour * 3600 + t.minute * 60 + t.second

    def _datetime_to_seconds(self, dt, reference_date):
        delta = dt - datetime.combine(reference_date, datetime.min.time())
        return int(delta.total_seconds())

    def _seconds_to_datetime(self, seconds, reference_date):
        return datetime.combine(reference_date, datetime.min.time()) + timedelta(seconds=seconds)
