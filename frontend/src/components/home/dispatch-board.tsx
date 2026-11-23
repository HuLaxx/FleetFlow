'use client';

import { useEffect, useState } from 'react';

/*
 * Hero dispatch board. Same map as the original route illustration, now played as
 * one shift: eight unassigned stops, a solving pass, three capacity-checked routes,
 * then vans driving them and stops ticking to delivered. Illustrative scenario only.
 */

type Pt = [number, number];
type RouteDef = { id: string; label: string; color: string; stops: Pt[]; seconds: number };

const DEPOT: Pt = [350, 308];

const ROUTES: RouteDef[] = [
  { id: 'north-west', label: 'Van A, Chelsea and Soho', color: '#95e6bc', stops: [[200, 188], [168, 364], [302, 450]], seconds: 6.4 },
  { id: 'midtown', label: 'Van B, Midtown', color: '#ffc28b', stops: [[520, 230], [532, 117], [410, 116]], seconds: 6.0 },
  { id: 'lower-east', label: 'Van C, Lower East Side', color: '#93baff', stops: [[484, 425], [560, 490]], seconds: 4.8 },
];

const ALL_STOPS = ROUTES.flatMap((r) => r.stops);
const TOTAL_STOPS = ALL_STOPS.length;

// Candidate links the "solver" flickers through before settling.
const CANDIDATES: Array<[Pt, Pt]> = [
  [DEPOT, [200, 188]], [[200, 188], [410, 116]], [[168, 364], [484, 425]], [DEPOT, [532, 117]],
  [[302, 450], [560, 490]], [[520, 230], [484, 425]], [DEPOT, [168, 364]], [[410, 116], [200, 188]],
  [[302, 450], [484, 425]], [DEPOT, [560, 490]], [[532, 117], [520, 230]], [[168, 364], [200, 188]],
];

const pathOf = (r: RouteDef) => `M ${DEPOT.join(' ')} ${r.stops.map((p) => `L ${p.join(' ')}`).join(' ')} L ${DEPOT.join(' ')}`;

function segmentFractions(r: RouteDef) {
  const pts = [DEPOT, ...r.stops, DEPOT];
  const lens = pts.slice(1).map((p, i) => Math.hypot(p[0] - pts[i][0], p[1] - pts[i][1]));
  const total = lens.reduce((a, b) => a + b, 0);
  let acc = 0;
  return r.stops.map((_, i) => {
    acc += lens[i];
    return acc / total;
  });
}

type Phase = 'unplanned' | 'solving' | 'dispatched';

const SOLVE_AT = 1700;
const DISPATCH_AT = 3900;

export function DispatchBoard() {
  const [phase, setPhase] = useState<Phase>('unplanned');
  const [run, setRun] = useState(0);
  const [delivered, setDelivered] = useState<string[]>([]);
  const [focus, setFocus] = useState<string | null>(null);

  useEffect(() => {
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const ids: number[] = [];
    const later = (ms: number, fn: () => void) => ids.push(window.setTimeout(fn, ms));
    const clear = () => ids.forEach((id) => window.clearTimeout(id));

    if (reduce) {
      later(0, () => {
        setPhase('dispatched');
        setDelivered(ALL_STOPS.map((p) => p.join(',')));
      });
      return clear;
    }

    later(0, () => {
      setPhase('unplanned');
      setDelivered([]);
    });
    later(SOLVE_AT, () => setPhase('solving'));
    later(DISPATCH_AT, () => setPhase('dispatched'));
    // Drawing takes ~900ms, then vans leave the depot.
    const depart = DISPATCH_AT + 900;
    ROUTES.forEach((r) => {
      segmentFractions(r).forEach((f, i) => {
        const key = r.stops[i].join(',');
        later(depart + f * r.seconds * 1000, () => setDelivered((d) => (d.includes(key) ? d : [...d, key])));
      });
    });
    const longest = Math.max(...ROUTES.map((r) => r.seconds));
    later(depart + longest * 1000 + 3200, () => setRun((n) => n + 1));
    return clear;
  }, [run]);

  const status =
    phase === 'unplanned'
      ? `${TOTAL_STOPS} stops waiting for a plan`
      : phase === 'solving'
        ? 'Solving: capacity and delivery windows'
        : delivered.length === TOTAL_STOPS
          ? 'Shift complete, every stop delivered'
          : 'Routes approved, vans on the road';

  return (
    <div className="ffb" data-phase={phase} data-focus={focus ?? 'none'} key={run}>
      <svg viewBox="0 10 700 660" preserveAspectRatio="none" className="ffb__svg" aria-hidden="true">
        <defs>
          <pattern id="ffb-grid" width="48" height="48" patternUnits="userSpaceOnUse">
            <path d="M 48 0 L 0 0 0 48" fill="none" stroke="#50605d" strokeWidth="1" opacity=".28" />
          </pattern>
          <radialGradient id="ffb-depot-glow">
            <stop offset="0" stopColor="#95e6bc" stopOpacity=".35" />
            <stop offset="1" stopColor="#95e6bc" stopOpacity="0" />
          </radialGradient>
        </defs>
        <rect width="700" height="700" fill="#112024" />
        <rect width="700" height="700" fill="url(#ffb-grid)" />
        <path d="M 0 0 L 100 0 Q 35 168 108 310 T 90 570 L 96 700 L 0 700 Z" fill="#143a43" />
        <path d="M 670 0 L 700 0 L 700 700 L 660 700 L 654 570 Q 600 280 670 0" fill="#143a43" />
        <g stroke="#3c5e59" fill="none" opacity=".6">
          <path d="M 175 0 L 121 700 M 278 0 L 251 700 M 376 0 L 344 700 M 484 0 L 448 700 M 580 0 L 562 700" strokeWidth="5" />
          <path d="M 96 120 L 642 87 M 93 224 L 640 200 M 95 330 L 637 306 M 90 439 L 639 411" strokeWidth="4" />
        </g>
        <g fontFamily="monospace" fontSize="10" fill="#6d9591" letterSpacing="2">
          <text x="180" y="70">CHELSEA</text>
          <text x="478" y="150">MIDTOWN</text>
          <text x="151" y="512">SOHO</text>
          <text x="432" y="495">LOWER EAST SIDE</text>
        </g>

        <g className="ffb__candidates">
          {CANDIDATES.map(([a, b], i) => (
            <line key={i} x1={a[0]} y1={a[1]} x2={b[0]} y2={b[1]} style={{ animationDelay: `${(i % 6) * 140}ms` }} />
          ))}
        </g>

        {ROUTES.map((r) => (
          <g key={r.id} className="ffb__route" data-route={r.id}>
            <path className="ffb__line" d={pathOf(r)} stroke={r.color} pathLength={1} />
            <g className="ffb__van" style={{ offsetPath: `path('${pathOf(r)}')`, animationDuration: `${r.seconds}s` }}>
              <rect x="-9" y="-6" width="18" height="12" rx="2" fill={r.color} stroke="#0b191b" strokeWidth="2" />
            </g>
          </g>
        ))}

        <circle cx={DEPOT[0]} cy={DEPOT[1]} r="46" fill="url(#ffb-depot-glow)" className="ffb__depot-glow" />
        {ROUTES.map((r) =>
          r.stops.map((p) => {
            const key = p.join(',');
            const done = delivered.includes(key);
            return (
              <g key={key} className="ffb__stop" data-route={r.id} data-done={done}>
                <circle cx={p[0]} cy={p[1]} r="11" stroke={r.color} />
                <path d={`M ${p[0] - 4.5} ${p[1]} l 3 3 l 6 -6`} className="ffb__tick" />
              </g>
            );
          }),
        )}
        <rect x="338" y="296" width="24" height="24" rx="4" fill="#b3f0d2" stroke="#142b29" strokeWidth="4" />
      </svg>

      <div className="ffb__chip">
        <span className="ffb__dot" />
        <span>{status}</span>
      </div>

      <button type="button" className="ffb__replan" onClick={() => setRun((n) => n + 1)}>
        Re-plan the shift
      </button>

      <div className="ffb__readout">
        <div>
          <p className="ffb__k">Route groups</p>
          <p className="ffb__v">
            {phase === 'dispatched' ? '03' : '00'} <span>vehicles</span>
          </p>
        </div>
        <div>
          <p className="ffb__k">Delivered</p>
          <p className="ffb__v" aria-live="polite">
            {String(delivered.length).padStart(2, '0')}
            <span>/{String(TOTAL_STOPS).padStart(2, '0')} stops</span>
          </p>
        </div>
        <ul className="ffb__legend" aria-label="Highlight a route">
          {ROUTES.map((r) => (
            <li key={r.id}>
              <button
                type="button"
                onMouseEnter={() => setFocus(r.id)}
                onMouseLeave={() => setFocus(null)}
                onFocus={() => setFocus(r.id)}
                onBlur={() => setFocus(null)}
                aria-pressed={focus === r.id}
              >
                <i style={{ background: r.color }} />
                {r.label}
              </button>
            </li>
          ))}
        </ul>
        <p className="ffb__note">Illustrative scenario. Real routing results are below.</p>
      </div>
    </div>
  );
}
