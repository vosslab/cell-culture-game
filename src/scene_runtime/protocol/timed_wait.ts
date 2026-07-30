// Browser-clock projection for authored laboratory durations. TimedWait keeps
// the authored duration as semantic data, while the interactive simulation must
// remain completable through visible UI (including 24- and 48-hour lab phases).

const MS_PER_LAB_HOUR = 300;
const MIN_RUNTIME_DELAY_MS = 300;
const MAX_RUNTIME_DELAY_MS = 600;

export function timed_wait_runtime_delay_ms(duration_min: number): number {
  if (!Number.isFinite(duration_min) || duration_min <= 0) {
    throw new Error(`TimedWait duration_min must be a positive finite number: ${duration_min}`);
  }
  const projected = (duration_min / 60) * MS_PER_LAB_HOUR;
  return Math.min(MAX_RUNTIME_DELAY_MS, Math.max(MIN_RUNTIME_DELAY_MS, projected));
}
