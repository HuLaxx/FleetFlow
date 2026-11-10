'use client';

import Link from 'next/link';
import { useMemo, useReducer, useState } from 'react';
import {
  Activity, ArrowDownRight, ArrowRight, Check, CheckCircle2, ChevronRight,
  Package, Play, Plus, RotateCcw, Route, ShieldCheck,
  SlidersHorizontal, X,
} from 'lucide-react';
import { SiteHeader } from '@/components/site/site-header';
import { SiteFooter } from '@/components/site/site-footer';
import {
  AREA_PRESETS, DEMO_DRIVERS, DEPOT, SCENARIO_STOPS, createScenarioStop,
  planDispatch, type DispatchPlan, type DispatchStop, type Priority,
  type StopStatus, type Point,
} from '@/lib/dispatch/engine';

type Phase = 'planning' | 'dispatched';
type ActivityItem = { id: number; title: string; detail: string };
interface LabState {
  stops: DispatchStop[];
  phase: Phase;
  plan: DispatchPlan | null;
  selectedId: string | null;
  activity: ActivityItem[];
}
type LabAction =
  | { type: 'select'; id: string }
  | { type: 'add'; stop: DispatchStop }
  | { type: 'plan' }
  | { type: 'dispatch' }
  | { type: 'deliver'; id: string }
  | { type: 'reset' };

const initialState = (): LabState => ({
  stops: SCENARIO_STOPS.map(stop => ({ ...stop, point: { ...stop.point } })),
  phase: 'planning',
  plan: null,
  selectedId: SCENARIO_STOPS[0].id,
  activity: [{ id: 1, title: 'Scenario initialized', detail: 'Nine sample deliveries, three vehicles. Awaiting dispatch decisions.' }],
});

function record(state: LabState, title: string, detail: string): ActivityItem[] {
  return [{ id: state.activity[0].id + 1, title, detail }, ...state.activity].slice(0, 8);
}

function labReducer(state: LabState, action: LabAction): LabState {
  switch (action.type) {
    case 'select':
      return { ...state, selectedId: action.id };
    case 'add':
      if (state.phase !== 'planning') return state;
      return {
        ...state, stops: [...state.stops, action.stop], plan: null,
        selectedId: action.stop.id,
        activity: record(state, 'New delivery added', action.stop.recipient + ' · ' + action.stop.address),
      };
    case 'plan': {
      if (state.phase !== 'planning') return state;
      const plan = planDispatch(state.stops);
      return {
        ...state, plan,
        activity: record(state, 'Route proposal calculated', plan.assignedCount + ' stops allocated; ' + plan.unassignedIds.length + ' require review.'),
      };
    }
    case 'dispatch': {
      if (state.phase !== 'planning' || !state.plan || !state.plan.assignedCount) return state;
      const assignments = new Map<string, string>();
      state.plan.routes.forEach(route => route.stopIds.forEach(id => assignments.set(id, route.driverId)));
      return {
        ...state,
        phase: 'dispatched',
        stops: state.stops.map(stop => assignments.has(stop.id)
          ? { ...stop, status: 'assigned', driverId: assignments.get(stop.id) }
          : stop),
        activity: record(state, 'Dispatch approved', 'Assigned routes are now active in this simulated shift.'),
      };
    }
    case 'deliver': {
      const stop = state.stops.find(item => item.id === action.id);
      if (state.phase !== 'dispatched' || stop?.status !== 'assigned') return state;
      return {
        ...state,
        stops: state.stops.map(item => item.id === action.id ? { ...item, status: 'delivered' } : item),
        activity: record(state, 'Stop delivered', stop.recipient + ' · ' + stop.id),
      };
    }
    case 'reset':
      return initialState();
  }
}

const formatKm = (km: number) => km.toFixed(1) + ' km';
const formatStatus = (status: StopStatus) => ({ queued: 'Unassigned', assigned: 'In route', delivered: 'Delivered' })[status];
const pointToMap = (point: Point) => ({
  x: 62 + (point.lon + 74.022) / 0.066 * 682,
  y: 493 - (point.lat - 40.699) / 0.063 * 415,
});

type Filter = 'all' | 'express' | 'queued' | 'assigned' | 'delivered';

function ScenarioMap({ state, onSelect }: { state: LabState; onSelect: (id: string) => void }) {
  const depotPoint = pointToMap(DEPOT);
  const stopMap = new Map(state.stops.map(stop => [stop.id, stop]));
  const activeRoutes = state.plan?.routes || [];

  return (
    <div className="relative h-[390px] md:h-[520px] overflow-hidden bg-[#101b21]">
      <svg viewBox="0 0 800 560" preserveAspectRatio="none" className="absolute inset-0 h-full w-full" aria-hidden="true">
        <defs>
          <pattern id="dispatch-grid" width="54" height="54" patternUnits="userSpaceOnUse">
            <path d="M 54 0 L 0 0 0 54" fill="none" stroke="#33444a" strokeWidth="1" opacity="0.35" />
          </pattern>
          <linearGradient id="dispatch-water" x1="0" x2="1"><stop stopColor="#0e323a"/><stop offset="1" stopColor="#12343c"/></linearGradient>
        </defs>
        <rect width="800" height="560" fill="#101b21" />
        <rect width="800" height="560" fill="url(#dispatch-grid)" />
        <path d="M 0 0 L 90 0 Q 48 155 101 270 T 80 560 L 0 560Z" fill="url(#dispatch-water)" opacity=".85" />
        <path d="M 710 0 L 800 0 L 800 560 L 755 560 Q 708 384 739 236 T 710 0Z" fill="url(#dispatch-water)" opacity=".8"/>
        {Array.from({ length: 7 }, (_, i) => (
          <g key={i} stroke="#344d52" opacity=".45" strokeWidth={i % 3 === 0 ? 4 : 2}>
            <path d={`M ${155 + i * 78} 0 L ${102 + i * 90} 560`} />
            <path d={`M 80 ${76 + i * 72} L 735 ${56 + i * 72}`} />
          </g>
        ))}
        <g fill="#536a71" fontSize="10" fontFamily="monospace" letterSpacing="2" opacity=".75">
          <text x="142" y="115">CHELSEA</text><text x="514" y="185">MIDTOWN</text>
          <text x="140" y="448">SOHO</text><text x="526" y="405">EAST VILLAGE</text>
          <text x="343" y="278">FLATIRON</text>
        </g>
        {activeRoutes.map(route => {
          const driver = DEMO_DRIVERS.find(item => item.id === route.driverId);
          if (!driver) return null;
          const points = [driver.depot, ...route.stopIds.map(id => stopMap.get(id)?.point).filter((point): point is Point => !!point), driver.depot];
          return (
            <polyline key={route.driverId}
              points={points.map(point => { const p = pointToMap(point); return p.x + ',' + p.y; }).join(' ')}
              fill="none" stroke={driver.color} strokeWidth="3.5" strokeLinejoin="round" strokeLinecap="round"
              opacity=".92" strokeDasharray={state.phase === 'planning' ? '8 6' : undefined}
            />
          );
        })}
        <circle cx={depotPoint.x} cy={depotPoint.y} r="20" fill="#91f2cf" opacity=".12"/>
        <rect x={depotPoint.x - 8} y={depotPoint.y - 8} width="16" height="16" rx="3" fill="#91f2cf" stroke="#0f1a1d" strokeWidth="3"/>
      </svg>
      <div className="absolute left-4 top-4 flex items-center gap-3 rounded-sm border border-white/10 bg-[#0a1418]/85 px-3 py-2 backdrop-blur">
        <span className="h-2 w-2 rounded-full bg-emerald-300"/>
        <span className="text-[10px] font-semibold tracking-[0.24em] text-[#d3e3de]">NYC / SCHEMATIC GRID</span>
      </div>
      <div className="absolute right-4 top-4 border border-white/10 bg-[#0a1418]/85 px-3 py-2 text-[10px] tracking-widest text-[#9baeb1]">
        NOT LIVE GPS
      </div>
      {state.stops.map(stop => {
        const p = pointToMap(stop.point);
        const planned = activeRoutes.find(route => route.stopIds.includes(stop.id));
        const driver = DEMO_DRIVERS.find(item => item.id === (stop.driverId || planned?.driverId));
        const selected = state.selectedId === stop.id;
        return (
          <button key={stop.id} type="button" aria-label={`Select ${stop.id}, ${stop.recipient}`}
            onClick={() => onSelect(stop.id)}
            title={stop.recipient}
            style={{ left: (p.x / 800 * 100) + '%', top: (p.y / 560 * 100) + '%' }}
            className={`absolute z-10 -translate-x-1/2 -translate-y-1/2 flex h-7 w-7 items-center justify-center rounded-full border-2 shadow-lg transition-transform hover:scale-125 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-300 ${selected ? 'scale-125 border-white' : 'border-[#15232a]'}`}
          >
            <span className="flex h-full w-full items-center justify-center rounded-full text-[10px] font-bold text-[#0e1719]"
              style={{ background: stop.status === 'delivered' ? '#e2f7e8' : driver?.color || (stop.priority === 'express' ? '#ffc188' : '#a6b7bc') }}>
              {stop.status === 'delivered' ? <Check size={13}/> : state.stops.indexOf(stop) + 1}
            </span>
          </button>
        );
      })}
      <div className="absolute bottom-4 left-4 flex flex-wrap gap-3 border border-white/10 bg-[#0a1418]/90 px-3 py-2 text-[10px] text-[#bdd0d1]">
        <span className="flex items-center gap-1.5"><span className="h-2 w-2 bg-[#91f2cf]"/> Depot</span>
        <span className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-[#ffc188]"/> Express</span>
        <span className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-[#a6b7bc]"/> Standard</span>
      </div>
      <div className="absolute bottom-4 right-4 text-[10px] uppercase tracking-widest text-[#71888b]">Illustrative layout</div>
    </div>
  );
}

function Stat({ label, value, sub }: { label: string; value: string; sub: string }) {
  return (
    <div className="min-w-0 border-r border-white/10 px-4 py-5 last:border-r-0 md:px-7">
      <p className="text-[10px] font-medium uppercase tracking-[.2em] text-[#8ba3a4]">{label}</p>
      <p className="mt-2 font-mono text-3xl font-medium tracking-tight text-[#f0f5f1] md:text-4xl">{value}</p>
      <p className="mt-1 text-xs text-[#7e9596]">{sub}</p>
    </div>
  );
}

export default function DemoPage() {
  const [state, dispatch] = useReducer(labReducer, undefined, initialState);
  const [filter, setFilter] = useState<Filter>('all');
  const [showAdd, setShowAdd] = useState(false);
  const [recipient, setRecipient] = useState('');
  const [zone, setZone] = useState(AREA_PRESETS[0].name);
  const [weight, setWeight] = useState('12');
  const [priority, setPriority] = useState<Priority>('standard');
  const [formError, setFormError] = useState('');

  const orderedStops = useMemo(() => state.stops.filter(stop => {
    if (filter === 'all') return true;
    if (filter === 'express') return stop.priority === 'express';
    return stop.status === filter;
  }), [state.stops, filter]);
  const selected = state.stops.find(stop => stop.id === state.selectedId);
  const selectedRoute = state.plan?.routes.find(route => route.stopIds.includes(selected?.id || ''));
  const selectedDriver = DEMO_DRIVERS.find(driver => driver.id === (selected?.driverId || selectedRoute?.driverId));
  const completed = state.stops.filter(stop => stop.status === 'delivered').length;
  const assigned = state.stops.filter(stop => stop.status === 'assigned').length;
  const unassigned = state.plan?.unassignedIds.length ?? 0;
  const routeCount = state.plan?.routes.length ?? 0;
  const plan = state.plan;

  function addStop(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      const nextNumber = 1100 + state.stops.length;
      const stop = createScenarioStop('FF-' + nextNumber, recipient, zone, Number(weight), priority);
      dispatch({ type: 'add', stop });
      setRecipient('');
      setWeight('12');
      setFormError('');
      setShowAdd(false);
      setFilter('all');
    } catch (error) {
      setFormError(error instanceof Error ? error.message : 'Unable to add delivery.');
    }
  }

  return (
    <div className="relative z-10 min-h-screen bg-[#0c1317] text-[#edf2ef]">
      <SiteHeader />
      <main className="mx-auto max-w-[1560px] px-4 pb-20 pt-32 md:px-8 md:pt-36">
        <div className="mb-9 flex flex-col justify-between gap-6 lg:flex-row lg:items-end">
          <div>
            <div className="mb-5 flex items-center gap-3 text-[11px] font-semibold uppercase tracking-[.24em] text-[#8dbaa9]">
              <span className="h-[1px] w-9 bg-[#8dbaa9]"/> FleetFlow / Dispatch lab / 01
            </div>
            <h1 className="max-w-3xl text-[clamp(2.6rem,5vw,5.6rem)] font-semibold leading-[.97] tracking-[-.065em]">
              Make every <span className="italic font-normal text-[#92d6bb]">stop</span> count.
            </h1>
            <p className="mt-5 max-w-2xl text-sm leading-relaxed text-[#8fa4a4] md:text-base">
              From manifest to route to delivery. Work through a complete dispatch scenario with capacity-aware vehicle allocation and clear operational decisions.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3 lg:justify-end">
            <Link href="/demo/live" className="inline-flex items-center gap-2 border border-[#3b5555] px-4 py-3 text-xs font-semibold text-[#d6e9de] transition hover:bg-white/5">
              Connected workspace <ArrowUpRightIcon />
            </Link>
            <button type="button" onClick={() => { dispatch({ type: 'reset' }); setFilter('all'); setShowAdd(false); }}
              className="inline-flex items-center gap-2 border border-white/10 px-4 py-3 text-xs font-semibold text-[#9aafb0] transition hover:border-white/30 hover:text-white">
              <RotateCcw size={14}/> Reset scenario
            </button>
          </div>
        </div>

        <div className="mb-4 flex flex-wrap items-center justify-between gap-2 border-y border-[#2b4a47] bg-[#12231f] px-4 py-3 text-[11px]">
          <span className="flex items-center gap-2 font-medium tracking-wider text-[#a5d3bb]"><ShieldCheck size={15}/> INTERACTIVE SCENARIO · NO LIVE ORDERS OR GPS</span>
          <span className="text-[#8daaa2]">Local heuristic · illustrative positions · no external API required</span>
        </div>

        <div className="mb-5 grid grid-cols-2 border border-white/10 bg-[#101b1f] lg:grid-cols-4">
          <Stat label="Manifest" value={String(state.stops.length).padStart(2, '0')} sub={completed + ' delivered / ' + assigned + ' in route'} />
          <Stat label="Vehicles" value={String(routeCount || DEMO_DRIVERS.length).padStart(2, '0')} sub={routeCount ? 'Allocated routes' : 'Available to assign'} />
          <Stat label="Proposed distance" value={plan ? formatKm(plan.totalKm) : '—'} sub="Straight-line round trips" />
          <Stat label="Exceptions" value={plan ? String(unassigned).padStart(2, '0') : '—'} sub={plan ? 'Unassigned stops' : 'Run planning to review'} />
        </div>

        <div className="grid gap-5 xl:grid-cols-[minmax(0,1.48fr)_minmax(340px,0.82fr)]">
          <section className="min-w-0 overflow-hidden border border-white/10 bg-[#101b1f]" aria-label="Dispatch map">
            <div className="flex flex-wrap items-center justify-between gap-4 px-5 py-5 md:px-7">
              <div>
                <p className="text-[10px] font-medium uppercase tracking-[.22em] text-[#8eaca7]">Operation surface / 01</p>
                <h2 className="mt-1 text-xl font-semibold tracking-tight">Manhattan dispatch grid</h2>
              </div>
              <span className="inline-flex items-center gap-2 border border-white/10 bg-[#16272a] px-3 py-2 font-mono text-[11px] text-[#a0b8b4]">
                <Activity size={13} className="text-[#87d4ac]"/>
                {state.phase === 'dispatched' ? 'SHIFT IN PROGRESS' : plan ? 'ROUTE PROPOSAL' : 'AWAITING PLAN'}
              </span>
            </div>
            <ScenarioMap state={state} onSelect={id => dispatch({ type: 'select', id })} />
            <div className="flex flex-col gap-3 border-t border-white/10 px-5 py-4 text-xs text-[#809a9b] md:flex-row md:items-center md:justify-between md:px-7">
              <span>Click any stop to inspect its assignment and delivery status.</span>
              <span className="font-mono text-[#a4cbbb]">40.7413° N / 73.9897° W</span>
            </div>
          </section>

          <section className="flex min-w-0 flex-col border border-white/10 bg-[#101b1f]" aria-label="Order manifest">
            <div className="border-b border-white/10 px-5 py-5 md:px-6">
              <div className="flex items-center justify-between gap-2">
                <div>
                  <p className="text-[10px] uppercase tracking-[.22em] text-[#8eaca7]">Manifest / 02</p>
                  <h2 className="mt-1 text-xl font-semibold">Dispatch queue</h2>
                </div>
                <button type="button" disabled={state.phase !== 'planning'}
                  onClick={() => setShowAdd(value => !value)}
                  className="inline-flex items-center gap-2 bg-[#9ce6bf] px-3 py-2 text-xs font-semibold text-[#0b2018] transition hover:bg-[#c3f6d7] disabled:cursor-not-allowed disabled:opacity-40">
                  {showAdd ? <X size={15}/> : <Plus size={15}/>} {showAdd ? 'Close' : 'Add stop'}
                </button>
              </div>
              {showAdd && state.phase === 'planning' && (
                <form onSubmit={addStop} className="mt-5 space-y-3 border border-[#38574e] bg-[#132820] p-4">
                  <div className="grid gap-3 sm:grid-cols-2">
                    <label className="block text-[11px] text-[#bacdc4]">Recipient
                      <input required maxLength={60} value={recipient} onChange={event => setRecipient(event.target.value)}
                        className="mt-1 block w-full border border-white/15 bg-[#0b1716] px-3 py-2.5 text-sm text-white outline-none focus:border-emerald-300" placeholder="Business name"/>
                    </label>
                    <label className="block text-[11px] text-[#bacdc4]">Delivery zone
                      <select value={zone} onChange={event => setZone(event.target.value)} className="mt-1 block w-full border border-white/15 bg-[#0b1716] px-3 py-2.5 text-sm text-white">
                        {AREA_PRESETS.map(area => <option key={area.name}>{area.name}</option>)}
                      </select>
                    </label>
                    <label className="block text-[11px] text-[#bacdc4]">Load (kg)
                      <input required type="number" min="1" max="50" step="1" value={weight} onChange={event => setWeight(event.target.value)}
                        className="mt-1 block w-full border border-white/15 bg-[#0b1716] px-3 py-2.5 text-sm text-white"/>
                    </label>
                    <label className="block text-[11px] text-[#bacdc4]">Service class
                      <select value={priority} onChange={event => setPriority(event.target.value as Priority)} className="mt-1 block w-full border border-white/15 bg-[#0b1716] px-3 py-2.5 text-sm text-white">
                        <option value="standard">Standard</option><option value="express">Express</option>
                      </select>
                    </label>
                  </div>
                  {formError && <p role="alert" className="text-xs text-[#ffc188]">{formError}</p>}
                  <button type="submit" className="w-full bg-[#9ce6bf] py-2.5 text-xs font-bold text-[#0b2018] hover:bg-[#c3f6d7]">Add to manifest</button>
                </form>
              )}
              <div className="mt-5 flex flex-wrap gap-1.5" aria-label="Filter orders">
                {(['all', 'express', 'queued', 'assigned', 'delivered'] as const).map(value => (
                  <button key={value} onClick={() => setFilter(value)} type="button"
                    aria-pressed={filter === value}
                    className={`px-3 py-1.5 text-[11px] capitalize transition ${filter === value ? 'bg-[#d2e8dc] text-[#11211b]' : 'bg-white/5 text-[#92a9a8] hover:bg-white/10'}`}>
                    {value === 'queued' ? 'Unassigned' : value === 'assigned' ? 'In route' : value}
                  </button>
                ))}
              </div>
            </div>

            <div className="max-h-[405px] min-h-[240px] flex-1 overflow-y-auto">
              {orderedStops.length === 0 && <p className="px-6 py-12 text-center text-sm text-[#92a8a5]">No deliveries match this filter.</p>}
              {orderedStops.map(stop => {
                const isSelected = state.selectedId === stop.id;
                return (
                  <button type="button" key={stop.id} onClick={() => dispatch({ type: 'select', id: stop.id })}
                    className={`flex w-full items-center gap-3 border-b border-white/[.07] px-5 py-3.5 text-left transition hover:bg-[#1c3031] md:px-6 ${isSelected ? 'bg-[#1d3230] shadow-[inset_3px_0_0_#9ce6bf]' : ''}`}>
                    <span className={`flex h-9 w-9 shrink-0 items-center justify-center border text-xs ${stop.status === 'delivered' ? 'border-[#85bda3] text-[#a7dec0]' : 'border-white/15 text-[#bfcec7]'}`}>
                      {stop.status === 'delivered' ? <CheckCircle2 size={16}/> : <Package size={15}/>}
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="flex items-center gap-2 text-sm font-semibold text-[#f1f6f2]">
                        <span className="truncate">{stop.recipient}</span>
                        {stop.priority === 'express' && <span className="shrink-0 bg-[#66452a] px-1.5 py-0.5 text-[9px] uppercase tracking-wide text-[#ffd4a5]">Express</span>}
                      </span>
                      <span className="mt-1 flex items-center gap-2 text-[11px] text-[#839b9b]"><span className="font-mono">{stop.id}</span><span>·</span>{stop.address}<span>·</span>{stop.weightKg} kg</span>
                    </span>
                    <ChevronRight size={16} className="shrink-0 text-[#607b79]"/>
                  </button>
                );
              })}
            </div>
            <div className="border-t border-white/10 bg-[#132126] px-5 py-5 md:px-6">
              {selected && (
                <div className="mb-4 flex flex-wrap items-center justify-between gap-3 border-b border-white/10 pb-4">
                  <div>
                    <span className="text-[10px] uppercase tracking-[.16em] text-[#8caaa3]">Selected · {selected.id}</span>
                    <p className="mt-1 text-sm font-semibold text-white">{selected.recipient}</p>
                    <p className="mt-1 text-xs text-[#89a6a4]">{formatStatus(selected.status)} · {selectedDriver ? selectedDriver.name : 'No driver assigned'}</p>
                  </div>
                  {selected.status === 'assigned' && (
                    <button onClick={() => dispatch({ type: 'deliver', id: selected.id })} className="inline-flex items-center gap-2 border border-[#8ccaab] px-3 py-2 text-xs text-[#b8ebcb] hover:bg-[#1b3c31]">
                      <Check size={14}/> Mark delivered
                    </button>
                  )}
                </div>
              )}
              <div className="flex gap-2">
                {state.phase === 'planning' && (
                  <>
                    <button type="button" onClick={() => dispatch({ type: 'plan' })}
                      className="inline-flex flex-1 items-center justify-center gap-2 border border-[#4d6863] px-3 py-3 text-xs font-semibold text-[#deebe1] hover:bg-white/5">
                      <SlidersHorizontal size={15}/> {plan ? 'Recalculate' : 'Generate plan'}
                    </button>
                    <button type="button" disabled={!plan?.assignedCount} onClick={() => dispatch({ type: 'dispatch' })}
                      className="inline-flex flex-1 items-center justify-center gap-2 bg-[#a3ebc5] px-3 py-3 text-xs font-bold text-[#0a1e17] hover:bg-[#c6f8d9] disabled:cursor-not-allowed disabled:opacity-30">
                      <Play size={14} fill="currentColor"/> Approve dispatch
                    </button>
                  </>
                )}
                {state.phase === 'dispatched' && (
                  <div className="flex w-full items-center justify-between gap-3 text-xs">
                    <span className="flex items-center gap-2 text-[#b0e8cc]"><CheckCircle2 size={16}/> Routes dispatched</span>
                    <span className="font-mono text-[#9fb5b2]">{completed} / {state.stops.length - unassigned} delivered</span>
                  </div>
                )}
              </div>
              {state.phase === 'planning' && <p className="mt-3 text-[11px] leading-relaxed text-[#778f8c]">Generate a capacity-checked proposal before approving. Changes to the manifest invalidate the previous plan.</p>}
            </div>
          </section>
        </div>

        <div className="mt-5 grid gap-5 xl:grid-cols-[minmax(0,1.48fr)_minmax(340px,0.82fr)]">
          <section className="border border-white/10 bg-[#101b1f] px-5 py-6 md:px-7" aria-label="Route allocation">
            <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
              <div><p className="text-[10px] uppercase tracking-[.2em] text-[#8ba7a2]">Route allocation / 03</p><h2 className="mt-1 text-xl font-semibold">Vehicle run sheets</h2></div>
              <span className="font-mono text-xs text-[#8ca7a2]">{plan ? formatKm(plan.manifestOrderKm - plan.totalKm) + ' vs manifest order' : 'NO PROPOSAL YET'}</span>
            </div>
            {!plan && <div className="border border-dashed border-white/15 px-5 py-12 text-center text-sm text-[#97aba9]"><Route className="mx-auto mb-3 text-[#83b79f]" size={28}/> Generate a plan to see capacity checks, route sequences and estimated travel distances.</div>}
            {plan && <div className="grid gap-3 md:grid-cols-3">
              {DEMO_DRIVERS.map(driver => {
                const route = plan.routes.find(item => item.driverId === driver.id);
                return (
                  <article key={driver.id} className="border border-white/10 bg-[#142328] p-4">
                    <div className="mb-4 flex items-center gap-2 text-xs font-bold"><span className="h-2.5 w-2.5 rounded-full" style={{background: driver.color}}/>{driver.id}</div>
                    <p className="text-sm font-semibold">{driver.name}</p>
                    <p className="mt-1 text-[11px] text-[#8eaaa6]">{driver.vehicle}</p>
                    <div className="mt-4 h-1 overflow-hidden bg-white/10">
                      <div className="h-full" style={{background:driver.color,width: ((route?.loadKg || 0) / driver.capacityKg * 100) + '%'}}/>
                    </div>
                    <p className="mt-2 font-mono text-[11px] text-[#b9c8c1]">{route?.loadKg ?? 0}/{driver.capacityKg} kg</p>
                    <p className="mt-4 font-mono text-2xl text-[#ecf4ed]">{route ? formatKm(route.distanceKm) : '—'}</p>
                    <p className="mt-2 text-[11px] text-[#90a8a6]">{route ? route.stopIds.length + ' scheduled stops' : 'No assignments'}</p>
                    {route && <div className="mt-4 space-y-1 border-t border-white/10 pt-3">
                      {route.stopIds.map((id, index) => <button key={id} onClick={() => dispatch({ type: 'select', id })} type="button" className="flex w-full items-center gap-2 py-1 text-left text-[11px] text-[#b5c8c1] hover:text-white">
                        <span className="font-mono text-[#7a9992]">{String(index+1).padStart(2,'0')}</span><span className="truncate">{state.stops.find(item => item.id === id)?.address}</span>
                      </button>)}
                    </div>}
                  </article>
                );
              })}
            </div>}
            {plan && plan.unassignedIds.length > 0 && <p className="mt-4 border border-[#80643f] bg-[#35281a] px-4 py-3 text-xs text-[#f9c895]">{plan.unassignedIds.length} stops exceed remaining capacity. They have not been dispatched.</p>}
          </section>

          <section className="border border-white/10 bg-[#101b1f] px-5 py-6 md:px-6" aria-label="Activity history">
            <p className="text-[10px] uppercase tracking-[.2em] text-[#8ba7a2]">System trail / 04</p>
            <h2 className="mt-1 text-xl font-semibold">Decision log</h2>
            <div className="mt-6 space-y-5">
              {state.activity.map((event, index) => <div key={event.id} className="relative flex gap-3">
                <span className={`mt-1 h-2 w-2 shrink-0 rounded-full ${index===0 ? 'bg-[#99e8be]' : 'bg-[#5b7672]'}`}/>
                <div className="min-w-0">
                  <p className="text-xs font-semibold text-[#e1eee6]">{event.title}</p>
                  <p className="mt-1 text-xs leading-relaxed text-[#8da4a0]">{event.detail}</p>
                </div>
              </div>)}
            </div>
            <div className="mt-7 border-t border-white/10 pt-4 text-[11px] leading-relaxed text-[#708e88]">
              <span className="font-semibold text-[#b4cabf]">Method:</span> express-first assignment, vehicle weight limits and a nearest-neighbor travel heuristic. Distances are great-circle estimates, not road distance, traffic, ETAs or a global optimum.
            </div>
          </section>
        </div>
        <div className="mt-8 flex flex-wrap items-center justify-between gap-4 border-t border-white/10 pt-5 text-xs text-[#78918d]">
          <p>FleetFlow Scenario Lab · demo data only · not connected to live fleet telemetry.</p>
          <Link href="/architecture" className="inline-flex items-center gap-2 text-[#a7cdbb] hover:text-white">Explore platform architecture <ArrowRight size={14}/></Link>
        </div>
      </main>
      <SiteFooter />
    </div>
  );
}

function ArrowUpRightIcon() {
  return <ArrowDownRight size={14} className="-rotate-90" aria-hidden="true" />;
}
