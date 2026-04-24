// Mirrors amaya/schemas.py + amaya/api/schemas.py.
// Hand-maintained rather than generated — the API surface is small and
// stable, and reading a single types file is easier than tracing an
// openapi-codegen pipeline during a demo.

export type DimensionCode =
  | "MCS" | "CPS" | "SCAE" | "CLS"
  | "VPR" | "WCI" | "RMV" | "TSR"
  | "LAL" | "SPS" | "ANCR" | "DIM";

export type ChainPosition = "upstream" | "downstream" | "lateral" | "end_consumer";

export type Grade = "A+" | "A" | "B+" | "B" | "C+" | "C" | "D" | "F";

export type JobStatus =
  | "pending"
  | "ingesting"
  | "rating"
  | "scoring"
  | "done"
  | "failed";

export interface EvidenceRef {
  source_id: string;
  kind: "document" | "interview" | "external";
  locator: string;
  snippet: string;
}

export interface DimensionScore {
  code: DimensionCode;
  score: number;
  rationale: string;
  confidence: number;
  evidence: EvidenceRef[];
}

export interface ChainPositionScore {
  position: ChainPosition;
  score: number;
  rationale: string;
}

export interface ChainAssessment {
  positions: ChainPositionScore[];
}

export interface CircuitBreakerTrigger {
  code: string;
  description: string;
  cap: number;
}

export interface ScoringResult {
  raw_score: number;
  chain_modifier: number;
  adjusted_score: number;
  final_score: number;
  grade: Grade;
  grade_label: string;
  grade_action: string;
  circuit_breakers_triggered: CircuitBreakerTrigger[];
  methodology_version: string;
}

export interface RatingInput {
  rating_id: string;
  company_name: string;
  sector: string;
  dimension_scores: DimensionScore[];
  chain: ChainAssessment;
  analyst_notes: string;
}

export interface Rating {
  input: RatingInput;
  result: ScoringResult;
  issued_at: string;
  methodology_version: string;
  pipeline_version: string;
}

export interface RatingProgress {
  dimensions_done: number;
  dimensions_total: number;
  chain_done: number;
  chain_total: number;
}

export interface RatingStatus {
  rating_id: string;
  company_name: string;
  sector: string;
  status: JobStatus;
  created_at: string;
  progress: RatingProgress;
  rating: Rating | null;
  error: string | null;
  sealed_digest: string | null;
}

export interface RatingListItem {
  rating_id: string;
  company_name: string;
  sector: string;
  status: JobStatus;
  created_at: string;
  grade: Grade | null;
  final_score: number | null;
}

export interface RatingAccepted {
  rating_id: string;
  status: JobStatus;
  created_at: string;
  events_url: string;
  detail_url: string;
}

// SSE event payloads from /ratings/{id}/events.
export type RatingEvent =
  | { type: "status"; status: JobStatus }
  | {
      type: "ingest";
      files_ingested: number;
      files_skipped: string[];
      chunks: number;
      summary: Record<string, number>;
    }
  | { type: "agent"; event: "start" | "done" | "error"; name: string }
  | { type: "rating"; rating: Rating }
  | { type: "sealed"; digest: string; ledger_root: string }
  | { type: "error"; error: string };

export const DIMENSION_CODES: DimensionCode[] = [
  "MCS", "CPS", "SCAE", "CLS",
  "VPR", "WCI", "RMV", "TSR",
  "LAL", "SPS", "ANCR", "DIM",
];

export const CHAIN_POSITIONS: ChainPosition[] = [
  "upstream", "downstream", "lateral", "end_consumer",
];

export const DIMENSION_NAMES: Record<DimensionCode, string> = {
  MCS: "Market Category Stability",
  CPS: "Client Profile Stability",
  SCAE: "Supply Chain AI Exposure",
  CLS: "Competitive Landscape Stability",
  VPR: "Value Proposition Replicability",
  WCI: "Workforce Cost Intensity",
  RMV: "Revenue Model Vulnerability",
  TSR: "Tech Stack Resilience",
  LAL: "Leadership AI Literacy",
  SPS: "Strategic Planning Sophistication",
  ANCR: "AI-Native Competitor Response",
  DIM: "Durability of Moat",
};

export const DIMENSION_LAYER: Record<DimensionCode, "external" | "internal" | "adaptive"> = {
  MCS: "external", CPS: "external", SCAE: "external", CLS: "external",
  VPR: "internal", WCI: "internal", RMV: "internal", TSR: "internal",
  LAL: "adaptive", SPS: "adaptive", ANCR: "adaptive", DIM: "adaptive",
};

export const LAYER_NAMES = {
  external: "External Pressure",
  internal: "Internal Resilience",
  adaptive: "Adaptive Capacity",
} as const;

export const LAYER_WEIGHTS = {
  external: 0.4,
  internal: 0.35,
  adaptive: 0.25,
} as const;

export const CHAIN_POSITION_NAMES: Record<ChainPosition, string> = {
  upstream: "Upstream (suppliers)",
  downstream: "Downstream (distribution)",
  lateral: "Lateral (peers)",
  end_consumer: "End consumer",
};
