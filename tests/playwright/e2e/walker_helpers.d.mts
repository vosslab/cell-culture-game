import type { Page } from "@playwright/test";

export type VisibleGesture = "click" | "drag" | "adjust" | "select" | "type";

export interface ReadonlyGameState {
  activeStepId: string | null;
  interactionIndex: number;
  activeScene: string | null;
  completedSteps: string[];
  selectedTool: string | null;
  heldLiquid: unknown;
  wrongOrderClicks: number;
  stepsOutOfOrder: number;
  isComplete: boolean;
  activeTarget: string | null;
  activeGesture: VisibleGesture | null;
}

export interface WalkerReport {
  summary: { totalClicks: number };
  info(message: string): void;
}

export declare function readGameState(page: Page): Promise<ReadonlyGameState>;

export declare function openVisibleActionHint(page: Page): Promise<void>;

export declare function clickTargetAndWaitProgress(
  page: Page,
  itemId: string,
  report: WalkerReport,
): Promise<unknown>;

export declare function adjustCommitAndWaitProgress(
  page: Page,
  numericValue: string,
  report: WalkerReport,
): Promise<unknown>;

export declare function waitForVisibleTimedWait(
  page: Page,
  stepName: string,
  resultsDir: string,
  report: WalkerReport,
  waitBudgetMs?: number,
): Promise<unknown>;
