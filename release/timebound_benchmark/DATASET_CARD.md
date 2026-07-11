# TimeBound-Long Dataset Card

## Purpose

TimeBound-Long is a controlled benchmark for interaction-time temporal memory in LLM agents.
It evaluates whether a system can retrieve and use memories whose validity changes through updates,
cancellations, delayed observations, rescheduling, expiration, recurrence, and retrospective query windows.

## Size

- Examples: 1000
- Task families: 8
- History length: 15--46, mean 29.8
- Gold evidence length: 1--2, mean 1.5
- Validation: 1000 / 1000 examples pass automatic checks

## Task families

- aging_facts: 125
- cancellation: 125
- conflicting_updates: 125
- delayed_observations: 125
- elapsed_time_reasoning: 125
- periodic_events: 125
- rescheduling: 125
- time_window_retrieval: 125

## Memory event fields

Each memory event contains:

- `turn_id`
- `text`
- `observation_time`
- `event_time`
- `valid_from`
- `valid_to`
- `status`
- `relation`
- `tag`

## Validation checks

The release validates that each example has:

- non-empty history;
- query and gold answer;
- gold evidence turns;
- gold evidence turns present in the history;
- observation time, event time, validity start, and status for each memory;
- well-formed validity intervals when an end time is present.

