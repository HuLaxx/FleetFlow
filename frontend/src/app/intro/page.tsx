import Link from 'next/link';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'FleetFlow | Loading Screen Preview',
  description: 'A full, interactive preview of the FleetFlow branded opening sequence.',
};

/**
 * The real animated intro is rendered by the shared layout LoadingScreen.
 * On this route it stays visible until the user clicks Continue to FleetFlow.
 * This semantic fallback remains available if the animation cannot render.
 */
export default function IntroPreviewPage() {
  return (
    <main className="flex min-h-svh flex-col items-center justify-center gap-4 bg-[#0a1417] px-6 text-center text-[#edf5ef]">
      <h1 className="text-3xl font-semibold">FleetFlow loading screen</h1>
      <p className="max-w-lg text-sm leading-relaxed text-[#a4c9b7]">
        This is the dedicated introduction preview. It stays on screen until
        you choose to continue to the application.
      </p>
      <Link href="/" className="border border-[#95d6b5] px-5 py-3 text-sm text-[#c5efd6]">
        Back to FleetFlow
      </Link>
    </main>
  );
}
