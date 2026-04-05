"""Repeatable Phase 5E optimization benchmarks.

This script measures the landed optimization work against lightweight legacy-style
simulations so Phase 5 packaging can start from a documented, reproducible
baseline.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import tracemalloc
from dataclasses import asdict
from pathlib import Path
from time import perf_counter
from types import SimpleNamespace
from unittest.mock import Mock, patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ravn_app.core.downloader import YouTubeDownloader
from ravn_app.core.persistence import MediaLibrary, MediaLibraryAutoAdder, MediaSearchFilters
from ravn_app.ui.main_window import YouTubeDownloaderApp


def _statement_counter(conn, fn):
    count = 0

    def tracer(statement: str) -> None:
        nonlocal count
        normalized = statement.strip().upper()
        if normalized.startswith(("BEGIN", "COMMIT", "ROLLBACK", "PRAGMA")):
            return
        count += 1

    conn.set_trace_callback(tracer)
    try:
        started = perf_counter()
        result = fn()
        elapsed_ms = round((perf_counter() - started) * 1000.0, 3)
        return {"statement_count": count, "elapsed_ms": elapsed_ms, "result": result}
    finally:
        conn.set_trace_callback(None)


def _measure_peak_memory(fn):
    tracemalloc.start()
    started = perf_counter()
    result = fn()
    elapsed_ms = round((perf_counter() - started) * 1000.0, 3)
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {
        "elapsed_ms": elapsed_ms,
        "current_kib": round(current / 1024.0, 3),
        "peak_kib": round(peak / 1024.0, 3),
        "result": result,
    }


def _build_library(tmp_dir: Path, *, item_count: int = 180) -> MediaLibrary:
    metadata_handler = Mock()
    metadata_handler.extract_metadata.side_effect = [
        {
            "title": f"Clip {index}",
            "format": "mp4" if index % 2 == 0 else "mp3",
            "duration": float(30 + index),
            "size": 2048 + index,
            "width": 1920 if index % 2 == 0 else 0,
            "height": 1080 if index % 2 == 0 else 0,
            "codec": "h264" if index % 2 == 0 else "mp3",
            "bitrate": 192000,
        }
        for index in range(item_count)
    ]
    library = MediaLibrary(db_path=str(tmp_dir / "library.db"), metadata_handler=metadata_handler, export_batch_size=40)
    for index in range(item_count):
        media_path = tmp_dir / f"clip-{index}.{'mp4' if index % 2 == 0 else 'mp3'}"
        media_path.write_bytes(b"data")
        library.add_media(str(media_path), tags=[f"tag-{index % 5}", "shared"])
    return library


def _legacy_list_media(library: MediaLibrary, *, limit: int = 120):
    rows = library.conn.execute(
        "SELECT * FROM media_items ORDER BY added_at DESC LIMIT ? OFFSET 0",
        (limit,),
    ).fetchall()
    records = []
    for row in rows:
        media_id = int(row["id"])
        tags_by_media_id = {media_id: library._load_tags_for_media_ids([media_id]).get(media_id, [])}
        records.append(library._build_media_record(row, tags_by_media_id))
    return records


def _legacy_export_file(library: MediaLibrary, output_path: Path):
    items = library.list_media(limit=10_000, offset=0)
    payload = {
        "media_items": [asdict(item) for item in items],
        "collections": [asdict(collection) for collection in library.list_collections()],
        "statistics": library.get_statistics(),
    }
    output_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return output_path


def benchmark_media_library() -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        library = _build_library(tmp_dir)
        try:
            optimized_list = _statement_counter(library.conn, lambda: library.list_media(limit=120, offset=0))
            legacy_list = _statement_counter(library.conn, lambda: _legacy_list_media(library, limit=120))
            search_run = _statement_counter(
                library.conn,
                lambda: library.search_media(
                    query="Clip",
                    filters=MediaSearchFilters(tags=["shared"], format="mp4", limit=80),
                ),
            )
            stats_run = _statement_counter(library.conn, library.get_statistics)
            streamed_export = _measure_peak_memory(lambda: library.export_library("json", str(tmp_dir / "streamed.json")))
            materialized_export = _measure_peak_memory(
                lambda: _legacy_export_file(library, tmp_dir / "materialized.json")
            )
            return {
                "list_media": {
                    "optimized_statement_count": optimized_list["statement_count"],
                    "legacy_statement_count": legacy_list["statement_count"],
                    "optimized_elapsed_ms": optimized_list["elapsed_ms"],
                    "legacy_elapsed_ms": legacy_list["elapsed_ms"],
                },
                "search_media": {
                    "statement_count": search_run["statement_count"],
                    "elapsed_ms": search_run["elapsed_ms"],
                    "result_count": len(search_run["result"]),
                },
                "statistics": {
                    "statement_count": stats_run["statement_count"],
                    "elapsed_ms": stats_run["elapsed_ms"],
                    "total_items": stats_run["result"]["total_items"],
                },
                "export_memory": {
                    "streamed_peak_kib": streamed_export["peak_kib"],
                    "materialized_peak_kib": materialized_export["peak_kib"],
                    "streamed_elapsed_ms": streamed_export["elapsed_ms"],
                    "materialized_elapsed_ms": materialized_export["elapsed_ms"],
                },
            }
        finally:
            library.close()


def benchmark_auto_add_batch() -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        output_files = []
        for index in range(80):
            output_file = tmp_dir / f"output-{index}.mp4"
            output_file.write_bytes(b"video")
            output_files.append(output_file)

        def build_auto_adder(db_name: str):
            created_handlers = []

            def handler_factory():
                handler = Mock()
                handler.extract_metadata.side_effect = [
                    {
                        "title": file_path.stem,
                        "format": "mp4",
                        "duration": 5.0,
                        "size": file_path.stat().st_size,
                        "codec": "h264",
                    }
                    for file_path in output_files
                ]
                created_handlers.append(handler)
                return handler

            auto_adder = MediaLibraryAutoAdder(
                config_manager={"library": {"auto_add_downloads": True}},
                db_path=str(tmp_dir / db_name),
                metadata_handler_factory=handler_factory,
            )
            return auto_adder, created_handlers

        batched_adder, batched_handlers = build_auto_adder("library-batched.db")
        current_batch = _measure_peak_memory(
            lambda: batched_adder.register_outputs(output_files, source_type="download")
        )

        naive_adder, naive_handlers = build_auto_adder("library-naive.db")
        naive_batch = _measure_peak_memory(
            lambda: [naive_adder.register_output(path, source_type="download") for path in output_files]
        )

        return {
            "batched_elapsed_ms": current_batch["elapsed_ms"],
            "naive_elapsed_ms": naive_batch["elapsed_ms"],
            "batched_peak_kib": current_batch["peak_kib"],
            "naive_peak_kib": naive_batch["peak_kib"],
            "batched_handler_count": len(batched_handlers),
            "naive_handler_count": len(naive_handlers),
        }


def _build_playlist_payload(entry_count: int, *, with_details: bool) -> dict:
    entries = []
    for index in range(entry_count):
        entry = {
            "id": f"video-{index}",
            "title": f"Video {index}",
            "duration": 60 + index,
            "uploader": "Channel",
            "channel": "Channel",
            "view_count": 1000 + index,
        }
        if with_details:
            entry["formats"] = [
                {
                    "format_id": "18",
                    "width": 854,
                    "height": 480,
                    "vcodec": "avc1",
                    "acodec": "mp4a",
                    "filesize": 30 * 1024 * 1024,
                    "format_note": "480p",
                },
                {
                    "format_id": "22",
                    "width": 1280,
                    "height": 720,
                    "vcodec": "avc1",
                    "acodec": "mp4a",
                    "filesize": 52 * 1024 * 1024,
                    "format_note": "720p",
                },
            ]
        entries.append(entry)
    return {
        "webpage_url": "https://www.youtube.com/playlist?list=PL123",
        "entries": entries,
    }


def benchmark_playlist_fetch() -> dict:
    downloader = YouTubeDownloader()
    flat_payload = json.dumps(_build_playlist_payload(140, with_details=False))
    detailed_payload = json.dumps(_build_playlist_payload(140, with_details=True))

    def fake_run(command, **_kwargs):
        output = flat_payload if "--flat-playlist" in command else detailed_payload
        return SimpleNamespace(returncode=0, stdout=output, stderr="")

    with patch("subprocess.run", side_effect=fake_run):
        initial_fetch = _measure_peak_memory(
            lambda: downloader.extract_playlist_entries(
                "https://www.youtube.com/playlist?list=PL123",
                quality_label="720p",
                with_details=False,
            )
        )
        detailed_fetch = _measure_peak_memory(
            lambda: downloader.extract_playlist_entries(
                "https://www.youtube.com/playlist?list=PL123",
                quality_label="720p",
                with_details=True,
            )
        )
        merged_entries = initial_fetch["result"]
        merge_started = perf_counter()
        merged_count = downloader.merge_playlist_entry_detail_fields(merged_entries, detailed_fetch["result"])
        merge_elapsed_ms = round((perf_counter() - merge_started) * 1000.0, 3)

    return {
        "initial_flat_fetch_ms": initial_fetch["elapsed_ms"],
        "initial_flat_peak_kib": initial_fetch["peak_kib"],
        "full_detail_fetch_ms": detailed_fetch["elapsed_ms"],
        "full_detail_peak_kib": detailed_fetch["peak_kib"],
        "merge_elapsed_ms": merge_elapsed_ms,
        "merged_entry_count": merged_count,
    }


def benchmark_idle_home() -> dict:
    app = YouTubeDownloaderApp.__new__(YouTubeDownloaderApp)
    snapshot = (("task-1", "running", 40, "working", ""),)
    refresh_counts = {"header": 0, "home": 0, "queue": 0}
    app._last_task_snapshot = snapshot
    app._current_view_key = "home"
    app._refresh_header_actions = lambda: refresh_counts.__setitem__("header", refresh_counts["header"] + 1)
    app.home_workspace = SimpleNamespace(
        refresh_dashboard=lambda: refresh_counts.__setitem__("home", refresh_counts["home"] + 1)
    )
    app.queue_tab = SimpleNamespace(
        refresh_queue=lambda force=False: refresh_counts.__setitem__("queue", refresh_counts["queue"] + 1)
    )

    started = perf_counter()
    for _ in range(5000):
        app._refresh_task_bound_surfaces_if_needed(snapshot)
    optimized_elapsed_ms = round((perf_counter() - started) * 1000.0, 3)

    legacy_counts = {"header": 0, "home": 0, "queue": 0}

    def legacy_tick():
        legacy_counts["header"] += 1
        legacy_counts["home"] += 1
        legacy_counts["queue"] += 1

    started = perf_counter()
    for _ in range(5000):
        legacy_tick()
    legacy_elapsed_ms = round((perf_counter() - started) * 1000.0, 3)

    return {
        "optimized_idle_loop_ms": optimized_elapsed_ms,
        "legacy_idle_loop_ms": legacy_elapsed_ms,
        "optimized_refresh_counts": refresh_counts,
        "legacy_refresh_counts": legacy_counts,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Phase 5E optimization benchmarks")
    parser.add_argument("--output", help="Optional JSON file to write benchmark results to")
    args = parser.parse_args()

    results = {
        "media_library": benchmark_media_library(),
        "auto_add_batch": benchmark_auto_add_batch(),
        "playlist_fetch": benchmark_playlist_fetch(),
        "idle_home": benchmark_idle_home(),
    }

    rendered = json.dumps(results, indent=2, ensure_ascii=False)
    print(rendered)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
