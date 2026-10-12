export const isNumber = value => typeof value === 'number' && Number.isFinite(value);
export function orderedRuns(runs, metric) {
  return [...runs].sort((a, b) => {
    const av = a.metrics[metric.id], bv = b.metrics[metric.id];
    if (!isNumber(av)) return isNumber(bv) ? 1 : 0;
    if (!isNumber(bv)) return -1;
    return (bv - av) * (metric.higher_is_better ? 1 : -1);
  });
}
export function compareDimensions(baseline, target, metric) {
  if (!baseline || !target || baseline.comparison_group !== target.comparison_group) return [];
  const base = new Map(baseline.dimensions.map(d => [d.id, d]));
  return target.dimensions.flatMap(d => {
    const b = base.get(d.id), av = b?.metrics[metric.id], bv = d.metrics[metric.id];
    if (!isNumber(av) || !isNumber(bv)) return [];
    return [{...d, baseline: av, target: bv, delta: bv - av, advantage: (bv - av) * (metric.higher_is_better ? 1 : -1)}];
  });
}
export function unionDimensions(runs) {
  const dimensions = new Map();
  for (const run of runs) for (const d of run.dimensions) if (!dimensions.has(d.id)) dimensions.set(d.id, d);
  return [...dimensions.values()];
}
export function metricScale(metric, values) {
  if (metric.range) return metric.range;
  const nums = values.filter(isNumber);
  return [Math.min(0, ...nums), Math.max(1, ...nums)];
}
export function barWidth(value, scale) {
  if (!isNumber(value)) return 0;
  return Math.max(0, Math.min(100, (value - scale[0]) / (scale[1] - scale[0]) * 100));
}
