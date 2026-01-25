'use client';

import { useState, useEffect, useMemo } from 'react';
import Map, { NavigationControl, Marker } from 'react-map-gl/maplibre';
import DeckGL from '@deck.gl/react';
import { PathLayer, ScatterplotLayer } from '@deck.gl/layers';
import { Layers, Wifi, WifiOff, MapPin } from 'lucide-react';
import 'maplibre-gl/dist/maplibre-gl.css';
import { useVehicleTracking, VehicleLocation } from '@/hooks/useWebSocket';

const INITIAL_VIEW_STATE = {
    longitude: -73.9857,
    latitude: 40.7484,
    zoom: 11,
    pitch: 0,
    bearing: 0,
};

// Mock data for static elements
const mockRoutes = [
    {
        id: 'route-1',
        path: [
            [-73.9857, 40.7484],
            [-73.9750, 40.7550],
            [-73.9650, 40.7600],
            [-73.9712, 40.7831],
        ],
    },
    {
        id: 'route-2',
        path: [
            [-74.0060, 40.7128],
            [-74.0100, 40.7200],
            [-74.0050, 40.7300],
            [-73.9900, 40.7400],
        ],
    },
];

const mockStops = [
    { id: 's1', longitude: -73.9750, latitude: 40.7550, status: 'completed' },
    { id: 's2', longitude: -73.9650, latitude: 40.7600, status: 'completed' },
    { id: 's3', longitude: -73.9712, latitude: 40.7831, status: 'pending' },
    { id: 's4', longitude: -74.0100, latitude: 40.7200, status: 'completed' },
    { id: 's5', longitude: -74.0050, latitude: 40.7300, status: 'pending' },
];

function VehicleMarker({ vehicle }: { vehicle: VehicleLocation }) {
    const statusColor = vehicle.speed_kmh > 10 ? 'bg-emerald-500' : 'bg-teal-400';

    return (
        <div className="relative group cursor-pointer">
            <div className={`w-4 h-4 ${statusColor} rounded-full border-2 border-zinc-900 shadow-lg`}>
                <div className="absolute inset-0 rounded-full animate-ping bg-emerald-400/30" />
            </div>

            {/* Tooltip */}
            <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50">
                <div className="bg-zinc-900 text-white text-xs rounded-lg px-3 py-2 shadow-xl border border-zinc-700 whitespace-nowrap">
                    <p className="font-semibold">{vehicle.driver}</p>
                    <p className="text-zinc-400">{Math.round(vehicle.speed_kmh)} km/h</p>
                </div>
            </div>
        </div>
    );
}

export default function LiveFleetMap() {
    const [viewState, setViewState] = useState(INITIAL_VIEW_STATE);
    const [showRoutes, setShowRoutes] = useState(true);
    const [mounted, setMounted] = useState(false);

    // Real-time vehicle tracking
    const { vehicles, isConnected, connectionState, lastUpdate } = useVehicleTracking();

    useEffect(() => {
        setMounted(true);
    }, []);

    // Route path layer
    const routeLayer = useMemo(
        () =>
            showRoutes
                ? new PathLayer({
                    id: 'routes',
                    data: mockRoutes,
                    pickable: false,
                    widthScale: 1,
                    widthMinPixels: 3,
                    getPath: (d: any) => d.path,
                    getColor: [16, 185, 129, 180],
                    getWidth: 3,
                })
                : null,
        [showRoutes]
    );

    // Delivery stops layer
    const stopsLayer = useMemo(
        () =>
            new ScatterplotLayer({
                id: 'stops',
                data: mockStops,
                pickable: true,
                opacity: 0.8,
                stroked: true,
                filled: true,
                radiusMinPixels: 6,
                radiusMaxPixels: 10,
                lineWidthMinPixels: 1,
                getPosition: (d: any) => [d.longitude, d.latitude],
                getFillColor: (d: any) =>
                    d.status === 'completed' ? [34, 197, 94, 255] : [251, 191, 36, 255],
                getLineColor: [24, 24, 27, 255],
            }),
        []
    );

    const layers = [routeLayer, stopsLayer].filter(Boolean);

    if (!mounted) {
        return (
            <div className="w-full h-full bg-zinc-900 flex items-center justify-center">
                <div className="text-zinc-500">Loading map...</div>
            </div>
        );
    }

    return (
        <div className="relative w-full h-full">
            <DeckGL
                viewState={viewState}
                onViewStateChange={(e: any) => setViewState(e.viewState)}
                controller={true}
                layers={layers}
            >
                <Map
                    mapStyle="https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json"
                    attributionControl={false}
                >
                    <NavigationControl position="bottom-right" />

                    {/* Real-time vehicle markers */}
                    {vehicles.map((vehicle) => (
                        <Marker
                            key={vehicle.vehicle_id}
                            longitude={vehicle.location.longitude}
                            latitude={vehicle.location.latitude}
                            anchor="center"
                        >
                            <VehicleMarker vehicle={vehicle} />
                        </Marker>
                    ))}
                </Map>
            </DeckGL>

            {/* Connection status */}
            <div className="absolute top-4 left-4 flex items-center gap-4">
                <div className="bg-zinc-900/90 backdrop-blur-sm border border-zinc-800 rounded-lg px-3 py-2 flex items-center gap-2">
                    {isConnected ? (
                        <>
                            <Wifi className="w-4 h-4 text-emerald-400" />
                            <span className="text-xs text-emerald-400">Live</span>
                        </>
                    ) : (
                        <>
                            <WifiOff className="w-4 h-4 text-red-400" />
                            <span className="text-xs text-red-400">{connectionState}</span>
                        </>
                    )}
                </div>

                {/* Stats */}
                <div className="bg-zinc-900/90 backdrop-blur-sm border border-zinc-800 rounded-lg p-3">
                    <div className="flex items-center gap-4">
                        <div>
                            <p className="text-xl font-bold text-emerald-400">{vehicles.length}</p>
                            <p className="text-[10px] text-zinc-500 uppercase">Vehicles</p>
                        </div>
                        <div className="h-8 w-px bg-zinc-700" />
                        <div>
                            <p className="text-xl font-bold text-cyan-400">{mockStops.length}</p>
                            <p className="text-[10px] text-zinc-500 uppercase">Stops</p>
                        </div>
                    </div>
                </div>
            </div>

            {/* Map Controls */}
            <div className="absolute top-4 right-4 flex flex-col gap-2">
                <button
                    onClick={() => setShowRoutes(!showRoutes)}
                    className={`p-2 rounded-lg transition-colors ${showRoutes
                            ? 'bg-cyan-500 text-white'
                            : 'bg-zinc-800 text-zinc-400 hover:bg-zinc-700'
                        }`}
                    title="Toggle Routes"
                >
                    <Layers className="w-4 h-4" />
                </button>
            </div>

            {/* Legend */}
            <div className="absolute bottom-4 left-4 bg-zinc-900/90 backdrop-blur-sm border border-zinc-800 rounded-lg p-3">
                <p className="text-xs font-semibold text-zinc-400 mb-2">LIVE TRACKING</p>
                <div className="space-y-1.5">
                    <div className="flex items-center gap-2">
                        <div className="w-2 h-2 rounded-full bg-emerald-500" />
                        <span className="text-xs text-zinc-300">Moving</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <div className="w-2 h-2 rounded-full bg-emerald-500" />
                        <span className="text-xs text-zinc-300">Stopped</span>
                    </div>
                </div>
                {lastUpdate && (
                    <p className="text-[10px] text-zinc-600 mt-2">
                        Updated: {lastUpdate.toLocaleTimeString()}
                    </p>
                )}
            </div>
        </div>
    );
}
