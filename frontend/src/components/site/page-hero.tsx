import type { ReactNode } from 'react';

type PageHeroProps = {
  eyebrow: string;
  title: string;
  lede: ReactNode;
  width?: '6xl' | '7xl';
  children?: ReactNode;
};

/** v2 page opening: mint rule label, large tight heading, the 76px mint grid from the intro as texture. */
export function PageHero({ eyebrow, title, lede, width = '7xl', children }: PageHeroProps) {
  const container = width === '6xl' ? 'max-w-6xl' : 'max-w-7xl';
  return (
    <section className="relative overflow-hidden border-b border-white/10">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 opacity-60"
        style={{
          backgroundImage:
            'linear-gradient(rgba(145,206,169,.07) 1px, transparent 1px), linear-gradient(90deg, rgba(145,206,169,.07) 1px, transparent 1px)',
          backgroundSize: '76px 76px',
          maskImage: 'linear-gradient(180deg, #000 30%, transparent 100%)',
          WebkitMaskImage: 'linear-gradient(180deg, #000 30%, transparent 100%)',
        }}
      />
      <div aria-hidden="true" className="pointer-events-none absolute -top-40 right-[-10%] h-[520px] w-[520px] rounded-full bg-[#95e6bc]/[0.06] blur-[120px]" />
      <div className={`relative mx-auto ${container} px-6 pb-16 pt-36 md:pb-20 md:pt-44`}>
        <div className="ff-rise mb-7 flex items-center gap-3 text-[11px] font-semibold uppercase tracking-[.24em] text-[#9dceb2]">
          <span className="h-px w-8 bg-[#9dceb2]" />
          {eyebrow}
        </div>
        <h1
          className="ff-rise max-w-[17ch] text-[clamp(2.9rem,5.4vw,5.6rem)] font-semibold leading-[.98] tracking-[-.065em] text-[#eaf2ed]"
          style={{ ['--ff-delay' as string]: '80ms' }}
        >
          {title}
        </h1>
        <p className="ff-rise mt-7 max-w-2xl text-base leading-[1.85] text-[#94aeaa] md:text-lg" style={{ ['--ff-delay' as string]: '160ms' }}>
          {lede}
        </p>
        {children ? (
          <div className="ff-rise mt-9" style={{ ['--ff-delay' as string]: '240ms' }}>
            {children}
          </div>
        ) : null}
      </div>
    </section>
  );
}
