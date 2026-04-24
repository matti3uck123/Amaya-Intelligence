"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { ApiError, resetDemo } from "@/lib/api";

export function HeaderNav() {
  const router = useRouter();
  const [resetting, setResetting] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  const onReset = async () => {
    if (!confirm("Reset the demo? All ratings will be dropped and flagships re-seeded.")) {
      return;
    }
    setResetting(true);
    setToast(null);
    try {
      const res = await resetDemo();
      setToast(
        `Reset: dropped ${res.dropped.length}, seeded ${res.seeded.length}`,
      );
      router.push("/");
      router.refresh();
      setTimeout(() => setToast(null), 3200);
    } catch (err) {
      const msg =
        err instanceof ApiError
          ? err.message
          : err instanceof Error
            ? err.message
            : String(err);
      setToast(`Reset failed — ${msg}`);
      setTimeout(() => setToast(null), 5000);
    } finally {
      setResetting(false);
    }
  };

  return (
    <>
      <nav className="flex items-center gap-1">
        <button
          onClick={onReset}
          disabled={resetting}
          title="Drop all ratings and re-seed flagship Colabor rating"
          className="btn-ghost text-ink-400 hover:text-ink-100 disabled:opacity-50"
        >
          {resetting ? "Resetting…" : "Reset demo"}
        </button>
        <Link href="/" className="btn-ghost">
          Ratings
        </Link>
        <Link href="/new" className="btn-primary">
          New rating
        </Link>
      </nav>
      {toast ? (
        <div className="fixed bottom-6 left-1/2 z-50 -translate-x-1/2 rounded-full border border-ink-700 bg-ink-900/95 px-4 py-2 text-sm text-ink-100 shadow-lg backdrop-blur">
          {toast}
        </div>
      ) : null}
    </>
  );
}
