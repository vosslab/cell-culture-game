import type { Page } from "@playwright/test";

export interface WalkOptions {
  protocol: string;
  baseUrl: string;
  wrongOrder?: boolean;
  screenshotMode?: "per-step" | "per-interaction" | "per-click";
  resultsDir: string;
}

export interface WalkOutcome {
  passed: boolean;
  protocol: string;
  stepCount: number;
  stepsPassed: number;
  stepsFailed: number;
  isComplete: boolean;
  failureReason: string | null;
  errorCount: number;
  checkpointManifest: TargetCheckpoint[];
  checkpointManifestValid: boolean;
  diagnostics: string;
}

export interface TargetCheckpoint {
  protocol: string;
  step: string;
  target: string;
  gesture: string;
  interactionIndex: number;
  screenshot: string;
  visibleTargetBounds: {
    x: number;
    y: number;
    width: number;
    height: number;
    viewportWidth: number;
    viewportHeight: number;
  };
}

export declare function runProtocolWalk(page: Page, options: WalkOptions): Promise<WalkOutcome>;
