import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";
import { HeaderNav } from "@/components/HeaderNav";

export const metadata: Metadata = {
  title: "Amaya Intelligence — ADI",
  description:
    "AI Durability Index ratings — evidence-linked, methodology-versioned, provenance-sealed.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen font-sans antialiased">
        <div className="flex min-h-screen flex-col">
          <Header />
          <main className="flex-1">
            <div className="mx-auto w-full max-w-6xl px-6 py-10">
              {children}
            </div>
          </main>
          <Footer />
        </div>
      </body>
    </html>
  );
}

function Header() {
  return (
    <header className="sticky top-0 z-40 border-b border-ink-800/60 bg-ink-950/85 backdrop-blur-md">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <Link href="/" className="flex items-center gap-3">
          <Logo />
          <div className="leading-tight">
            <div className="font-display text-base font-semibold tracking-tight">
              Amaya Intelligence
            </div>
            <div className="text-[11px] uppercase tracking-[0.2em] text-ink-400">
              AI Durability Index
            </div>
          </div>
        </Link>
        <HeaderNav />
      </div>
    </header>
  );
}

function Footer() {
  return (
    <footer className="border-t border-ink-800/60 py-6">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-2 px-6 text-xs text-ink-500">
        <div>
          Methodology v1.0 · deterministic scoring · provenance-sealed
        </div>
        <div className="font-mono text-ink-600">
          yvl capital partners
        </div>
      </div>
    </footer>
  );
}

function Logo() {
  return (
    <svg
      width="32"
      height="32"
      viewBox="0 0 32 32"
      fill="none"
      aria-hidden="true"
      className="text-copper-500"
    >
      <circle
        cx="16"
        cy="16"
        r="13"
        stroke="currentColor"
        strokeWidth="1.5"
        className="opacity-60"
      />
      <path
        d="M9 20 L14 10 L18 16 L23 10"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
