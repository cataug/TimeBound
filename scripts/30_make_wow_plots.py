import math
import textwrap
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.patches import Rectangle

ROOT = Path("/home/tahiti/TimeBound")
STATS = ROOT / "stats"
OUT = ROOT / "PLOTS_WOW"
OUT.mkdir(parents=True, exist_ok=True)

SUMMARY_CANDIDATES = [
    STATS / "suite82_summary_fixed.csv",
    STATS / "suite82_summary.csv",
]

SUMMARY_PATH = None
for p in SUMMARY_CANDIDATES:
    if p.exists():
        SUMMARY_PATH = p
        break

if SUMMARY_PATH is None:
    raise FileNotFoundError("Could not find suite82_summary_fixed.csv or suite82_summary.csv in stats/")

df = pd.read_csv(SUMMARY_PATH)

# -----------------------------------------------------------------------------
# Global style
# -----------------------------------------------------------------------------
plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 18,
    "axes.titlesize": 26,
    "axes.labelsize": 20,
    "xtick.labelsize": 16,
    "ytick.labelsize": 16,
    "legend.fontsize": 16,
    "figure.titlesize": 28,
    "axes.linewidth": 1.8,
    "grid.linewidth": 1.0,
    "grid.alpha": 0.25,
    "savefig.bbox": "tight",
})

BG = "#fbfbfd"
FG = "#222222"
GRID = "#cfd4dd"

PALETTE = {
    "semantic": "#5b8ff9",
    "recency": "#9b59b6",
    "semantic_recency": "#36cfc9",
    "chronological": "#95a5a6",
    "timebound": "#e74c3c",
    "oracle": "#f4b400",
    "full_history": "#34495e",
    "semantic_rag": "#5b8ff9",
    "recency_rag": "#9b59b6",
    "semantic_recency_rag": "#36cfc9",
    "timebound_rag": "#e74c3c",
    "oracle_evidence": "#f4b400",
}

MODEL_COLORS = {
    "qwen25_coder_1p5b": "#16a085",
    "qwen25_coder_7b": "#c0392b",
    "qwen25_7b": "#2980b9",
    "mistral_7b_v03": "#8e44ad",
}

TEXT_FX = [pe.withStroke(linewidth=3.5, foreground="white", alpha=0.95)]
BOX = dict(boxstyle="round,pad=0.35,rounding_size=0.18", fc="white", ec="#444", lw=1.4, alpha=0.95)
BOX_SOFT = dict(boxstyle="round,pad=0.35,rounding_size=0.18", fc="#f8f9fd", ec="#888", lw=1.1, alpha=0.95)

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def nice_model(x):
    m = {
        "qwen25_coder_1p5b": "Qwen2.5-Coder-1.5B",
        "qwen25_coder_7b": "Qwen2.5-Coder-7B",
        "qwen25_7b": "Qwen2.5-7B",
        "mistral_7b_v03": "Mistral-7B-v0.3",
    }
    return m.get(str(x), str(x))

def nice_regime(x):
    m = {
        "full_history": "Full History",
        "semantic_rag": "Semantic RAG",
        "recency_rag": "Recency RAG",
        "semantic_recency_rag": "Semantic+Recency",
        "timebound_rag": "TimeBound-RAG",
        "oracle_evidence": "Oracle Evidence",
        "query_only": "Query Only",
    }
    return m.get(str(x), str(x))

def nice_retriever(x):
    m = {
        "semantic": "Semantic",
        "recency": "Recency",
        "semantic_recency": "Semantic+Recency",
        "chronological": "Chronological",
        "timebound": "TimeBound",
        "oracle": "Oracle",
        "timebound_ablation": "TimeBound Ablation",
    }
    return m.get(str(x), str(x))

def nice_component(x):
    m = {
        "semantic": "Semantic only",
        "temporal": "Temporal only",
        "status": "Status only",
        "semantic+temporal": "Semantic + Temporal",
        "semantic+status": "Semantic + Status",
        "temporal+status": "Temporal + Status",
        "semantic+temporal+status": "Full TimeBound",
    }
    return m.get(str(x), str(x))

def nice_meta(x):
    m = {
        "": "Full metadata",
        "status": "No status",
        "valid_interval": "No valid interval",
        "event_time": "No event time",
        "observation_time": "No observation time",
        "relation_links": "No relation links",
        "query_time": "No query time",
    }
    return m.get(str(x), str(x))

def color_for_key(x):
    x = str(x)
    if x in PALETTE:
        return PALETTE[x]
    if x in MODEL_COLORS:
        return MODEL_COLORS[x]
    return "#4c78a8"

def ensure_numeric(frame, cols):
    for c in cols:
        if c in frame.columns:
            frame[c] = pd.to_numeric(frame[c], errors="coerce")
    return frame

def style_axes(ax, title, subtitle=None, xlabel=None, ylabel=None):
    ax.set_facecolor(BG)
    ax.grid(True, axis="x", color=GRID, linestyle="--", linewidth=1)
    for side in ["top", "right"]:
        ax.spines[side].set_visible(False)
    ax.spines["left"].set_color("#666")
    ax.spines["bottom"].set_color("#666")
    ax.tick_params(colors="#333")
    ax.set_title(title, loc="left", pad=18, color=FG, fontweight="bold")
    if subtitle:
        ax.text(
            0.0, 1.02, subtitle, transform=ax.transAxes,
            ha="left", va="bottom", fontsize=14, color="#555",
            bbox=dict(boxstyle="round,pad=0.25", fc="#f4f6fb", ec="#d0d5df", lw=0.8, alpha=0.9)
        )
    if xlabel:
        ax.set_xlabel(xlabel, color=FG)
    if ylabel:
        ax.set_ylabel(ylabel, color=FG)

def add_panel_tag(ax, tag):
    ax.text(
        -0.065, 1.08, tag, transform=ax.transAxes,
        ha="center", va="center", fontsize=18, fontweight="bold", color="white",
        bbox=dict(boxstyle="round,pad=0.35", fc="#20232a", ec="#20232a", lw=0)
    )

def save(fig, name):
    png = OUT / f"{name}.png"
    pdf = OUT / f"{name}.pdf"
    fig.savefig(png, dpi=300, facecolor="white")
    fig.savefig(pdf, dpi=300, facecolor="white")
    plt.close(fig)
    print("[OK]", png)
    print("[OK]", pdf)

def add_value_boxes_barh(ax, bars, values, fmt="{:.3f}", dx=0.01, text_color="#111", fc="white", ec="#444"):
    for b, v in zip(bars, values):
        y = b.get_y() + b.get_height() / 2
        x = b.get_width()
        ax.text(
            x + dx, y, fmt.format(v),
            va="center", ha="left", fontsize=14, color=text_color,
            bbox=dict(boxstyle="round,pad=0.25", fc=fc, ec=ec, lw=1.0, alpha=0.95),
            path_effects=TEXT_FX,
        )

def wrap(s, width=28):
    return "\n".join(textwrap.wrap(str(s), width=width))

# -----------------------------------------------------------------------------
# Figure 1: Main retrieval scoreboard
# -----------------------------------------------------------------------------
def fig_main_retrieval_scoreboard(df):
    sub = df[df["block"] == "A_main_retrieval"].copy()
    sub = ensure_numeric(sub, ["metric_evidence_f1", "metric_invalid_retrieval_rate", "metric_exact_evidence_hit"])
    sub = sub.sort_values("metric_evidence_f1", ascending=True)

    labels = [nice_retriever(x) for x in sub["retriever"]]
    vals = sub["metric_evidence_f1"].values
    invalid = sub["metric_invalid_retrieval_rate"].values
    colors = [color_for_key(x) for x in sub["retriever"]]

    fig, ax = plt.subplots(figsize=(15, 9))
    bars = ax.barh(labels, vals, color=colors, edgecolor="black", linewidth=1.2, zorder=3)

    # highlight TimeBound row
    for i, (lab, b) in enumerate(zip(labels, bars)):
        if "TimeBound" in lab:
            ax.axhspan(b.get_y()-0.08, b.get_y()+b.get_height()+0.08, color="#fdecea", alpha=0.8, zorder=0)

    style_axes(
        ax,
        "Main Retrieval-Only Scoreboard",
        subtitle="Higher is better on Evidence F1. Right-side badges show invalid retrieval rate ↓",
        xlabel="Evidence F1",
        ylabel=None
    )
    add_panel_tag(ax, "A")

    add_value_boxes_barh(ax, bars, vals, fmt="{:.3f}", dx=0.012, fc="#ffffff", ec="#444")

    xmax = max(vals) * 1.42 if len(vals) else 1.0
    ax.set_xlim(0, xmax)

    for b, inv in zip(bars, invalid):
        y = b.get_y() + b.get_height()/2
        ax.text(
            xmax*0.84, y, f"invalid {inv:.3f}",
            ha="left", va="center", fontsize=13, color="#7b241c",
            bbox=dict(boxstyle="round,pad=0.25", fc="#fff2f0", ec="#e74c3c", lw=1.1, alpha=0.98)
        )

    ax.text(
        0.99, 0.03,
        "Semantic reaches the highest evidence F1,\n"
        "but TimeBound retrieves far fewer invalid memories.",
        transform=ax.transAxes, ha="right", va="bottom", fontsize=14, color="#333",
        bbox=BOX_SOFT
    )

    save(fig, "01_main_retrieval_scoreboard")

# -----------------------------------------------------------------------------
# Figure 2: Retrieval trade-off scatter
# -----------------------------------------------------------------------------
def fig_retrieval_tradeoff(df):
    sub = df[df["block"] == "A_main_retrieval"].copy()
    sub = ensure_numeric(sub, ["metric_evidence_f1", "metric_invalid_retrieval_rate", "metric_retrieved_chars"])

    fig, ax = plt.subplots(figsize=(12.5, 9))
    style_axes(
        ax,
        "Retrieval Trade-off: Evidence Quality vs Invalid Memories",
        subtitle="Upper-left is best: high evidence F1 and low invalid retrieval rate",
        xlabel="Invalid retrieval rate ↓",
        ylabel="Evidence F1 ↑"
    )
    add_panel_tag(ax, "B")

    sizes = 200 + 0.12 * sub["metric_retrieved_chars"].fillna(0).values
    for _, r in sub.iterrows():
        x = r["metric_invalid_retrieval_rate"]
        y = r["metric_evidence_f1"]
        label = nice_retriever(r["retriever"])
        c = color_for_key(r["retriever"])
        s = 200 + 0.12 * float(r.get("metric_retrieved_chars", 0))
        ax.scatter([x], [y], s=s, color=c, edgecolor="black", linewidth=1.3, zorder=4)
        ax.text(
            x + 0.008, y + 0.006, label,
            fontsize=14, ha="left", va="bottom",
            bbox=dict(boxstyle="round,pad=0.22", fc="white", ec=c, lw=1.2, alpha=0.97),
            path_effects=TEXT_FX
        )

    ax.axvline(sub["metric_invalid_retrieval_rate"].mean(), color="#999", linestyle="--", linewidth=1.3)
    ax.axhline(sub["metric_evidence_f1"].mean(), color="#999", linestyle="--", linewidth=1.3)
    ax.set_xlim(-0.02, max(0.45, sub["metric_invalid_retrieval_rate"].max() + 0.08))
    ax.set_ylim(0, 1.05)

    ax.text(
        0.02, 0.03,
        "TimeBound moves leftward strongly (fewer stale/invalid memories)\n"
        "while keeping evidence quality competitive.",
        transform=ax.transAxes, ha="left", va="bottom", fontsize=14, bbox=BOX_SOFT
    )
    save(fig, "02_retrieval_tradeoff_scatter")

# -----------------------------------------------------------------------------
# Figure 3: Top-k sensitivity
# -----------------------------------------------------------------------------
def fig_topk_sensitivity(df):
    sub = df[(df["block"] == "B_retrieval_ablations") & (df["ablation_group"] == "topk_sensitivity")].copy()
    sub = ensure_numeric(sub, ["top_k", "metric_evidence_f1", "metric_invalid_retrieval_rate", "metric_exact_evidence_hit"])
    sub = sub.sort_values("top_k")

    fig, ax = plt.subplots(figsize=(13, 8))
    style_axes(
        ax,
        "Top-k Sensitivity for TimeBound Retrieval",
        subtitle="Evidence F1 peaks at k=1; adding more retrieved turns introduces noise",
        xlabel="Top-k",
        ylabel="Evidence F1"
    )
    add_panel_tag(ax, "C")

    x = sub["top_k"].values
    y = sub["metric_evidence_f1"].values
    ax.plot(x, y, marker="o", markersize=12, linewidth=3.5, color="#e74c3c", zorder=4)

    for xx, yy in zip(x, y):
        ax.text(
            xx, yy + 0.022, f"{yy:.3f}",
            ha="center", va="bottom", fontsize=14,
            bbox=dict(boxstyle="round,pad=0.22", fc="white", ec="#e74c3c", lw=1.1, alpha=0.98)
        )

    ax2 = ax.twinx()
    ax2.set_ylabel("Invalid retrieval rate", color="#7b241c", fontsize=18)
    ax2.plot(
        x, sub["metric_invalid_retrieval_rate"].values,
        marker="s", markersize=10, linewidth=3.0, color="#8e44ad", linestyle="--", zorder=3
    )
    ax2.tick_params(axis="y", colors="#7b241c")
    ax2.grid(False)

    for xx, yy in zip(x, sub["metric_invalid_retrieval_rate"].values):
        ax2.text(
            xx, yy + 0.01, f"{yy:.3f}",
            ha="center", va="bottom", fontsize=13,
            bbox=dict(boxstyle="round,pad=0.20", fc="#faf5ff", ec="#8e44ad", lw=1.0, alpha=0.97)
        )

    ax.set_xticks(x)
    ax.set_ylim(0, 0.85)
    ax2.set_ylim(0, max(0.20, sub["metric_invalid_retrieval_rate"].max() + 0.05))

    best_row = sub.loc[sub["metric_evidence_f1"].idxmax()]
    ax.text(
        0.98, 0.05,
        f"Best setting: k={int(best_row['top_k'])}\n"
        f"F1={best_row['metric_evidence_f1']:.3f}, invalid={best_row['metric_invalid_retrieval_rate']:.3f}",
        transform=ax.transAxes, ha="right", va="bottom", fontsize=14, bbox=BOX
    )

    save(fig, "03_topk_sensitivity_timebound")

# -----------------------------------------------------------------------------
# Figure 4: Main LLM heatmap
# -----------------------------------------------------------------------------
def fig_main_llm_heatmap(df):
    sub = df[df["block"] == "C_main_llm_timebound"].copy()
    sub = ensure_numeric(sub, ["metric_relaxed_accuracy"])
    order_models = ["mistral_7b_v03", "qwen25_7b", "qwen25_coder_1p5b", "qwen25_coder_7b"]
    order_regimes = ["full_history", "semantic_rag", "recency_rag", "semantic_recency_rag", "timebound_rag", "oracle_evidence"]

    pivot = sub.pivot_table(index="model_key", columns="regime", values="metric_relaxed_accuracy", aggfunc="mean")
    pivot = pivot.reindex(index=order_models, columns=order_regimes)

    fig, ax = plt.subplots(figsize=(16, 8.5))
    ax.set_facecolor(BG)

    mat = ax.imshow(pivot.values, aspect="auto", cmap="YlOrRd", vmin=0, vmax=1)

    ax.set_xticks(np.arange(len(order_regimes)))
    ax.set_xticklabels([nice_regime(x) for x in order_regimes], rotation=25, ha="right")
    ax.set_yticks(np.arange(len(order_models)))
    ax.set_yticklabels([nice_model(x) for x in order_models])

    ax.set_title(
        "Main LLM Result Matrix on TimeBound-Long",
        loc="left", pad=18, color=FG, fontweight="bold"
    )
    ax.text(
        0.0, 1.02,
        "Cell values are relaxed accuracy. TimeBound-RAG should dominate its row if temporal filtering helps.",
        transform=ax.transAxes, ha="left", va="bottom", fontsize=14, color="#555",
        bbox=dict(boxstyle="round,pad=0.25", fc="#f4f6fb", ec="#d0d5df", lw=0.8, alpha=0.9)
    )
    add_panel_tag(ax, "D")

    for i in range(pivot.shape[0]):
        for j in range(pivot.shape[1]):
            val = pivot.iloc[i, j]
            if pd.isna(val):
                continue
            txt_color = "black" if val < 0.55 else "white"
            ax.text(
                j, i, f"{val:.3f}",
                ha="center", va="center", fontsize=16, fontweight="bold",
                color=txt_color,
                bbox=dict(
                    boxstyle="round,pad=0.18",
                    fc=(1, 1, 1, 0.35) if txt_color == "black" else (0, 0, 0, 0.18),
                    ec=(0, 0, 0, 0.10), lw=0.8
                )
            )

    cbar = fig.colorbar(mat, ax=ax, pad=0.015)
    cbar.set_label("Relaxed accuracy", fontsize=18)

    # highlight TimeBound column
    tb_col = order_regimes.index("timebound_rag")
    ax.add_patch(Rectangle((tb_col - 0.5, -0.5), 1.0, len(order_models), fill=False, ec="#2c3e50", lw=3.0))

    save(fig, "04_main_llm_heatmap")

# -----------------------------------------------------------------------------
# Figure 5: TimeBound vs Semantic dumbbell
# -----------------------------------------------------------------------------
def fig_timebound_gain_dumbbell(df):
    sub = df[df["block"] == "C_main_llm_timebound"].copy()
    sub = ensure_numeric(sub, ["metric_relaxed_accuracy"])

    rows = []
    for model in sorted(sub["model_key"].dropna().unique()):
        sem = sub[(sub["model_key"] == model) & (sub["regime"] == "semantic_rag")]
        tb = sub[(sub["model_key"] == model) & (sub["regime"] == "timebound_rag")]
        if len(sem) and len(tb):
            semv = float(sem["metric_relaxed_accuracy"].iloc[0])
            tbv = float(tb["metric_relaxed_accuracy"].iloc[0])
            rows.append({
                "model": model,
                "semantic": semv,
                "timebound": tbv,
                "gain": tbv - semv,
            })

    sub2 = pd.DataFrame(rows).sort_values("gain", ascending=True)

    fig, ax = plt.subplots(figsize=(14, 8))
    style_axes(
        ax,
        "Per-Model Gain: TimeBound-RAG vs Semantic RAG",
        subtitle="Rightward shift indicates a downstream accuracy gain from temporal filtering",
        xlabel="Relaxed accuracy",
        ylabel=None
    )
    add_panel_tag(ax, "E")

    y = np.arange(len(sub2))
    for i, r in enumerate(sub2.itertuples(index=False)):
        ax.plot([r.semantic, r.timebound], [i, i], color="#555", linewidth=3, zorder=2)
        ax.scatter([r.semantic], [i], s=230, color=PALETTE["semantic_rag"], edgecolor="black", linewidth=1.1, zorder=4)
        ax.scatter([r.timebound], [i], s=260, color=PALETTE["timebound_rag"], edgecolor="black", linewidth=1.3, zorder=5)
        ax.text(
            r.timebound + 0.012, i, f"+{r.gain:.3f}",
            ha="left", va="center", fontsize=14,
            bbox=dict(boxstyle="round,pad=0.22", fc="#fff2f0", ec="#e74c3c", lw=1.0, alpha=0.98)
        )

    ax.set_yticks(y)
    ax.set_yticklabels([nice_model(x) for x in sub2["model"]])
    ax.set_xlim(0, max(0.9, sub2["timebound"].max() + 0.11))
    ax.legend(
        handles=[
            plt.Line2D([0], [0], marker="o", color="w", markerfacecolor=PALETTE["semantic_rag"], markeredgecolor="black", markersize=10, label="Semantic RAG"),
            plt.Line2D([0], [0], marker="o", color="w", markerfacecolor=PALETTE["timebound_rag"], markeredgecolor="black", markersize=10, label="TimeBound-RAG"),
        ],
        loc="lower right", frameon=True
    )

    mean_gain = sub2["gain"].mean()
    ax.text(
        0.98, 0.05, f"Mean gain: +{mean_gain:.3f}",
        transform=ax.transAxes, ha="right", va="bottom", fontsize=15, bbox=BOX
    )
    save(fig, "05_timebound_vs_semantic_gain")

# -----------------------------------------------------------------------------
# Figure 6: Main LLM leaderboard
# -----------------------------------------------------------------------------
def fig_main_llm_leaderboard(df):
    sub = df[df["block"] == "C_main_llm_timebound"].copy()
    sub = ensure_numeric(sub, ["metric_relaxed_accuracy", "metric_contradiction"])
    sub["label"] = sub["model_key"].map(nice_model) + " | " + sub["regime"].map(nice_regime)
    sub = sub.sort_values("metric_relaxed_accuracy", ascending=True).tail(12)

    fig, ax = plt.subplots(figsize=(16, 10))
    colors = [MODEL_COLORS.get(x, "#4c78a8") for x in sub["model_key"]]
    bars = ax.barh(sub["label"], sub["metric_relaxed_accuracy"], color=colors, edgecolor="black", linewidth=1.2)

    style_axes(
        ax,
        "Top Main LLM Runs",
        subtitle="Ranked by relaxed accuracy. Badges show contradiction rate ↓",
        xlabel="Relaxed accuracy",
        ylabel=None
    )
    add_panel_tag(ax, "F")

    add_value_boxes_barh(ax, bars, sub["metric_relaxed_accuracy"].values, fmt="{:.3f}", dx=0.012)

    xmax = max(sub["metric_relaxed_accuracy"].max() + 0.18, 0.95)
    ax.set_xlim(0, xmax)

    for b, ctr in zip(bars, sub["metric_contradiction"].values):
        y = b.get_y() + b.get_height()/2
        ax.text(
            xmax*0.83, y, f"ctr {ctr:.3f}",
            ha="left", va="center", fontsize=13,
            bbox=dict(boxstyle="round,pad=0.22", fc="#eef7ff", ec="#5b8ff9", lw=1.0, alpha=0.98)
        )

    save(fig, "06_main_llm_leaderboard")

# -----------------------------------------------------------------------------
# Figure 7: Score-component ablation
# -----------------------------------------------------------------------------
def fig_score_component_ablation(df):
    sub = df[(df["block"] == "B_retrieval_ablations") & (df["ablation_group"] == "score_components")].copy()
    sub = ensure_numeric(sub, ["metric_evidence_f1", "metric_invalid_retrieval_rate"])
    sub["comp_label"] = sub["components"].map(nice_component)
    sub = sub.sort_values("metric_evidence_f1", ascending=True)

    fig, ax = plt.subplots(figsize=(14, 9))
    colors = ["#bdc3c7" if "Full" not in lab else "#e74c3c" for lab in sub["comp_label"]]
    bars = ax.barh(sub["comp_label"], sub["metric_evidence_f1"], color=colors, edgecolor="black", linewidth=1.2)

    style_axes(
        ax,
        "TimeBound Score-Component Ablation",
        subtitle="Which ingredients matter most for evidence retrieval quality?",
        xlabel="Evidence F1",
        ylabel=None
    )
    add_panel_tag(ax, "G")
    add_value_boxes_barh(ax, bars, sub["metric_evidence_f1"].values, fmt="{:.3f}", dx=0.012)

    xmax = max(sub["metric_evidence_f1"].max() + 0.18, 0.85)
    ax.set_xlim(0, xmax)

    for b, inv in zip(bars, sub["metric_invalid_retrieval_rate"].values):
        y = b.get_y() + b.get_height()/2
        ax.text(
            xmax*0.82, y, f"invalid {inv:.3f}",
            ha="left", va="center", fontsize=13,
            bbox=dict(boxstyle="round,pad=0.22", fc="#fff2f0", ec="#e74c3c", lw=1.0, alpha=0.96)
        )
    save(fig, "07_score_component_ablation")

# -----------------------------------------------------------------------------
# Figure 8: Metadata ablation
# -----------------------------------------------------------------------------
def fig_metadata_ablation(df):
    sub = df[(df["block"] == "B_retrieval_ablations") & (df["ablation_group"] == "metadata_removal")].copy()
    sub = ensure_numeric(sub, ["metric_evidence_f1", "metric_invalid_retrieval_rate"])
    sub["meta_label"] = sub["disabled_metadata"].fillna("").map(nice_meta)
    sub = sub.sort_values("metric_evidence_f1", ascending=True)

    fig, ax = plt.subplots(figsize=(14, 9))
    colors = ["#d0d7de" if lab != "Full metadata" else "#2ecc71" for lab in sub["meta_label"]]
    bars = ax.barh(sub["meta_label"], sub["metric_evidence_f1"], color=colors, edgecolor="black", linewidth=1.2)

    style_axes(
        ax,
        "Metadata Removal Ablation",
        subtitle="Removing temporal fields should hurt if the benchmark really depends on temporal grounding",
        xlabel="Evidence F1",
        ylabel=None
    )
    add_panel_tag(ax, "H")
    add_value_boxes_barh(ax, bars, sub["metric_evidence_f1"].values, fmt="{:.3f}", dx=0.012)

    xmax = max(sub["metric_evidence_f1"].max() + 0.18, 0.85)
    ax.set_xlim(0, xmax)

    for b, inv in zip(bars, sub["metric_invalid_retrieval_rate"].values):
        y = b.get_y() + b.get_height()/2
        ax.text(
            xmax*0.82, y, f"invalid {inv:.3f}",
            ha="left", va="center", fontsize=13,
            bbox=dict(boxstyle="round,pad=0.22", fc="#eefbf3", ec="#2ecc71", lw=1.0, alpha=0.96)
        )

    save(fig, "08_metadata_ablation")

# -----------------------------------------------------------------------------
# Figure 9: External diagnostics heatmap
# -----------------------------------------------------------------------------
def fig_external_heatmap(df):
    sub = df[(df["block"] == "D_external_diagnostics") & (df["run_type"] == "llm")].copy()
    sub = ensure_numeric(sub, ["metric_relaxed_accuracy"])

    # best relaxed acc per dataset/model across regimes
    best = (
        sub.groupby(["dataset_key", "model_key"], as_index=False)["metric_relaxed_accuracy"]
        .max()
    )
    dataset_order = ["tempreason", "complextr", "tcp", "locomo"]
    model_order = ["mistral_7b_v03", "qwen25_7b", "qwen25_coder_1p5b", "qwen25_coder_7b"]
    pivot = best.pivot_table(index="dataset_key", columns="model_key", values="metric_relaxed_accuracy", aggfunc="max")
    pivot = pivot.reindex(index=dataset_order, columns=model_order)

    fig, ax = plt.subplots(figsize=(12, 8))
    ax.set_facecolor(BG)

    mat = ax.imshow(pivot.values, aspect="auto", cmap="PuBuGn", vmin=0, vmax=max(0.2, np.nanmax(pivot.values)))

    ax.set_xticks(np.arange(len(model_order)))
    ax.set_xticklabels([nice_model(x) for x in model_order], rotation=20, ha="right")
    ax.set_yticks(np.arange(len(dataset_order)))
    ax.set_yticklabels([x.upper() if x == "tcp" else x for x in dataset_order])

    ax.set_title(
        "External Diagnostic Coverage",
        loc="left", pad=18, color=FG, fontweight="bold"
    )
    ax.text(
        0.0, 1.02,
        "Best relaxed accuracy per dataset/model across diagnostic regimes. Use as robustness probes, not leaderboard claims.",
        transform=ax.transAxes, ha="left", va="bottom", fontsize=13.5, color="#555",
        bbox=dict(boxstyle="round,pad=0.25", fc="#f4f6fb", ec="#d0d5df", lw=0.8, alpha=0.9)
    )
    add_panel_tag(ax, "I")

    for i in range(pivot.shape[0]):
        for j in range(pivot.shape[1]):
            val = pivot.iloc[i, j]
            if pd.isna(val):
                continue
            txt_color = "black" if val < 0.11 else "white"
            ax.text(
                j, i, f"{val:.3f}",
                ha="center", va="center", fontsize=15, fontweight="bold",
                color=txt_color,
                bbox=dict(boxstyle="round,pad=0.18", fc=(1,1,1,0.25) if txt_color=="black" else (0,0,0,0.18), ec="none")
            )

    cbar = fig.colorbar(mat, ax=ax, pad=0.015)
    cbar.set_label("Best relaxed accuracy", fontsize=16)
    save(fig, "09_external_diagnostics_heatmap")

# -----------------------------------------------------------------------------
# Figure 10: Compact context vs accuracy
# -----------------------------------------------------------------------------
def fig_context_vs_accuracy(df):
    sub = df[df["block"] == "C_main_llm_timebound"].copy()
    sub = ensure_numeric(sub, ["metric_relaxed_accuracy", "metric_retrieved_chars", "metric_contradiction"])

    # Aggregate by regime across models
    ag = sub.groupby("regime", as_index=False).agg({
        "metric_relaxed_accuracy": "mean",
        "metric_retrieved_chars": "mean",
        "metric_contradiction": "mean",
    })

    fig, ax = plt.subplots(figsize=(13, 9))
    style_axes(
        ax,
        "Compact Context vs Downstream Accuracy",
        subtitle="Bubble size reflects average contradiction rate. TimeBound aims for strong answers with compact evidence.",
        xlabel="Average retrieved context (chars)",
        ylabel="Mean relaxed accuracy"
    )
    add_panel_tag(ax, "J")

    for _, r in ag.iterrows():
        regime = r["regime"]
        x = r["metric_retrieved_chars"]
        y = r["metric_relaxed_accuracy"]
        s = 1200 * (0.15 + float(r["metric_contradiction"]))
        c = color_for_key(regime)
        ax.scatter([x], [y], s=s, color=c, edgecolor="black", linewidth=1.3, alpha=0.92)
        ax.text(
            x + 15, y + 0.006, nice_regime(regime),
            ha="left", va="bottom", fontsize=14,
            bbox=dict(boxstyle="round,pad=0.22", fc="white", ec=c, lw=1.1, alpha=0.97)
        )

    ax.set_ylim(0, 0.95)
    ax.set_xlim(0, max(1600, ag["metric_retrieved_chars"].max() + 180))
    save(fig, "10_context_vs_accuracy")

# -----------------------------------------------------------------------------
# Small markdown manifest
# -----------------------------------------------------------------------------
def write_manifest():
    md = OUT / "README_PLOTS.md"
    lines = [
        "# TimeBound WOW Plots",
        "",
        f"Source summary: `{SUMMARY_PATH}`",
        "",
        "Generated figures:",
        "",
        "1. `01_main_retrieval_scoreboard`",
        "2. `02_retrieval_tradeoff_scatter`",
        "3. `03_topk_sensitivity_timebound`",
        "4. `04_main_llm_heatmap`",
        "5. `05_timebound_vs_semantic_gain`",
        "6. `06_main_llm_leaderboard`",
        "7. `07_score_component_ablation`",
        "8. `08_metadata_ablation`",
        "9. `09_external_diagnostics_heatmap`",
        "10. `10_context_vs_accuracy`",
        "",
    ]
    md.write_text("\n".join(lines), encoding="utf-8")
    print("[OK]", md)

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
def main():
    required_cols = ["block"]
    for c in required_cols:
        if c not in df.columns:
            raise ValueError(f"Missing required column in summary: {c}")

    fig_main_retrieval_scoreboard(df)
    fig_retrieval_tradeoff(df)
    fig_topk_sensitivity(df)
    fig_main_llm_heatmap(df)
    fig_timebound_gain_dumbbell(df)
    fig_main_llm_leaderboard(df)
    fig_score_component_ablation(df)
    fig_metadata_ablation(df)
    fig_external_heatmap(df)
    fig_context_vs_accuracy(df)
    write_manifest()

    print("\n[DONE] WOW plots saved to:", OUT)

if __name__ == "__main__":
    main()
