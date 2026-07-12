#!/usr/bin/env python3
import argparse, html, json, re
from pathlib import Path
from markdown_it import MarkdownIt


def load_config(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def build(config_path: Path, output: Path):
    cfg = load_config(config_path)
    output.mkdir(parents=True, exist_ok=True)
    content = output / "content"
    content.mkdir(exist_ok=True)
    md = MarkdownIt("commonmark", {"html": False, "linkify": True, "typographer": True})
    manifest = []
    base = config_path.parent
    for ci, chapter in enumerate(cfg["chapters"], 1):
        folder = (base / chapter["path"]).resolve()
        files = sorted(p for p in folder.glob("*.md") if not p.name.startswith("00"))
        for li, path in enumerate(files, 1):
            title = path.stem
            raw = path.read_text(encoding="utf-8")
            display = re.sub(r"\[\[([^\]]+)\]\]", r"`\1`", raw)
            body = md.render(display)
            slug = f"c{ci}-{li:02d}"
            (content / f"{slug}.html").write_text(body, encoding="utf-8")
            plain = html.unescape(re.sub(r"<[^>]+>", " ", body))
            manifest.append({"chapter": chapter["name"], "title": title, "slug": slug,
                             "search": re.sub(r"\s+", " ", plain)[:12000]})
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    runtime = {k: cfg[k] for k in ("site_title", "site_subtitle") if k in cfg}
    (output / "runtime-config.json").write_text(json.dumps(runtime, ensure_ascii=False), encoding="utf-8")
    print(f"Built {len(manifest)} lessons in {output}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.json")
    ap.add_argument("--output", default=".")
    args = ap.parse_args()
    build(Path(args.config).resolve(), Path(args.output).resolve())
