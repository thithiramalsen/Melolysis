"""CLI shared with main.py; analysis never silently creates demonstration audio."""
import argparse
from dataclasses import asdict
import json
import logging
from pathlib import Path
import sys
from .schema import AnalysisConfig
from .storage import write_json


def parser():
    p = argparse.ArgumentParser(description="Melolysis: inspectable vocal melody analysis and songwriting")
    p.add_argument("--verbose", action="store_true")
    sub = p.add_subparsers(dest="command")
    a = sub.add_parser("analyze", help="Analyze one or more existing vocal recordings")
    a.add_argument("audio", nargs="+")
    a.add_argument("--output", default="outputs")
    a.add_argument("--config", help="JSON file containing AnalysisConfig fields")
    a.add_argument("--estimator", choices=["pyin", "torchcrepe"])
    a.add_argument("--artist", default="")
    a.add_argument("--song", default="")
    a.add_argument("--section", default="unknown")
    a.add_argument("--metadata", help="Optional metadata JSON file")
    a.add_argument("--tempo", type=float, help="User-confirmed quarter-note BPM; no automatic drum grid")
    a.add_argument("--beat-origin", type=float, default=0.)
    a.add_argument("--chords", help="JSON list of source-second spans and pitch_classes")
    add_model_args(a)
    s = sub.add_parser("serve", help="Start the local audio/note correction workspace")
    s.add_argument("--output", default="outputs")
    s.add_argument("--port", default=8765, type=int)
    b = sub.add_parser("benchmark", help="Run known-reference synthetic AUDIO inference")
    b.add_argument("--output", default="outputs/benchmark")
    b.add_argument("--estimators", nargs="+", choices=["pyin", "torchcrepe"], default=["pyin"])
    b.add_argument("--suite", choices=["development", "stress"], default="development")
    e = sub.add_parser("evaluate", help="Evaluate user-annotated excerpts from a manifest")
    e.add_argument("manifest")
    e.add_argument("--output", default="outputs/evaluation")
    e.add_argument("--estimator", default="pyin", choices=["pyin", "torchcrepe"])
    add_model_args(e, imported=False)
    c = sub.add_parser("profile", help="Build a recording-balanced profile")
    c.add_argument("reports", nargs="*")
    c.add_argument("--all", action="store_true", help="Use analyses under --output; one per input hash")
    c.add_argument("--output", default="outputs")
    c.add_argument("--artist", default="Unspecified")
    c.add_argument("--reference", nargs="*", default=[])
    g = sub.add_parser("compose", help="Explore reference melodies from a saved profile")
    g.add_argument("profile")
    g.add_argument("--config", help="CompositionConfig JSON file")
    g.add_argument("--output", default="outputs/composition")
    f = sub.add_parser("feedback", help="Compare an analyzed sung attempt with an exercise")
    f.add_argument("report"); f.add_argument("exercise")
    real=sub.add_parser('real-evaluate',help='Compare actual inference on frozen, reviewed human references')
    real.add_argument('manifest');real.add_argument('--systems',default='evaluation/real/systems.example.json')
    real.add_argument('--split',choices=['development','heldout'],default='development')
    real.add_argument('--output',default='outputs/real-validation')
    ref=sub.add_parser('reference-create',help='Prepare an independent source-time annotation draft; never auto-review it')
    ref.add_argument('report');ref.add_argument('--start',type=float,required=True);ref.add_argument('--end',type=float,required=True)
    ref.add_argument('--annotator',required=True);ref.add_argument('--split',choices=['unassigned','development','heldout'],default='unassigned')
    ref.add_argument('--group');ref.add_argument('--seed-predictions',action='store_true');ref.add_argument('--output',default='outputs')
    export=sub.add_parser('reference-manifest',help='Freeze reviewed reference revisions for reproducible evaluation')
    export.add_argument('--output',default='outputs');export.add_argument('--manifest',default='outputs/real-validation/reviewed.manifest.json')
    refine=sub.add_parser('refine-notes',help='Create an optional acoustic offset-refined edition, preserving raw model events')
    refine.add_argument('report');refine.add_argument('--config',help='Bounded acoustic tail settings JSON')
    refine.add_argument('--output',default='outputs')
    return p


def add_model_args(p, imported=True):
    p.add_argument("--note-model", choices=["heuristic", "game", "some", "basic-pitch"], default="heuristic")
    p.add_argument("--model-python", help="Interpreter in the isolated GAME/SOME environment")
    p.add_argument("--model-repo", help="Path to external repository with infer.py")
    p.add_argument("--weights", help="Existing pretrained model checkpoint; never downloaded implicitly")
    if imported:
        p.add_argument("--import-midi", help="Import external model notes instead of local note inference")
        p.add_argument("--timestamp-offset", type=float, default=0., help="Explicit documented MIDI-to-source time correction")


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def main(argv=None):
    p = parser(); args = p.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(levelname)s %(message)s")
    if not args.command:
        from main import find_audio_file
        audio = find_audio_file("data/vocals")
        if not audio:
            p.error("No recording in data/vocals. Supply: python main.py analyze path/to/vocals.wav")
        return main(["analyze", audio])
    try:
        if args.command == "analyze":
            from .pipeline import analyze_file
            config = read_json(args.config) if args.config else {}
            if args.estimator:
                config["estimator"] = args.estimator
            config = AnalysisConfig(**config)
            metadata = read_json(args.metadata) if args.metadata else {}
            reports = []
            for audio in args.audio:
                fields = {**metadata, "artist": args.artist or metadata.get("artist", ""),
                    "song": args.song or Path(audio).stem, "section": args.section}
                report = analyze_file(audio, args.output, config, fields, note_model=args.note_model,
                    model_python=args.model_python, model_repo=args.model_repo, weights=args.weights,
                    imported_midi=args.import_midi, timestamp_offset=args.timestamp_offset,
                    beat_grid={"tempo": args.tempo, "origin": args.beat_origin} if args.tempo else None,
                    chords=read_json(args.chords) if args.chords else None)
                reports.append(report)
                print(f"{audio}: {len(report['notes'])} notes; {report['features']['phrase_count']} phrases")
                print(f"Report: {report['report_path']}")
            if len(reports) > 1:
                from .corpus import profile_artist, songwriting_exercises
                profile = profile_artist(reports, args.artist or "Unspecified")
                profile["exercises"] = songwriting_exercises(profile)
                write_json(Path(args.output)/"artist-profile.json", profile)
            print(f"Review: python main.py serve --output \"{args.output}\"")
        elif args.command == "serve":
            from .workspace import serve
            serve(args.output, args.port)
        elif args.command == "benchmark":
            from .evaluation import run_benchmark
            result = run_benchmark(args.output, tuple(args.estimators), args.suite)
            print(json.dumps(result["summary"], indent=2))
        elif args.command == "evaluate":
            from .evaluation import evaluate_manifest
            result = evaluate_manifest(args.manifest, args.output, args.estimator, args.note_model,
                model_python=args.model_python, model_repo=args.model_repo, weights=args.weights)
            print(json.dumps(result, indent=2))
        elif args.command == "profile":
            from .corpus import profile_artist, songwriting_exercises
            from .pipeline import load_report
            paths = args.reports
            if args.all:
                paths += [str(p) for p in sorted((Path(args.output)/"analyses").glob("*/*/report.json"), key=lambda p: p.stat().st_mtime)]
            if not paths:
                raise ValueError("Supply report.json paths or --all")
            profile = profile_artist([load_report(path) for path in paths], args.artist,
                                     [load_report(path) for path in args.reference])
            profile["exercises"] = songwriting_exercises(profile)
            write_json(Path(args.output)/"artist-profile.json", profile)
            print(f"Profile: {profile['songs']} songs, {profile['recordings']} recordings, {profile['phrases']} phrases, {profile['notes']} notes")
        elif args.command == "compose":
            from .composition import CompositionConfig, generate_candidates
            from .pipeline import export_notes
            from .schema import notes_from_dicts
            cfg = CompositionConfig(**(read_json(args.config) if args.config else {}))
            result = generate_candidates(read_json(args.profile), cfg)
            write_json(Path(args.output)/"candidates.json", result)
            for i, c in enumerate(result["candidates"], 1):
                export_notes(notes_from_dicts(c["notes"]), Path(args.output)/f"candidate-{i}.csv",
                             Path(args.output)/f"candidate-{i}.mid", cfg.tempo)
            print(f"{len(result['candidates'])} candidates saved to {args.output}")
        elif args.command == "feedback":
            from .corpus import assess_attempt
            from .schema import notes_from_dicts
            print(json.dumps(assess_attempt(notes_from_dicts(read_json(args.report)["notes"]), read_json(args.exercise)), indent=2))
        elif args.command=='real-evaluate':
            from .real_evaluation import run_comparison
            result=run_comparison(args.manifest,args.systems,args.output,args.split)
            print(json.dumps(result['summary'],indent=2))
        elif args.command=='reference-create':
            from .references import ReferenceStore
            from .pipeline import load_report
            result=ReferenceStore(Path(args.output)/'references').create(load_report(args.report),args.start,args.end,
                args.annotator,args.split,args.group,args.seed_predictions)
            print(f"UNREVIEWED annotation draft {result['id']}: {result['excerpt']['start']}–{result['excerpt']['end']} source seconds. Human review required.")
        elif args.command=='reference-manifest':
            from .references import ReferenceStore
            store=ReferenceStore(Path(args.output)/'references')
            ids=[r['id'] for r in store.list() if r['review']['status']=='reviewed' and r['split']!='unassigned']
            if not ids: raise ValueError('No reviewed, split-assigned references')
            store.export_manifest(args.manifest,ids);print(f'Frozen {len(ids)} reviewed references to {args.manifest}')
        elif args.command=='refine-notes':
            from .note_refinement import refine_report
            result=refine_report(args.report,args.output,read_json(args.config) if args.config else None)
            print(f"Optional acoustic refinement: {len(result['offset_refinement']['changes'])} offsets changed. Review {result['report_path']}")
        return 0
    except (ValueError, RuntimeError, OSError, KeyError, TypeError) as exc:
        logging.error("%s", exc)
        if args.verbose:
            raise
        return 1
