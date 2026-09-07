# Pitch deck — SIH 2026, PS 26162

**AI-Based Detection and Classification of Industrial Fires and Persistent Thermal Sources**
NTRO · Disaster Management · Software

Format: ~12 slides, 8 min talk + 4 min live demo + Q&A. One person drives slides, one drives the demo.
Every slide below has a **headline** (put this big on the slide), **on-slide** (the few things that go on the slide), and **say** (speaker notes — do not put on the slide).

---

## Slide 1 — Title

- **Headline:** FIRMS tells you *where* something is hot. We tell you *what* it is.
- **On-slide:** Project name · team names · PS 26162 · one line: "AI geospatial system for industrial fire & persistent thermal-source monitoring."
- **Say:** "Problem statement 26162 from NTRO. We built an AI system that takes NASA's raw thermal-anomaly feed and turns it into an enforcement-grade map of what is actually burning across India — and flags the thermal sources that match no facility on record."

---

## Slide 2 — The problem

- **Headline:** A satellite sees heat. It cannot see intent.
- **On-slide:** A screenshot of raw FIRMS points over India — all the same colour. Caption: "NASA FIRMS: 647,000 thermal detections over India in 2025. Every one is an identical red dot."
- **Say:** "FIRMS gives a latitude, a longitude, a brightness temperature, an FRP value, a confidence score, a day/night flag. That's it. A refinery gas flare, a steel plant, a brick kiln, stubble burning, a coal-seam fire, and a real forest wildfire all arrive as the same red dot. For a disaster-management or enforcement agency that is close to useless — you cannot triage, you cannot investigate, you cannot prioritise."

---

## Slide 3 — Why NTRO cares

- **Headline:** Three questions a red dot cannot answer.
- **On-slide:**
  1. Is this an accident that needs an emergency response, or a facility operating normally?
  2. Is that persistent heat a registered plant — or an unregistered one nobody is monitoring?
  3. Is this a wildfire spreading toward infrastructure, or an industrial process?
- **Say:** "Critical-infrastructure safety, environmental enforcement, and disaster response all need the answer to 'what is it'. The third one — unregistered persistent sources — is the one with no existing tool. That's our differentiator, and I'll come back to it."

---

## Slide 4 — The core insight

- **Headline:** How something behaves over time beats how it looks in one image.
- **On-slide:** the discriminator table (trimmed):

  | Source | Day/Night | Persistence | FRP stability | Footprint |
  |---|---|---|---|---|
  | Gas flare | ~50/50, constant | years, one point | very stable | tiny, fixed |
  | Industrial fire (accident) | sudden, transient | hours–days | spikes then dies | small, fixed |
  | Brick kiln | daytime, cyclic | months, seasonal | moderate | small cluster |
  | Agricultural burning | strongly daytime | days, Oct–Nov | high variance | scattered, moves |
  | Mining / coal fire | 24/7 | years | very low variance | fixed |
  | Wildfire | variable | days–weeks | grows then decays | large, expanding |

- **Say:** "This table is most of the AI. Diurnal signature plus persistence plus FRP stability is a stronger, cheaper, and — critically for a government panel — *explainable* discriminator than a black-box CNN on raw imagery. A gradient-boosted model on these engineered features trains in seconds and every prediction comes with a plain-language reason."

---

## Slide 5 — Data fusion

- **Headline:** Four independent signals, one entity.
- **On-slide:** a simple 4-into-1 diagram.
  - **NASA FIRMS** — VIIRS thermal detections (live + full-year 2025 archive)
  - **OpenStreetMap** — 42,255 industrial / power / mining features across India
  - **EOG / VIIRS Nightfire** flare catalogue — 542 catalogued Indian flares, 2012–2019
  - **ESA WorldCover** 10 m land cover + **Sentinel-2** imagery — via Google Earth Engine
- **Say:** "We fuse all four. FIRMS is the detection. OSM and the flare catalogue tell us whether there's a facility here. WorldCover tells us if it's cropland or built-up. Sentinel-2 lets us check for an actual burn scar. No single source could do this."

---

## Slide 6 — The unit of the system

- **Headline:** We don't reason about pixels. We reason about *thermal sources*.
- **On-slide:** one hotspot's lifecycle — "First seen, last seen, 385 days, seen on 68 distinct days, 137 detections, day/night 0.01, FRP mean 1.3 MW, footprint 5 km², growth −0.01 km²/day." Small chart if possible.
- **Say:** "Raw detections get clustered — DBSCAN, roughly 1 km, with a persistence filter that drops one-off specks. What comes out is a *thermal source*: a fixed location with a lifecycle. 647,000 detections collapse to 4,984 persistent thermal sources over India. Every downstream decision is about these entities."

---

## Slide 7 — Classification

- **Headline:** Seven classes. Every one explainable.
- **On-slide:**
  - Classes: industrial fire · gas flare · steel / smelter · brick kiln · agricultural burning · mining · wildfire
  - Stage 1 — rule engine (encodes the Slide 4 table, fully transparent)
  - Stage 2 — LightGBM, **weak supervision** (flare catalogue + OSM proximity + land cover + rule engine as noisy labels)
  - Current India breakdown: agricultural burning 3,736 · brick kiln 691 · steel 198 · mining 165 · gas flare 128 · wildfire 34 · industrial fire 32
- **Say:** "Two stages. The rule engine alone is 60–70% and 100% explainable — it never gets cut. LightGBM refines it. We say 'weak supervision' out loud because it answers the obvious question, 'where's your labelled training data?' — we don't have hand labels, we derive them from authoritative reference data the model never sees directly."

---

## Slide 8 — The differentiator  ⭐

- **Headline:** 27 persistent thermal sources that match no facility on record.
- **On-slide:** the map filtered to "unregistered only" — ~27 white-ringed dots clustered in the eastern brick-kiln and coal belt. Caption: "Persistent + stable + facility-type behaviour + > 3 km from any mapped facility + absent from every flare catalogue."
- **Say:** "Everyone can build a fire classifier. We built the classifier *plus* an anomaly detector. An Isolation Forest over the behavioural feature space flags sources that behave exactly like a facility — persistent, stable, running for months — but sit far from every mapped facility and every catalogued flare. That is the enforcement signal NTRO actually needs: 'this location has been burning steadily for eight months and there is no record of a plant here. Send someone.'"

---

## Slide 9 — Confirmation + the AI layer

- **Headline:** Cross-check the imagery. Then write the brief.
- **On-slide:**
  - **Sentinel-2 NBR** — for every wildfire prediction, compare pre/post-fire imagery. dNBR ≥ 0.27 confirms a burn scar; near zero contradicts it. Result: 8 of 34 wildfire predictions downgraded — persistent sources that only *looked* like wildfires.
  - **LLM incident brief** — per source: feature vector + class probabilities + nearest facility name → a 3–4 sentence analyst brief with a recommended action and a caveat.
  - **Natural-language query** — "unregistered brick kilns in West Bengal" → structured filter → results + summary.
- **Say:** "Sentinel-2 is the reality check — it caught eight false wildfires. The LLM turns a coloured dot into something an analyst can act on: it names the nearest facility, recommends a specific check, and states what could make the call wrong. And you can just ask the map a question in English."

---

## Slide 10 — LIVE DEMO

- **On-slide:** just the word "Demo" and the URL. Switch to the app.
- See `docs/demo-script.md` for the exact sequence. Four clicks, ~3 minutes.

---

## Slide 11 — Does it work?

- **Headline:** 93.8% on every source we can independently check.
- **On-slide:** the confusion matrix from `ml/validation_report.md` + one line on method: "Reference labels derived from proximity to the EOG flare catalogue and the OSM infrastructure registry — not hand annotation. 96 sources labelable this way; classes without a reliable reference signal are excluded."
- **Say:** "We're honest about this number. We don't have a hand-labelled truth set, so we validate against independent authoritative data: is a source next to a catalogued multi-year flare classified as a flare? Next to a mapped quarry, as mining? On that checkable subset, 93.8%. The QGIS ground-truth pass against named facilities — Jamnagar, a Punjab stubble window — is [done / in progress]."

---

## Slide 12 — Impact + roadmap

- **Headline:** From a red dot to a work order.
- **On-slide:**
  - **Deliverable i** — industrial vs natural fire classification ✓ (explainable, validated)
  - **Deliverable ii** — PostGIS storage + map-overlay GIS ✓ (web + mobile, GeoJSON/KML export)
  - **Roadmap:** SMS/email alerts to district authorities · data.gov.in / Bhuvan cross-validation · continuous archive ingestion · confidence-weighted enforcement queue
- **Say:** "Both stated deliverables are met and demoable. The natural next step is closing the loop — pushing the unregistered-source flags straight to the relevant district office as an alert, and folding in India's own government infrastructure datasets to cut the false-positive rate further."

---

## Backup slides (only if asked)

**B1 — Stack.** FastAPI + PostGIS (hosted) · React + MapLibre GL · React Native (Expo) · scikit-learn + LightGBM · Google Earth Engine · Celery/Redis · Gemini via an OpenAI-compatible endpoint (provider-swappable).

**B2 — What's real vs mocked.** All data is real: 647k live + archive FIRMS detections, the full India OSM extract, the EOG flare catalogue, live WorldCover and Sentinel-2 sampling. No synthetic data. The demo DB is a frozen snapshot so a live API rate-limit can't break the presentation.

**B3 — Why not a CNN on imagery?** Slower to train, needs labelled data we don't have, not explainable to a government panel, and — the key point — a single image can't distinguish a flare that's burned for five years from an accident that started yesterday. Behaviour over time can.
