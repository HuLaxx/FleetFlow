import Link from 'next/link';
import {
  ArrowRight, ArrowUpRight, CheckCircle2, Database, Layers3,
  MapPinned, MoveUpRight, Route, ShieldCheck,
} from 'lucide-react';
import { SiteHeader } from '@/components/site/site-header';
import { SiteFooter } from '@/components/site/site-footer';
import { ReplayIntroButton } from '@/components/effects/replay-intro-button';
import { DispatchBoard } from '@/components/home/dispatch-board';
import { RoutingProof } from '@/components/home/routing-proof';
import { StreamReplay } from '@/components/home/stream-replay';
import './home.css';

const shift = [
  { code: '01', title: 'Import the manifest', text: 'Bring orders, depots, delivery zones and vehicle capacity into one dispatch view.', detail: 'Understand the work' },
  { code: '02', title: 'Build a feasible plan', text: 'Compare suggested routes, review exceptions and check loads before approving assignments.', detail: 'Make the decision' },
  { code: '03', title: 'Follow every delivery', text: 'Track state changes, surface exceptions and keep a reviewable decision trail for operators.', detail: 'Close the loop' },
];

const systems = [
  { label: 'Control surface', value: 'Next.js · tRPC · MapLibre', icon: MapPinned },
  { label: 'Optimization path', value: 'FastAPI · OR-Tools', icon: Route },
  { label: 'Operational data', value: 'PostgreSQL · PostGIS · WebSockets', icon: Database },
  { label: 'Data platform', value: 'Kafka · Spark streaming · dbt lakehouse', icon: Layers3 },
];

export default function HomePage() {
  return (
    <div className="ff-home relative z-10 min-h-screen bg-[#0c1418] text-[#eaf2ed]">
      <SiteHeader />
      <main>
        <section className="mx-auto max-w-[1580px] px-4 pb-20 pt-36 md:px-8 md:pt-44">
          <div className="grid items-center gap-12 xl:grid-cols-[.94fr_1.06fr] xl:gap-16">
            <div className="ff-rise pb-2">
              <div className="mb-7 flex items-center gap-3 text-[11px] font-semibold uppercase tracking-[.24em] text-[#9dceb2]">
                <span className="h-[1px] w-8 bg-[#9dceb2]"/> Logistics, without guesswork
              </div>
              <h1 className="max-w-[850px] text-[clamp(3.5rem,6.25vw,7.2rem)] font-semibold leading-[.95] tracking-[-.075em]">
                A better way to <span className="italic font-normal text-[#a7ddbf]">move</span> everything.
              </h1>
              <p className="mt-8 max-w-xl text-base leading-[1.85] text-[#94aeaa] md:text-lg">
                FleetFlow is a dispatch decision workspace for planning deliveries, allocating capacity and keeping every stop accountable. Not another map filled with unexplained dots.
              </p>
              <div className="mt-9 flex flex-wrap gap-3">
                <Link href="/demo" className="inline-flex items-center gap-3 bg-[#aff1cb] px-6 py-4 text-sm font-bold text-[#0a2017] transition hover:bg-[#d1fbe2]">
                  Open the dispatch lab <ArrowUpRight size={17}/>
                </Link>
                <Link href="/demo/live" className="inline-flex items-center gap-3 border border-[#405d55] px-6 py-4 text-sm font-semibold text-[#d2e7d8] transition hover:bg-white/5">
                  Connected workspace <ArrowRight size={16}/>
                </Link>
              </div>
              <p className="mt-5 flex items-center gap-2 text-xs text-[#79978b]"><ShieldCheck size={14}/> Interactive lab is simulated. The connected workspace requires a configured backend.</p>
              <ReplayIntroButton className="mt-4" />
              <div className="mt-14 flex flex-wrap items-center gap-6 border-t border-white/10 pt-6">
                <div><span className="font-mono text-xl text-[#d9ede2]">01</span><p className="text-[11px] uppercase tracking-widest text-[#79948b]">Plan</p></div>
                <span className="h-px w-10 bg-white/15"/>
                <div><span className="font-mono text-xl text-[#d9ede2]">02</span><p className="text-[11px] uppercase tracking-widest text-[#79948b]">Dispatch</p></div>
                <span className="h-px w-10 bg-white/15"/>
                <div><span className="font-mono text-xl text-[#d9ede2]">03</span><p className="text-[11px] uppercase tracking-widest text-[#79948b]">Deliver</p></div>
              </div>
            </div>
            <div className="ff-rise" style={{ ['--ff-delay' as string]: '160ms' }}>
              <DispatchBoard />
            </div>
          </div>
        </section>

        <section className="border-y border-[#2c4643] bg-[#11221e]">
          <div className="mx-auto grid max-w-[1580px] gap-3 px-4 py-7 text-xs uppercase tracking-[.18em] text-[#a0c9b3] md:grid-cols-3 md:gap-6 md:px-8">
            <p className="flex items-center gap-3"><CheckCircle2 size={16}/> Capacity-aware planning</p>
            <p className="flex items-center gap-3"><CheckCircle2 size={16}/> Operator-controlled dispatch</p>
            <p className="flex items-center gap-3"><CheckCircle2 size={16}/> Traceable delivery states</p>
          </div>
        </section>

        <section className="mx-auto max-w-[1580px] px-4 py-24 md:px-8 md:py-32">
          <div className="mb-12 flex flex-col justify-between gap-6 md:flex-row md:items-end">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[.22em] text-[#96bea8]">How dispatch actually works</p>
              <h2 className="mt-5 max-w-3xl text-[clamp(2.5rem,4.5vw,5.1rem)] font-semibold leading-[1.03] tracking-[-.06em]">One shift. Three decisions.</h2>
            </div>
            <p className="max-w-sm text-sm leading-relaxed text-[#8da7a1]">A connected workflow designed around real operational questions, not technical buzzwords.</p>
          </div>
          <div className="grid border-t border-white/15 lg:grid-cols-3">
            {shift.map((stage, index) => (
              <article key={stage.code} className="group flex min-h-[340px] flex-col justify-between border-b border-white/15 p-6 lg:border-b-0 lg:border-r lg:p-8 lg:last:border-r-0">
                <div className="flex items-start justify-between">
                  <span className="font-mono text-5xl tracking-tighter text-[#719f87]">{stage.code}</span>
                  <MoveUpRight size={20} className="text-[#587f6d] transition group-hover:-translate-y-1 group-hover:translate-x-1 group-hover:text-[#b2e9ca]"/>
                </div>
                <div>
                  <p className="mb-4 text-[11px] uppercase tracking-[.2em] text-[#8eafa2]">{stage.detail}</p>
                  <h3 className="max-w-sm text-3xl font-semibold leading-tight tracking-[-.04em]">{stage.title}</h3>
                  <p className="mt-4 max-w-sm text-sm leading-relaxed text-[#94a8a3]">{stage.text}</p>
                </div>
              </article>
            ))}
          </div>
        </section>

        <section className="border-y border-white/10 bg-[#0f1a1d]">
          <div className="mx-auto max-w-[1580px] px-4 py-24 md:px-8 md:py-32">
            <div className="mb-12 flex flex-col justify-between gap-6 md:flex-row md:items-end">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[.22em] text-[#96bea8]">Measured in CI, not promised</p>
                <h2 className="mt-5 max-w-3xl text-[clamp(2.5rem,4.5vw,5.1rem)] font-semibold leading-[1.03] tracking-[-.06em]">A plan only counts if it holds.</h2>
              </div>
              <p className="max-w-sm text-sm leading-relaxed text-[#8da7a1]">Both results come from GitHub Actions runs on main, against real OR-Tools and a real Kafka broker. The data is synthetic and the limits are stated.</p>
            </div>
            <div className="grid gap-12 xl:grid-cols-[1.15fr_.85fr] xl:gap-16">
              <div>
                <h3 className="mb-6 text-2xl font-semibold tracking-[-.03em]">Route planning against simple baselines</h3>
                <RoutingProof />
              </div>
              <div>
                <h3 className="mb-6 text-2xl font-semibold tracking-[-.03em]">GPS stream, played at its real speed</h3>
                <StreamReplay />
              </div>
            </div>
          </div>
        </section>

        <section className="border-y border-white/10 bg-[#121e22]">
          <div className="mx-auto grid max-w-[1580px] gap-14 px-4 py-20 md:px-8 lg:grid-cols-[.78fr_1.22fr] lg:py-28">
            <div>
              <p className="text-[11px] uppercase tracking-[.22em] text-[#9dbba7]">An engineering foundation</p>
              <h2 className="mt-5 text-4xl font-semibold leading-tight tracking-[-.055em] md:text-5xl">Built for decisions. Designed for operators.</h2>
              <p className="mt-6 max-w-lg text-sm leading-[1.9] text-[#91a7a2]">The repository includes routing, data and event-processing components. Some integrations are local-first or optional; the deployed scenario is deliberately independent of them.</p>
              <Link href="/architecture" className="mt-8 inline-flex items-center gap-2 border-b border-[#8aa999] pb-2 text-sm font-semibold text-[#d4e9db]">Explore the architecture <ArrowUpRight size={16}/></Link>
            </div>
            <div className="grid grid-cols-1 gap-px border border-white/10 bg-white/10 sm:grid-cols-2">
              {systems.map(item => (
                <div key={item.label} className="min-h-44 bg-[#121e22] p-6 md:p-8">
                  <item.icon size={24} className="text-[#9cd9b4]"/>
                  <h3 className="mt-7 text-sm font-semibold">{item.label}</h3>
                  <p className="mt-2 text-xs leading-relaxed text-[#8fa7a3]">{item.value}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="mx-auto max-w-[1580px] px-4 py-24 md:px-8 md:py-32">
          <div className="grid items-end gap-10 lg:grid-cols-[1fr_auto]">
            <div>
              <p className="mb-5 text-[11px] uppercase tracking-[.22em] text-[#95c4a6]">Try the complete scenario</p>
              <h2 className="max-w-4xl text-[clamp(2.7rem,5.3vw,6rem)] font-semibold leading-[1.02] tracking-[-.06em]">Your next shift starts with a plan.</h2>
              <p className="mt-6 max-w-xl text-sm leading-relaxed text-[#8fa7a1]">Assign a driver, inspect capacity, approve routes and mark deliveries completed. Every action changes the scenario.</p>
            </div>
            <Link href="/demo" className="inline-flex items-center justify-center gap-3 bg-[#aff1cb] px-7 py-5 text-sm font-bold text-[#0a2017] transition hover:bg-[#d1fbe2]">
              Enter Dispatch Lab <ArrowRight size={17}/>
            </Link>
          </div>
        </section>
      </main>
      <SiteFooter />
    </div>
  );
}
