import json
import re
import textwrap
from pathlib import Path
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle, FancyArrowPatch
import matplotlib.patheffects as pe

ROOT = Path("/home/tahiti/TimeBound")
OUT = ROOT / "PLOTS_QUALITATIVE"
OUT.mkdir(parents=True, exist_ok=True)

DATASET = ROOT / "synthetic" / "timebound_long.jsonl"
SUITE = ROOT / "outputs" / "suite82"

MAIN_MODEL = "qwen25_coder_7b"

MODEL_ORDER = [
    "qwen25_coder_1p5b",
    "qwen25_coder_7b",
    "qwen25_7b",
    "mistral_7b_v03",
]

MODEL_NICE = {
    "qwen25_coder_1p5b": "Qwen2.5-Coder-1.5B",
    "qwen25_coder_7b": "Qwen2.5-Coder-7B",
    "qwen25_7b": "Qwen2.5-7B",
    "mistral_7b_v03": "Mistral-7B-v0.3",
}

REGIME_NICE = {
    "semantic_rag": "Semantic RAG",
    "timebound_rag": "TimeBound-RAG",
    "full_history": "Full History",
    "oracle_evidence": "Oracle Evidence",
}

STATUS_COLORS = {
    "active": "#d5f5e3",
    "scheduled": "#eaf2f8",
    "superseded": "#fdebd0",
    "expired": "#eeeeee",
    "cancelled": "#fadbd8",
    "canceled": "#fadbd8",
    "delayed": "#fcf3cf",
    "unknown": "#f4f6f7",
}

STATUS_EDGES = {
    "active": "#27ae60",
    "scheduled": "#3498db",
    "superseded": "#e67e22",
    "expired": "#7f8c8d",
    "cancelled": "#c0392b",
    "canceled": "#c0392b",
    "delayed": "#f1c40f",
    "unknown": "#95a5a6",
}

PAL = {
    "semantic": "#5b8ff9",
    "timebound": "#e74c3c",
    "gold": "#f4b400",
    "ok": "#27ae60",
    "bad": "#c0392b",
    "soft": "#f7f9fc",
    "ink": "#1f2933",
    "muted": "#566573",
    "border": "#2c3e50",
}

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 16,
    "axes.titlesize": 24,
    "figure.titlesize": 26,
    "savefig.bbox": "tight",
})

FX = [pe.withStroke(linewidth=3.2, foreground="white", alpha=0.95)]


# -----------------------------------------------------------------------------
# IO
# -----------------------------------------------------------------------------
def read_jsonl(path):
    rows = []
    path = Path(path)
    if not path.exists():
        print("[MISS]", path)
        return rows
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            s = line.strip()
            if s:
                rows.append(json.loads(s))
    return rows


def index_by_id(rows):
    return {r.get("id"): r for r in rows if r.get("id")}


def run_path(model, regime):
    return SUITE / f"C_llm_timebound_{model}_{regime}" / "predictions.jsonl"


def load_preds(model, regime):
    return index_by_id(read_jsonl(run_path(model, regime)))


def load_dataset():
    return index_by_id(read_jsonl(DATASET))


# -----------------------------------------------------------------------------
# Text utilities
# -----------------------------------------------------------------------------
def norm(s):
    s = str(s or "").lower()
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"[^a-z0-9а-яё ,:;./\\-+]+", "", s)
    return s.strip(" .,:;")


def shorten(s, n=260):
    s = str(s or "")
    s = re.sub(r"\s+", " ", s).strip()
    if len(s) <= n:
        return s
    return s[: n - 1].rstrip() + "…"


def wrap(s, width=68):
    return "\n".join(textwrap.wrap(str(s), width=width))


def get_turn_map(ex):
    return {ev.get("turn_id"): ev for ev in ex.get("history", [])}


def selected_events(ex, pred):
    tmap = get_turn_map(ex)
    return [tmap[t] for t in pred.get("retrieved_turns", []) if t in tmap]


def answer_ok(pred):
    try:
        return int(pred.get("relaxed_accuracy", 0)) == 1
    except Exception:
        return False


def is_invalid_event(ev):
    return str(ev.get("status", "")).lower() in {"superseded", "expired", "cancelled", "canceled"}


def event_line(ev):
    tid = ev.get("turn_id")
    st = ev.get("status", "unknown")
    obs = ev.get("observation_time", "")
    evt = ev.get("event_time", "")
    valid = f"{ev.get('valid_from', '')}..{ev.get('valid_to', '')}"
    txt = shorten(ev.get("text", ""), 190)
    return f"[{tid}] status={st} | obs={obs} | event={evt} | valid={valid}\n{txt}"


# -----------------------------------------------------------------------------
# Drawing primitives
# -----------------------------------------------------------------------------
def add_round_box(ax, x, y, w, h, fc="#ffffff", ec="#333333", lw=1.4, radius=0.025, alpha=1.0):
    patch = FancyBboxPatch(
        (x, y), w, h,
        boxstyle=f"round,pad=0.012,rounding_size={radius}",
        facecolor=fc,
        edgecolor=ec,
        linewidth=lw,
        alpha=alpha,
        transform=ax.transAxes,
        clip_on=False,
    )
    ax.add_patch(patch)
    return patch


def add_label(ax, x, y, text, fc="#ffffff", ec="#333333", color="#111111", size=14, weight="bold", ha="left"):
    ax.text(
        x, y, text,
        transform=ax.transAxes,
        ha=ha,
        va="center",
        fontsize=size,
        fontweight=weight,
        color=color,
        bbox=dict(boxstyle="round,pad=0.28", fc=fc, ec=ec, lw=1.1, alpha=0.98),
        path_effects=FX,
    )


def add_text(ax, x, y, text, size=13, color="#111111", ha="left", va="top", weight=None, width=None):
    if width:
        text = wrap(text, width)
    ax.text(
        x, y, text,
        transform=ax.transAxes,
        ha=ha,
        va=va,
        fontsize=size,
        color=color,
        fontweight=weight,
        linespacing=1.28,
    )


def add_event_card(ax, x, y, w, h, ev, is_gold=False, is_selected=False):
    status = str(ev.get("status", "unknown")).lower()
    fc = STATUS_COLORS.get(status, STATUS_COLORS["unknown"])
    ec = STATUS_EDGES.get(status, STATUS_EDGES["unknown"])

    if is_gold:
        ec = PAL["gold"]
        lw = 3.0
    elif is_selected:
        lw = 2.1
    else:
        lw = 1.2

    add_round_box(ax, x, y, w, h, fc=fc, ec=ec, lw=lw, radius=0.018)

    tid = ev.get("turn_id")
    st = ev.get("status", "unknown")
    obs = ev.get("observation_time", "")
    evt = ev.get("event_time", "")
    txt = shorten(ev.get("text", ""), 155)

    badge = f"T{tid} · {st}"
    add_label(ax, x + 0.012, y + h - 0.036, badge, fc="#ffffff", ec=ec, size=10.5)

    if is_gold:
        add_label(ax, x + w - 0.115, y + h - 0.036, "GOLD", fc="#fff8dc", ec=PAL["gold"], size=10.5, ha="left")

    add_text(ax, x + 0.014, y + h - 0.076, f"obs: {obs}\nevent: {evt}", size=9.8, color="#34495e")
    add_text(ax, x + 0.014, y + h - 0.148, txt, size=10.8, color="#111111", width=34)


def answer_badge(ax, x, y, label, pred, ok):
    fc = "#eafaf1" if ok else "#fdecea"
    ec = PAL["ok"] if ok else PAL["bad"]
    icon = "✓" if ok else "✗"
    add_round_box(ax, x, y, 0.40, 0.085, fc=fc, ec=ec, lw=1.6, radius=0.018)
    add_text(ax, x + 0.012, y + 0.063, f"{icon} {label}", size=12, color=ec, weight="bold")
    add_text(ax, x + 0.012, y + 0.036, shorten(pred, 88), size=10.5, color="#111111")


def big_title(fig, title, subtitle=None):
    fig.text(0.035, 0.965, title, fontsize=27, fontweight="bold", color=PAL["ink"], ha="left", va="top")
    if subtitle:
        fig.text(
            0.035, 0.925, subtitle,
            fontsize=14.5,
            color=PAL["muted"],
            ha="left",
            va="top",
            bbox=dict(boxstyle="round,pad=0.25", fc="#f4f6fb", ec="#d0d5df", lw=0.8, alpha=0.95),
        )


def save(fig, name):
    png = OUT / f"{name}.png"
    pdf = OUT / f"{name}.pdf"
    fig.savefig(png, dpi=300, facecolor="white")
    fig.savefig(pdf, dpi=300, facecolor="white")
    plt.close(fig)
    print("[OK]", png)
    print("[OK]", pdf)


# -----------------------------------------------------------------------------
# Case selection
# -----------------------------------------------------------------------------
def pick_semantic_fail_timebound_win(dataset, sem, tb, n=4):
    cases = []
    for ex_id, ex in dataset.items():
        if ex_id not in sem or ex_id not in tb:
            continue

        s = sem[ex_id]
        t = tb[ex_id]

        if answer_ok(t) and not answer_ok(s):
            sev = selected_events(ex, s)
            tev = selected_events(ex, t)
            s_invalid = sum(is_invalid_event(ev) for ev in sev)
            t_invalid = sum(is_invalid_event(ev) for ev in tev)

            score = 0
            score += 10 * s_invalid
            score += 5 * int(t_invalid < s_invalid)
            score += 2 * int(ex.get("task_type") in {"conflicting_updates", "rescheduling", "cancellation", "time_window_retrieval"})
            score += int(len(str(t.get("prediction", ""))) < 80)

            cases.append((score, ex_id))

    cases = sorted(cases, reverse=True)
    return [ex_id for _, ex_id in cases[:n]]


def pick_full_history_fail_timebound_win(dataset, full, tb, n=3):
    cases = []
    for ex_id, ex in dataset.items():
        if ex_id not in full or ex_id not in tb:
            continue

        f = full[ex_id]
        t = tb[ex_id]

        if answer_ok(t) and not answer_ok(f):
            cases.append((ex.get("task_type", ""), ex_id))

    preferred = []
    for task in ["conflicting_updates", "cancellation", "aging_facts", "time_window_retrieval", "rescheduling"]:
        for task_name, ex_id in cases:
            if task_name == task and ex_id not in preferred:
                preferred.append(ex_id)
            if len(preferred) >= n:
                return preferred

    return preferred[:n]


def pick_timebound_failure(dataset, tb, n=3):
    cases = []
    for ex_id, ex in dataset.items():
        if ex_id not in tb:
            continue
        t = tb[ex_id]
        if not answer_ok(t):
            tev = selected_events(ex, t)
            gold = set(ex.get("gold_evidence_turns", []))
            ret = set(t.get("retrieved_turns", []))
            hit = len(gold & ret)
            cases.append((hit, ex.get("task_type", ""), ex_id))
    cases = sorted(cases)
    return [ex_id for _, _, ex_id in cases[:n]]


def pick_timeline_case(dataset, sem, tb):
    preferred_tasks = ["conflicting_updates", "rescheduling", "time_window_retrieval", "cancellation"]
    for task in preferred_tasks:
        for ex_id, ex in dataset.items():
            if ex.get("task_type") != task:
                continue
            if ex_id in sem and ex_id in tb and answer_ok(tb[ex_id]):
                return ex_id
    return next(iter(dataset.keys()))


# -----------------------------------------------------------------------------
# Figure 1: Semantic fail vs TimeBound win case cards
# -----------------------------------------------------------------------------
def fig_semantic_vs_timebound_cases(dataset, sem, tb):
    case_ids = pick_semantic_fail_timebound_win(dataset, sem, tb, n=4)
    if not case_ids:
        case_ids = list(dataset.keys())[:4]

    fig = plt.figure(figsize=(18, 22))
    big_title(
        fig,
        "Qualitative Cases: Semantic RAG Fails, TimeBound-RAG Recovers",
        "Each row shows the question, gold answer, retrieved memories, and final model outputs."
    )

    for idx, ex_id in enumerate(case_ids):
        ax = fig.add_axes([0.035, 0.74 - idx * 0.225, 0.93, 0.195])
        ax.set_axis_off()

        ex = dataset[ex_id]
        s = sem[ex_id]
        t = tb[ex_id]

        add_round_box(ax, 0.0, 0.0, 1.0, 1.0, fc="#ffffff", ec="#2c3e50", lw=1.7, radius=0.022)

        task = ex.get("task_type", "unknown")
        add_label(ax, 0.015, 0.92, f"CASE {idx+1}: {task}", fc="#f4f6fb", ec="#2c3e50", size=12.5)

        add_text(ax, 0.018, 0.82, "Question", size=11.5, color=PAL["muted"], weight="bold")
        add_text(ax, 0.018, 0.765, shorten(ex.get("query", ""), 150), size=13.5, color=PAL["ink"], width=55)

        add_text(ax, 0.018, 0.58, "Gold answer", size=11.5, color=PAL["muted"], weight="bold")
        add_label(ax, 0.018, 0.50, shorten(ex.get("gold_answer", ""), 90), fc="#fff8dc", ec=PAL["gold"], size=12.0)

        # retrieved cards
        add_label(ax, 0.31, 0.92, "Semantic RAG retrieved", fc="#eef4ff", ec=PAL["semantic"], size=11.5)
        add_label(ax, 0.63, 0.92, "TimeBound-RAG retrieved", fc="#fff2f0", ec=PAL["timebound"], size=11.5)

        gold = set(ex.get("gold_evidence_turns", []))

        s_events = selected_events(ex, s)[:3]
        t_events = selected_events(ex, t)[:3]

        for j, ev in enumerate(s_events):
            add_event_card(
                ax,
                0.31,
                0.66 - j * 0.205,
                0.30,
                0.17,
                ev,
                is_gold=ev.get("turn_id") in gold,
                is_selected=True,
            )

        for j, ev in enumerate(t_events):
            add_event_card(
                ax,
                0.63,
                0.66 - j * 0.205,
                0.30,
                0.17,
                ev,
                is_gold=ev.get("turn_id") in gold,
                is_selected=True,
            )

        answer_badge(ax, 0.31, 0.055, "Semantic answer", s.get("prediction", ""), answer_ok(s))
        answer_badge(ax, 0.63, 0.055, "TimeBound answer", t.get("prediction", ""), answer_ok(t))

    save(fig, "01_semantic_fail_timebound_win_cards")


# -----------------------------------------------------------------------------
# Figure 2: Single case storyboard with all readers
# -----------------------------------------------------------------------------
def fig_model_storyboard(dataset):
    # choose a strong TimeBound case that all/most readers solve
    tb_preds = {m: load_preds(m, "timebound_rag") for m in MODEL_ORDER}

    best_case = None
    best_score = -1
    for ex_id, ex in dataset.items():
        score = 0
        for m in MODEL_ORDER:
            if ex_id in tb_preds[m] and answer_ok(tb_preds[m][ex_id]):
                score += 1
        if ex.get("task_type") in {"rescheduling", "conflicting_updates", "time_window_retrieval"}:
            score += 1
        if score > best_score:
            best_score = score
            best_case = ex_id

    ex = dataset[best_case]
    first_pred = next(tb_preds[m][best_case] for m in MODEL_ORDER if best_case in tb_preds[m])
    evs = selected_events(ex, first_pred)
    gold = set(ex.get("gold_evidence_turns", []))

    fig = plt.figure(figsize=(18, 13))
    big_title(
        fig,
        "Qualitative Storyboard: One Temporal Query Across Four Readers",
        "The same TimeBound-RAG evidence is shown with model outputs below."
    )

    ax = fig.add_axes([0.035, 0.055, 0.93, 0.84])
    ax.set_axis_off()

    add_round_box(ax, 0.0, 0.77, 1.0, 0.22, fc="#ffffff", ec="#2c3e50", lw=1.8)
    add_label(ax, 0.018, 0.94, f"Task: {ex.get('task_type')}", fc="#f4f6fb", ec="#2c3e50", size=13)
    add_text(ax, 0.02, 0.875, "Question", size=12, color=PAL["muted"], weight="bold")
    add_text(ax, 0.02, 0.83, ex.get("query", ""), size=17, color=PAL["ink"], width=78)
    add_text(ax, 0.68, 0.875, "Gold answer", size=12, color=PAL["muted"], weight="bold")
    add_label(ax, 0.68, 0.81, shorten(ex.get("gold_answer", ""), 140), fc="#fff8dc", ec=PAL["gold"], size=14)

    add_label(ax, 0.02, 0.72, "TimeBound evidence", fc="#fff2f0", ec=PAL["timebound"], size=13)

    card_w = 0.30
    for j, ev in enumerate(evs[:3]):
        add_event_card(
            ax,
            0.02 + j * 0.32,
            0.46,
            card_w,
            0.22,
            ev,
            is_gold=ev.get("turn_id") in gold,
            is_selected=True,
        )

    add_label(ax, 0.02, 0.38, "Reader answers", fc="#eef7ff", ec="#2980b9", size=13)

    y0 = 0.27
    for i, m in enumerate(MODEL_ORDER):
        p = tb_preds[m].get(best_case, {})
        ok = answer_ok(p)
        x = 0.02 + (i % 2) * 0.49
        y = y0 - (i // 2) * 0.14

        fc = "#eafaf1" if ok else "#fdecea"
        ec = PAL["ok"] if ok else PAL["bad"]
        add_round_box(ax, x, y, 0.46, 0.115, fc=fc, ec=ec, lw=1.7)
        add_text(ax, x + 0.015, y + 0.088, f"{'✓' if ok else '✗'} {MODEL_NICE[m]}", size=13.5, color=ec, weight="bold")
        add_text(ax, x + 0.015, y + 0.052, shorten(p.get("prediction", ""), 150), size=12.3, color=PAL["ink"], width=55)

    save(fig, "02_one_case_four_readers_storyboard")


# -----------------------------------------------------------------------------
# Figure 3: Full history vs TimeBound
# -----------------------------------------------------------------------------
def fig_full_history_vs_timebound(dataset, full, tb):
    case_ids = pick_full_history_fail_timebound_win(dataset, full, tb, n=3)
    if not case_ids:
        case_ids = pick_semantic_fail_timebound_win(dataset, full, tb, n=3)

    fig = plt.figure(figsize=(18, 16))
    big_title(
        fig,
        "Why Full History Is Not Enough",
        "Full-history prompting sees much more text, but temporal filtering provides the operative evidence."
    )

    for idx, ex_id in enumerate(case_ids):
        ax = fig.add_axes([0.035, 0.69 - idx * 0.30, 0.93, 0.255])
        ax.set_axis_off()

        ex = dataset[ex_id]
        f = full[ex_id]
        t = tb[ex_id]

        add_round_box(ax, 0.0, 0.0, 1.0, 1.0, fc="#ffffff", ec="#2c3e50", lw=1.7)
        add_label(ax, 0.015, 0.91, f"CASE {idx+1}: {ex.get('task_type')}", fc="#f4f6fb", ec="#2c3e50", size=12.5)

        add_text(ax, 0.02, 0.81, "Question", size=11.5, color=PAL["muted"], weight="bold")
        add_text(ax, 0.02, 0.75, shorten(ex.get("query", ""), 160), size=14, color=PAL["ink"], width=60)
        add_text(ax, 0.02, 0.55, "Gold", size=11.5, color=PAL["muted"], weight="bold")
        add_label(ax, 0.02, 0.47, shorten(ex.get("gold_answer", ""), 100), fc="#fff8dc", ec=PAL["gold"], size=12)

        add_round_box(ax, 0.31, 0.58, 0.29, 0.30, fc="#f4f6f7", ec="#34495e", lw=1.5)
        add_text(ax, 0.33, 0.82, "Full History", size=13, color="#34495e", weight="bold")
        add_text(ax, 0.33, 0.755, f"context chars: {int(f.get('prompt_chars', 0))}", size=11.8, color=PAL["muted"])
        add_text(ax, 0.33, 0.695, f"retrieved chars: {int(f.get('retrieved_chars', 0))}", size=11.8, color=PAL["muted"])
        answer_badge(ax, 0.32, 0.44, "Full-history answer", f.get("prediction", ""), answer_ok(f))

        add_round_box(ax, 0.64, 0.58, 0.31, 0.30, fc="#fff2f0", ec=PAL["timebound"], lw=1.8)
        add_text(ax, 0.66, 0.82, "TimeBound-RAG", size=13, color=PAL["timebound"], weight="bold")
        add_text(ax, 0.66, 0.755, f"context chars: {int(t.get('prompt_chars', 0))}", size=11.8, color=PAL["muted"])
        add_text(ax, 0.66, 0.695, f"retrieved chars: {int(t.get('retrieved_chars', 0))}", size=11.8, color=PAL["muted"])
        answer_badge(ax, 0.65, 0.44, "TimeBound answer", t.get("prediction", ""), answer_ok(t))

        gold = set(ex.get("gold_evidence_turns", []))
        tev = selected_events(ex, t)[:3]
        add_label(ax, 0.31, 0.31, "TimeBound selected evidence", fc="#fff2f0", ec=PAL["timebound"], size=11.5)
        for j, ev in enumerate(tev):
            add_event_card(
                ax,
                0.31 + j * 0.215,
                0.055,
                0.20,
                0.22,
                ev,
                is_gold=ev.get("turn_id") in gold,
                is_selected=True,
            )

    save(fig, "03_full_history_vs_timebound_cases")


# -----------------------------------------------------------------------------
# Figure 4: Timeline view
# -----------------------------------------------------------------------------
def fig_timeline(dataset, sem, tb):
    ex_id = pick_timeline_case(dataset, sem, tb)
    ex = dataset[ex_id]
    s = sem[ex_id]
    t = tb[ex_id]

    history = ex.get("history", [])
    gold = set(ex.get("gold_evidence_turns", []))
    sem_ret = set(s.get("retrieved_turns", []))
    tb_ret = set(t.get("retrieved_turns", []))

    # Keep timeline manageable: selected/gold + nearby first 12
    important = []
    for ev in history:
        tid = ev.get("turn_id")
        if tid in gold or tid in sem_ret or tid in tb_ret:
            important.append(ev)

    if len(important) < 7:
        important = history[:12]

    important = important[:12]

    fig = plt.figure(figsize=(18, 11))
    big_title(
        fig,
        "Temporal Evidence Timeline",
        "Gold, Semantic-selected, and TimeBound-selected memories are overlaid on the same history."
    )

    ax = fig.add_axes([0.04, 0.08, 0.92, 0.80])
    ax.set_axis_off()

    add_round_box(ax, 0.0, 0.82, 1.0, 0.17, fc="#ffffff", ec="#2c3e50", lw=1.7)
    add_label(ax, 0.018, 0.955, f"Task: {ex.get('task_type')}", fc="#f4f6fb", ec="#2c3e50", size=12.5)
    add_text(ax, 0.02, 0.90, "Question", size=11.5, color=PAL["muted"], weight="bold")
    add_text(ax, 0.02, 0.855, ex.get("query", ""), size=15.5, color=PAL["ink"], width=95)
    add_label(ax, 0.70, 0.89, f"Gold: {shorten(ex.get('gold_answer',''), 80)}", fc="#fff8dc", ec=PAL["gold"], size=12.5)

    # legend
    add_label(ax, 0.02, 0.77, "GOLD border", fc="#fff8dc", ec=PAL["gold"], size=10.8)
    add_label(ax, 0.15, 0.77, "Semantic selected", fc="#eef4ff", ec=PAL["semantic"], size=10.8)
    add_label(ax, 0.32, 0.77, "TimeBound selected", fc="#fff2f0", ec=PAL["timebound"], size=10.8)

    # horizontal timeline
    y_line = 0.58
    ax.plot([0.05, 0.95], [y_line, y_line], transform=ax.transAxes, color="#2c3e50", lw=2.2)

    n = len(important)
    xs = [0.06 + i * (0.88 / max(1, n - 1)) for i in range(n)]

    for i, (x, ev) in enumerate(zip(xs, important)):
        tid = ev.get("turn_id")
        st = str(ev.get("status", "unknown")).lower()

        is_gold = tid in gold
        is_sem = tid in sem_ret
        is_tb = tid in tb_ret

        marker_fc = STATUS_COLORS.get(st, "#f4f6f7")
        marker_ec = STATUS_EDGES.get(st, "#95a5a6")

        ax.scatter([x], [y_line], transform=ax.transAxes, s=340, color=marker_fc, edgecolor=marker_ec, linewidth=2.0, zorder=4)

        if is_gold:
            ax.scatter([x], [y_line], transform=ax.transAxes, s=520, facecolors="none", edgecolors=PAL["gold"], linewidth=3.2, zorder=5)
        if is_sem:
            ax.scatter([x], [y_line], transform=ax.transAxes, s=690, facecolors="none", edgecolors=PAL["semantic"], linewidth=2.8, zorder=6)
        if is_tb:
            ax.scatter([x], [y_line], transform=ax.transAxes, s=850, facecolors="none", edgecolors=PAL["timebound"], linewidth=2.8, zorder=7)

        label_y = 0.63 if i % 2 == 0 else 0.34
        ax.plot([x, x], [y_line, label_y + (0.04 if i % 2 else -0.02)], transform=ax.transAxes, color="#95a5a6", lw=1.2)

        add_round_box(
            ax,
            max(0.01, min(0.88, x - 0.08)),
            label_y,
            0.17,
            0.18,
            fc=marker_fc,
            ec=marker_ec,
            lw=1.2,
            radius=0.015,
        )
        add_text(
            ax,
            max(0.02, min(0.89, x - 0.071)),
            label_y + 0.145,
            f"T{tid} · {st}",
            size=9.5,
            color="#111",
            weight="bold",
        )
        add_text(
            ax,
            max(0.02, min(0.89, x - 0.071)),
            label_y + 0.108,
            shorten(ev.get("text", ""), 85),
            size=8.7,
            color="#111",
            width=24,
        )

    answer_badge(ax, 0.08, 0.08, "Semantic answer", s.get("prediction", ""), answer_ok(s))
    answer_badge(ax, 0.52, 0.08, "TimeBound answer", t.get("prediction", ""), answer_ok(t))

    save(fig, "04_temporal_evidence_timeline")


# -----------------------------------------------------------------------------
# Figure 5: Failure gallery / limitations
# -----------------------------------------------------------------------------
def fig_timebound_failure_gallery(dataset, tb):
    case_ids = pick_timebound_failure(dataset, tb, n=3)
    if not case_ids:
        return

    fig = plt.figure(figsize=(18, 15))
    big_title(
        fig,
        "Failure Gallery: Where TimeBound-RAG Still Misses",
        "Useful for limitations: temporal retrieval helps, but imperfect evidence or ambiguous phrasing still causes errors."
    )

    for idx, ex_id in enumerate(case_ids):
        ax = fig.add_axes([0.035, 0.68 - idx * 0.30, 0.93, 0.255])
        ax.set_axis_off()

        ex = dataset[ex_id]
        t = tb[ex_id]

        add_round_box(ax, 0.0, 0.0, 1.0, 1.0, fc="#ffffff", ec="#2c3e50", lw=1.7)
        add_label(ax, 0.015, 0.91, f"FAILURE {idx+1}: {ex.get('task_type')}", fc="#fdecea", ec=PAL["bad"], size=12.5)

        add_text(ax, 0.02, 0.80, "Question", size=11.5, color=PAL["muted"], weight="bold")
        add_text(ax, 0.02, 0.745, shorten(ex.get("query", ""), 160), size=14, color=PAL["ink"], width=64)

        add_text(ax, 0.02, 0.55, "Gold", size=11.5, color=PAL["muted"], weight="bold")
        add_label(ax, 0.02, 0.47, shorten(ex.get("gold_answer", ""), 110), fc="#fff8dc", ec=PAL["gold"], size=12)

        answer_badge(ax, 0.02, 0.28, "TimeBound answer", t.get("prediction", ""), answer_ok(t))

        gold = set(ex.get("gold_evidence_turns", []))
        tev = selected_events(ex, t)[:3]

        add_label(ax, 0.40, 0.91, "Retrieved evidence", fc="#fff2f0", ec=PAL["timebound"], size=11.5)
        for j, ev in enumerate(tev):
            add_event_card(
                ax,
                0.40 + j * 0.19,
                0.55,
                0.18,
                0.29,
                ev,
                is_gold=ev.get("turn_id") in gold,
                is_selected=True,
            )

        retrieved = set(t.get("retrieved_turns", []))
        hit = len(gold & retrieved)
        add_text(
            ax,
            0.40,
            0.36,
            f"Gold evidence turns: {sorted(gold)}\nRetrieved turns: {sorted(retrieved)}\nEvidence overlap: {hit}/{len(gold)}",
            size=12,
            color="#34495e",
            width=70,
        )

    save(fig, "05_timebound_failure_gallery")


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
def main():
    dataset = load_dataset()

    sem = load_preds(MAIN_MODEL, "semantic_rag")
    tb = load_preds(MAIN_MODEL, "timebound_rag")
    full = load_preds(MAIN_MODEL, "full_history")

    print("[INFO] dataset:", len(dataset))
    print("[INFO] semantic:", len(sem))
    print("[INFO] timebound:", len(tb))
    print("[INFO] full:", len(full))
    print("[INFO] main model:", MAIN_MODEL)

    fig_semantic_vs_timebound_cases(dataset, sem, tb)
    fig_model_storyboard(dataset)
    fig_full_history_vs_timebound(dataset, full, tb)
    fig_timeline(dataset, sem, tb)
    fig_timebound_failure_gallery(dataset, tb)

    readme = OUT / "README_QUALITATIVE.md"
    readme.write_text(
        "\n".join([
            "# TimeBound Qualitative Panels",
            "",
            "Generated qualitative figures:",
            "",
            "1. `01_semantic_fail_timebound_win_cards.png/.pdf`",
            "2. `02_one_case_four_readers_storyboard.png/.pdf`",
            "3. `03_full_history_vs_timebound_cases.png/.pdf`",
            "4. `04_temporal_evidence_timeline.png/.pdf`",
            "5. `05_timebound_failure_gallery.png/.pdf`",
            "",
            f"Main model for case mining: `{MAIN_MODEL}`",
            "",
        ]),
        encoding="utf-8",
    )
    print("[OK]", readme)
    print("[DONE] qualitative panels saved to:", OUT)

if __name__ == "__main__":
    main()
