// Plain-language + investigation-priority helpers.
// Pure functions of a source's merged GeoJSON feature props (lifecycle metrics
// + classification). Used by the detail panel (common-person view) and the
// overview counts. No backend changes — everything is derived client-side.

const cap = (s) => (s ? s.charAt(0).toUpperCase() + s.slice(1) : s);

// FRP (Fire Radiative Power, MW) -> heat intensity in plain words.
export function heatLevel(frp) {
  if (frp == null) return "Heat not measured";
  if (frp < 2) return "Faint heat";
  if (frp < 6) return "Moderate heat";
  if (frp < 15) return "Strong heat";
  return "Very intense heat";
}

// day_night_ratio = day / (day + night).
export function activityPattern(r) {
  if (r == null) return "Timing unknown";
  if (r >= 0.85) return "Seen mostly during the day";
  if (r <= 0.15) return "Seen mostly at night";
  if (r >= 0.35 && r <= 0.65) return "Burns round the clock, day and night";
  return "Seen day and night";
}

// span_days -> "about 13 months" / "about 3 weeks" / "about 5 days"
export function persistencePhrase(spanDays) {
  if (spanDays == null) return "duration unknown";
  const d = Math.round(spanDays);
  if (d >= 60) return `active for about ${Math.round(d / 30)} months`;
  if (d >= 14) return `active for about ${Math.round(d / 7)} weeks`;
  if (d <= 1) return "seen only briefly";
  return `active for about ${d} days`;
}

// bbox_growth_rate (km²/day)
export function spreadPhrase(growth) {
  if (growth == null) return "Location unknown";
  if (growth > 0.1) return "The burning area is growing — it may be spreading";
  if (growth < -0.1) return "The burning area is shrinking — likely dying down";
  return "Stays in one fixed spot";
}

// One-sentence, always-available headline (works even when the AI brief is offline).
export function plainSummary(m, classLabel) {
  const label = (classLabel ?? "a heat source").toLowerCase();
  const where = m.land_cover ? ` on ${String(m.land_cover).replace(/_/g, " ")}` : "";
  return `Likely ${label}${where}. ${cap(persistencePhrase(m.span_days))}, ${activityPattern(
    m.day_night_ratio
  ).toLowerCase()}, giving off ${heatLevel(m.frp_mean).toLowerCase()}.`;
}

// Investigation priority — explainable, matches the enforcement triage the PS asks for.
const LEVELS = {
  high: { label: "High priority", color: "#dc2626" },
  medium: { label: "Worth a look", color: "#d97706" },
  low: { label: "Routine", color: "#16a34a" },
};
function at(level, reason) {
  return { level, reason, ...LEVELS[level] };
}

export function priority(m) {
  const cls = m.predicted_class;
  const growing = (m.bbox_growth_rate ?? 0) > 0.1;
  if (m.is_unregistered) return at("high", "No facility on record — worth investigating");
  if (cls === "industrial_fire") return at("high", "Looks like an industrial accident — may need a response");
  if (cls === "wildfire" && growing) return at("high", "Wildfire footprint is growing — may be spreading");
  if (cls === "wildfire") return at("medium", "Active wildfire — keep watching");
  if ((m.frp_mean ?? 0) > 15) return at("medium", "Unusually intense heat for its type");
  return at("low", "Behaves like a known, registered site");
}
