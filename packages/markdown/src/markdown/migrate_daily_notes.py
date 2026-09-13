import argparse
import re
import shutil
from datetime import datetime
from pathlib import Path

WIKILINK_PATTERN = re.compile(r"!?\[\[([^\]|#]+)(\|[^\]]*)?\]\]")
MDLINK_PATTERN = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")

DEFAULT_FRONTMATTER = """---
tags:
  - notes
  - daily
---

"""


def parse_note_date(filename):
    stem = filename.stem
    try:
        return datetime.strptime(stem, "%m-%d-%Y")
    except ValueError:
        return None


def dest_path_for(root, date):
    month_folder = f"{date.strftime('%m')} - {date.strftime('%B')}"
    filename = date.strftime("%Y-%m-%d") + ".md"
    return root / "Notes" / "Daily" / date.strftime("%Y") / month_folder / filename


def has_frontmatter(text):
    return text.startswith("---\n") and "\n---" in text[4:]


def find_referenced_attachments(text):
    names = set()
    for match in WIKILINK_PATTERN.finditer(text):
        names.add(match.group(1).strip())
    for match in MDLINK_PATTERN.finditer(text):
        target = match.group(2).strip()
        if not target.startswith(("http://", "https://")):
            names.add(target)
    return names


def rewrite_links(text, moved):
    for old_name, new_rel_path in moved.items():
        text = text.replace(f"[[{old_name}]]", f"[[{new_rel_path}]]")
        text = text.replace(f"![[{old_name}]]", f"![[{new_rel_path}]]")
        escaped = re.escape(old_name)
        text = re.sub(
            rf"(!\[[^\]]*\]\()[^)]*{escaped}([^)]*\))",
            rf"\g<1>{new_rel_path}\g<2>",
            text,
        )
    return text


def migrate(root, dry_run):
    source_dir = root / "_archive" / "Daily Notes"
    attachments_dir = source_dir / "Attachments"
    dest_attachments_dir = root / "_attachments"

    notes = sorted(p for p in source_dir.glob("*.md") if p.is_file())

    planned_moves = []
    skipped = []
    note_rename_map = {}

    for note_path in notes:
        date = parse_note_date(note_path)
        if date is None:
            skipped.append(note_path)
        else:
            note_rename_map[note_path.stem] = date.strftime("%Y-%m-%d")

    for note_path in notes:
        date = parse_note_date(note_path)
        if date is None:
            continue

        text = note_path.read_text(encoding="utf-8")
        referenced = find_referenced_attachments(text)

        attachment_moves = {}
        for name in referenced:
            candidate = attachments_dir / name
            if candidate.exists():
                dest = dest_attachments_dir / candidate.name
                attachment_moves[name] = (candidate, dest)

        link_rewrite_map = {
            name: dest.name for name, (src, dest) in attachment_moves.items()
        }
        link_rewrite_map.update(note_rename_map)

        new_text = rewrite_links(text, link_rewrite_map)

        if not has_frontmatter(new_text):
            new_text = DEFAULT_FRONTMATTER + new_text

        dest_note_path = dest_path_for(root, date)

        planned_moves.append(
            {
                "note_src": note_path,
                "note_dest": dest_note_path,
                "attachments": attachment_moves,
                "new_text": new_text,
            }
        )

    for item in planned_moves:
        print(
            f"{item['note_src'].relative_to(root)}  ->  {item['note_dest'].relative_to(root)}"
        )
        for name, (src, dest) in item["attachments"].items():
            print(
                f"    attachment: {src.relative_to(root)}  ->  {dest.relative_to(root)}"
            )

    if skipped:
        print()
        print("Skipped (filename did not match MM-DD-YYYY):")
        for path in skipped:
            print(f"    {path.relative_to(root)}")

    print()
    print(f"{len(planned_moves)} notes to migrate, {len(skipped)} skipped")

    if dry_run:
        print()
        print("Dry run only, nothing was changed. Re-run with --execute to apply.")
        return

    for item in planned_moves:
        item["note_dest"].parent.mkdir(parents=True, exist_ok=True)
        item["note_dest"].write_text(item["new_text"], encoding="utf-8")
        item["note_src"].unlink()

        for name, (src, dest) in item["attachments"].items():
            dest_attachments_dir.mkdir(parents=True, exist_ok=True)
            if not dest.exists():
                shutil.move(str(src), str(dest))

    print("Migration complete.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path.home() / "Documents" / "obsidian"))
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    root = Path(args.root).expanduser()
    migrate(root, dry_run=not args.execute)


if __name__ == "__main__":
    main()
