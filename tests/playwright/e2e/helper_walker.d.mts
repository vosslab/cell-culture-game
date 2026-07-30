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
  affordance: {
    expectedKind: "active" | "candidate";
    renderedKind: string;
    indicatorWidth: number;
    indicatorStyle: string;
    candidateCount: number;
  };
  actionCue: {
    target: string | null;
    label: string | null;
    gesture: string | null;
    text: string;
  };
}

export declare function runProtocolWalk(page: Page, options: WalkOptions): Promise<WalkOutcome>;
