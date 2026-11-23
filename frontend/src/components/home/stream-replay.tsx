'use client';

import { useEffect, useRef, useState } from 'react';

/*
 * Plays back the Spark Structured Streaming benchmark at its measured speed:
 * 200,000 synthetic GPS events from Kafka to validated, de-duplicated Parquet in
 * 11.27 s on a GitHub Actions runner (single-node Spark local[2]).
 */
const EVENTS = 200_000;
const SECONDS = 11.27;

export function StreamReplay() {
  const ref = useRef<HTMLDivElement>(null);
  const valueRef = useRef<HTMLSpanElement>(null);
  const clockRef = useRef<HTMLSpanElement>(null);
  const barRef = useRef<HTMLSpanElement>(null);
  const [state, setState] = useState<'idle' | 'running' | 'done'>('idle');
  const [run, setRun] = useState(0);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    let raf = 0;
    let started = false;

    const paint = (fraction: number) => {
      const n = Math.round(EVENTS * fraction);
      if (valueRef.current) valueRef.current.textContent = n.toLocaleString('en-GB');
      if (clockRef.current) clockRef.current.textContent = (SECONDS * fraction).toFixed(2);
      if (barRef.current) barRef.current.style.transform = `scaleX(${fraction})`;
    };

    const start = () => {
      started = true;
      if (reduce) {
        paint(1);
        raf = requestAnimationFrame(() => setState('done'));
        return;
      }
      const t0 = performance.now();
      raf = requestAnimationFrame(function step(now) {
        const f = Math.min(1, (now - t0) / (SECONDS * 1000));
        paint(f);
        if (f < 1) raf = requestAnimationFrame(step);
        else setState('done');
      });
      setState('running');
    };

    paint(0);
    const io = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !started) start();
      },
      { threshold: 0.5 },
    );
    io.observe(el);
    return () => {
      io.disconnect();
      cancelAnimationFrame(raf);
    };
  }, [run]);

  return (
    <div className="ffs" ref={ref} data-state={state}>
      <p className="ffs__k">GPS events, Kafka to clean Parquet</p>
      <p className="ffs__value">
        <span ref={valueRef}>0</span>
      </p>
      <div className="ffs__bar" aria-hidden="true">
        <span ref={barRef} />
      </div>
      <div className="ffs__meta">
        <span>
          <span ref={clockRef}>0.00</span> s of 11.27 s, played at real speed
        </span>
        <button type="button" onClick={() => setRun((n) => n + 1)} disabled={state === 'running'}>
          Replay
        </button>
      </div>
      <dl className="ffs__facts">
        <div>
          <dt>End to end</dt>
          <dd>17,748 events/s</dd>
        </div>
        <div>
          <dt>Spark peak</dt>
          <dd>19,566 rows/s</dd>
        </div>
        <div>
          <dt>Duplicates, late data</dt>
          <dd>Dropped, tested</dd>
        </div>
      </dl>
      <p className="ffs__note">Synthetic GPS events on a 2-core GitHub Actions runner, Spark local[2]. Not a production throughput claim.</p>
    </div>
  );
}
