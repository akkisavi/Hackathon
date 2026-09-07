# Demo script — SIH 2026, PS 26162

**Target: 3 minutes, 4 clicks.** One person narrates, one drives. Pre-script every click. Do not improvise navigation on stage.

---

## Before you start (do this 10 minutes before)

1. **Backend up:**
   ```
   cd backend && uvicorn app.main:app --port 8000
   ```
2. **Freeze the demo DB** so nothing depends on a live FIRMS pull or a rate-limited API:
   ```
   cd backend && python scripts/demo_snapshot.py load
   ```
3. **Web up:**
   ```
   cd web && npm run dev
   ```
   Open `http://localhost:5173`, confirm the map draws ~5,000 coloured dots over India.
4. **Mobile** (optional, if a second presenter shows it): `cd mobile && npx expo start`, Expo Go on a phone, `EXPO_PUBLIC_API_BASE_URL` = laptop LAN IP.
5. **LLM quota:** the incident-brief text uses Gemini's free tier. If it's rate-limited the classification, rationale, scores and every other panel still work — the brief just shows blank and regenerates later. Don't rely on a fresh brief generating live; open source #90047 once beforehand so its brief is cached.
6. **Video fallback:** screen-record this exact run once, the day before. Keep the file on the presenting laptop. If wifi dies, play the video and narrate over it.
7. Reset the view: all classes on, "unregistered only" off, "industrial infrastructure" off, date filter off.

---

## Click 1 — the map (~40 s)

**Do:** Land on the full India view, all sources shown.

**Say:**
> "This is every persistent thermal source over India — about five thousand, clustered from 647,000 NASA FIRMS detections. FIRMS gives all of these as identical red dots. We colour them by *what they are*.
> Green is agricultural burning — you can see it concentrated across the northern grain belt. Purple is mining — that's the eastern coal belt, Jharkhand and Odisha. Orange and amber are steel plants and brick kilns. Blue is gas flares. Circle size is detection count."

**Point at:** the purple cluster in the east, the green band in the north. The geography should look obviously right.

---

## Click 2 — one source, the explainable "why" (~45 s)

**Do:** Click a large source in the eastern belt (or search-zoom to a known one). The detail panel slides in from the right.

**Say:**
> "Click any source. This one is classified **mining**, 100% confidence, by the LightGBM model. Under 'Why' is the rule-engine read in plain English — persistent for over a year, static footprint, adjacent to a mapped mine. The class-score bars show the runner-up classes.
> Land cover at the site comes from ESA WorldCover. And this is the incident brief — the LLM takes the feature vector and the nearest facility name and writes an analyst brief: what it most likely is, the strongest evidence, a recommended action, and a caveat. It names the actual facility — 'Tata Iron and Steel, West Bokaro, 1.1 km away.' That's the difference between a coloured dot and something you can act on."

**If the brief is blank** (quota): say "the brief is generated on demand and the free-tier LLM quota resets daily — the classification and the explainable reasoning don't depend on it" and move on.

---

## Click 3 — natural-language query (~30 s)

**Do:** In the top bar, type: `unregistered brick kilns in West Bengal` → Enter.

**Say:**
> "You can also just ask the map. The model turns that into a structured filter — state, class, unregistered flag — it never writes raw SQL, it only fills in typed parameters. Here are the matches and a one-line summary."

**Point at:** the "interpreted" JSON and the summary line. The map narrows to the results.

Then click **clear**.

---

## Click 4 — the differentiator (~45 s)

**Do:** Left rail → turn on **"Industrial infrastructure"** (the grey haze appears — 42,255 OSM features). Then turn on **"Unregistered only"**. The map drops to ~27 white-ringed dots.

**Say:**
> "Here's every mapped industrial facility in the country. And here" — toggle unregistered — "are 27 thermal sources that behave exactly like a facility: persistent, stable, running for months — but they sit in the *gaps*, more than three kilometres from anything mapped, and they're in no flare catalogue.
> Click one." — open an unregistered source — "Persistent brick-kiln-type source, eight months, no facility on record. Under any existing system this is one more red dot. For an enforcement agency, this is the one you investigate."

**Close with:** "Everyone builds a fire classifier. We built the classifier plus the anomaly detector that finds what nobody's monitoring. Export to KML from the top bar and it drops straight into the evaluator's own GIS."

---

## Timing budget

| Segment | Target |
|---|---|
| Click 1 — map overview | 0:40 |
| Click 2 — source detail + brief | 1:25 |
| Click 3 — NL query | 1:55 |
| Click 4 — unregistered differentiator | 2:40 |
| Buffer / breathe | 3:00 |

---

## If something breaks

| Failure | Recovery |
|---|---|
| Map won't draw | Reload once. Still broken → switch to the video fallback, keep narrating. |
| API 500 / no data | You forgot `demo_snapshot.py load` or the backend isn't up. Video fallback. |
| LLM brief blank | Expected under quota. Say the line in Click 2 and move on — everything else works. |
| NL query errors | Skip Click 3, spend the time on Click 4. Don't debug on stage. |
| Wifi dead | Video fallback + narration. This is why you recorded it. |

---

## Rehearsal checklist (do this 5+ times)

- [ ] Full run under 3:15 without looking at notes
- [ ] Every presenter can drive the demo solo (in case someone's sick)
- [ ] Video fallback recorded and on the presenting laptop
- [ ] `demo_snapshot.py load` run fresh before every rehearsal
- [ ] Answers ready for: "where's your labelled data?" (weak supervision), "why not deep learning on imagery?" (backup slide B3), "what's your accuracy?" (93.8% on the checkable subset, + method), "is this real data?" (yes, all of it — backup B2)
