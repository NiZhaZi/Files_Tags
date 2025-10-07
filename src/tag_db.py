#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tag database loader and query utilities.

Schema (JSON):
{
  "version": 1,
  "files": [
    {
      "path": "/absolute/path/to/file.ext",
      "tags": [
        {"category": "Project", "name": "Apollo"},
        {"category": "Type", "name": "Report"},
        {"category": "Year", "name": "2025"}
      ]
    },
    ...
  ]
}
Notes:
- "tags" may also contain entries shaped like {"category": "...", "tag": "..."}
  or {"category": "...", "value": "..."} for convenience. They are normalized to
  (category, name) internally.
- "path" must be an absolute path on the local machine.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Dict, List, Tuple, Set, Iterable, Optional


TagKey = Tuple[str, str]  # (category, name)


@dataclass(frozen=True)
class FileEntry:
    path: str
    tags: Tuple[TagKey, ...]


class TagDB:
    def __init__(self) -> None:
        self._entries: List[FileEntry] = []
        self._index_by_tag: Dict[TagKey, Set[int]] = {}
        self._category_to_tags: Dict[str, Set[str]] = {}
        self._path_to_idx: Dict[str, int] = {}
        self._json_path: Optional[str] = None

    @property
    def json_path(self) -> Optional[str]:
        return self._json_path

    @staticmethod
    def _normalize_tag(tag_obj) -> TagKey:
        """Return a TagKey (category, name) from various allowed shapes."""
        if isinstance(tag_obj, dict):
            category = str(tag_obj.get("category", "")).strip()
            # Support multiple possible keys for the tag name
            name = (
                tag_obj.get("name", None)
                or tag_obj.get("tag", None)
                or tag_obj.get("value", None)
            )
            if name is None:
                raise ValueError(f"Tag object missing name: {tag_obj}")
            name = str(name).strip()
        else:
            raise TypeError(f"Tag must be a dict with 'category' and 'name' keys, got: {tag_obj}")
        if not category or not name:
            raise ValueError(f"Invalid tag: {tag_obj}")
        return (category, name)

    def load(self, json_path: str) -> None:
        """Load database from JSON file and build indices."""
        if not os.path.isabs(json_path):
            # Allow relative path for convenience; resolve to abs
            json_path = os.path.abspath(json_path)
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict) or "files" not in data or not isinstance(data["files"], list):
            raise ValueError("Invalid DB format: root must contain a 'files' array.")

        self._entries.clear()
        self._index_by_tag.clear()
        self._category_to_tags.clear()
        self._path_to_idx.clear()

        for idx, raw in enumerate(data["files"]):
            path = raw.get("path")
            if not path or not os.path.isabs(path):
                raise ValueError(f"File entry #{idx} has missing or non-absolute 'path': {raw}")
            tags_raw = raw.get("tags", [])
            if not isinstance(tags_raw, list):
                raise ValueError(f"'tags' must be a list in entry #{idx}")
            tags: List[TagKey] = []
            for t in tags_raw:
                tk = self._normalize_tag(t)
                tags.append(tk)
                # category index
                self._category_to_tags.setdefault(tk[0], set()).add(tk[1])
            entry = FileEntry(path=path, tags=tuple(tags))
            self._path_to_idx[path] = len(self._entries)
            self._entries.append(entry)

        # Build inverted index from tag to set of file indices
        for i, e in enumerate(self._entries):
            for tk in e.tags:
                self._index_by_tag.setdefault(tk, set()).add(i)

        self._json_path = json_path

    def categories(self) -> List[str]:
        return sorted(self._category_to_tags.keys())

    def tags_in_category(self, category: str) -> List[str]:
        return sorted(self._category_to_tags.get(category, set()))

    def all_files(self) -> List[FileEntry]:
        return list(self._entries)

    def get_entry_by_index(self, idx: int) -> FileEntry:
        return self._entries[idx]

    def find_files(
        self,
        tag_filters: Iterable[TagKey],
        mode: str = "AND",
        filename_substring: str = "",
    ) -> List[int]:
        """
        Return list of file indices matching the selected TagKeys.

        mode='AND' means a file must contain all provided TagKeys.
        mode='OR' means a file containing any provided TagKey will match.
        filename_substring: optional case-insensitive substring to match in the file name.
        """
        tag_filters = list(tag_filters)
        if not tag_filters:
            # If no tag filters, return all indices (subject to name filter)
            candidates = set(range(len(self._entries)))
        else:
            sets: List[Set[int]] = []
            for tk in tag_filters:
                sets.append(self._index_by_tag.get(tk, set()))
            if mode.upper() == "AND":
                candidates = set.intersection(*sets) if sets else set()
            else:
                # OR
                candidates = set.union(*sets) if sets else set()

        if filename_substring:
            needle = filename_substring.lower()
            filtered = [
                i for i in candidates
                if needle in os.path.basename(self._entries[i].path).lower()
            ]
            return sorted(filtered)
        return sorted(candidates)

    def exists(self, idx: int) -> bool:
        return os.path.exists(self._entries[idx].path)
