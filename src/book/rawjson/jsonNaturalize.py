#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Step-2 naturalization: rewrite step-1 problem JSON into standardized math wording.

Input:  step-1 JSON rows (from texTojson.py)
Output: same rows + step-2 fields:
  - problem_standardized_math
  - naturalize_status
  - naturalize_prompt_version
  - naturalize_notes
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from openai import OpenAI
from tqdm import tqdm


_CHAT_FORCE_STREAM: Optional[bool] = None
ALLOWED_STATUS = {"ok", "fallback_original", "fallback_context", "skipped", "failed"}
PROMPT_VERSION_DEFAULT = "v1"


def _safe_json_load(s: str) -> Optional[Dict[str, Any]]:
    try:
        v = json.loads(s)
    except Exception:
        return None
    return v if isinstance(v, dict) else None


def _extract_first_json_object(text: str) -> Optional[Dict[str, Any]]:
    s = (text or "").strip()
    if not s:
        return None
    direct = _safe_json_load(s)
    if direct is not None:
        return direct
    l = s.find("{")
    r = s.rfind("}")
    if l >= 0 and r > l:
        return _safe_json_load(s[l : r + 1])
    return None


def _is_stream_required_error(err: Exception) -> bool:
    return "stream must be set to true" in str(err or "").lower()


def _collect_stream_text(stream_obj: Any) -> str:
    parts: List[str] = []
    try:
        for chunk in stream_obj:
            choices = getattr(chunk, "choices", None) or []
            if not choices:
                continue
            delta = getattr(choices[0], "delta", None)
            if delta is None:
                continue
            content = getattr(delta, "content", None)
            if isinstance(content, str):
                parts.append(content)
            elif isinstance(content, list):
                for it in content:
                    if isinstance(it, dict):
                        t = it.get("text") or it.get("content") or ""
                    else:
                        t = getattr(it, "text", "") or getattr(it, "content", "") or ""
                    if isinstance(t, str) and t:
                        parts.append(t)
    finally:
        close_fn = getattr(stream_obj, "close", None)
        if callable(close_fn):
            try:
                close_fn()
            except Exception:
                pass
    return "".join(parts)


def _chat_completion_text(
    client: OpenAI,
    *,
    model: str,
    prompt: str,
    max_tokens: int,
    temperature: float = 0.0,
    top_p: float = 1.0,
) -> str:
    global _CHAT_FORCE_STREAM
    kwargs = dict(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        temperature=temperature,
        top_p=top_p,
    )
    if _CHAT_FORCE_STREAM is True:
        stream_obj = client.chat.completions.create(stream=True, **kwargs)
        return (_collect_stream_text(stream_obj) or "").strip()
    try:
        resp = client.chat.completions.create(**kwargs)
        return (resp.choices[0].message.content or "").strip()
    except Exception as e:
        if _is_stream_required_error(e):
            _CHAT_FORCE_STREAM = True
            stream_obj = client.chat.completions.create(stream=True, **kwargs)
            return (_collect_stream_text(stream_obj) or "").strip()
        raise


def _default_cache_dir() -> Path:
    d = Path.cwd() / "cache" / "naturalize"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _call_cached(
    client: OpenAI,
    *,
    model: str,
    prompt: str,
    max_tokens: int,
    cache_dir: Optional[Path],
    cache_enabled: bool,
) -> str:
    if not cache_enabled:
        return _chat_completion_text(client, model=model, prompt=prompt, max_tokens=max_tokens)

    cdir = cache_dir or _default_cache_dir()
    key = hashlib.sha256((model + "\n" + str(max_tokens) + "\n" + prompt).encode("utf-8")).hexdigest()
    path = cdir / f"{key}.txt"
    if path.exists():
        try:
            return path.read_text(encoding="utf-8")
        except Exception:
            pass
    out = _chat_completion_text(client, model=model, prompt=prompt, max_tokens=max_tokens)
    try:
        path.write_text(out, encoding="utf-8")
    except Exception:
        pass
    return out


def find_config_json() -> Path:
    p = Path.cwd() / "config.json"
    if p.exists():
        return p.resolve()
    here = Path(__file__).resolve().parent
    for d in [here] + list(here.parents):
        q = d / "config.json"
        if q.exists():
            return q.resolve()
    raise FileNotFoundError("config.json not found (checked CWD and script parents).")


def load_config() -> Dict[str, Any]:
    cfg_path = find_config_json()
    data = json.loads(cfg_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{cfg_path} must contain a JSON object.")
    return data


def _compact_text(s: str, max_chars: int = 320) -> str:
    t = re.sub(r"\s+", " ", s or "").strip()
    if len(t) <= max_chars:
        return t
    return t[: max_chars - 1].rstrip() + "…"


def build_naturalize_input(record: Dict[str, Any]) -> Dict[str, Any]:
    source_idx = str(record.get("source_idx") or "").strip()
    source = str(record.get("source") or "").strip()
    original_problem = str(record.get("problem") or "").strip()
    problem_with_context = str(record.get("problem_with_context") or "").strip()
    targets = record.get("body_ref_targets")
    if not isinstance(targets, list):
        targets = []

    equations: List[Dict[str, str]] = []
    contexts: List[Dict[str, str]] = []
    for t in targets:
        if not isinstance(t, dict):
            continue
        tag = str(t.get("tag") or "").strip()
        display_tag = str(t.get("display_tag") or "").strip()
        eq = str(t.get("equation_content") or "").strip()
        ctx = str(t.get("content") or "").strip()
        if eq:
            equations.append(
                {
                    "tag": tag,
                    "display_tag": display_tag,
                    "equation_content": eq,
                }
            )
        if ctx:
            contexts.append(
                {
                    "tag": tag,
                    "display_tag": display_tag,
                    "content": _compact_text(ctx, max_chars=320),
                }
            )
    return {
        "source_idx": source_idx,
        "source": source,
        "original_problem": original_problem,
        "problem_with_context": problem_with_context,
        "equations": equations,
        "contexts": contexts,
    }


def make_prompt(payload: Dict[str, Any]) -> str:
    return (
        "You are rewriting ONE mathematical exercise into a more self-contained, standard, and fluent form.\n"
        "Treat this input record as ONE independent proposition. Do not use other records.\n\n"
        "You are given:\n"
        "1. original_problem\n"
        "2. problem_with_context\n"
        "3. equations (core anchors from references)\n"
        "4. contexts (auxiliary background from references)\n\n"
        "Your task:\n"
        "Rewrite the exercise so it is faithful, mathematically precise, and textbook-style.\n\n"
        "Hard constraints:\n"
        "- Do NOT solve the problem.\n"
        "- Do NOT add new assumptions, definitions, or symbols.\n"
        "- Do NOT change task type (prove/show/find/derive/evaluate/etc.).\n"
        "- Do NOT remove essential formulas, variables, conditions, or constraints.\n"
        "- Prioritize equations as anchors; use contexts only when necessary for coherence.\n"
        "- Keep the mathematical meaning strictly faithful to the source.\n"
        "- The output sentence(s) must be in ENGLISH only.\n"
        "- Return ONLY a JSON object. No markdown, no code fences, no extra keys.\n\n"
        "Output JSON schema:\n"
        '{"problem_standardized_math":"<English standardized exercise statement>"}\n\n'
        "Input record:\n\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
    )


def make_retry_prompt(payload: Dict[str, Any]) -> str:
    return (
        "Retry. Return STRICT JSON ONLY for one independent exercise.\n"
        "Rules:\n"
        "- English only.\n"
        "- Preserve objective, notation, and constraints.\n"
        "- No new assumptions or symbols.\n"
        "- No explanation text.\n"
        "- Exactly one key: problem_standardized_math.\n\n"
        "Output template:\n"
        '{"problem_standardized_math":"<English standardized exercise statement>"}\n\n'
        "Input:\n"
        + json.dumps(payload, ensure_ascii=False)
    )


def _extract_standardized_text(raw: str) -> str:
    text = (raw or "").strip()
    if not text:
        return ""
    obj = _extract_first_json_object(text)
    if obj:
        val = str(obj.get("problem_standardized_math") or "").strip()
        if val:
            return val
    # Try key-value extraction from quasi-JSON output
    m = re.search(r'"problem_standardized_math"\s*:\s*"([\s\S]*?)"\s*(?:[,}])', text)
    if m:
        val = m.group(1)
        val = val.replace('\\"', '"').replace("\\n", "\n")
        val = val.strip()
        if val:
            return val
    # Fallback: strip code fences / leading labels and keep plain text
    text = re.sub(r"^\s*```(?:json|text)?\s*", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"\s*```\s*$", "", text).strip()
    text = re.sub(r"^\s*problem_standardized_math\s*[:：]\s*", "", text, flags=re.IGNORECASE).strip()
    if text.startswith("{") and text.endswith("}"):
        return ""
    return text


_CJK_RE = re.compile(r"[\u4e00-\u9fff]")
_EN_WORD_RE = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")
_EN_ALPHA_RE = re.compile(r"[A-Za-z]")
_UNICODE_ALPHA_RE = re.compile(r"[^\W\d_]", flags=re.UNICODE)


def _looks_non_english(s: str) -> bool:
    t = (s or "").strip()
    if not t:
        return True
    return bool(_CJK_RE.search(t))


def _english_quality_ok(s: str, *, min_words: int = 6, min_alpha_ratio: float = 0.6) -> bool:
    t = (s or "").strip()
    if not t:
        return False
    if _looks_non_english(t):
        return False

    en_words = _EN_WORD_RE.findall(t)
    if len(en_words) < int(min_words):
        return False

    en_alpha = len(_EN_ALPHA_RE.findall(t))
    uni_alpha = len(_UNICODE_ALPHA_RE.findall(t))
    if uni_alpha <= 0:
        return False
    if (en_alpha / float(uni_alpha)) < float(min_alpha_ratio):
        return False
    return True


def _fallback_problem(record: Dict[str, Any]) -> Tuple[str, str, str]:
    pwc = str(record.get("problem_with_context") or "").strip()
    prob = str(record.get("problem") or "").strip()
    if pwc:
        return pwc, "fallback_context", "llm_empty_or_unavailable"
    if prob:
        return prob, "fallback_original", "llm_empty_or_unavailable"
    return "", "failed", "empty_problem_and_context"


def naturalize_one(
    record: Dict[str, Any],
    *,
    client: Optional[OpenAI],
    model: str,
    max_tokens: int,
    prompt_version: str,
    cache_dir: Optional[Path],
    cache_enabled: bool,
    use_llm: bool,
    llm_retries: int,
    min_english_words: int,
    min_english_alpha_ratio: float,
) -> Dict[str, Any]:
    out = dict(record)
    if not use_llm or client is None:
        text, status, notes = _fallback_problem(record)
        out["problem_standardized_math"] = text
        out["naturalize_status"] = status
        out["naturalize_prompt_version"] = prompt_version
        out["naturalize_notes"] = "llm_disabled_or_missing_key; " + notes
        return out

    payload = build_naturalize_input(record)
    prompt = make_prompt(payload)

    try:
        attempts = max(1, int(llm_retries))
        reasons: List[str] = []
        standardized = ""

        for i in range(1, attempts + 1):
            prompt_i = prompt if i == 1 else make_retry_prompt(payload)
            raw_i = _call_cached(
                client,
                model=model,
                prompt=prompt_i,
                max_tokens=max_tokens,
                cache_dir=cache_dir,
                cache_enabled=cache_enabled,
            )
            standardized = _extract_standardized_text(raw_i)
            if not standardized:
                reasons.append(f"attempt{i}:empty_or_unparseable")
                continue
            if not _english_quality_ok(
                standardized,
                min_words=int(min_english_words),
                min_alpha_ratio=float(min_english_alpha_ratio),
            ):
                reasons.append(f"attempt{i}:non_english_or_low_quality")
                continue
            break

        if not standardized or not _english_quality_ok(
            standardized,
            min_words=int(min_english_words),
            min_alpha_ratio=float(min_english_alpha_ratio),
        ):
            text, status, notes = _fallback_problem(record)
            out["problem_standardized_math"] = text
            out["naturalize_status"] = status
            out["naturalize_prompt_version"] = prompt_version
            out["naturalize_notes"] = "; ".join(reasons + [notes]) if reasons else notes
            return out

        out["problem_standardized_math"] = standardized
        out["naturalize_status"] = "ok"
        out["naturalize_prompt_version"] = prompt_version
        out["naturalize_notes"] = ""
        return out
    except Exception as e:
        text, status, notes = _fallback_problem(record)
        out["problem_standardized_math"] = text
        out["naturalize_status"] = status
        out["naturalize_prompt_version"] = prompt_version
        out["naturalize_notes"] = f"llm_error={e.__class__.__name__}; {notes}"
        return out


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Step-2 naturalize step-1 JSON records.")
    ap.add_argument("in_json", type=str, help="Input step-1 JSON file")
    ap.add_argument("out_json", nargs="?", default="", help="Output step-2 JSON file (optional)")
    ap.add_argument(
        "--out-dir",
        type=str,
        default="output_json_naturalized",
        help="Default output root dir when out_json is omitted",
    )
    ap.add_argument("--model", type=str, default="", help="LLM model override (default: config.model)")
    ap.add_argument("--max-tokens", type=int, default=900, help="LLM max tokens per item")
    ap.add_argument("--max-items", type=int, default=0, help="Max rows to send to LLM (0 = all)")
    ap.add_argument("--prompt-version", type=str, default=PROMPT_VERSION_DEFAULT, help="Prompt version tag")
    ap.add_argument("--cache-dir", type=str, default="", help="Cache dir (default: cache/naturalize)")
    ap.add_argument("--no-cache", action="store_true", help="Disable LLM cache")
    ap.add_argument("--disable-llm", action="store_true", help="Do not call LLM; fallback only")
    ap.add_argument("--force", action="store_true", help="Rewrite rows even if problem_standardized_math exists")
    ap.add_argument("--llm-retries", type=int, default=3, help="Max LLM attempts per row")
    ap.add_argument("--min-english-words", type=int, default=6, help="Min English word count for accepted output")
    ap.add_argument(
        "--min-english-alpha-ratio",
        type=float,
        default=0.6,
        help="Min ratio of ASCII English letters among all alphabetic chars",
    )
    ap.add_argument("--stats-out", type=str, default="", help="Optional path to write per-file stats JSON")
    ap.add_argument(
        "--cleanup-cache-on-exit",
        action="store_true",
        help="Delete naturalize cache directory after run",
    )
    return ap.parse_args()


def _derive_out_path(in_path: Path, out_json: str, out_dir: str) -> Path:
    if out_json:
        return Path(out_json).expanduser().resolve()

    project_root = find_config_json().parent
    base_step1 = project_root / "output_json"
    out_root = project_root / str(out_dir or "output_json_naturalized")

    try:
        rel = in_path.relative_to(base_step1)
        return (out_root / rel).resolve()
    except Exception:
        return in_path.with_name(in_path.stem + ".naturalized" + in_path.suffix).resolve()


def _strip_naturalize_meta(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for row in rows:
        r = dict(row)
        r.pop("naturalize_status", None)
        r.pop("naturalize_prompt_version", None)
        r.pop("naturalize_notes", None)
        out.append(r)
    return out


def main() -> None:
    args = parse_args()
    in_path = Path(args.in_json).expanduser().resolve()
    out_path = _derive_out_path(in_path, str(args.out_json or ""), str(args.out_dir or ""))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    rows_raw = json.loads(in_path.read_text(encoding="utf-8"))
    if not isinstance(rows_raw, list):
        raise ValueError("Input JSON must be a list of records.")
    rows: List[Dict[str, Any]] = [r if isinstance(r, dict) else {} for r in rows_raw]

    cfg = {}
    try:
        cfg = load_config()
    except Exception:
        cfg = {}
    api_key = str(cfg.get("api_key") or os.getenv("OPENAI_API_KEY") or "").strip()
    base_url = str(cfg.get("base_url") or "").strip()
    model = str(args.model or cfg.get("model") or "gpt-5-mini").strip()
    cache_dir = Path(args.cache_dir).expanduser().resolve() if args.cache_dir else None
    cache_enabled = not bool(args.no_cache)
    cleanup_cache = bool(args.cleanup_cache_on_exit)
    effective_cache_dir = cache_dir or (Path.cwd() / "cache" / "naturalize")

    use_llm = (not bool(args.disable_llm)) and bool(api_key)
    client: Optional[OpenAI] = None
    if use_llm:
        if base_url:
            client = OpenAI(api_key=api_key, base_url=base_url, timeout=180)
        else:
            client = OpenAI(api_key=api_key, timeout=180)

    budget = max(0, int(args.max_items))
    touched = 0
    out_rows: List[Dict[str, Any]] = []
    t0 = time.time()
    ok_cnt = 0
    fb_cnt = 0
    skip_cnt = 0
    fail_cnt = 0

    pbar = tqdm(rows, total=len(rows), desc="Naturalize rows", unit="row")
    for row in pbar:
        has_prev = str(row.get("problem_standardized_math") or "").strip()
        if has_prev and not args.force:
            kept = dict(row)
            out_rows.append(kept)
            st = str(kept.get("naturalize_status") or "skipped")
            if st == "ok":
                ok_cnt += 1
            elif st.startswith("fallback"):
                fb_cnt += 1
            elif st == "failed":
                fail_cnt += 1
            else:
                skip_cnt += 1
            pbar.set_postfix({
                "llm": touched,
                "ok": ok_cnt,
                "fb": fb_cnt,
                "skip": skip_cnt,
                "fail": fail_cnt,
            })
            continue
        can_use_llm = use_llm and (budget == 0 or touched < budget)
        if can_use_llm:
            touched += 1
        new_row = naturalize_one(
            row,
            client=client,
            model=model,
            max_tokens=max(200, int(args.max_tokens)),
            prompt_version=str(args.prompt_version or PROMPT_VERSION_DEFAULT),
            cache_dir=cache_dir,
            cache_enabled=cache_enabled,
            use_llm=can_use_llm,
            llm_retries=max(1, int(args.llm_retries)),
            min_english_words=max(1, int(args.min_english_words)),
            min_english_alpha_ratio=max(0.0, min(1.0, float(args.min_english_alpha_ratio))),
        )
        out_rows.append(new_row)
        st = str(new_row.get("naturalize_status") or "")
        if st == "ok":
            ok_cnt += 1
        elif st.startswith("fallback"):
            fb_cnt += 1
        elif st == "failed":
            fail_cnt += 1
        else:
            skip_cnt += 1
        pbar.set_postfix({
            "llm": touched,
            "ok": ok_cnt,
            "fb": fb_cnt,
            "skip": skip_cnt,
            "fail": fail_cnt,
        })

    pbar.close()

    output_rows = _strip_naturalize_meta(out_rows)
    out_path.write_text(json.dumps(output_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    dt = time.time() - t0
    ok = sum(1 for r in out_rows if str(r.get("naturalize_status") or "") == "ok")
    fb = sum(1 for r in out_rows if str(r.get("naturalize_status") or "").startswith("fallback"))
    skip = sum(1 for r in out_rows if str(r.get("naturalize_status") or "") == "skipped")
    fail = sum(1 for r in out_rows if str(r.get("naturalize_status") or "") == "failed")

    if args.stats_out:
        stats_path = Path(str(args.stats_out)).expanduser().resolve()
        stats_path.parent.mkdir(parents=True, exist_ok=True)
        stats_obj = {
            "in_json": str(in_path),
            "out_json": str(out_path),
            "rows": int(len(out_rows)),
            "llm_touched": int(touched),
            "ok": int(ok),
            "fallback": int(fb),
            "skipped": int(skip),
            "failed": int(fail),
            "seconds": float(round(dt, 4)),
        }
        stats_path.write_text(json.dumps(stats_obj, ensure_ascii=False, indent=2), encoding="utf-8")

    print(
        "DONE: "
        f"{out_path} (rows={len(out_rows)}, llm_touched={touched}, ok={ok}, "
        f"fallback={fb}, skipped={skip}, failed={fail}, sec={dt:.2f})"
    )

    if cleanup_cache:
        try:
            if effective_cache_dir.exists():
                shutil.rmtree(effective_cache_dir)
                print(f"CACHE CLEANED: {effective_cache_dir}")
        except Exception as e:
            print(f"CACHE CLEAN FAILED: {effective_cache_dir} ({e.__class__.__name__})")


if __name__ == "__main__":
    main()
