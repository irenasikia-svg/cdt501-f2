"""Build summary tables, figures and the C2 failure file from results/runs/*.jsonl only."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

from f2agent.eval.metrics import summarize

CONDITION_ORDER = ["C0", "C1", "C2", "A1", "A2", "D"]
# Categorical slots 1-6 of the validated default palette (dataviz skill), fixed order.
COLORS = dict(zip(CONDITION_ORDER, ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4",
                                    "#008300"], strict=True))
GROUP_META = ["run_id", "split", "backend", "model_id", "condition", "temperature", "seed",
              "git_commit", "prompt_hash", "manifest_hash"]


def load_runs(runs_dir: Path) -> list[dict]:
    recs = []
    for p in sorted(runs_dir.glob("*.jsonl")):
        recs += [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line]
    return recs


def _groups(recs, keys):
    g = defaultdict(list)
    for r in recs:
        g[tuple(r[k] for k in keys)].append(r)
    return g


def _order(row):
    return (row["run_id"], row["split"], CONDITION_ORDER.index(row["condition"]))


def summary_rows(recs: list[dict]) -> list[dict]:
    rows = []
    for key, rs in _groups(recs, GROUP_META).items():
        stamp = max(r["timestamp"] for r in rs)
        rows.append(dict(zip(GROUP_META, key, strict=True)) | {"k_max": max(r["k"] for r in rs) + 1,
                    "timestamp": stamp} | summarize(rs))
    return sorted(rows, key=_order)


def family_rows(recs: list[dict]) -> list[dict]:
    keys = ["run_id", "split", "backend", "model_id", "condition", "family", "git_commit",
            "temperature", "seed", "prompt_hash", "manifest_hash"]
    rows = []
    for key, rs in _groups([r for r in recs if r["case_type"] == "attack"], keys).items():
        s = summarize(rs)
        rows.append(dict(zip(keys, key, strict=True)) | {
            "timestamp": max(r["timestamp"] for r in rs), "n_cases": s["n_attack_cases"],
            "ASR": s["ASR"], "ASR_lo": s["ASR_lo"], "ASR_hi": s["ASR_hi"], "UA": s["UA"]})
    return sorted(rows, key=lambda r: (*_order(r), r["family"]))


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        for r in rows:
            w.writerow({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()})


def failures_md(recs: list[dict]) -> str:
    fails = [r for r in recs if r["condition"] == "C2" and r["case_type"] == "attack"
             and r["attack_success"]]
    runs = sorted({(r["run_id"], r["git_commit"], r["manifest_hash"]) for r in recs})
    lines = ["# Attacks that succeeded under C2", "",
             f"Generated: {datetime.now(UTC).isoformat(timespec='seconds')} from "
             "`results/runs/*.jsonl` by `scripts/make_report.py`.", "",
             "| run_id | git_commit | manifest_hash |", "|---|---|---|",
             *[f"| {a} | {b} | {c} |" for a, b, c in runs], ""]
    if not fails:
        return "\n".join([*lines, "**None.** No attack succeeded under C2 in any run above.", ""])
    for r in fails:
        lines += [f"## {r['run_id']} · {r['case_id']} (k={r['k']})",
                  f"split={r['split']} family={r['family']} goal={r['goal']} "
                  f"model={r['model_id']}", "", "Audit log excerpt:", "```"]
        lines += [json.dumps({k: a[k] for k in ("step", "tool", "args", "decision", "rule_id")},
                             ensure_ascii=False)[:400] for a in r["audit"]]
        lines += ["```", ""]
    return "\n".join(lines)


def figures(rows: list[dict], fam: list[dict], out: Path) -> list[str]:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    made = []
    for (run_id, split), rs in _groups(rows, ["run_id", "split"]).items():
        fig, ax = plt.subplots(figsize=(5.2, 4.2), dpi=150)
        for r in rs:
            ax.scatter(r["BU"], r["ASR"], s=70, color=COLORS[r["condition"]], zorder=3,
                       edgecolor="white", linewidth=1.5)
            ax.annotate(f"{r['condition']}", (r["BU"], r["ASR"]), xytext=(6, 4),
                        textcoords="offset points", fontsize=9, color="#333333")
        ax.set(xlim=(-0.05, 1.08), ylim=(-0.05, 1.08), xlabel="Benign utility (BU) →",
               ylabel="Attack success rate (ASR) ↓")
        ax.set_title(f"ASR vs BU · {run_id} · {split}", fontsize=10, loc="left")
        ax.grid(color="#e6e6e3", linewidth=0.6)
        ax.spines[["top", "right"]].set_visible(False)
        name = f"asr_vs_bu__{run_id}__{split}.png"
        fig.tight_layout()
        fig.savefig(out / name)
        plt.close(fig)
        made.append(name)
    for run_id, rs in _groups(fam, ["run_id"]).items():
        fams = sorted({(r["split"], r["family"]) for r in rs})
        conds = [c for c in CONDITION_ORDER if any(r["condition"] == c for r in rs)]
        val = {(r["split"], r["family"], r["condition"]): r["ASR"] for r in rs}
        grid = [[val.get((s, f, c), float("nan")) for c in conds] for s, f in fams]
        fig, ax = plt.subplots(figsize=(1.0 + 0.8 * len(conds), 0.9 + 0.38 * len(fams)), dpi=150)
        ax.imshow(grid, cmap="Blues", vmin=0, vmax=1, aspect="auto")
        for i, row in enumerate(grid):
            for j, v in enumerate(row):
                ax.text(j, i, "–" if v != v else f"{v:.2f}", ha="center", va="center",
                        fontsize=8, color="white" if v == v and v > 0.6 else "#222222")
        ax.set_xticks(range(len(conds)), conds)
        ax.set_yticks(range(len(fams)), [f"{s} · {f}" for s, f in fams], fontsize=8)
        ax.set_title(f"ASR by attack family · {run_id}", fontsize=10, loc="left")
        name = f"asr_by_family__{run_id}.png"
        fig.tight_layout()
        fig.savefig(out / name)
        plt.close(fig)
        made.append(name)
    return made


def build_report(results: Path) -> dict:
    recs = load_runs(results / "runs")
    rows, fam = summary_rows(recs), family_rows(recs)
    write_csv(results / "summary.csv", rows)
    write_csv(results / "family_breakdown.csv", fam)
    (results / "failures_C2.md").write_text(failures_md(recs), encoding="utf-8")
    figdir = results / "figures"
    figdir.mkdir(exist_ok=True)
    for old in figdir.glob("*.png"):
        old.unlink()
    made = figures(rows, fam, figdir) if rows else []
    meta = {"generated": datetime.now(UTC).isoformat(timespec="seconds"),
            "source_runs": sorted({r["run_id"] for r in recs}),
            "git_commits": sorted({r["git_commit"] for r in recs}),
            "manifest_hashes": sorted({r["manifest_hash"] for r in recs}),
            "files": made}
    (figdir / "meta.json").write_text(json.dumps(meta, indent=1))
    return {"summary": rows, "families": fam}
