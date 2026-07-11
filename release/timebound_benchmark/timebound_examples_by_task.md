# TimeBound-Long examples by task family

## rescheduling

### rescheduling_0783

**Query:** When is Priya's delivery after rescheduling?

**Gold answer:** 2026-01-12 20:00

**Gold evidence turns:** [1, 5]

**History excerpt:**

- T1 GOLD | obs=2026-01-04 09:00 | evt=2026-01-10 18:00 | status=superseded | Priya's delivery was scheduled for 2026-01-10 18:00.
- T2 | obs=2026-01-05 18:00 | evt=2026-01-11 18:00 | status=active | Priya mentioned an unrelated appointment at the online room.
- T3 | obs=2026-01-06 01:00 | evt=2026-01-08 01:00 | status=scheduled | Alex mentioned an unrelated meeting at the lab.
- T4 | obs=2026-01-06 01:00 | evt=2026-01-06 01:00 | status=scheduled | Nina mentioned an unrelated meeting at the clinic.
- T5 GOLD | obs=2026-01-06 09:00 | evt=2026-01-12 20:00 | status=active | Priya moved the delivery from 2026-01-10 18:00 to 2026-01-12 20:00.
- T6 | obs=2026-01-07 21:00 | evt=2026-01-10 21:00 | status=expired | Sam mentioned an unrelated review at the library.
- T7 | obs=2026-01-10 20:00 | evt=2026-01-17 20:00 | status=expired | Omar mentioned an unrelated review at the lab.
- T8 | obs=2026-01-13 02:00 | evt=2026-01-19 02:00 | status=expired | Alex mentioned an unrelated reminder at the library.
- T9 | obs=2026-01-13 02:00 | evt=2026-01-16 02:00 | status=active | Alex mentioned an unrelated report at the airport.
- T10 | obs=2026-01-15 22:00 | evt=2026-01-16 22:00 | status=active | Alex mentioned an unrelated meeting at the clinic.
- T11 | obs=2026-01-16 03:00 | evt=2026-01-19 03:00 | status=scheduled | Mira mentioned an unrelated delivery at the library.
- T12 | obs=2026-01-18 19:00 | evt=2026-01-23 19:00 | status=active | Priya mentioned an unrelated delivery at the library.

### rescheduling_0871

**Query:** When is Nina's call after rescheduling?

**Gold answer:** 2026-01-10 20:00

**Gold evidence turns:** [1, 4]

**History excerpt:**

- T1 GOLD | obs=2026-01-02 09:00 | evt=2026-01-08 18:00 | status=superseded | Nina's call was scheduled for 2026-01-08 18:00.
- T2 | obs=2026-01-02 21:00 | evt=2026-01-06 21:00 | status=active | Leo mentioned an unrelated meeting at the client site.
- T3 | obs=2026-01-04 02:00 | evt=2026-01-06 02:00 | status=scheduled | Nina mentioned an unrelated call at the clinic.
- T4 GOLD | obs=2026-01-04 09:00 | evt=2026-01-10 20:00 | status=active | Nina moved the call from 2026-01-08 18:00 to 2026-01-10 20:00.
- T5 | obs=2026-01-05 02:00 | evt=2026-01-08 02:00 | status=expired | Jordan mentioned an unrelated call at the online room.
- T6 | obs=2026-01-05 17:00 | evt=2026-01-11 17:00 | status=scheduled | Nina mentioned an unrelated delivery at the office.
- T7 | obs=2026-01-06 22:00 | evt=2026-01-13 22:00 | status=active | Alex mentioned an unrelated call at the library.
- T8 | obs=2026-01-07 23:00 | evt=2026-01-13 23:00 | status=active | Mira mentioned an unrelated report at the office.
- T9 | obs=2026-01-08 00:00 | evt=2026-01-11 00:00 | status=scheduled | Jordan mentioned an unrelated meeting at the office.
- T10 | obs=2026-01-09 20:00 | evt=2026-01-16 20:00 | status=active | Nina mentioned an unrelated appointment at the online room.
- T11 | obs=2026-01-10 20:00 | evt=2026-01-17 20:00 | status=scheduled | Mira mentioned an unrelated task at the clinic.
- T12 | obs=2026-01-12 02:00 | evt=2026-01-15 02:00 | status=scheduled | Priya mentioned an unrelated delivery at the online room.

## conflicting_updates

### conflicting_updates_0371

**Query:** When is Mira's meeting now planned?

**Gold answer:** 2026-01-16 21:00

**Gold evidence turns:** [1, 2]

**History excerpt:**

- T1 GOLD | obs=2026-01-12 09:00 | evt=2026-01-16 19:00 | status=superseded | Mira's meeting is planned for 2026-01-16 19:00.
- T2 GOLD | obs=2026-01-13 09:00 | evt=2026-01-16 21:00 | status=active | Update: Mira's meeting is now planned for 2026-01-16 21:00 instead.
- T3 | obs=2026-01-13 23:00 | evt=2026-01-13 23:00 | status=expired | Sam mentioned an unrelated delivery at the client site.
- T4 | obs=2026-01-14 17:00 | evt=2026-01-19 17:00 | status=active | Jordan mentioned an unrelated meeting at the office.
- T5 | obs=2026-01-16 02:00 | evt=2026-01-19 02:00 | status=expired | Alex mentioned an unrelated reminder at the office.
- T6 | obs=2026-01-16 18:00 | evt=2026-01-20 18:00 | status=expired | Nina mentioned an unrelated delivery at the online room.
- T7 | obs=2026-01-17 22:00 | evt=2026-01-19 22:00 | status=expired | Priya mentioned an unrelated call at the airport.
- T8 | obs=2026-01-18 01:00 | evt=2026-01-20 01:00 | status=scheduled | Leo mentioned an unrelated meeting at the lab.
- T9 | obs=2026-01-18 19:00 | evt=2026-01-18 19:00 | status=expired | Sam mentioned an unrelated review at the library.
- T10 | obs=2026-01-21 20:00 | evt=2026-01-25 20:00 | status=expired | Omar mentioned an unrelated delivery at the client site.
- T11 | obs=2026-01-22 02:00 | evt=2026-01-24 02:00 | status=scheduled | Priya mentioned an unrelated reminder at the client site.
- T12 | obs=2026-01-23 00:00 | evt=2026-01-24 00:00 | status=expired | Alex mentioned an unrelated call at the airport.

### conflicting_updates_0258

**Query:** When is Leo's task now planned?

**Gold answer:** 2026-01-23 21:00

**Gold evidence turns:** [1, 4]

**History excerpt:**

- T1 GOLD | obs=2026-01-19 09:00 | evt=2026-01-23 19:00 | status=superseded | Leo's task is planned for 2026-01-23 19:00.
- T2 | obs=2026-01-19 17:00 | evt=2026-01-24 17:00 | status=scheduled | Jordan mentioned an unrelated review at the online room.
- T3 | obs=2026-01-19 21:00 | evt=2026-01-26 21:00 | status=active | Jordan mentioned an unrelated delivery at the clinic.
- T4 GOLD | obs=2026-01-20 09:00 | evt=2026-01-23 21:00 | status=active | Update: Leo's task is now planned for 2026-01-23 21:00 instead.
- T5 | obs=2026-01-23 01:00 | evt=2026-01-26 01:00 | status=scheduled | Leo mentioned an unrelated call at the airport.
- T6 | obs=2026-01-23 20:00 | evt=2026-01-23 20:00 | status=expired | Jordan mentioned an unrelated appointment at the office.
- T7 | obs=2026-01-24 23:00 | evt=2026-01-31 23:00 | status=expired | Jordan mentioned an unrelated task at the library.
- T8 | obs=2026-01-26 01:00 | evt=2026-01-29 01:00 | status=expired | Alex mentioned an unrelated reminder at the client site.
- T9 | obs=2026-01-26 18:00 | evt=2026-01-26 18:00 | status=scheduled | Mira mentioned an unrelated report at the office.
- T10 | obs=2026-01-29 21:00 | evt=2026-02-04 21:00 | status=expired | Priya mentioned an unrelated call at the airport.
- T11 | obs=2026-02-02 01:00 | evt=2026-02-06 01:00 | status=active | Sam mentioned an unrelated call at the lab.
- T12 | obs=2026-02-07 19:00 | evt=2026-02-11 19:00 | status=scheduled | Alex mentioned an unrelated call at the clinic.

## time_window_retrieval

### time_window_retrieval_0944

**Query:** What was Sam's preferred contact method on 2026-01-20 09:00?

**Gold answer:** email

**Gold evidence turns:** [2]

**History excerpt:**

- T1 | obs=2026-01-15 21:00 | evt=2026-01-19 21:00 | status=active | Priya mentioned an unrelated appointment at the online room.
- T2 GOLD | obs=2026-01-16 09:00 | evt=2026-01-16 09:00 | status=superseded | Sam's preferred contact method was email.
- T3 | obs=2026-01-17 01:00 | evt=2026-01-19 01:00 | status=active | Leo mentioned an unrelated report at the office.
- T4 | obs=2026-01-18 01:00 | evt=2026-01-21 01:00 | status=active | Sam mentioned an unrelated call at the airport.
- T5 | obs=2026-01-18 23:00 | evt=2026-01-24 23:00 | status=active | Leo mentioned an unrelated delivery at the online room.
- T6 | obs=2026-01-19 02:00 | evt=2026-01-26 02:00 | status=expired | Nina mentioned an unrelated call at the clinic.
- T7 | obs=2026-01-22 17:00 | evt=2026-01-26 17:00 | status=expired | Alex mentioned an unrelated meeting at the airport.
- T8 | obs=2026-01-23 09:00 | evt=2026-01-23 09:00 | status=active | Sam's preferred contact method changed to phone.
- T9 | obs=2026-01-23 17:00 | evt=2026-01-23 17:00 | status=active | Priya mentioned an unrelated delivery at the office.
- T10 | obs=2026-01-24 20:00 | evt=2026-01-26 20:00 | status=scheduled | Sam mentioned an unrelated task at the airport.
- T11 | obs=2026-01-25 01:00 | evt=2026-01-27 01:00 | status=scheduled | Leo mentioned an unrelated delivery at the client site.
- T12 | obs=2026-01-26 01:00 | evt=2026-01-26 01:00 | status=scheduled | Nina mentioned an unrelated reminder at the airport.

### time_window_retrieval_0904

**Query:** What was Jordan's preferred contact method on 2026-01-10 09:00?

**Gold answer:** email

**Gold evidence turns:** [2]

**History excerpt:**

- T1 | obs=2026-01-05 18:00 | evt=2026-01-07 18:00 | status=scheduled | Mira mentioned an unrelated reminder at the lab.
- T2 GOLD | obs=2026-01-06 09:00 | evt=2026-01-06 09:00 | status=superseded | Jordan's preferred contact method was email.
- T3 | obs=2026-01-07 00:00 | evt=2026-01-08 00:00 | status=expired | Nina mentioned an unrelated review at the clinic.
- T4 | obs=2026-01-07 17:00 | evt=2026-01-10 17:00 | status=active | Nina mentioned an unrelated call at the client site.
- T5 | obs=2026-01-07 21:00 | evt=2026-01-11 21:00 | status=expired | Sam mentioned an unrelated meeting at the online room.
- T6 | obs=2026-01-08 21:00 | evt=2026-01-09 21:00 | status=scheduled | Nina mentioned an unrelated report at the library.
- T7 | obs=2026-01-12 02:00 | evt=2026-01-12 02:00 | status=active | Mira mentioned an unrelated appointment at the office.
- T8 | obs=2026-01-13 03:00 | evt=2026-01-14 03:00 | status=expired | Sam mentioned an unrelated review at the client site.
- T9 | obs=2026-01-13 09:00 | evt=2026-01-13 09:00 | status=active | Jordan's preferred contact method changed to phone.
- T10 | obs=2026-01-14 17:00 | evt=2026-01-18 17:00 | status=expired | Nina mentioned an unrelated call at the client site.
- T11 | obs=2026-01-14 18:00 | evt=2026-01-18 18:00 | status=expired | Alex mentioned an unrelated report at the clinic.
- T12 | obs=2026-01-15 21:00 | evt=2026-01-15 21:00 | status=scheduled | Nina mentioned an unrelated appointment at the library.

## aging_facts

### aging_facts_0043

**Query:** What is Mira's currently valid access code?

**Gold answer:** No currently valid access code is available.

**Gold evidence turns:** [2]

**History excerpt:**

- T1 | obs=2026-01-14 17:00 | evt=2026-01-18 17:00 | status=scheduled | Nina mentioned an unrelated appointment at the lab.
- T2 GOLD | obs=2026-01-15 09:00 | evt=2026-01-15 09:00 | status=expired | Mira's access code is 4812 until next week.
- T3 | obs=2026-01-16 21:00 | evt=2026-01-19 21:00 | status=active | Jordan mentioned an unrelated report at the library.
- T4 | obs=2026-01-17 21:00 | evt=2026-01-22 21:00 | status=scheduled | Mira mentioned an unrelated delivery at the lab.
- T5 | obs=2026-01-19 00:00 | evt=2026-01-23 00:00 | status=expired | Leo mentioned an unrelated meeting at the clinic.
- T6 | obs=2026-01-19 17:00 | evt=2026-01-22 17:00 | status=scheduled | Leo mentioned an unrelated task at the airport.
- T7 | obs=2026-01-19 18:00 | evt=2026-01-22 18:00 | status=expired | Sam mentioned an unrelated call at the office.
- T8 | obs=2026-01-22 21:00 | evt=2026-01-25 21:00 | status=expired | Alex mentioned an unrelated meeting at the online room.
- T9 | obs=2026-01-22 21:00 | evt=2026-01-23 21:00 | status=active | Alex mentioned an unrelated appointment at the online room.
- T10 | obs=2026-01-22 23:00 | evt=2026-01-22 23:00 | status=expired | Priya mentioned an unrelated reminder at the office.
- T11 | obs=2026-01-28 21:00 | evt=2026-01-28 21:00 | status=active | Priya mentioned an unrelated call at the clinic.
- T12 | obs=2026-01-28 21:00 | evt=2026-01-29 21:00 | status=expired | Sam mentioned an unrelated delivery at the office.

### aging_facts_0047

**Query:** What is Jordan's currently valid access code?

**Gold answer:** No currently valid access code is available.

**Gold evidence turns:** [2]

**History excerpt:**

- T1 | obs=2026-01-18 22:00 | evt=2026-01-23 22:00 | status=scheduled | Alex mentioned an unrelated reminder at the clinic.
- T2 GOLD | obs=2026-01-19 09:00 | evt=2026-01-19 09:00 | status=expired | Jordan's access code is 4812 until next week.
- T3 | obs=2026-01-19 20:00 | evt=2026-01-24 20:00 | status=active | Alex mentioned an unrelated meeting at the clinic.
- T4 | obs=2026-01-20 03:00 | evt=2026-01-26 03:00 | status=active | Alex mentioned an unrelated review at the lab.
- T5 | obs=2026-01-21 01:00 | evt=2026-01-22 01:00 | status=active | Alex mentioned an unrelated reminder at the client site.
- T6 | obs=2026-01-21 21:00 | evt=2026-01-27 21:00 | status=expired | Mira mentioned an unrelated delivery at the lab.
- T7 | obs=2026-01-28 02:00 | evt=2026-01-31 02:00 | status=active | Leo mentioned an unrelated review at the client site.
- T8 | obs=2026-01-28 19:00 | evt=2026-01-28 19:00 | status=expired | Priya mentioned an unrelated meeting at the clinic.
- T9 | obs=2026-01-29 02:00 | evt=2026-01-29 02:00 | status=expired | Nina mentioned an unrelated task at the clinic.
- T10 | obs=2026-01-29 18:00 | evt=2026-02-01 18:00 | status=scheduled | Mira mentioned an unrelated review at the online room.
- T11 | obs=2026-01-31 01:00 | evt=2026-01-31 01:00 | status=scheduled | Jordan mentioned an unrelated task at the online room.
- T12 | obs=2026-01-31 03:00 | evt=2026-02-04 03:00 | status=expired | Priya mentioned an unrelated task at the office.

## periodic_events

### periodic_events_0738

**Query:** When is the next check-in after 2026-01-26 09:00?

**Gold answer:** 2026-01-29 18:00

**Gold evidence turns:** [1]

**History excerpt:**

- T1 GOLD | obs=2026-01-19 09:00 | evt=2026-01-20 18:00 | status=scheduled | Priya's check-in repeats every 3 days starting 2026-01-20 18:00.
- T2 | obs=2026-01-19 22:00 | evt=2026-01-25 22:00 | status=active | Alex mentioned an unrelated delivery at the library.
- T3 | obs=2026-01-20 23:00 | evt=2026-01-23 23:00 | status=active | Nina mentioned an unrelated meeting at the clinic.
- T4 | obs=2026-01-21 17:00 | evt=2026-01-27 17:00 | status=scheduled | Leo mentioned an unrelated review at the client site.
- T5 | obs=2026-01-21 22:00 | evt=2026-01-28 22:00 | status=active | Leo mentioned an unrelated reminder at the library.
- T6 | obs=2026-01-23 22:00 | evt=2026-01-27 22:00 | status=active | Alex mentioned an unrelated review at the clinic.
- T7 | obs=2026-01-24 19:00 | evt=2026-01-30 19:00 | status=active | Leo mentioned an unrelated delivery at the airport.
- T8 | obs=2026-01-27 20:00 | evt=2026-02-03 20:00 | status=scheduled | Priya mentioned an unrelated report at the library.
- T9 | obs=2026-01-31 17:00 | evt=2026-02-05 17:00 | status=scheduled | Mira mentioned an unrelated report at the airport.
- T10 | obs=2026-02-04 00:00 | evt=2026-02-10 00:00 | status=active | Mira mentioned an unrelated delivery at the lab.
- T11 | obs=2026-02-11 19:00 | evt=2026-02-13 19:00 | status=active | Leo mentioned an unrelated reminder at the airport.
- T12 | obs=2026-02-13 00:00 | evt=2026-02-14 00:00 | status=active | Alex mentioned an unrelated call at the lab.

### periodic_events_0655

**Query:** When is the next check-in after 2026-02-02 09:00?

**Gold answer:** 2026-02-05 18:00

**Gold evidence turns:** [1]

**History excerpt:**

- T1 GOLD | obs=2026-01-26 09:00 | evt=2026-01-27 18:00 | status=scheduled | Leo's check-in repeats every 3 days starting 2026-01-27 18:00.
- T2 | obs=2026-01-27 23:00 | evt=2026-01-30 23:00 | status=scheduled | Omar mentioned an unrelated report at the online room.
- T3 | obs=2026-01-28 01:00 | evt=2026-02-02 01:00 | status=active | Priya mentioned an unrelated meeting at the online room.
- T4 | obs=2026-02-01 21:00 | evt=2026-02-03 21:00 | status=active | Priya mentioned an unrelated review at the library.
- T5 | obs=2026-02-09 21:00 | evt=2026-02-15 21:00 | status=scheduled | Omar mentioned an unrelated report at the lab.
- T6 | obs=2026-02-10 03:00 | evt=2026-02-15 03:00 | status=expired | Priya mentioned an unrelated delivery at the clinic.
- T7 | obs=2026-02-11 01:00 | evt=2026-02-17 01:00 | status=expired | Mira mentioned an unrelated appointment at the library.
- T8 | obs=2026-02-12 17:00 | evt=2026-02-19 17:00 | status=active | Leo mentioned an unrelated meeting at the lab.
- T9 | obs=2026-02-13 00:00 | evt=2026-02-17 00:00 | status=scheduled | Mira mentioned an unrelated review at the lab.
- T10 | obs=2026-02-13 17:00 | evt=2026-02-13 17:00 | status=expired | Leo mentioned an unrelated call at the airport.
- T11 | obs=2026-02-14 02:00 | evt=2026-02-19 02:00 | status=expired | Mira mentioned an unrelated report at the client site.
- T12 | obs=2026-02-14 21:00 | evt=2026-02-20 21:00 | status=scheduled | Jordan mentioned an unrelated report at the client site.

## delayed_observations

### delayed_observations_0427

**Query:** Had the reminder happened before 2026-01-11 09:00?

**Gold answer:** Yes.

**Gold evidence turns:** [5]

**History excerpt:**

- T1 | obs=2026-01-08 22:00 | evt=2026-01-12 22:00 | status=active | Omar mentioned an unrelated appointment at the library.
- T2 | obs=2026-01-11 00:00 | evt=2026-01-18 00:00 | status=expired | Mira mentioned an unrelated appointment at the online room.
- T3 | obs=2026-01-11 19:00 | evt=2026-01-11 19:00 | status=expired | Sam mentioned an unrelated task at the online room.
- T4 | obs=2026-01-12 23:00 | evt=2026-01-17 23:00 | status=scheduled | Priya mentioned an unrelated delivery at the lab.
- T5 GOLD | obs=2026-01-13 09:00 | evt=2026-01-09 11:00 | status=delayed | Omar reported late that the reminder actually happened on 2026-01-09 11:00.
- T6 | obs=2026-01-14 03:00 | evt=2026-01-20 03:00 | status=active | Mira mentioned an unrelated call at the library.
- T7 | obs=2026-01-15 20:00 | evt=2026-01-18 20:00 | status=scheduled | Alex mentioned an unrelated appointment at the client site.
- T8 | obs=2026-01-15 21:00 | evt=2026-01-15 21:00 | status=scheduled | Leo mentioned an unrelated appointment at the lab.
- T9 | obs=2026-01-18 02:00 | evt=2026-01-22 02:00 | status=active | Omar mentioned an unrelated report at the airport.
- T10 | obs=2026-01-18 19:00 | evt=2026-01-23 19:00 | status=scheduled | Jordan mentioned an unrelated meeting at the airport.
- T11 | obs=2026-01-19 03:00 | evt=2026-01-21 03:00 | status=active | Nina mentioned an unrelated review at the airport.
- T12 | obs=2026-01-19 17:00 | evt=2026-01-26 17:00 | status=scheduled | Omar mentioned an unrelated call at the clinic.

### delayed_observations_0448

**Query:** Had the reminder happened before 2026-02-01 09:00?

**Gold answer:** Yes.

**Gold evidence turns:** [3]

**History excerpt:**

- T1 | obs=2026-02-02 17:00 | evt=2026-02-03 17:00 | status=active | Leo mentioned an unrelated report at the office.
- T2 | obs=2026-02-02 18:00 | evt=2026-02-09 18:00 | status=active | Mira mentioned an unrelated report at the airport.
- T3 GOLD | obs=2026-02-03 09:00 | evt=2026-01-30 11:00 | status=delayed | Sam reported late that the reminder actually happened on 2026-01-30 11:00.
- T4 | obs=2026-02-09 18:00 | evt=2026-02-10 18:00 | status=active | Jordan mentioned an unrelated reminder at the online room.
- T5 | obs=2026-02-10 03:00 | evt=2026-02-15 03:00 | status=active | Sam mentioned an unrelated meeting at the clinic.
- T6 | obs=2026-02-12 21:00 | evt=2026-02-12 21:00 | status=expired | Omar mentioned an unrelated report at the office.
- T7 | obs=2026-02-13 00:00 | evt=2026-02-14 00:00 | status=active | Priya mentioned an unrelated call at the client site.
- T8 | obs=2026-02-13 18:00 | evt=2026-02-14 18:00 | status=scheduled | Omar mentioned an unrelated call at the airport.
- T9 | obs=2026-02-15 02:00 | evt=2026-02-16 02:00 | status=expired | Nina mentioned an unrelated task at the online room.
- T10 | obs=2026-02-15 19:00 | evt=2026-02-16 19:00 | status=active | Leo mentioned an unrelated delivery at the office.
- T11 | obs=2026-02-15 21:00 | evt=2026-02-18 21:00 | status=expired | Sam mentioned an unrelated appointment at the airport.
- T12 | obs=2026-02-16 03:00 | evt=2026-02-19 03:00 | status=scheduled | Omar mentioned an unrelated reminder at the airport.

## cancellation

### cancellation_0198

**Query:** Is Jordan's delivery still scheduled?

**Gold answer:** No, it was cancelled.

**Gold evidence turns:** [1, 2]

**History excerpt:**

- T1 GOLD | obs=2026-01-19 09:00 | evt=2026-01-24 14:00 | status=cancelled | Jordan scheduled a delivery for 2026-01-24 14:00.
- T2 GOLD | obs=2026-01-21 09:00 | evt=2026-01-24 14:00 | status=active | Jordan cancelled the delivery scheduled for 2026-01-24 14:00.
- T3 | obs=2026-01-22 19:00 | evt=2026-01-27 19:00 | status=active | Nina mentioned an unrelated call at the lab.
- T4 | obs=2026-01-24 03:00 | evt=2026-01-29 03:00 | status=expired | Mira mentioned an unrelated meeting at the office.
- T5 | obs=2026-01-26 02:00 | evt=2026-01-29 02:00 | status=scheduled | Mira mentioned an unrelated report at the airport.
- T6 | obs=2026-01-30 03:00 | evt=2026-01-31 03:00 | status=scheduled | Priya mentioned an unrelated meeting at the office.
- T7 | obs=2026-01-31 00:00 | evt=2026-02-07 00:00 | status=active | Omar mentioned an unrelated report at the client site.
- T8 | obs=2026-02-02 01:00 | evt=2026-02-08 01:00 | status=expired | Leo mentioned an unrelated reminder at the lab.
- T9 | obs=2026-02-03 00:00 | evt=2026-02-04 00:00 | status=expired | Alex mentioned an unrelated meeting at the client site.
- T10 | obs=2026-02-06 03:00 | evt=2026-02-08 03:00 | status=scheduled | Priya mentioned an unrelated appointment at the client site.
- T11 | obs=2026-02-06 17:00 | evt=2026-02-12 17:00 | status=active | Omar mentioned an unrelated task at the client site.
- T12 | obs=2026-02-06 17:00 | evt=2026-02-13 17:00 | status=active | Priya mentioned an unrelated call at the client site.

### cancellation_0233

**Query:** Is Nina's delivery still scheduled?

**Gold answer:** No, it was cancelled.

**Gold evidence turns:** [1, 2]

**History excerpt:**

- T1 GOLD | obs=2026-01-24 09:00 | evt=2026-01-29 14:00 | status=cancelled | Nina scheduled a delivery for 2026-01-29 14:00.
- T2 GOLD | obs=2026-01-26 09:00 | evt=2026-01-29 14:00 | status=active | Nina cancelled the delivery scheduled for 2026-01-29 14:00.
- T3 | obs=2026-01-26 19:00 | evt=2026-01-26 19:00 | status=scheduled | Leo mentioned an unrelated review at the office.
- T4 | obs=2026-01-28 23:00 | evt=2026-01-30 23:00 | status=active | Priya mentioned an unrelated report at the online room.
- T5 | obs=2026-01-30 02:00 | evt=2026-02-06 02:00 | status=scheduled | Alex mentioned an unrelated delivery at the clinic.
- T6 | obs=2026-01-31 19:00 | evt=2026-02-02 19:00 | status=scheduled | Nina mentioned an unrelated report at the client site.
- T7 | obs=2026-02-01 19:00 | evt=2026-02-03 19:00 | status=scheduled | Omar mentioned an unrelated reminder at the airport.
- T8 | obs=2026-02-03 03:00 | evt=2026-02-07 03:00 | status=scheduled | Mira mentioned an unrelated appointment at the online room.
- T9 | obs=2026-02-04 19:00 | evt=2026-02-07 19:00 | status=expired | Omar mentioned an unrelated reminder at the office.
- T10 | obs=2026-02-04 19:00 | evt=2026-02-06 19:00 | status=active | Mira mentioned an unrelated reminder at the lab.
- T11 | obs=2026-02-05 02:00 | evt=2026-02-06 02:00 | status=active | Omar mentioned an unrelated delivery at the lab.
- T12 | obs=2026-02-06 22:00 | evt=2026-02-08 22:00 | status=scheduled | Leo mentioned an unrelated report at the clinic.

## elapsed_time_reasoning

### elapsed_time_reasoning_0559

**Query:** How long did Nina's task take?

**Gold answer:** 3 days

**Gold evidence turns:** [1, 4]

**History excerpt:**

- T1 GOLD | obs=2026-01-22 18:00 | evt=2026-01-22 18:00 | status=active | Nina started the task on 2026-01-22 18:00.
- T2 | obs=2026-01-22 23:00 | evt=2026-01-25 23:00 | status=active | Leo mentioned an unrelated task at the client site.
- T3 | obs=2026-01-25 00:00 | evt=2026-01-29 00:00 | status=scheduled | Jordan mentioned an unrelated task at the clinic.
- T4 GOLD | obs=2026-01-25 18:00 | evt=2026-01-25 18:00 | status=active | Nina finished the task on 2026-01-25 18:00.
- T5 | obs=2026-02-02 17:00 | evt=2026-02-05 17:00 | status=expired | Alex mentioned an unrelated report at the airport.
- T6 | obs=2026-02-02 17:00 | evt=2026-02-03 17:00 | status=scheduled | Sam mentioned an unrelated delivery at the office.
- T7 | obs=2026-02-03 23:00 | evt=2026-02-08 23:00 | status=scheduled | Omar mentioned an unrelated meeting at the client site.
- T8 | obs=2026-02-05 01:00 | evt=2026-02-12 01:00 | status=scheduled | Mira mentioned an unrelated task at the library.
- T9 | obs=2026-02-05 02:00 | evt=2026-02-07 02:00 | status=expired | Sam mentioned an unrelated report at the clinic.
- T10 | obs=2026-02-10 18:00 | evt=2026-02-12 18:00 | status=active | Priya mentioned an unrelated task at the client site.
- T11 | obs=2026-02-10 19:00 | evt=2026-02-11 19:00 | status=scheduled | Leo mentioned an unrelated delivery at the clinic.
- T12 | obs=2026-02-14 23:00 | evt=2026-02-16 23:00 | status=active | Priya mentioned an unrelated task at the clinic.

### elapsed_time_reasoning_0505

**Query:** How long did Mira's report take?

**Gold answer:** 3 days

**Gold evidence turns:** [2, 4]

**History excerpt:**

- T1 | obs=2026-01-28 03:00 | evt=2026-01-30 03:00 | status=scheduled | Sam mentioned an unrelated reminder at the airport.
- T2 GOLD | obs=2026-01-28 18:00 | evt=2026-01-28 18:00 | status=active | Mira started the report on 2026-01-28 18:00.
- T3 | obs=2026-01-30 18:00 | evt=2026-01-31 18:00 | status=scheduled | Nina mentioned an unrelated task at the airport.
- T4 GOLD | obs=2026-01-31 18:00 | evt=2026-01-31 18:00 | status=active | Mira finished the report on 2026-01-31 18:00.
- T5 | obs=2026-02-05 19:00 | evt=2026-02-07 19:00 | status=scheduled | Priya mentioned an unrelated task at the lab.
- T6 | obs=2026-02-10 01:00 | evt=2026-02-16 01:00 | status=scheduled | Omar mentioned an unrelated appointment at the clinic.
- T7 | obs=2026-02-10 19:00 | evt=2026-02-17 19:00 | status=expired | Mira mentioned an unrelated meeting at the client site.
- T8 | obs=2026-02-10 21:00 | evt=2026-02-11 21:00 | status=scheduled | Omar mentioned an unrelated call at the library.
- T9 | obs=2026-02-10 22:00 | evt=2026-02-17 22:00 | status=active | Leo mentioned an unrelated delivery at the airport.
- T10 | obs=2026-02-12 02:00 | evt=2026-02-18 02:00 | status=scheduled | Nina mentioned an unrelated review at the clinic.
- T11 | obs=2026-02-14 00:00 | evt=2026-02-15 00:00 | status=scheduled | Nina mentioned an unrelated meeting at the clinic.
- T12 | obs=2026-02-14 23:00 | evt=2026-02-20 23:00 | status=expired | Leo mentioned an unrelated call at the clinic.

