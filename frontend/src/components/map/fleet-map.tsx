'use client';

import { useState, useMemo, useEffect, useRef } from 'react';
import Map, { NavigationControl } from 'react-map-gl/maplibre';
import DeckGL from '@deck.gl/react';
import { PathLayer, ScatterplotLayer } from '@deck.gl/layers';
import { Layers } from 'lucide-react';
import 'maplibre-gl/dist/maplibre-gl.css';
import { useWebSocket } from '@/hooks/use-websocket';
import { z } from 'zod';

const vehicleUpdateSchema = z.object({
    vehicle_id: z.string(),
    location: z.object({ latitude: z.number().min(-90).max(90), longitude: z.number().min(-180).max(180) }),
});

// Initial view state centered on NYC
const INITIAL_VIEW_STATE = {
    longitude: -73.9857,
    latitude: 40.7484,
    zoom: 11,
    pitch: 0,
    bearing: 0,
};

// Mock data to initialize with before socket connects
const INITIAL_VEHICLES = [
    { id: '1', longitude: -73.9857, latitude: 40.7484, status: 'active', driver: 'Marcus J.' },
    { id: '2', longitude: -73.9712, latitude: 40.7831, status: 'active', driver: 'Sarah C.' },
    { id: '3', longitude: -74.0060, latitude: 40.7128, status: 'idle', driver: 'James W.' },
    { id: '4', longitude: -73.9442, latitude: 40.6782, status: 'active', driver: 'Emily R.' },
    { id: '5', longitude: -73.9171, latitude: 40.8448, status: 'break', driver: 'David K.' },
];

// Mock route data
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

// Mock delivery stops
const mockStops = [
    { id: 's1', longitude: -73.9750, latitude: 40.7550, status: 'completed' },
    { id: 's2', longitude: -73.9650, latitude: 40.7600, status: 'completed' },
    { id: 's3', longitude: -73.9712, latitude: 40.7831, status: 'pending' },
    { id: 's4', longitude: -74.0100, latitude: 40.7200, status: 'completed' },
    { id: 's5', longitude: -74.0050, latitude: 40.7300, status: 'pending' },
];

export default function FleetMap() {
    const [viewState, setViewState] = useState(INITIAL_VIEW_STATE);
    const [showRoutes, setShowRoutes] = useState(true);
    const [mounted, setMounted] = useState(false);
    const [hasWebGL, setHasWebGL] = useState(true);

    // Real-time Vehicle State
    const [vehicles, setVehicles] = useState(INITIAL_VEHICLES);
    const { lastMessage, isConnected } = useWebSocket('vehicles');

    // Handle incoming WebSocket messages
    useEffect(() => {
        if (lastMessage?.type === 'vehicle_update') {
            const parsed = vehicleUpdateSchema.safeParse(lastMessage.data);
            if (!parsed.success) return;
            const update = parsed.data;
            const frame = requestAnimationFrame(() => setVehicles(prev => {
                const index = prev.findIndex(v => v.id === update.vehicle_id);
                if (index >= 0) {
                    // Update existing vehicle
                    const newVehicles = [...prev];
                    newVehicles[index] = {
                        ...newVehicles[index],
                        longitude: update.location.longitude,
                        latitude: update.location.latitude,
                        // Could update driver, status etc if backend sent it changed
                    };
                    return newVehicles;
                }
                // Add new vehicle if not found (optional, depending on requirements)
                return prev;
            }));
            return () => cancelAnimationFrame(frame);
        }
    }, [lastMessage]);

    useEffect(() => {
        const frame = requestAnimationFrame(() => {
            setMounted(true);
            // Check for WebGL support
        try {
            const canvas = document.createElement('canvas');
            const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
            setHasWebGL(!!gl);
        } catch {
            setHasWebGL(false);
        }
        });
        return () => cancelAnimationFrame(frame);
    }, []);

    // Vehicle layer
    const vehicleLayer = useMemo(
        () =>
            new ScatterplotLayer({
                id: 'vehicles',
                data: vehicles,
                pickable: true,
                opacity: 1,
                stroked: true,
                filled: true,
                radiusScale: 1,
                radiusMinPixels: 12,
                radiusMaxPixels: 20,
                lineWidthMinPixels: 2,
                getPosition: (d: (typeof INITIAL_VEHICLES)[number]) => [d.longitude, d.latitude],
                getFillColor: (d: (typeof INITIAL_VEHICLES)[number]) => {
                    switch (d.status) {
                        case 'active':
                            return [16, 185, 129, 255]; // Emerald
                        case 'idle':
                            return [6, 182, 212, 255]; // Cyan
                        case 'break':
                            return [245, 158, 11, 255]; // Amber
                        default:
                            return [113, 113, 122, 255]; // Gray
                    }
                },
                getLineColor: [24, 24, 27, 255],
                transitions: {
                    getPosition: {
                        duration: 1800,
                        easing: (t: number) => t, // Simple linear interpolation matches the update rate well
                    },
                },
            }),
        [vehicles]
    );

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
                    getPath: (d: (typeof mockRoutes)[number]) => d.path,
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
                getPosition: (d: (typeof mockStops)[number]) => [d.longitude, d.latitude],
                getFillColor: (d: (typeof mockStops)[number]) =>
                    d.status === 'completed' ? [34, 197, 94, 255] : [251, 191, 36, 255],
                getLineColor: [24, 24, 27, 255],
            }),
        []
    );

    const layers = [routeLayer, stopsLayer, vehicleLayer].filter(Boolean);

    const [containerDimensions, setContainerDimensions] = useState({ width: 0, height: 0 });
    const containerRef = useRef<HTMLDivElement | null>(null);

    useEffect(() => {
        const node = containerRef.current;
        if (!node) {
            return;
        }

        const updateDimensions = () => {
            const { clientWidth, clientHeight } = node;
            if (clientWidth > 0 && clientHeight > 0) {
                setContainerDimensions({ width: clientWidth, height: clientHeight });
            }
        };

        updateDimensions();
        const observer = new ResizeObserver(updateDimensions);
        observer.observe(node);

        return () => observer.disconnect();
    }, []);

    // Show loading state before mount
    if (!mounted) {
        return (
            <div className="w-full h-full bg-stone-900 flex items-center justify-center">
                <div className="text-stone-500">Loading map...</div>
            </div>
        );
    }

    // Show fallback if no WebGL
    if (!hasWebGL) {
        return (
            <div className="w-full h-full bg-stone-900 flex items-center justify-center">
                <div className="text-center">
                    <p className="text-stone-400 mb-2">WebGL not available</p>
                    <p className="text-xs text-stone-600">Map requires WebGL support</p>
                </div>
            </div>
        );
    }

    return (
        <div ref={containerRef} className="relative w-full h-full overflow-hidden bg-stone-900">
            {containerDimensions.width > 0 && containerDimensions.height > 0 && (
                <DeckGL
                    width={containerDimensions.width}
                    height={containerDimensions.height}
                    viewState={viewState}
                    onViewStateChange={(e) => setViewState((prev) => ({ ...prev, ...e.viewState }))}
                    controller={true}
                    layers={layers}
                    style={{ position: 'absolute', top: '0px', left: '0px', width: '100%', height: '100%' }}

                    getTooltip={({ object }) =>
                        object && object.driver
                            ? {
                                text: `${object.driver}\nStatus: ${object.status}`,
                                style: {
                                    backgroundColor: '#1c1917',
                                    color: '#fafafa',
                                    padding: '8px 12px',
                                    borderRadius: '8px',
                                    fontSize: '12px',
                                },
                            }
                            : null
                    }
                >
                    <Map
                        mapStyle="https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json"
                        attributionControl={false}
                        reuseMaps
                    >
                        <NavigationControl position="bottom-right" />
                    </Map>
                </DeckGL>
            )}

            {/* Map Controls */}
            <div className="absolute top-4 right-4 flex flex-col gap-2">
                <div className={`px-2 py-1 rounded-md text-xs font-mono mb-1 text-center border ${isConnected ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400' : 'bg-red-500/10 border-red-500/20 text-red-400'
                    }`}>
                    {isConnected ? 'LIVE' : 'OFFLINE'}
                </div>
                <button
                    onClick={() => setShowRoutes(!showRoutes)}
                    className={`p-2 rounded-lg transition-colors ${showRoutes
                        ? 'bg-emerald-500 text-stone-900'
                        : 'bg-stone-800 text-stone-400 hover:bg-stone-700'
                        }`}
                    title="Toggle Routes"
                >
                    <Layers className="w-4 h-4" />
                </button>
            </div>

            {/* Legend */}
            <div className="absolute bottom-4 left-4 bg-stone-950/90 backdrop-blur-sm border border-stone-800 rounded-lg p-3">
                <p className="text-xs font-semibold text-stone-400 mb-2">VEHICLE STATUS</p>
                <div className="space-y-1.5">
                    {[
                        { label: 'Active', color: 'bg-emerald-500' },
                        { label: 'Idle', color: 'bg-cyan-500' },
                        { label: 'On Break', color: 'bg-emerald-500' },
                    ].map((item) => (
                        <div key={item.label} className="flex items-center gap-2">
                            <div className={`w-2 h-2 rounded-full ${item.color}`} />
                            <span className="text-xs text-stone-300">{item.label}</span>
                        </div>
                    ))}
                </div>
                <div className="border-t border-stone-700 mt-2 pt-2">
                    <p className="text-xs font-semibold text-stone-400 mb-2">DELIVERY STOPS</p>
                    <div className="space-y-1.5">
                        {[
                            { label: 'Completed', color: 'bg-emerald-500' },
                            { label: 'Pending', color: 'bg-emerald-400' },
                        ].map((item) => (
                            <div key={item.label} className="flex items-center gap-2">
                                <div className={`w-2 h-2 rounded-full ${item.color}`} />
                                <span className="text-xs text-stone-300">{item.label}</span>
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            {/* Stats Overlay */}
            <div className="absolute top-4 left-4 bg-stone-950/90 backdrop-blur-sm border border-stone-800 rounded-lg p-3">
                <div className="flex items-center gap-4">
                    <div>
                        <p className="text-xl font-bold text-emerald-400">{vehicles.length}</p>
                        <p className="text-[10px] text-stone-500 uppercase">Vehicles</p>
                    </div>
                    <div className="h-8 w-px bg-stone-700" />
                    <div>
                        <p className="text-xl font-bold text-cyan-400">{mockStops.length}</p>
                        <p className="text-[10px] text-stone-500 uppercase">Sample stops</p>
                    </div>
                    <div className="h-8 w-px bg-stone-700" />
                    <div>
                        <p className="text-xl font-bold text-emerald-400">{mockRoutes.length}</p>
                        <p className="text-[10px] text-stone-500 uppercase">Sample routes</p>
                    </div>
                </div>
            </div>
        </div>
    );
}
