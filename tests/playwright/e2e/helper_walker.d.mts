import type { Page } from "@playwright/test";

export interface WalkOptions {
  protocol: string;
  baseUrl: string;
  wrongOrder?: boolean;
  screenshotMode?: "per-step" | "per-interaction" | "per-click";
  resultsDir: string;
  authoredProtocol?: {
    protocol_type: "mini_protocol" | "sequence_runner";
    steps?: ReadonlyArray<{
      step_name: string;
      prompt: string;
      sequence: ReadonlyArray<{ instruction: string; hint: string }>;
    }>;
  } | null;
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
    isInteractionEnvelope: boolean;
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
    value: string | null;
    text: string;
    targetText: string;
    progress: string;
    message: string;
    goal: string;
    hint: string;
    hintOpen: boolean;
  };
  effectiveClickTarget: {
    authoredDomTarget: string | null;
    hitDomTarget: string | null;
    coreWidth: number;
    coreHeight: number;
  };
  declaredStateBefore: DeclaredStateEvidence;
  declaredStateAfter: DeclaredStateEvidence;
  stateAfterScreenshot?: string;
  timedWait?: {
    screenshot: string;
    observedDurationMs: number;
    waitBudgetMs: number;
  };
}

export interface DeclaredStateEvidence {
  revision: number;
  snapshot: Record<string, Record<string, string | number | boolean>> | null;
  lastDelta: {
    target: string;
    before: Record<string, string | number | boolean>;
    after: Record<string, string | number | boolean>;
  } | null;
  stateDeltaLog?: Array<{
    target: string;
    before: Record<string, string | number | boolean>;
    after: Record<string, string | number | boolean>;
  }> | null;
  activeStateWrites?: Array<{
    target: string;
    state: Record<string, string | number | boolean>;
  }> | null;
}

export declare function runProtocolWalk(page: Page, options: WalkOptions): Promise<WalkOutcome>;

export declare function validateDeclaredStateMutation(
  before: {
    stateRevision: number;
    lastStateDelta: DeclaredStateEvidence["lastDelta"];
    activeStateWrites: NonNullable<DeclaredStateEvidence["activeStateWrites"]>;
    declaredState: NonNullable<DeclaredStateEvidence["snapshot"]>;
  },
  after: {
    stateRevision: number;
    lastStateDelta: DeclaredStateEvidence["lastDelta"];
    activeStateWrites: NonNullable<DeclaredStateEvidence["activeStateWrites"]>;
    declaredState: NonNullable<DeclaredStateEvidence["snapshot"]>;
  },
  target: string,
  step: string,
  interactionIndex: number,
): void;

export declare function shouldAwaitTimedStateWrite(
  gameState: { activeStateWrites: DeclaredStateEvidence["activeStateWrites"] },
  timedWaitVisible: boolean,
): boolean;
