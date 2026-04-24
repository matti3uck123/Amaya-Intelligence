"""`amaya` CLI — the shell entry point for the rating pipeline.

  amaya score <input.json>                      # compute rating
  amaya score <input.json> --seal <dir>         # also write provenance bundle
  amaya verify <rating_id> --ledger <dir>       # recompute bundle hash
  amaya methodology                              # dump active methodology
  amaya ingest <data-room-path>                 # extract + classify documents
  amaya ingest <path> --classifier claude       # use Claude Haiku (needs key)
  amaya ingest <path> --out evidence.json       # write result to file
  amaya rate <data-room-path> --company "X"     # end-to-end: ingest + agents + score
  amaya rate <path> --seal ./ledger             # also seal into provenance ledger
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from . import __version__
from .methodology import load_methodology
from .provenance import ProvenanceLedger
from .schemas import Rating, RatingInput
from .scoring import score as score_rating


def cmd_score(args: argparse.Namespace) -> int:
    methodology = load_methodology(args.methodology)
    input_data = json.loads(Path(args.input).read_text())
    rating_input = RatingInput.model_validate(input_data)
    result = score_rating(rating_input, methodology)

    rating = Rating(
        input=rating_input,
        result=result,
        issued_at=datetime.now(timezone.utc),
        methodology_version=methodology.version,
        pipeline_version=__version__,
    )

    output = rating.model_dump(mode="json")
    if args.seal:
        ledger = ProvenanceLedger(Path(args.seal))
        bundle = ledger.seal(rating)
        output["provenance"] = {
            "sealed": True,
            "ledger_root": str(args.seal),
            "bundle_hash": bundle["seal"]["digest"],
        }

    print(json.dumps(output, indent=2, default=str))
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    ledger = ProvenanceLedger(Path(args.ledger))
    ok = ledger.verify(args.rating_id)
    print(json.dumps({"rating_id": args.rating_id, "verified": ok}))
    return 0 if ok else 1


def cmd_methodology(args: argparse.Namespace) -> int:
    m = load_methodology(args.version)
    print(json.dumps(m.raw_yaml, indent=2))
    return 0


def cmd_ingest(args: argparse.Namespace) -> int:
    from .ingest import AnthropicClassifier, KeywordClassifier, ingest

    if args.classifier == "claude":
        classifier = AnthropicClassifier()
    else:
        classifier = KeywordClassifier()

    result = ingest(args.path, classifier=classifier)
    payload = result.model_dump(mode="json")
    payload["summary"] = result.summary()

    if args.out:
        Path(args.out).write_text(json.dumps(payload, indent=2))
        print(
            json.dumps(
                {
                    "source_path": result.source_path,
                    "files_ingested": result.files_ingested,
                    "files_skipped": result.files_skipped,
                    "chunks_total": len(result.chunks),
                    "summary": result.summary(),
                    "written_to": args.out,
                },
                indent=2,
            )
        )
    else:
        print(json.dumps(payload, indent=2))
    return 0


def cmd_rate(args: argparse.Namespace) -> int:
    from .agents import AnthropicCompletion, rate
    from .ingest import AnthropicClassifier, KeywordClassifier, ingest

    classifier = (
        AnthropicClassifier() if args.classifier == "claude" else KeywordClassifier()
    )
    ingest_result = ingest(args.path, classifier=classifier)

    completion = AnthropicCompletion(model=args.model)

    rating_id = args.rating_id or f"adi-{datetime.now(timezone.utc):%Y%m%d}-{uuid.uuid4().hex[:8]}"

    def _progress(event: str, name: str) -> None:
        symbol = {"start": "▶", "done": "✓", "error": "✗"}.get(event, "·")
        print(f"  {symbol} {name} ({event})", file=sys.stderr, flush=True)

    print(
        f"Ingesting {args.path} …  {ingest_result.files_ingested} files, "
        f"{len(ingest_result.chunks)} chunks",
        file=sys.stderr,
    )
    print(f"Running 16 agents against {args.model} …", file=sys.stderr)

    rating_input = asyncio.run(
        rate(
            rating_id=rating_id,
            company_name=args.company,
            sector=args.sector or "",
            ingest_result=ingest_result,
            completion=completion,
            analyst_notes=args.notes or "",
            on_progress=_progress,
        )
    )

    methodology = load_methodology(args.methodology)
    result = score_rating(rating_input, methodology)
    rating = Rating(
        input=rating_input,
        result=result,
        issued_at=datetime.now(timezone.utc),
        methodology_version=methodology.version,
        pipeline_version=__version__,
    )

    output = rating.model_dump(mode="json")
    if args.seal:
        ledger = ProvenanceLedger(Path(args.seal))
        bundle = ledger.seal(rating)
        output["provenance"] = {
            "sealed": True,
            "ledger_root": str(args.seal),
            "bundle_hash": bundle["seal"]["digest"],
        }

    print(json.dumps(output, indent=2, default=str))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="amaya", description="ADI rating engine")
    p.add_argument("--version", action="version", version=f"amaya {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("score", help="score a rating input")
    s.add_argument("input", help="path to rating input JSON")
    s.add_argument("--methodology", default="v1.0", help="methodology version")
    s.add_argument("--seal", help="if given, write provenance bundle to this dir")
    s.set_defaults(func=cmd_score)

    v = sub.add_parser("verify", help="verify a sealed provenance bundle")
    v.add_argument("rating_id")
    v.add_argument("--ledger", required=True, help="provenance ledger directory")
    v.set_defaults(func=cmd_verify)

    m = sub.add_parser("methodology", help="dump active methodology")
    m.add_argument("--version", default="v1.0")
    m.set_defaults(func=cmd_methodology)

    i = sub.add_parser("ingest", help="extract + classify documents in a data room")
    i.add_argument("path", help="file or directory to ingest")
    i.add_argument(
        "--classifier",
        choices=["keyword", "claude"],
        default="keyword",
        help="classifier backend (keyword is free/offline; claude needs ANTHROPIC_API_KEY)",
    )
    i.add_argument("--out", help="write IngestResult JSON to this file")
    i.set_defaults(func=cmd_ingest)

    r = sub.add_parser("rate", help="end-to-end: ingest + agents + scoring (needs ANTHROPIC_API_KEY)")
    r.add_argument("path", help="file or directory (data room) to rate")
    r.add_argument("--company", required=True, help="company name")
    r.add_argument("--sector", help="sector / industry label")
    r.add_argument("--rating-id", dest="rating_id", help="explicit rating id (auto-generated if omitted)")
    r.add_argument("--notes", help="free-form analyst notes")
    r.add_argument("--methodology", default="v1.0", help="methodology version")
    r.add_argument("--model", default="claude-sonnet-4-6", help="agent LLM model id")
    r.add_argument(
        "--classifier",
        choices=["keyword", "claude"],
        default="keyword",
        help="section classifier for the ingest stage",
    )
    r.add_argument("--seal", help="if given, seal the resulting rating into this ledger dir")
    r.set_defaults(func=cmd_rate)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
