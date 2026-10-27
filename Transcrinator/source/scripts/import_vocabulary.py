"""Merge explicit UTF-8 lexicons into the user's local dictionary."""
import argparse
import json
from pathlib import Path

from app.core.settings import Settings
from app.core.text_options import Vocabulary, key, normalize_vocabulary


def read_entries(path):
    text = Path(path).read_text(encoding="utf-8-sig")
    if Path(path).suffix.lower() != ".json":
        return normalize_vocabulary([line.strip() for line in text.splitlines()
                                     if line.strip() and not line.lstrip().startswith("#")])
    value = json.loads(text)
    if isinstance(value, dict):
        value = value.get("entrees", value.get("vocabulary", []))
    result = []
    for entry in value if isinstance(value, list) else []:
        if isinstance(entry, dict) and isinstance(entry.get("forme"), str):
            # Only vocabulary data is imported; sources, prose, priorities and
            # suggested contextual policies are not executable instructions.
            entry = {"name": entry["forme"], "aliases": entry.get("variantes_de_detection", []),
                     "category": entry.get("category")}
        result.extend(normalize_vocabulary([entry]))
    return result


def merge_entries(existing, imported):
    merged = {}
    for entry in normalize_vocabulary(existing) + normalize_vocabulary(imported):
        identity = key(entry["name"])
        if identity not in merged:
            merged[identity] = {"name": entry["name"], "aliases": []}
        if "category" in entry and "category" not in merged[identity]:
            merged[identity]["category"] = entry["category"]
        aliases = merged[identity]["aliases"]
        for alias in entry["aliases"]:
            if key(alias) != identity and alias not in aliases:
                aliases.append(alias)
    result = list(merged.values())
    ambiguous = Vocabulary(result).ambiguous
    for entry in result:
        entry["aliases"] = [alias for alias in entry["aliases"] if key(alias) not in ambiguous]
    return result


def import_paths(settings, paths, exclude=()):
    imported = [entry for path in paths for entry in read_entries(path)]
    excluded = {key(name) for name in exclude}
    skipped = {key(entry["name"]) for entry in imported if key(entry["name"]) in excluded}
    before = len(settings.vocabulary)
    settings.vocabulary = merge_entries(settings.vocabulary, [entry for entry in imported
                                                              if key(entry["name"]) not in excluded])
    return {"files": len(paths), "source_entries": len(imported), "previous_entries": before,
            "dictionary_entries": len(settings.vocabulary),
            "excluded_ambiguous_entries": len(skipped),
            "aliases": sum(len(entry["aliases"]) for entry in settings.vocabulary),
            "ambiguous_terms": len(Vocabulary(settings.vocabulary).ambiguous)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    settings = Settings.load()
    report = import_paths(settings, args.files)
    if args.apply:
        settings.save()
    report["applied"] = args.apply
    if args.report:
        args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
