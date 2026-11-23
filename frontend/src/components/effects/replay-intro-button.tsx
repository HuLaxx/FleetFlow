import Link from 'next/link';
import { Play } from 'lucide-react';

/** Direct link to the persistent intro. No timing or session-storage dependence. */
export function ReplayIntroButton({ className = '' }: { className?: string }) {
  return (
    <Link
      href="/intro"
      className={`inline-flex items-center gap-2 border border-[#568371] px-4 py-3 text-xs font-semibold text-[#bce8cf] transition hover:border-[#c8f7dc] hover:bg-[#19372d] hover:text-white focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#9ce6bf] ${className}`}
    >
      <Play size={14} aria-hidden="true" />
      View loading screen
    </Link>
  );
}
