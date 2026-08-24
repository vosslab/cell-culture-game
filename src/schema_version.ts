// One repository-wide version for persisted data whose shape can outlive the
// current build. Do not add per-surface schema counters; bump this value when a
// persisted boundary becomes incompatible with a newer runtime.
export const SCHEMA_VERSION = 1;
