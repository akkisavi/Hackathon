// Locked classification legend — colours are referenced by the map paint
// expression and the UI. Keep in sync with the backend CLASSES tuple.
export const CLASS_LEGEND = {
  gas_flare: { label: "Gas flare", color: "#38bdf8" },
  industrial_fire: { label: "Industrial fire", color: "#f472b6" },
  steel_smelter: { label: "Steel / smelter", color: "#fb923c" },
  brick_kiln: { label: "Brick kiln", color: "#fbbf24" },
  agricultural_burning: { label: "Agricultural burning", color: "#4ade80" },
  mining: { label: "Mining", color: "#a78bfa" },
  wildfire: { label: "Wildfire", color: "#ef4444" },
  unknown: { label: "Unclassified", color: "#71717a" },
};

export const CLASS_KEYS = Object.keys(CLASS_LEGEND);

export const INFRA_LEGEND = {
  industrial: { label: "Industrial area", color: "#64748b" },
  power_plant: { label: "Power plant", color: "#eab308" },
  quarry: { label: "Mine / quarry", color: "#a16207" },
  works: { label: "Works", color: "#0ea5e9" },
};

// MapLibre "match" expression: predicted_class -> colour, with a fallback.
export const classColorExpr = [
  "match",
  ["get", "predicted_class"],
  ...CLASS_KEYS.flatMap((k) => [k, CLASS_LEGEND[k].color]),
  CLASS_LEGEND.unknown.color,
];
