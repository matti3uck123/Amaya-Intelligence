"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useRef, useState } from "react";

import { ApiError, createRatingFromPath, createRatingFromUpload } from "@/lib/api";

type Mode = "upload" | "path";

export default function NewRatingPage() {
  const router = useRouter();
  const [mode, setMode] = useState<Mode>("upload");
  const [company, setCompany] = useState("");
  const [sector, setSector] = useState("");
  const [notes, setNotes] = useState("");
  const [seal, setSeal] = useState(false);
  const [files, setFiles] = useState<File[]>([]);
  const [dragActive, setDragActive] = useState(false);
  const [path, setPath] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const addFiles = useCallback((incoming: FileList | File[]) => {
    const next = Array.from(incoming);
    setFiles((prev) => {
      const seen = new Set(prev.map((f) => `${f.name}:${f.size}`));
      const merged = [...prev];
      for (const f of next) {
        const key = `${f.name}:${f.size}`;
        if (!seen.has(key)) {
          seen.add(key);
          merged.push(f);
        }
      }
      return merged;
    });
  }, []);

  const removeFile = (idx: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== idx));
  };

  const onDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragActive(false);
    if (e.dataTransfer.files.length > 0) addFiles(e.dataTransfer.files);
  };

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!company.trim()) {
      setError("Company name is required.");
      return;
    }
    if (mode === "upload" && files.length === 0) {
      setError("Add at least one file to the data room.");
      return;
    }
    if (mode === "path" && !path.trim()) {
      setError("Enter a local directory path.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const accepted =
        mode === "upload"
          ? await createRatingFromUpload({
              files,
              company: company.trim(),
              sector: sector.trim() || undefined,
              notes: notes.trim() || undefined,
              seal,
            })
          : await createRatingFromPath({
              path: path.trim(),
              company: company.trim(),
              sector: sector.trim() || undefined,
              notes: notes.trim() || undefined,
              seal,
            });
      router.push(`/ratings/${encodeURIComponent(accepted.rating_id)}`);
    } catch (err) {
      const msg =
        err instanceof ApiError
          ? err.message
          : err instanceof Error
            ? err.message
            : String(err);
      setError(msg);
      setSubmitting(false);
    }
  };

  const totalBytes = files.reduce((acc, f) => acc + f.size, 0);

  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <header className="space-y-2">
        <Link
          href="/"
          className="text-xs font-medium uppercase tracking-widest text-ink-500 hover:text-ink-300"
        >
          ← Ratings
        </Link>
        <h1 className="font-display text-3xl font-bold tracking-tight">
          New rating
        </h1>
        <p className="text-ink-300">
          Upload a data room and Amaya will run 16 specialized agents across
          12 durability dimensions and 4 chain positions, then deterministically
          score and grade the company.
        </p>
      </header>

      <form onSubmit={onSubmit} className="space-y-6">
        <div className="card p-6 space-y-5">
          <div className="grid gap-5 sm:grid-cols-2">
            <div className="space-y-1.5">
              <label className="label" htmlFor="company">
                Company <span className="text-grade-f">*</span>
              </label>
              <input
                id="company"
                className="input"
                placeholder="e.g. Nordic Logistics AG"
                value={company}
                onChange={(e) => setCompany(e.target.value)}
                required
              />
            </div>
            <div className="space-y-1.5">
              <label className="label" htmlFor="sector">
                Sector
              </label>
              <input
                id="sector"
                className="input"
                placeholder="e.g. Industrial Logistics"
                value={sector}
                onChange={(e) => setSector(e.target.value)}
              />
            </div>
          </div>
          <div className="space-y-1.5">
            <label className="label" htmlFor="notes">
              Analyst notes
            </label>
            <textarea
              id="notes"
              rows={3}
              className="input resize-y"
              placeholder="Context that should inform the rating (commissioning analyst, known caveats, etc.)"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
            />
          </div>
          <label className="flex cursor-pointer items-center gap-2.5 text-sm text-ink-200">
            <input
              type="checkbox"
              checked={seal}
              onChange={(e) => setSeal(e.target.checked)}
              className="h-4 w-4 rounded border-ink-700 bg-ink-900 text-copper-500 focus:ring-copper-500"
            />
            Seal rating into provenance ledger
            <span className="text-xs text-ink-500">
              (writes an immutable bundle on completion)
            </span>
          </label>
        </div>

        <div className="card p-6 space-y-4">
          <div className="flex items-center gap-2">
            <ModeTab
              label="Upload files"
              active={mode === "upload"}
              onClick={() => setMode("upload")}
            />
            <ModeTab
              label="Local directory"
              active={mode === "path"}
              onClick={() => setMode("path")}
            />
          </div>

          {mode === "upload" ? (
            <div className="space-y-3">
              <div
                onDragOver={(e) => {
                  e.preventDefault();
                  setDragActive(true);
                }}
                onDragLeave={() => setDragActive(false)}
                onDrop={onDrop}
                onClick={() => inputRef.current?.click()}
                className={`flex cursor-pointer flex-col items-center justify-center gap-2 rounded-2xl border-2 border-dashed px-6 py-10 text-center transition-colors ${
                  dragActive
                    ? "border-copper-400 bg-copper-500/10"
                    : "border-ink-700 hover:border-ink-600 hover:bg-ink-900/50"
                }`}
              >
                <UploadIcon />
                <div className="text-sm text-ink-200">
                  Drop files here or{" "}
                  <span className="text-copper-300 underline">browse</span>
                </div>
                <div className="text-xs text-ink-500">
                  PDF, DOCX, XLSX, PPTX, TXT, MD, HTML, CSV, JSON, TSV
                </div>
                <input
                  ref={inputRef}
                  type="file"
                  multiple
                  className="hidden"
                  onChange={(e) => {
                    if (e.target.files) addFiles(e.target.files);
                    e.target.value = "";
                  }}
                />
              </div>
              {files.length > 0 ? (
                <div className="space-y-1.5">
                  <div className="flex items-baseline justify-between text-xs text-ink-400">
                    <span className="font-medium uppercase tracking-wider">
                      {files.length} file{files.length === 1 ? "" : "s"}
                    </span>
                    <span className="font-mono">{formatBytes(totalBytes)}</span>
                  </div>
                  <ul className="divide-y divide-ink-800 overflow-hidden rounded-xl border border-ink-800">
                    {files.map((f, i) => (
                      <li
                        key={`${f.name}:${f.size}:${i}`}
                        className="flex items-center justify-between gap-3 bg-ink-900/40 px-3 py-2 text-sm"
                      >
                        <div className="min-w-0 flex-1 truncate">
                          <span className="text-ink-100">{f.name}</span>
                          <span className="ml-2 font-mono text-[11px] text-ink-500">
                            {formatBytes(f.size)}
                          </span>
                        </div>
                        <button
                          type="button"
                          onClick={() => removeFile(i)}
                          className="text-xs text-ink-500 hover:text-grade-f"
                        >
                          remove
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </div>
          ) : (
            <div className="space-y-2">
              <label className="label" htmlFor="path">
                Directory path on the API host
              </label>
              <input
                id="path"
                className="input font-mono text-sm"
                placeholder="/absolute/path/to/dataroom"
                value={path}
                onChange={(e) => setPath(e.target.value)}
              />
              <p className="text-xs text-ink-500">
                Useful when files already sit next to the API server — skips
                upload entirely.
              </p>
            </div>
          )}
        </div>

        {error ? (
          <div className="card border-grade-f/40 bg-grade-f/10 p-4 text-sm text-grade-f">
            {error}
          </div>
        ) : null}

        <div className="flex items-center justify-between">
          <Link href="/" className="btn-ghost">
            Cancel
          </Link>
          <button
            type="submit"
            disabled={submitting}
            className="btn-primary disabled:cursor-not-allowed disabled:opacity-60"
          >
            {submitting ? "Starting…" : "Start rating"}
          </button>
        </div>
      </form>
    </div>
  );
}

function ModeTab({
  label,
  active,
  onClick,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-full px-3 py-1 text-xs font-medium uppercase tracking-wider transition-colors ${
        active
          ? "bg-copper-500/20 text-copper-200 ring-1 ring-copper-500/40"
          : "text-ink-400 hover:text-ink-200"
      }`}
    >
      {label}
    </button>
  );
}

function UploadIcon() {
  return (
    <svg
      width="28"
      height="28"
      viewBox="0 0 24 24"
      fill="none"
      className="text-ink-400"
      aria-hidden
    >
      <path
        d="M12 16V4m0 0-4 4m4-4 4 4M4 20h16"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  if (n < 1024 * 1024 * 1024) return `${(n / (1024 * 1024)).toFixed(1)} MB`;
  return `${(n / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}
