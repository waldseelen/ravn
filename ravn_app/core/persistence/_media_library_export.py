"""Internal export helpers for the media library."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable, Iterable


class MediaLibraryExporter:
    """Stream JSON/CSV media-library exports without large one-shot materialization."""

    def __init__(
        self,
        media_iterator: Callable[[], Iterable[Any]],
        collections_loader: Callable[[], list[Any]],
        statistics_loader: Callable[[], dict[str, Any]],
    ) -> None:
        self._media_iterator = media_iterator
        self._collections_loader = collections_loader
        self._statistics_loader = statistics_loader

    def export(self, export_format: str, output_file: str) -> bool:
        normalized_format = export_format.strip().lower()
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if normalized_format == "json":
            self._write_json_export(output_path)
            return True

        if normalized_format == "csv":
            self._write_csv_export(output_path)
            return True

        raise ValueError("Unsupported export format. Use 'json' or 'csv'.")

    def _write_json_export(self, output_path: Path) -> None:
        with open(output_path, "w", encoding="utf-8") as handle:
            handle.write('{\n  "media_items": [')
            first_item = True
            for item in self._media_iterator():
                if first_item:
                    handle.write("\n")
                    first_item = False
                else:
                    handle.write(",\n")
                handle.write("    ")
                json.dump(asdict(item), handle, ensure_ascii=False)
            if not first_item:
                handle.write("\n")
            handle.write('  ],\n  "collections": ')
            json.dump([asdict(collection) for collection in self._collections_loader()], handle, ensure_ascii=False)
            handle.write(',\n  "statistics": ')
            json.dump(self._statistics_loader(), handle, ensure_ascii=False)
            handle.write("\n}\n")

    def _write_csv_export(self, output_path: Path) -> None:
        with open(output_path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "id",
                    "file_path",
                    "title",
                    "format",
                    "duration",
                    "size",
                    "width",
                    "height",
                    "fps",
                    "sample_rate",
                    "codec",
                    "bitrate",
                    "created_at",
                    "added_at",
                    "thumbnail",
                    "tags",
                ],
            )
            writer.writeheader()
            for item in self._media_iterator():
                row = asdict(item)
                row["tags"] = ",".join(item.tags)
                row.pop("metadata", None)
                writer.writerow(row)
