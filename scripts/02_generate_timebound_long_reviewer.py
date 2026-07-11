import json
import random
from pathlib import Path
from datetime import datetime, timedelta
from collections import Counter

ROOT = Path("/home/tahiti/TimeBound")
OUT = ROOT / "synthetic"
OUT.mkdir(parents=True, exist_ok=True)

SEED = 42
N_TOTAL = 1000
TASKS = [
    "aging_facts",
    "cancellation",
    "conflicting_updates",
    "delayed_observations",
    "elapsed_time_reasoning",
    "periodic_events",
    "rescheduling",
    "time_window_retrieval",
]
PER_TASK = N_TOTAL // len(TASKS)

random.seed(SEED)
BASE = datetime(2026, 1, 1, 9, 0, 0)

NAMES = ["Alex", "Mira", "Sam", "Jordan", "Priya", "Nina", "Leo", "Omar"]
ITEMS = ["meeting", "call", "report", "appointment", "delivery", "reminder", "task", "review"]
PLACES = ["office", "clinic", "lab", "library", "airport", "client site", "online room"]

def iso(dt):
    if dt is None:
        return None
    return dt.strftime("%Y-%m-%d %H:%M")

def add_event(hist, text, obs, evt=None, valid_from=None, valid_to=None,
              status="active", relation=None, tag=None):
    turn_id = len(hist) + 1
    hist.append({
        "turn_id": turn_id,
        "text": text,
        "observation_time": iso(obs),
        "event_time": iso(evt or obs),
        "valid_from": iso(valid_from or obs),
        "valid_to": iso(valid_to),
        "status": status,
        "relation": relation,
        "tag": tag,
    })
    return turn_id

def add_distractors(hist, start, n):
    for _ in range(n):
        day = random.randint(0, 45)
        hour = random.randint(8, 18)
        obs = start + timedelta(days=day, hours=hour)
        name = random.choice(NAMES)
        item = random.choice(ITEMS)
        place = random.choice(PLACES)
        status = random.choice(["active", "scheduled", "expired"])
        add_event(
            hist,
            f"{name} mentioned an unrelated {item} at the {place}.",
            obs=obs,
            evt=obs + timedelta(days=random.randint(0, 7)),
            valid_from=obs,
            valid_to=obs + timedelta(days=random.randint(2, 14)) if status == "expired" else None,
            status=status,
            tag="distractor",
        )

def make_example(task, idx):
    hist = []
    start = BASE + timedelta(days=idx % 30)
    name = random.choice(NAMES)
    item = random.choice(ITEMS)

    # Put distractors before, between, and after core events.
    add_distractors(hist, start, random.randint(6, 12))

    if task == "aging_facts":
        t1 = start + timedelta(days=1)
        t_exp = start + timedelta(days=7)
        ev1 = add_event(
            hist,
            f"{name}'s access code is 4812 until next week.",
            obs=t1, evt=t1, valid_from=t1, valid_to=t_exp,
            status="expired", tag="gold_old",
        )
        add_distractors(hist, start, random.randint(6, 14))
        qtime = start + timedelta(days=12)
        query = f"What is {name}'s currently valid access code?"
        answer = "No currently valid access code is available."
        evidence = [ev1]

    elif task == "cancellation":
        meeting = start + timedelta(days=5, hours=5)
        ev1 = add_event(
            hist,
            f"{name} scheduled a {item} for {iso(meeting)}.",
            obs=start, evt=meeting, valid_from=start,
            status="cancelled", tag="gold_original",
        )
        add_distractors(hist, start, random.randint(5, 10))
        ev2 = add_event(
            hist,
            f"{name} cancelled the {item} scheduled for {iso(meeting)}.",
            obs=start + timedelta(days=2), evt=meeting,
            valid_from=start + timedelta(days=2),
            status="active", relation={"cancels": ev1},
            tag="gold_cancel",
        )
        qtime = start + timedelta(days=3)
        query = f"Is {name}'s {item} still scheduled?"
        answer = "No, it was cancelled."
        evidence = [ev1, ev2]

    elif task == "conflicting_updates":
        old_time = start + timedelta(days=4, hours=10)
        new_time = start + timedelta(days=4, hours=12)
        ev1 = add_event(
            hist,
            f"{name}'s {item} is planned for {iso(old_time)}.",
            obs=start, evt=old_time, valid_from=start,
            status="superseded", tag="gold_old",
        )
        add_distractors(hist, start, random.randint(5, 12))
        ev2 = add_event(
            hist,
            f"Update: {name}'s {item} is now planned for {iso(new_time)} instead.",
            obs=start + timedelta(days=1), evt=new_time,
            valid_from=start + timedelta(days=1),
            status="active", relation={"supersedes": ev1},
            tag="gold_update",
        )
        qtime = start + timedelta(days=2)
        query = f"When is {name}'s {item} now planned?"
        answer = iso(new_time)
        evidence = [ev1, ev2]

    elif task == "delayed_observations":
        evt = start + timedelta(days=1, hours=2)
        obs = start + timedelta(days=5)
        ev1 = add_event(
            hist,
            f"{name} reported late that the {item} actually happened on {iso(evt)}.",
            obs=obs, evt=evt, valid_from=obs,
            status="delayed", tag="gold_delayed",
        )
        qtime = start + timedelta(days=6)
        query = f"Had the {item} happened before {iso(start + timedelta(days=3))}?"
        answer = "Yes."
        evidence = [ev1]

    elif task == "elapsed_time_reasoning":
        start_evt = start + timedelta(days=2, hours=9)
        end_evt = start + timedelta(days=5, hours=9)
        ev1 = add_event(
            hist,
            f"{name} started the {item} on {iso(start_evt)}.",
            obs=start_evt, evt=start_evt, valid_from=start_evt,
            status="active", tag="gold_start",
        )
        ev2 = add_event(
            hist,
            f"{name} finished the {item} on {iso(end_evt)}.",
            obs=end_evt, evt=end_evt, valid_from=end_evt,
            status="active", tag="gold_end",
        )
        qtime = start + timedelta(days=6)
        query = f"How long did {name}'s {item} take?"
        answer = "3 days"
        evidence = [ev1, ev2]

    elif task == "periodic_events":
        first = start + timedelta(days=1, hours=9)
        ev1 = add_event(
            hist,
            f"{name}'s check-in repeats every 3 days starting {iso(first)}.",
            obs=start, evt=first, valid_from=start,
            status="scheduled", tag="gold_rule",
        )
        qtime = start + timedelta(days=10)
        query = f"When is the next check-in after {iso(start + timedelta(days=7))}?"
        answer = iso(first + timedelta(days=9))
        evidence = [ev1]

    elif task == "rescheduling":
        old = start + timedelta(days=6, hours=9)
        new = start + timedelta(days=8, hours=11)
        ev1 = add_event(
            hist,
            f"{name}'s {item} was scheduled for {iso(old)}.",
            obs=start, evt=old, valid_from=start,
            status="superseded", tag="gold_old",
        )
        add_distractors(hist, start, random.randint(5, 10))
        ev2 = add_event(
            hist,
            f"{name} moved the {item} from {iso(old)} to {iso(new)}.",
            obs=start + timedelta(days=2), evt=new,
            valid_from=start + timedelta(days=2),
            status="active", relation={"reschedules": ev1},
            tag="gold_reschedule",
        )
        qtime = start + timedelta(days=3)
        query = f"When is {name}'s {item} after rescheduling?"
        answer = iso(new)
        evidence = [ev1, ev2]

    elif task == "time_window_retrieval":
        old = start + timedelta(days=1)
        update = start + timedelta(days=8)
        ev1 = add_event(
            hist,
            f"{name}'s preferred contact method was email.",
            obs=old, evt=old, valid_from=old, valid_to=update,
            status="superseded", tag="gold_old_window",
        )
        add_distractors(hist, start, random.randint(5, 10))
        ev2 = add_event(
            hist,
            f"{name}'s preferred contact method changed to phone.",
            obs=update, evt=update, valid_from=update,
            status="active", relation={"supersedes": ev1},
            tag="gold_new_window",
        )
        qtime = start + timedelta(days=5)
        query = f"What was {name}'s preferred contact method on {iso(qtime)}?"
        answer = "email"
        evidence = [ev1]

    add_distractors(hist, start, random.randint(8, 20))

    # Sort by observation time, then reassign turn ids and evidence mapping.
    old_to_event = {ev["turn_id"]: ev for ev in hist}
    hist_sorted = sorted(hist, key=lambda x: (x["observation_time"], x["turn_id"]))
    remap = {}
    for new_id, ev in enumerate(hist_sorted, 1):
        remap[ev["turn_id"]] = new_id
        ev["turn_id"] = new_id

    for ev in hist_sorted:
        rel = ev.get("relation")
        if isinstance(rel, dict):
            ev["relation"] = {k: remap.get(v, v) for k, v in rel.items()}

    evidence = [remap[e] for e in evidence]

    return {
        "id": f"{task}_{idx:04d}",
        "dataset": "TimeBound-Long",
        "task_type": task,
        "difficulty": "long",
        "query_time": iso(qtime),
        "query": query,
        "gold_answer": answer,
        "gold_evidence_turns": evidence,
        "history": hist_sorted,
        "metadata": {
            "seed": SEED,
            "generator": "02_generate_timebound_long_reviewer.py",
            "n_turns": len(hist_sorted),
        }
    }

rows = []
idx = 0
for task in TASKS:
    for _ in range(PER_TASK):
        rows.append(make_example(task, idx))
        idx += 1

random.shuffle(rows)

out_path = OUT / "timebound_long.jsonl"
with out_path.open("w", encoding="utf-8") as f:
    for r in rows:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

summary = {
    "path": str(out_path),
    "n_examples": len(rows),
    "seed": SEED,
    "task_distribution": Counter(r["task_type"] for r in rows),
    "history_min": min(len(r["history"]) for r in rows),
    "history_mean": sum(len(r["history"]) for r in rows) / len(rows),
    "history_max": max(len(r["history"]) for r in rows),
    "evidence_min": min(len(r["gold_evidence_turns"]) for r in rows),
    "evidence_mean": sum(len(r["gold_evidence_turns"]) for r in rows) / len(rows),
    "evidence_max": max(len(r["gold_evidence_turns"]) for r in rows),
}
summary["task_distribution"] = dict(summary["task_distribution"])

summary_path = OUT / "timebound_long.summary.json"
summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

print(json.dumps(summary, indent=2, ensure_ascii=False))
