// Runnable check: `node src/lib/humanize.selfcheck.mjs`. Fails loudly if the
// plain-language buckets or the priority ladder break.
import assert from "node:assert/strict";
import { heatLevel, activityPattern, persistencePhrase, spreadPhrase, priority } from "./humanize.js";

assert.equal(heatLevel(1), "Faint heat");
assert.equal(heatLevel(4), "Moderate heat");
assert.equal(heatLevel(60), "Very intense heat");

assert.equal(activityPattern(1.0), "Seen mostly during the day");
assert.equal(activityPattern(0.0), "Seen mostly at night");
assert.equal(activityPattern(0.5), "Burns round the clock, day and night");

assert.match(persistencePhrase(400), /months/);
assert.match(persistencePhrase(20), /weeks/);
assert.match(persistencePhrase(5), /5 days/);

assert.match(spreadPhrase(0.5), /growing/);
assert.match(spreadPhrase(-0.5), /shrinking/);
assert.match(spreadPhrase(0), /fixed spot/);

// priority ladder: unregistered beats class; industrial fire high; calm flare low
assert.equal(priority({ is_unregistered: true, predicted_class: "gas_flare" }).level, "high");
assert.equal(priority({ predicted_class: "industrial_fire" }).level, "high");
assert.equal(priority({ predicted_class: "wildfire", bbox_growth_rate: 0.5 }).level, "high");
assert.equal(priority({ predicted_class: "wildfire" }).level, "medium");
assert.equal(priority({ predicted_class: "gas_flare", frp_mean: 3 }).level, "low");

console.log("humanize self-check OK");
