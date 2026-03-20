#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Pipeline runner with resume support for book and paper modes."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, List, Optional


PROJECT_ROOT = Path(__file__).resolve().parent
INPUT_PDF_DIR: Path
OUTPUT_JSON_DIR: Path
WORK_DIR: Path
PIPELINE_MODE: str
RAWJSON_SRC_DIR: Optional[Path]
OCR_MAX_TOKENS: Optional[int]
ONLY_THESE_STEMS: set[str]
OVERWRITE_JSON: bool
OCR_WORKERS: Optional[int]
THINK_WORKERS: Optional[int]
STRICT_RESUME: bool
ATOMIC_OUTPUTS: bool
CLEAN_STALE_TMPS: bool


def find_settings_json() -> Path:
    path = PROJECT_ROOT / "settings.json"
    if not path.exists():
        raise FileNotFoundError(f"Missing settings file: {path}")
    return path


def load_settings() -> dict[str, Any]:
    path = find_settings_json()
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return data


def get_setting(settings: dict[str, Any], key: str, default: Any) -> Any:
    return settings.get(key, default)


def run_cmd(cmd: list[str]) -> None:
    print("\n$ " + " ".join(cmd))
    proc = subprocess.run(cmd, stdout=sys.stdout, stderr=sys.stderr)
    if proc.returncode != 0:
        raise SystemExit(proc.returncode)


def ensure_scripts_exist(script_dir: Path, mode: str, rawjson_src_dir: Optional[Path] = None) -> tuple[Path, Path, Path, Optional[Path], Path, Path, Path]:
    if mode not in {"book", "exercise", "paper"}:
        raise SystemExit(
            f"Unsupported mode: {mode!r} (expected 'book', 'exercise', or 'paper')")

    src_dir_rawjson = rawjson_src_dir if rawjson_src_dir is not None else script_dir / \
        "src" / mode / "rawjson"
    pdf_to_md = src_dir_rawjson / "pdfTomd.py"
    md_to_tex = src_dir_rawjson / "mdTotex.py"
    tex_to_json = src_dir_rawjson / "texTojson.py"
    json_naturalize = src_dir_rawjson / "jsonNaturalize.py"
    if not json_naturalize.exists():
        json_naturalize = None

    src_dir_stdjson = script_dir / "src" / "stdjson"
    raw_to_complete = src_dir_stdjson / "raw_to_complete.py"
    complete_to_concise = src_dir_stdjson / "complete_to_concise.py"
    concise_to_lean = src_dir_stdjson / "concise_to_lean.py"

    missing = [p for p in [pdf_to_md, md_to_tex, tex_to_json,
                           raw_to_complete, complete_to_concise, concise_to_lean] if not p.exists()]
    if missing:
        raise SystemExit("Missing scripts:\n" + "\n".join(str(p)
                         for p in missing))
    return pdf_to_md, md_to_tex, tex_to_json, json_naturalize, raw_to_complete, complete_to_concise, concise_to_lean


def _tmp_path(final_path: Path) -> Path:
    return final_path.with_name(final_path.name + ".tmp")


def _file_nonempty(p: Path) -> bool:
    return p.exists() and p.is_file() and p.stat().st_size > 0


_PAGE_SENTINEL_RE = re.compile(r"(?m)^\s*<!--\s*PAGE\s+(\d+)\s*-->\s*$")


def _pdf_page_count(pdf_path: Path) -> Optional[int]:
    """Best-effort PDF page count using PyMuPDF (fitz)."""
    try:
        import fitz  # type: ignore
    except Exception:
        return None
    try:
        doc = fitz.open(str(pdf_path))
        try:
            return int(doc.page_count)
        finally:
            doc.close()
    except Exception:
        return None


def md_complete(md_path: Path, pdf_path: Path) -> bool:
    """MD is complete iff it contains the last PAGE sentinel matching PDF page count."""
    if not _file_nonempty(md_path):
        return False
    if not STRICT_RESUME:
        return True

    # Read a tail window first (fast for large files); fall back to full read if needed.
    try:
        tail_bytes = 1024 * 1024  # 1 MiB
        with md_path.open("rb") as f:
            try:
                f.seek(0, 2)
                size = f.tell()
                f.seek(max(0, size - tail_bytes), 0)
            except Exception:
                # Some file-like implementations may not support seek/tell well; fall back.
                f.seek(0)
            chunk = f.read()
        tail_text = chunk.decode("utf-8", errors="ignore")
        pages = [int(x) for x in _PAGE_SENTINEL_RE.findall(tail_text)]
        if not pages:
            # fallback: full file read
            text = md_path.read_text(encoding="utf-8", errors="ignore")
            pages = [int(x) for x in _PAGE_SENTINEL_RE.findall(text)]
    except Exception:
        return False
    if not pages:
        # If the OCR script didn't emit page sentinels, fall back to non-empty.
        return True

    max_md_page = max(pages)
    n_pdf = _pdf_page_count(pdf_path)
    if n_pdf is None:
        # can't confirm; accept as complete
        return True

    return max_md_page >= n_pdf


def tex_complete(tex_path: Path) -> bool:
    """TEX is complete iff it has \begin{document} and ends with \end{document} (best-effort)."""
    if not _file_nonempty(tex_path):
        return False
    if not STRICT_RESUME:
        return True

    try:
        head_bytes = 64 * 1024  # 64 KiB
        tail_bytes = 64 * 1024  # 64 KiB

        with tex_path.open("rb") as f:
            head = f.read(head_bytes)

            try:
                f.seek(0, 2)
                size = f.tell()
                f.seek(max(0, size - tail_bytes), 0)
            except Exception:
                # fall back: if seek/tell fails, just keep reading (small files)
                pass

            tail = f.read()

        head_text = head.decode("utf-8", errors="ignore")
        tail_text = tail.decode("utf-8", errors="ignore")
    except Exception:
        return False

    if "\\begin{document}" not in head_text and "\\begin{document}" not in tail_text:
        return False

    # Allow trailing whitespace/comments after \end{document}
    if re.search(r"\\end\{document\}\s*\Z", tail_text) is None:
        return False

    return True


def json_complete(json_path: Path) -> bool:
    """JSON is complete iff it parses and is a non-empty list/dict."""
    if not _file_nonempty(json_path):
        return False
    if not STRICT_RESUME:
        return True

    try:
        obj = json.loads(json_path.read_text(encoding="utf-8"))
    except Exception:
        return False

    if isinstance(obj, list):
        return len(obj) > 0
    if isinstance(obj, dict):
        return len(obj) > 0
    return False


Validator = Callable[[Path], bool]


def run_stage_atomic(
    *,
    cmd: list[str],
    out_path: Path,
    validate_out: Validator,
) -> bool:
    tmp = _tmp_path(out_path)
    if CLEAN_STALE_TMPS and tmp.exists():
        try:
            tmp.unlink()
        except Exception:
            pass

    if len(cmd) < 4:
        raise RuntimeError(
            "cmd too short (expected: python script IN OUT [flags...])")
    cmd2 = list(cmd)
    cmd2[3] = str(tmp)

    try:
        run_cmd(cmd2)
    except SystemExit as e:
        print(
            f"[warn] stage command failed: {' '.join(cmd2)}; reason={e}", file=sys.stderr)
        try:
            if tmp.exists():
                tmp.unlink()
        except Exception:
            pass
        return False

    if not validate_out(tmp):
        print(
            f"[warn] Stage produced incomplete output: {tmp}", file=sys.stderr)
        try:
            if tmp.exists():
                tmp.unlink()
        except Exception:
            pass
        return False

    tmp.replace(out_path)
    return True


def process_one(
    pdf_path: Path,
    pdf_to_md: Path,
    md_to_tex: Path,
    tex_to_json: Path,
    *,
    mode: str,
    input_pdf_dir: Path,
    output_json_dir: Path,
    work_dir: Path,
) -> Path:
    rel_pdf = pdf_path.relative_to(input_pdf_dir)
    rel_no_suffix = rel_pdf.with_suffix("")

    job_dir = work_dir / rel_no_suffix
    job_dir.mkdir(parents=True, exist_ok=True)

    stem = pdf_path.stem
    md_path = job_dir / f"{stem}.md"
    tex_path = job_dir / f"{stem}.tex"

    json_path = (output_json_dir / rel_pdf).with_suffix(".json")
    json_path.parent.mkdir(parents=True, exist_ok=True)

    if json_complete(json_path) and not OVERWRITE_JSON:
        print(f"[skip] {rel_pdf.as_posix()} -> JSON exists: {json_path}")
        return json_path

    if md_complete(md_path, pdf_path):
        print(f"[resume] skip PDF->MD (complete): {md_path}")
    else:
        cmd1 = [sys.executable, str(pdf_to_md), str(pdf_path), str(md_path)]
        if OCR_MAX_TOKENS is not None:
            cmd1 += ["--max-tokens", str(OCR_MAX_TOKENS)]
        if OCR_WORKERS is not None:
            cmd1 += ["--workers", str(int(OCR_WORKERS))]

        if ATOMIC_OUTPUTS:
            ok = run_stage_atomic(
                cmd=cmd1,
                out_path=md_path,
                validate_out=lambda p: md_complete(p, pdf_path),
            )
            if not ok:
                print(
                    f"[warn] PDF->MD stage failed for {pdf_path}; skipping remaining stages", file=sys.stderr)
                return json_path
        else:
            run_cmd(cmd1)
            if not md_complete(md_path, pdf_path):
                raise SystemExit(f"PDF->MD output incomplete: {md_path}")

    if tex_complete(tex_path):
        print(f"[resume] skip MD->TEX (complete): {tex_path}")
    else:
        cmd2 = [sys.executable, str(md_to_tex), str(md_path), str(tex_path)]
        if THINK_WORKERS is not None:
            cmd2 += ["--workers", str(int(THINK_WORKERS))]

        if ATOMIC_OUTPUTS:
            ok = run_stage_atomic(
                cmd=cmd2,
                out_path=tex_path,
                validate_out=tex_complete,
            )
            if not ok:
                print(
                    f"[warn] MD->TEX stage failed for {pdf_path}; skipping remaining stages", file=sys.stderr)
                return json_path
        else:
            run_cmd(cmd2)
            if not tex_complete(tex_path):
                raise SystemExit(f"MD->TEX output incomplete: {tex_path}")

    if json_complete(json_path) and not OVERWRITE_JSON:
        print(f"[resume] skip TEX->JSON (complete): {json_path}")
        return json_path

    cmd3 = [sys.executable, str(tex_to_json), str(tex_path), str(json_path)]

    if ATOMIC_OUTPUTS:
        ok = run_stage_atomic(
            cmd=cmd3,
            out_path=json_path,
            validate_out=json_complete,
        )
        if not ok:
            print(
                f"[warn] TEX->JSON stage failed for {pdf_path}; skipping remaining stages", file=sys.stderr)
            return json_path
    else:
        run_cmd(cmd3)
        if not json_complete(json_path):
            raise SystemExit(f"TEX->JSON output incomplete: {json_path}")

    return json_path


def process_json(
    json_path: Path,
    raw_to_complete: Path,
    complete_to_concise: Path,
    concise_to_lean: Path,
    *,
    mode: str,
    input_json_dir: Path,
    output_json_dir: Path,
    work_dir: Path,
) -> Path:
    """Run stdjson stages: raw_to_complete -> complete_to_concise -> concise_to_lean.

    Uses atomic stage runner when configured. Returns final lean JSON path.
    """
    try:
        rel = json_path.relative_to(input_json_dir)
    except ValueError:
        # Allow book-mode naturalized inputs from work_dir, e.g.
        # work/book/foo/foo.naturalized.json -> rel book/foo.json
        try:
            rel_work = json_path.relative_to(work_dir)
        except ValueError as err:
            raise ValueError(
                f"{json_path!s} is not under either {input_json_dir!s} or {work_dir!s}"
            ) from err

        stem = json_path.stem
        if stem.endswith(".naturalized"):
            stem = stem[:-len(".naturalized")]

        # If the file lives in work/<mode>/<stem>/<stem>.naturalized.json,
        # collapse it back to <mode>/<stem>.json.
        parent = rel_work.parent
        if parent.name == stem:
            rel = parent.parent / (stem + ".json")
        else:
            rel = rel_work.with_name(stem + ".json")

    rel_no_suffix = rel.with_suffix("")
    base_stem = rel_no_suffix.name

    job_dir = work_dir / rel_no_suffix
    job_dir.mkdir(parents=True, exist_ok=True)

    complete_json = job_dir / f"{base_stem}.complete.json"
    concise_json = job_dir / f"{base_stem}.concise.json"
    lean_json = (output_json_dir / rel).with_suffix(".lean.json")
    lean_json.parent.mkdir(parents=True, exist_ok=True)

    # Stage 1: raw -> complete
    if json_complete(complete_json) and not OVERWRITE_JSON:
        print(f"[skip] RAW->COMPLETE (complete): {complete_json}")
    else:
        cmd1 = [sys.executable, str(raw_to_complete), str(
            json_path), str(complete_json)]
        if ATOMIC_OUTPUTS:
            ok = run_stage_atomic(cmd=cmd1, out_path=complete_json,
                                  validate_out=json_complete)
            if not ok:
                print(
                    f"[warn] RAW->COMPLETE stage failed for {json_path}; skipping remaining stdjson stages", file=sys.stderr)
                return lean_json
        else:
            run_cmd(cmd1)
            if not json_complete(complete_json):
                raise SystemExit(
                    f"RAW->COMPLETE output incomplete: {complete_json}")

    # Stage 2: complete -> concise
    if json_complete(concise_json) and not OVERWRITE_JSON:
        print(f"[skip] COMPLETE->CONCISE (complete): {concise_json}")
    else:
        cmd2 = [sys.executable, str(complete_to_concise), str(
            complete_json), str(concise_json)]
        if ATOMIC_OUTPUTS:
            ok = run_stage_atomic(cmd=cmd2, out_path=concise_json,
                                  validate_out=json_complete)
            if not ok:
                print(
                    f"[warn] COMPLETE->CONCISE stage failed for {complete_json}; skipping CONCISE->LEAN", file=sys.stderr)
                return lean_json
        else:
            run_cmd(cmd2)
            if not json_complete(concise_json):
                raise SystemExit(
                    f"COMPLETE->CONCISE output incomplete: {concise_json}")

    # Stage 3: concise -> lean
    if json_complete(lean_json) and not OVERWRITE_JSON:
        print(f"[skip] CONCISE->LEAN (complete): {lean_json}")
        return lean_json

    cmd3 = [sys.executable, str(concise_to_lean), str(
        concise_json), str(lean_json)]
    if ATOMIC_OUTPUTS:
        ok = run_stage_atomic(cmd=cmd3, out_path=lean_json,
                              validate_out=json_complete)
        if not ok:
            print(
                f"[warn] CONCISE->LEAN stage failed for {concise_json}; skipping", file=sys.stderr)
            return lean_json
    else:
        run_cmd(cmd3)
        if not json_complete(lean_json):
            raise SystemExit(f"CONCISE->LEAN output incomplete: {lean_json}")

    return lean_json


def process_book_naturalize(
    json_path: Path,
    json_naturalize: Path,
    *,
    input_json_dir: Path,
    work_dir: Path,
) -> Path:
    """Run optional book rawjson naturalize stage after texTojson."""
    rel = json_path.relative_to(input_json_dir)
    rel_no_suffix = rel.with_suffix("")

    job_dir = work_dir / rel_no_suffix
    job_dir.mkdir(parents=True, exist_ok=True)

    stem = json_path.stem
    naturalized_json = job_dir / f"{stem}.naturalized.json"

    if json_complete(naturalized_json) and not OVERWRITE_JSON:
        print(f"[skip] JSON->NATURALIZED (complete): {naturalized_json}")
        return naturalized_json

    cmd = [sys.executable, str(json_naturalize), str(
        json_path), str(naturalized_json)]
    if ATOMIC_OUTPUTS:
        ok = run_stage_atomic(cmd=cmd, out_path=naturalized_json,
                              validate_out=json_complete)
        if not ok:
            print(
                f"[warn] JSON->NATURALIZED stage failed for {json_path}; fallback to raw JSON", file=sys.stderr)
            return json_path
    else:
        run_cmd(cmd)
        if not json_complete(naturalized_json):
            print(
                f"[warn] JSON->NATURALIZED output incomplete: {naturalized_json}; fallback to raw JSON", file=sys.stderr)
            return json_path

    return naturalized_json


def parse_args() -> argparse.Namespace:
    settings = load_settings()
    ap = argparse.ArgumentParser(
        description="Run the OCR -> Markdown -> TeX -> JSON pipeline.")
    ap.add_argument(
        "--mode",
        choices=["book", "paper", "exercise"],
        default=str(get_setting(settings, "PIPELINE_MODE", "book")),
        help="Pipeline mode to run (default: %(default)s)",
    )
    return ap.parse_args()


def main() -> None:
    global INPUT_PDF_DIR, OUTPUT_JSON_DIR, WORK_DIR
    global PIPELINE_MODE, OCR_MAX_TOKENS, ONLY_THESE_STEMS, OVERWRITE_JSON
    global OCR_WORKERS, THINK_WORKERS, STRICT_RESUME, ATOMIC_OUTPUTS, CLEAN_STALE_TMPS

    settings = load_settings()
    INPUT_PDF_DIR = PROJECT_ROOT / \
        str(get_setting(settings, "INPUT_PDF_DIR", "input_pdfs"))
    OUTPUT_JSON_DIR = PROJECT_ROOT / \
        str(get_setting(settings, "OUTPUT_JSON_DIR", "output_json"))
    WORK_DIR = PROJECT_ROOT / str(get_setting(settings, "WORK_DIR", "work"))
    PIPELINE_MODE = str(get_setting(settings, "PIPELINE_MODE", "book"))
    OCR_MAX_TOKENS = get_setting(settings, "OCR_MAX_TOKENS", None)
    ONLY_THESE_STEMS = set(get_setting(settings, "ONLY_THESE_STEMS", []))
    OVERWRITE_JSON = bool(get_setting(settings, "OVERWRITE_JSON", False))
    OCR_WORKERS = get_setting(settings, "OCR_WORKERS", 4)
    THINK_WORKERS = get_setting(settings, "THINK_WORKERS", 4)
    STRICT_RESUME = bool(get_setting(settings, "STRICT_RESUME", True))
    ATOMIC_OUTPUTS = bool(get_setting(settings, "ATOMIC_OUTPUTS", True))
    CLEAN_STALE_TMPS = bool(get_setting(settings, "CLEAN_STALE_TMPS", True))

    args = parse_args()
    mode = args.mode

    # Always use mode-specific rawjson scripts so `--mode book` runs `src/book/rawjson/*`.
    RAWJSON_SRC_DIR = PROJECT_ROOT / "src" / mode / "rawjson"

    INPUT_PDF_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON_DIR.mkdir(parents=True, exist_ok=True)
    WORK_DIR.mkdir(parents=True, exist_ok=True)

    pdf_to_md, md_to_tex, tex_to_json, json_naturalize, raw_to_complete, complete_to_concise, concise_to_lean = ensure_scripts_exist(
        PROJECT_ROOT, mode, rawjson_src_dir=RAWJSON_SRC_DIR)
    mode_input_dir = INPUT_PDF_DIR / mode
    mode_input_dir.mkdir(parents=True, exist_ok=True)

    pdfs = sorted(mode_input_dir.rglob("*.pdf"))

    if ONLY_THESE_STEMS:
        raw_selectors = list(ONLY_THESE_STEMS)

        norm: List[str] = []
        for s in raw_selectors:
            t = s.strip().replace("\\", "/")
            if t.endswith(".pdf"):
                t = t[:-4]
            norm.append(t)

        def _matches(p: Path) -> bool:
            rel = p.relative_to(INPUT_PDF_DIR)
            rel_no_suffix_posix = rel.with_suffix("").as_posix()

            for sel in norm:
                if not sel:
                    continue
                sel_strip = sel.rstrip("/")

                if p.stem == sel_strip:
                    return True

                if rel_no_suffix_posix == sel_strip:
                    return True

                if rel_no_suffix_posix.startswith(sel_strip + "/"):
                    return True

            return False

        pdfs = [p for p in pdfs if _matches(p)]

    def _json_out_path(p: Path) -> Path:
        rel = p.relative_to(INPUT_PDF_DIR)
        return (OUTPUT_JSON_DIR / rel).with_suffix(".json")

    '''
    if not OVERWRITE_JSON:
        pdfs = [p for p in pdfs if not json_complete(_json_out_path(p))]

    
    if not pdfs:
        print(f"No PDFs to process for mode={mode!r} in: {mode_input_dir}")
        return
    '''
    print(f"Mode: {mode}")
    print(f"Found {len(pdfs)} PDF(s) to process in {mode_input_dir}")
    for pdf in pdfs:
        print(
            f"\n=== Processing: {pdf.relative_to(INPUT_PDF_DIR).as_posix()} ===")
        out_json = process_one(
            pdf,
            pdf_to_md,
            md_to_tex,
            tex_to_json,
            mode=mode,
            input_pdf_dir=INPUT_PDF_DIR,
            output_json_dir=OUTPUT_JSON_DIR,
            work_dir=WORK_DIR,
        )
        print(f"[ok] JSON -> {out_json}")

        stdjson_input = out_json

        # Optional book-only naturalize stage in src/book/rawjson/jsonNaturalize.py
        if mode == "book" and json_naturalize is not None:
            try:
                stdjson_input = process_book_naturalize(
                    out_json,
                    json_naturalize,
                    input_json_dir=OUTPUT_JSON_DIR,
                    work_dir=WORK_DIR,
                )
                print(f"[ok] NATURALIZED JSON -> {stdjson_input}")
            except Exception as e:
                print(
                    f"[warn] jsonNaturalize failed for {out_json}; fallback to raw JSON. reason={e}",
                    file=sys.stderr,
                )
                stdjson_input = out_json

        # Run stdjson processing (raw_to_complete, complete_to_concise, concise_to_lean)
        try:
            lean = process_json(
                stdjson_input,
                raw_to_complete,
                complete_to_concise,
                concise_to_lean,
                mode=mode,
                input_json_dir=OUTPUT_JSON_DIR,
                output_json_dir=OUTPUT_JSON_DIR,
                work_dir=WORK_DIR,
            )
            print(f"[ok] STDJSON -> {lean}")
        except Exception as e:
            print(f"[warn] stdjson processing failed for {out_json}: {e}")

    print("\nALL DONE")


if __name__ == "__main__":
    main()
