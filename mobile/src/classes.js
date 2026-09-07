// Locked classification legend — mirrors web/src/lib/classes.js.
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

export const classInfo = (k) => CLASS_LEGEND[k] ?? CLASS_LEGEND.unknown;
