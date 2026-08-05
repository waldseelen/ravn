from __future__ import annotations

import ast
import json
import re
from pathlib import Path


def _load_translations(lang: str) -> dict:
    path = Path("ravn_app/translations") / f"{lang}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_key(source: dict, key: str) -> bool:
    current = source
    for part in key.split("."):
        if not isinstance(current, dict) or part not in current:
            return False
        current = current[part]
    return True


def test_all_literal_i18n_keys_exist_in_en_and_tr() -> None:
    en = _load_translations("en")
    tr = _load_translations("tr")

    keys: set[str] = set()
    root = Path("ravn_app")

    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not isinstance(node.func, ast.Name) or node.func.id != "t":
                continue
            if not node.args:
                continue
            arg0 = node.args[0]
            if isinstance(arg0, ast.Constant) and isinstance(arg0.value, str):
                keys.add(arg0.value)

    # Keys used via loop variables instead of direct t("...") calls.
    keys.update(
        {
            "download.guideLine1",
            "download.guideLine2",
            "download.guideLine3",
            "libraryWorkspace.guideLine1",
            "libraryWorkspace.guideLine2",
            "libraryWorkspace.guideLine3",
            "studio.guideLine1",
            "studio.guideLine2",
            "studio.guideLine3",
        }
    )

    missing_en = sorted(key for key in keys if "." in key and not _resolve_key(en, key))
    missing_tr = sorted(key for key in keys if "." in key and not _resolve_key(tr, key))

    assert not missing_en, f"Missing EN translations: {missing_en}"
    assert not missing_tr, f"Missing TR translations: {missing_tr}"


def test_translation_files_have_identical_key_sets() -> None:
    """tr.json and en.json must define exactly the same keys — a key added to one
    language but not the other renders as a raw <MISSING> token at runtime."""
    def _flatten(d: dict, prefix: str = "") -> set:
        out: set = set()
        for key, value in d.items():
            full = f"{prefix}{key}"
            if isinstance(value, dict):
                out |= _flatten(value, full + ".")
            else:
                out.add(full)
        return out

    en_keys = _flatten(_load_translations("en"))
    tr_keys = _flatten(_load_translations("tr"))

    assert en_keys == tr_keys, (
        f"Translation parity broken. EN-only: {sorted(en_keys - tr_keys)} | "
        f"TR-only: {sorted(tr_keys - en_keys)}"
    )


def test_all_design_token_references_are_defined() -> None:
    design_tokens = Path("ravn_app/ui/design_tokens.py")
    if not design_tokens.exists():
        return  # Legacy Tkinter UI retired; skip design tokens test
    tree = ast.parse(design_tokens.read_text(encoding="utf-8"), filename=str(design_tokens))

    defined: dict[str, set[str]] = {}
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        if node.name not in {"Colors", "Sizes", "Spacing", "Motion", "Cursors", "Icons", "_FontRegistry"}:
            continue
        names: set[str] = set()
        for child in node.body:
            if isinstance(child, ast.Assign):
                for target in child.targets:
                    if isinstance(target, ast.Name):
                        names.add(target.id)
            elif isinstance(child, ast.FunctionDef):
                names.add(child.name)
        defined[node.name] = names

    patterns = {
        "Colors": re.compile(r"\bColors\.([A-Z_]+)\b"),
        "Sizes": re.compile(r"\bSizes\.([A-Z_]+)\b"),
        "Spacing": re.compile(r"\bSpacing\.([A-Z_]+)\b"),
        "Motion": re.compile(r"\bMotion\.([A-Z_]+)\b"),
        "Cursors": re.compile(r"\bCursors\.([A-Z_]+)\b"),
        "Icons": re.compile(r"\bIcons\.([A-Z_]+)\b"),
        "Fonts": re.compile(r"\bFonts\.([A-Z_]+)\b"),
    }

    invalid: list[str] = []
    for path in Path("ravn_app").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for token_group, pattern in patterns.items():
            valid_names = defined["_FontRegistry"] if token_group == "Fonts" else defined[token_group]
            for match in pattern.finditer(text):
                token_name = match.group(1)
                if token_name not in valid_names:
                    invalid.append(f"{path}: {token_group}.{token_name}")

    assert not invalid, "Undefined design token references found:\n" + "\n".join(sorted(set(invalid)))
