export function getSimilarityLevel(value) {
  if (value >= 0.7) return "high";
  if (value >= 0.4) return "moderate";
  return "low";
}

export function getPercentageLevel(value) {
  if (value > 50) return "high";
  if (value > 25) return "moderate";
  return "low";
}
