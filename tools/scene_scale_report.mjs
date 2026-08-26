// tools/scene_scale_report.mjs
//
// Developer tool: reports vertical scale health for one or all scenes.
//
// For each scene, the layout pipeline measures the total vertical content
// (reflowTotalContent) and the available scene range (reflowSceneRangeTop /
// reflowSceneRangeBottom). When content exceeds the range, a terminal uniform
// object rescale compresses everything to fit. This tool reports the
// PIPELINE'S ACTUAL applied scale (reflowUniformScale), not a recomputed
// estimate, so the dense-scene values match the engine's corrected formula:
//   applied = (sceneRange - fixedOverhead) / (totalContent - fixedOverhead)
// clamped to [UNIFORM_RESCALE_MIN_SCALE, 1].
//
// Run (requires generated/ to exist -- run bash pipeline/build_generated.sh first):
//   node --import tsx tools/scene_scale_report.mjs --scene <name>
//   node --import tsx tools/scene_scale_report.mjs --all
//   node --import tsx tools/scene_scale_report.mjs --write-census-report
//
// Exit codes:
//   0: success (report produced, even if scenes are overloaded)
//   1: error (unknown scene name, missing generated/, bad args)
//
// Note: normal report modes are read-only. --write-census-report writes the
// reproducible structural-census evidence pair under
// docs/active_plans/reports/ only; it never writes to generated/ or dist/.

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { runPipeline } from "../src/scene_runtime/layout/index.ts";
import { SCENES } from "../generated/scenes.js";
import { OBJECT_LIBRARY, ASSET_SPECS } from "../generated/object_library.js";
import { SVG_MANIFEST } from "../generated/svg_manifest.js";
import { parseSvgTree } from "./svg_census_xml.mjs";

//============================================
// Constants
//============================================

// Canonical 16:9 viewport -- matches precompute_layout.mjs.
const VIEWPORT = { w: 1920, h: 1080 };

// Health label thresholds (advisory only; not a gate).
// appliedScale >= 0.85: healthy (content fits with room to spare)
// 0.70 <= appliedScale < 0.85: dense (tight but survivable)
// appliedScale < 0.70: overloaded (uniform rescale will compress objects significantly)
const HEALTHY_THRESHOLD = 0.85;
const DENSE_THRESHOLD = 0.7;

const ASSET_NAME_PATTERN = /^[a-z0-9_]+$/;
const EQUIPMENT_DIR = "assets/equipment";
const REPORT_DIR = "docs/active_plans/reports";
const REPORT_BASENAME = "svg_visual_size_flatness_census";
const REPO_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

//============================================
// Run the layout pipeline for one scene
//============================================

// Returns the PipelineResult for a single scene at the canonical viewport.
// Read-only: does not write any files.
function runScenePipeline(scene) {
  const result = runPipeline(scene, {
    library: OBJECT_LIBRARY,
    assets: ASSET_SPECS,
    viewport: VIEWPORT,
  });
  return result;
}

//============================================
// Scale health label
//============================================

// Returns a health label string based on the applied uniform scale.
// >= HEALTHY_THRESHOLD -> healthy
// >= DENSE_THRESHOLD   -> dense
// < DENSE_THRESHOLD    -> overloaded
function healthLabel(appliedScale) {
  if (appliedScale >= HEALTHY_THRESHOLD) return "healthy";
  if (appliedScale >= DENSE_THRESHOLD) return "dense";
  return "overloaded";
}

//============================================
// Extract per-scene scale metrics from pipeline result
//============================================

// Computes the key metrics for a scene from its PipelineResult:
//   totalContent: measured sum of per-group content extents
//   sceneRange: bottom - top of the reflow range
//   overflowRatio: totalContent / sceneRange
//   appliedScale: the pipeline's actual uniform rescale factor (reflowUniformScale);
//                 1.0 when no overflow (corrected formula, not the old estimate)
//   overflow: true when content exceeded range before rescale
// Returns an object with these fields.
function computeScaleMetrics(result) {
  const total = result.reflowTotalContent;
  const rangeTop = result.reflowSceneRangeTop;
  const rangeBottom = result.reflowSceneRangeBottom;
  const sceneRange = rangeBottom - rangeTop;

  // Guard: a degenerate scene with zero range or zero content is trivially healthy.
  if (sceneRange <= 0 || total <= 0) {
    return {
      totalContent: total,
      sceneRange: sceneRange,
      overflowRatio: 0,
      appliedScale: 1,
      overflow: false,
      labelDominant: false,
    };
  }

  const overflowRatio = total / sceneRange;
  // Use the pipeline's actual applied scale rather than recomputing the old
  // sceneRange/totalContent estimate. reflowUniformScale is 1.0 when no overflow
  // ran and the corrected clamped factor when the rescale fired.
  const appliedScale = result.reflowUniformScale ?? 1;

  return {
    totalContent: total,
    sceneRange: sceneRange,
    overflowRatio: overflowRatio,
    appliedScale: appliedScale,
    overflow: result.reflowOverflow,
    labelDominant: result.labelDominant ?? false,
  };
}

//============================================
// Find the heaviest vertical band group
//============================================

// A band group is the set of zones that share one vertical band (side-by-side
// zones at the same authored vertical extent are merged into one group by the
// reflow logic). The heaviest group is the one with the largest contentExtent,
// since that group drives the overflow.
//
// We reconstruct band groups from the zoneBands on the PipelineResult, grouping
// by identical [top, bottom] pairs (zones in the same group get the same
// computed top/bottom from reflow_zones). For each group we collect:
//   - zone ids
//   - the group's contentExtent (same as the heaviest member's computed height)
//   - total tier count across all member zones
//   - the 2-3 tallest contributing items (placement_name + _combinedHeight)
//
// Returns null if the scene has no zone bands (empty scene).
function findHeaviestBandGroup(result) {
  const zoneBands = result.zoneBands;
  if (!zoneBands || zoneBands.size === 0) return null;

  // Index computed items by placement_name so we can look up _combinedHeight.
  const itemByName = new Map();
  for (const item of result.final) {
    itemByName.set(item.placement_name, item);
  }
  // _combinedHeight is set in measure-vertical and threaded through all subsequent
  // phases, so result.final items carry it.

  // Group zones by their computed [top, bottom] band (same computed extent = same group).
  // Use a string key "top|bottom" for grouping.
  const groupMap = new Map();
  for (const [zoneId, band] of zoneBands) {
    const key = `${band.top.toFixed(4)}|${band.bottom.toFixed(4)}`;
    const existing = groupMap.get(key);
    if (existing) {
      existing.zoneIds.push(zoneId);
      existing.tiers.push(...band.tiers);
    } else {
      groupMap.set(key, {
        zoneIds: [zoneId],
        tiers: [...band.tiers],
        // Computed band height = contentExtent of this group's representative member.
        // All members in a group share the same [top, bottom], so any member's
        // (bottom - top) is the group's computed height.
        computedHeight: band.bottom - band.top,
        bandTop: band.top,
        bandBottom: band.bottom,
      });
    }
  }

  // Find the group with the largest computed height (= heaviest contentExtent).
  let heaviest = null;
  for (const group of groupMap.values()) {
    if (!heaviest || group.computedHeight > heaviest.computedHeight) {
      heaviest = group;
    }
  }
  if (!heaviest) return null;

  // Collect all placement names across the group's tiers and find their _combinedHeight.
  const placementsInGroup = [];
  for (const tier of heaviest.tiers) {
    for (const pname of tier.placementNames) {
      const item = itemByName.get(pname);
      const combined = item ? (item._combinedHeight ?? 0) : 0;
      placementsInGroup.push({ name: pname, combinedHeight: combined });
    }
  }

  // Sort by combinedHeight descending to surface the top contributors.
  placementsInGroup.sort((a, b) => b.combinedHeight - a.combinedHeight);
  const topItems = placementsInGroup.slice(0, 3);

  return {
    zoneIds: heaviest.zoneIds,
    computedHeight: heaviest.computedHeight,
    tierCount: heaviest.tiers.length,
    topItems,
  };
}

//============================================
// Single-scene detailed report
//============================================

// Print a detailed breakdown for one scene: scale metrics plus a per-zone-group
// breakdown so a writer sees which zone is overfull.
function reportSingleScene(sceneName) {
  const scene = SCENES[sceneName];
  if (!scene) {
    process.stderr.write(`Error: unknown scene "${sceneName}"\n`);
    process.stderr.write(`Known scenes: ${Object.keys(SCENES).sort().join(", ")}\n`);
    process.exit(1);
  }

  const result = runScenePipeline(scene);
  const metrics = computeScaleMetrics(result);
  const heavy = findHeaviestBandGroup(result);

  const label = healthLabel(metrics.appliedScale);
  const labelStr = label.toUpperCase().padEnd(10);

  process.stdout.write(`Scene: ${sceneName}\n`);
  process.stdout.write(`  totalContent   : ${metrics.totalContent.toFixed(2)}\n`);
  process.stdout.write(`  sceneRange     : ${metrics.sceneRange.toFixed(2)}\n`);
  process.stdout.write(`  overflow ratio : ${metrics.overflowRatio.toFixed(2)}`);
  if (metrics.overflow) {
    process.stdout.write(`  [OVERFLOW]\n`);
  } else {
    process.stdout.write(`\n`);
  }
  process.stdout.write(`  applied scale  : ${metrics.appliedScale.toFixed(3)}\n`);
  process.stdout.write(`  label dominant : ${metrics.labelDominant ? "yes" : "no"}\n`);
  process.stdout.write(`  health         : ${labelStr}\n`);

  if (!heavy) {
    process.stdout.write(`  (no zone bands computed)\n`);
    return;
  }

  process.stdout.write(`\n`);
  process.stdout.write(`Heaviest band group:\n`);
  process.stdout.write(`  zones          : ${heavy.zoneIds.join(", ")}\n`);
  process.stdout.write(`  computed height: ${heavy.computedHeight.toFixed(2)}\n`);
  process.stdout.write(`  tier count     : ${heavy.tierCount}\n`);
  if (heavy.topItems.length > 0) {
    process.stdout.write(`  top contributors (placement + combinedHeight):\n`);
    for (const item of heavy.topItems) {
      process.stdout.write(`    ${item.name.padEnd(45)} ${item.combinedHeight.toFixed(2)}\n`);
    }
  }

  // Per-zone band breakdown: show each zone's tier rows and their items.
  process.stdout.write(`\nZone band detail:\n`);
  const zoneBands = result.zoneBands;
  if (zoneBands && zoneBands.size > 0) {
    // Sort zones by band top for readable top-to-bottom output.
    const sortedBands = [...zoneBands.entries()].sort((a, b) => a[1].top - b[1].top);
    for (const [zoneId, band] of sortedBands) {
      const bandH = band.bottom - band.top;
      process.stdout.write(
        `  [${zoneId}]  top=${band.top.toFixed(2)}  ` +
          `bottom=${band.bottom.toFixed(2)}  height=${bandH.toFixed(2)}\n`,
      );
      for (const tier of band.tiers) {
        const namesStr = tier.placementNames.join(", ");
        process.stdout.write(
          `    tier ${tier.depthTier}  ` +
            `rowHeight=${tier.rowHeight.toFixed(2)}  items: ${namesStr}\n`,
        );
      }
    }
  }
}

//============================================
// All-scenes table report
//============================================

// Row data for the --all table.
function buildAllRows() {
  const rows = [];
  for (const [sceneName, scene] of Object.entries(SCENES)) {
    const result = runScenePipeline(scene);
    const metrics = computeScaleMetrics(result);
    const heavy = findHeaviestBandGroup(result);
    rows.push({ sceneName, metrics, heavy });
  }
  // Sort densest first (smallest appliedScale first, then by name).
  rows.sort((a, b) => {
    const diff = a.metrics.appliedScale - b.metrics.appliedScale;
    if (Math.abs(diff) > 1e-9) return diff;
    return a.sceneName < b.sceneName ? -1 : 1;
  });
  return rows;
}

// Print the --all summary table and a short count summary.
function reportAllScenes() {
  const rows = buildAllRows();

  // Column widths (fixed): scene name 55, ratio 6, scale 7, ldom 4, health 10.
  const COL_SCENE = 55;
  const COL_RATIO = 6;
  const COL_SCALE = 7;
  const COL_LDOM = 4; // label dominant: "yes" or "no"
  const COL_HEALTH = 10;
  const COL_HEAVY = 30; // heaviest zone group zone ids (truncated)

  // Header
  const header =
    "SCENE".padEnd(COL_SCENE) +
    "  " +
    "RATIO".padStart(COL_RATIO) +
    "  " +
    "SCALE".padStart(COL_SCALE) +
    "  " +
    "LDOM".padEnd(COL_LDOM) +
    "  " +
    "HEALTH".padEnd(COL_HEALTH) +
    "  " +
    "HEAVIEST BAND";
  const separator = "-".repeat(header.length);
  process.stdout.write(header + "\n");
  process.stdout.write(separator + "\n");

  let overloaded = 0;
  let dense = 0;
  let healthy = 0;

  for (const row of rows) {
    const { sceneName, metrics, heavy } = row;
    const label = healthLabel(metrics.appliedScale);
    if (label === "overloaded") overloaded++;
    else if (label === "dense") dense++;
    else healthy++;

    // Heaviest band: show zone ids, truncated to fit column.
    let heavyStr = "";
    if (heavy) {
      heavyStr = heavy.zoneIds.join(",");
      if (heavyStr.length > COL_HEAVY) {
        heavyStr = heavyStr.slice(0, COL_HEAVY - 3) + "...";
      }
    }

    // Overflow marker on ratio column.
    const ratioStr = metrics.overflowRatio.toFixed(2) + (metrics.overflow ? "*" : " ");
    const scaleStr = metrics.appliedScale.toFixed(3);
    // Label-dominant flag: "yes" when the scene's label strip is visually dominant.
    const ldomStr = metrics.labelDominant ? "yes" : "no";
    const labelStr = label.toUpperCase();

    process.stdout.write(
      sceneName.padEnd(COL_SCENE) +
        "  " +
        ratioStr.padStart(COL_RATIO + 1) +
        "  " +
        scaleStr.padStart(COL_SCALE) +
        "  " +
        ldomStr.padEnd(COL_LDOM) +
        "  " +
        labelStr.padEnd(COL_HEALTH) +
        "  " +
        heavyStr +
        "\n",
    );
  }

  process.stdout.write(separator + "\n");
  process.stdout.write(
    `  * = overflow (terminal uniform rescale applied)\n` +
      `  overloaded: ${overloaded}  dense: ${dense}  healthy: ${healthy}  total: ${rows.length}\n`,
  );
}

//============================================
// SVG visual-size and flatness census
//============================================

// The census intentionally records structural evidence, not a verdict on whether
// an object is well drawn. "root_paint_cluster_count" is a reproducible inventory
// signal: the number of visible root-level paint clusters after definitions and
// hidden semantic anchors are excluded. It must not be read as a flatness or
// volume score: a well-constructed SVG may deliberately use one root group.
function analyzeSvgMarkup(markup) {
  const root = parseSvgTree(markup);
  const visibleNodes = walkVisibleSvgNodes(root);
  const rootPaintClusterCount = root.children.filter(function isVisibleRootCluster(child) {
    return (
      isPaintClusterTag(child.tag) &&
      !isSemanticAnchor(child) &&
      subtreeContainsVisiblePaint(child, false)
    );
  }).length;
  const ellipsePresent = visibleNodes.some(function isVisibleEllipse(node) {
    return node.tag === "ellipse";
  });
  const rotationOrSkew = visibleNodes.some(function hasRotationOrSkew(node) {
    const transform = node.attributes.transform;
    return transform !== undefined && /\b(?:rotate|skewX|skewY)\s*\(/i.test(transform);
  });

  return { rootPaintClusterCount, ellipsePresent, rotationOrSkew };
}

const PAINT_TAGS = new Set([
  "path",
  "rect",
  "circle",
  "ellipse",
  "line",
  "polyline",
  "polygon",
  "use",
  "image",
  "text",
]);

function isHiddenNode(node) {
  const display = node.attributes.display?.trim().toLowerCase();
  const visibility = node.attributes.visibility?.trim().toLowerCase();
  const style = node.attributes.style?.toLowerCase() ?? "";
  return (
    display === "none" ||
    visibility === "hidden" ||
    /(?:^|;)\s*(?:display\s*:\s*none|visibility\s*:\s*hidden)\s*(?:;|$)/.test(style)
  );
}

function isDefinitionNode(node) {
  return (
    node.tag === "defs" || node.tag === "symbol" || node.tag === "clippath" || node.tag === "mask"
  );
}

function isSemanticAnchor(node) {
  const id = node.attributes.id ?? "";
  return id === "overlay_root" || id.startsWith("anchor_");
}

function isPaintClusterTag(tag) {
  return tag === "g" || PAINT_TAGS.has(tag);
}

function walkVisibleSvgNodes(root) {
  const visible = [];
  function visit(node, hiddenOrDefinition) {
    const excluded = hiddenOrDefinition || isHiddenNode(node) || isDefinitionNode(node);
    if (!excluded) visible.push(node);
    for (const child of node.children) visit(child, excluded);
  }
  for (const child of root.children) visit(child, false);
  return visible;
}

function subtreeContainsVisiblePaint(node, hiddenOrDefinition) {
  const excluded = hiddenOrDefinition || isHiddenNode(node) || isDefinitionNode(node);
  if (excluded) return false;
  if (PAINT_TAGS.has(node.tag)) return true;
  return node.children.some(function childHasVisiblePaint(child) {
    return subtreeContainsVisiblePaint(child, false);
  });
}

function repoRoot() {
  return REPO_ROOT;
}

function pathInside(root, candidate) {
  const relative = path.relative(root, candidate);
  return relative !== "" && !relative.startsWith(`..${path.sep}`) && relative !== "..";
}

function validateAssetName(assetName) {
  if (!ASSET_NAME_PATTERN.test(assetName)) {
    throw new Error(`asset census: unsafe asset name '${assetName}'`);
  }
}

function indexEquipmentAssets(repoRootPath) {
  const equipmentRoot = path.resolve(repoRootPath, EQUIPMENT_DIR);
  const files = fs.readdirSync(equipmentRoot, { recursive: true, withFileTypes: true });
  const byName = new Map();
  for (const entry of files) {
    if (!entry.isFile() || !entry.name.endsWith(".svg")) continue;
    const absolutePath = path.resolve(entry.parentPath, entry.name);
    if (!pathInside(equipmentRoot, absolutePath)) {
      throw new Error(`asset census: equipment path escaped root: ${absolutePath}`);
    }
    const assetName = path.basename(entry.name, ".svg");
    validateAssetName(assetName);
    if (byName.has(assetName)) {
      throw new Error(`asset census: duplicate equipment asset basename '${assetName}'`);
    }
    byName.set(assetName, absolutePath);
  }
  return byName;
}

function boxForItem(item, frameWidth) {
  const frameHeight = frameWidth * (VIEWPORT.h / VIEWPORT.w);
  const widthPx = (item._visualWidth / 100) * frameWidth;
  const heightPx = (item._height / 100) * frameHeight;
  const box = {
    width_px: Number(widthPx.toFixed(2)),
    height_px: Number(heightPx.toFixed(2)),
  };
  return box;
}

function compareBoxes(a, b) {
  const areaDifference =
    a.canonical_box.width_px * a.canonical_box.height_px -
    b.canonical_box.width_px * b.canonical_box.height_px;
  if (Math.abs(areaDifference) > 1e-9) return areaDifference;
  return (
    a.scene_name.localeCompare(b.scene_name) || a.placement_name.localeCompare(b.placement_name)
  );
}

function medianIndex(items) {
  return Math.floor((items.length - 1) / 2);
}

function collectReachableObjectAssets() {
  const assetsByObject = new Map();
  for (const [objectName, object] of Object.entries(OBJECT_LIBRARY)) {
    if (object.object_name !== objectName) {
      throw new Error(`asset census: object library key '${objectName}' has mismatched identity`);
    }
    validateAssetName(object.asset);
    const ownedAssets = new Map([[object.asset, new Set(["base_asset"])]]);
    for (const [fieldName, visualState] of Object.entries(object.visual_states)) {
      if (visualState.applies_to !== "object" || visualState.cases === undefined) continue;
      for (const visualCase of visualState.cases) {
        for (const assetName of assetsReferencedByOutput(visualCase.output)) {
          validateAssetName(assetName);
          const bindings = ownedAssets.get(assetName) ?? new Set();
          bindings.add(`visual_state:${fieldName}`);
          ownedAssets.set(assetName, bindings);
        }
      }
    }
    assetsByObject.set(objectName, ownedAssets);
  }
  return assetsByObject;
}

function assetsReferencedByOutput(output) {
  if ("asset_name" in output) return [output.asset_name];
  if ("overlay_name" in output) return [];
  return output.composite.flatMap(function assetsInChild(child) {
    return assetsReferencedByOutput(child);
  });
}

function collectAssetPlacements(assetsByObject) {
  const byAsset = new Map();
  for (const [sceneName, scene] of Object.entries(SCENES)) {
    const result = runScenePipeline(scene);
    const minimumFrame = result.interactionGeometry.minimum_frame;
    if (minimumFrame === undefined) {
      throw new Error(`asset census: scene '${sceneName}' has no valid minimum interaction frame`);
    }
    for (const item of result.final) {
      const owner = OBJECT_LIBRARY[item.object_name];
      if (owner === undefined || owner.object_name !== item.object_name) {
        throw new Error(
          `asset census: placement '${item.placement_name}' has an unknown object owner`,
        );
      }
      if (item.asset !== owner.asset) {
        throw new Error(
          `asset census: placement '${item.placement_name}' base asset does not ` +
            `match '${item.object_name}'`,
        );
      }
      const reachableAssets = assetsByObject.get(item.object_name);
      if (reachableAssets === undefined) {
        throw new Error(
          `asset census: object '${item.object_name}' has no reachable asset mapping`,
        );
      }
      for (const [assetName, bindings] of reachableAssets) {
        const placement = {
          scene_name: sceneName,
          workspace: result.scene.workspace,
          placement_name: item.placement_name,
          owner_object_name: item.object_name,
          asset_bindings: [...bindings].sort(),
          reflow_uniform_scale: Number(result.reflowUniformScale.toFixed(6)),
          frame_fraction_width: Number((item._visualWidth / 100).toFixed(6)),
          canonical_box: boxForItem(item, VIEWPORT.w),
          smallest_frame_width_px: minimumFrame.width_px,
          smallest_box: boxForItem(item, minimumFrame.width_px),
        };
        const existing = byAsset.get(assetName);
        if (existing === undefined) {
          byAsset.set(assetName, [placement]);
        } else {
          existing.push(placement);
        }
      }
    }
  }
  return byAsset;
}

function nominalSizeForUnplacedAsset(assetName) {
  const spec = ASSET_SPECS[assetName];
  if (spec !== undefined) {
    return {
      source: "generated ASSET_SPECS default_width",
      frame_fraction_width: Number((spec.default_width / 100).toFixed(6)),
      canonical_width_px: Number(((spec.default_width / 100) * VIEWPORT.w).toFixed(2)),
      canonical_height_px: Number(
        (((spec.default_width / 100) * VIEWPORT.w) / spec.aspect).toFixed(2),
      ),
    };
  }
  const object = Object.values(OBJECT_LIBRARY).find(function objectForAsset(candidate) {
    return candidate.asset === assetName || assetsReferencedByObject(candidate).has(assetName);
  });
  if (object === undefined) {
    throw new Error(`asset census: unplaced '${assetName}' has no declared nominal size`);
  }
  const width = object.layout.default_width;
  const assetSpec = ASSET_SPECS[object.asset];
  if (assetSpec === undefined) {
    throw new Error(`asset census: object '${object.object_name}' has no asset specification`);
  }
  return {
    source: `generated object '${object.object_name}' layout.default_width`,
    frame_fraction_width: Number((width / 100).toFixed(6)),
    canonical_width_px: Number(((width / 100) * VIEWPORT.w).toFixed(2)),
    canonical_height_px: Number((((width / 100) * VIEWPORT.w) / assetSpec.aspect).toFixed(2)),
  };
}

function assetsReferencedByObject(object) {
  const assets = new Set([object.asset]);
  for (const visualState of Object.values(object.visual_states)) {
    if (visualState.applies_to !== "object" || visualState.cases === undefined) continue;
    for (const visualCase of visualState.cases) {
      for (const assetName of assetsReferencedByOutput(visualCase.output)) assets.add(assetName);
    }
  }
  return assets;
}

function buildAssetCensus(repoRootPath) {
  const assetPaths = indexEquipmentAssets(repoRootPath);
  const assetsByObject = collectReachableObjectAssets();
  const placementsByAsset = collectAssetPlacements(assetsByObject);
  const rows = [];
  for (const assetName of Object.keys(SVG_MANIFEST).sort()) {
    validateAssetName(assetName);
    const assetPath = assetPaths.get(assetName);
    if (assetPath === undefined) {
      throw new Error(
        `asset census: manifest asset '${assetName}' is absent from ${EQUIPMENT_DIR}`,
      );
    }
    const manifest = SVG_MANIFEST[assetName];
    const feature = analyzeSvgMarkup(fs.readFileSync(assetPath, "utf8"));
    const placements = [...(placementsByAsset.get(assetName) ?? [])].sort(compareBoxes);
    const workspaces = [
      ...new Set(
        placements.map(function workspaceOf(row) {
          return row.workspace;
        }),
      ),
    ].sort();
    const row = {
      asset_name: assetName,
      asset_path: path.relative(repoRootPath, assetPath),
      render_mode: manifest.requires_dom_svg ? "inline_dom_svg" : "img",
      root_paint_cluster_count: feature.rootPaintClusterCount,
      ellipse_present: feature.ellipsePresent,
      rotation_or_skew_present: feature.rotationOrSkew,
      workspaces,
      placement_count: placements.length,
      placements,
    };
    if (placements.length > 0) {
      row.size_range = {
        min: placements[0],
        median: placements[medianIndex(placements)],
        max: placements[placements.length - 1],
      };
    } else {
      row.nominal_size = nominalSizeForUnplacedAsset(assetName);
    }
    rows.push(row);
  }
  if (assetPaths.size !== rows.length) {
    throw new Error(
      `asset census: manifest covers ${rows.length} assets but ` +
        `${assetPaths.size} equipment SVGs exist`,
    );
  }
  return {
    meta: {
      command: "node --import tsx tools/scene_scale_report.mjs --write-census-report",
      canonical_frame: { width_px: VIEWPORT.w, height_px: VIEWPORT.h },
      smallest_frame_source:
        "layout interactionGeometry.minimum_frame plus CSS scene-panel-inner " +
        "minimum frame variables",
      root_paint_cluster_count_definition:
        "visible root-level paint clusters; an inventory signal, not a " +
        "flatness, volume, or visual-quality verdict",
      asset_count: rows.length,
      scene_count: Object.keys(SCENES).length,
    },
    assets: rows,
  };
}

function formatBox(box) {
  return `${box.width_px.toFixed(2)} x ${box.height_px.toFixed(2)}`;
}

function formatRangeEntry(entry) {
  const fractionPercent = (entry.frame_fraction_width * 100).toFixed(3);
  return (
    `${entry.scene_name}/${entry.placement_name}: ${fractionPercent}% width, scale ` +
    `${entry.reflow_uniform_scale}; ${formatBox(entry.canonical_box)} px @ 1920; ` +
    `${formatBox(entry.smallest_box)} px @ ${entry.smallest_frame_width_px}`
  );
}

function censusMarkdown(census) {
  const lines = [];
  lines.push("# SVG visual size and structural census");
  lines.push("");
  lines.push(
    "This generated structural baseline covers every current equipment SVG in the manifest.",
  );
  lines.push(
    "Regenerate with `node --import tsx tools/scene_scale_report.mjs --write-census-report`.",
  );
  lines.push(
    "The adjacent JSON carries every placement; this table presents each " +
      "asset's min, median, and max box.",
  );
  lines.push("");
  lines.push("## Measurement method");
  lines.push("");
  lines.push("- Layout comes from the real `runPipeline` result for every generated scene.");
  lines.push(
    "- Final boxes already include that scene's `reflowUniformScale`; " +
      "the factor is retained per placement.",
  );
  lines.push("- Fractions are visual-box width divided by the 16:9 frame width.");
  lines.push(
    "- The smallest frame is emitted by `interactionGeometry.minimum_frame` and reserved by",
  );
  lines.push(
    "  `.scene-panel-inner` CSS variables, so it is the smallest currently " +
      "valid scrollable scene frame.",
  );
  lines.push(
    "- Visible root clusters are an inventory signal, not a flatness, " +
      "volume, or visual-quality verdict.",
  );
  lines.push("- A well-constructed SVG may deliberately use one root group.");
  lines.push("- Explicit `<ellipse>` and rotate/skew transforms stay separate structural signals.");
  lines.push("");
  lines.push("## Asset census");
  lines.push("");
  lines.push(
    "| Asset | Visible root clusters | Ellipse | Rotate/skew | Render | " +
      "Workspaces | Placements | Size evidence |",
  );
  lines.push("| --- | ---: | --- | --- | --- | --- | ---: | --- |");
  for (const asset of census.assets) {
    const size =
      asset.size_range === undefined
        ? `unplaced; ${asset.nominal_size.canonical_width_px.toFixed(2)} x ` +
          `${asset.nominal_size.canonical_height_px.toFixed(2)} px @ 1920 ` +
          `(${asset.nominal_size.source})`
        : `min ${formatRangeEntry(asset.size_range.min)}; ` +
          `median ${formatRangeEntry(asset.size_range.median)}; ` +
          `max ${formatRangeEntry(asset.size_range.max)}`;
    lines.push(
      `| \`${asset.asset_name}\` | ${asset.root_paint_cluster_count} | ` +
        `${asset.ellipse_present ? "yes" : "no"} | ` +
        `${asset.rotation_or_skew_present ? "yes" : "no"} | ${asset.render_mode} | ` +
        `${asset.workspaces.join(", ") || "unplaced"} | ${asset.placement_count} | ${size} |`,
    );
  }
  lines.push("");
  return lines.join("\n");
}

function assetCensusText(census) {
  const lines = ["", "SVG VISUAL SIZE AND STRUCTURAL CENSUS"];
  for (const asset of census.assets) {
    const feature =
      `root_paint_clusters=${asset.root_paint_cluster_count} ` +
      `ellipse=${asset.ellipse_present ? "yes" : "no"} ` +
      `rotate_or_skew=${asset.rotation_or_skew_present ? "yes" : "no"}`;
    lines.push(`${asset.asset_name}: ${feature}; render=${asset.render_mode}`);
    if (asset.size_range === undefined) {
      lines.push(
        `  unplaced nominal: ${asset.nominal_size.canonical_width_px.toFixed(2)} px wide @ 1920 ` +
          `(${asset.nominal_size.source})`,
      );
      continue;
    }
    lines.push(`  reachable placements (${asset.placements.length}):`);
    for (const entry of asset.placements) {
      lines.push(
        `  ${entry.scene_name}/${entry.placement_name} (${entry.owner_object_name}; ` +
          `${entry.asset_bindings.join(", ")}): ${formatRangeEntry(entry)}`,
      );
    }
  }
  return lines.join("\n") + "\n";
}

function reportAssetCensus(census) {
  process.stdout.write(assetCensusText(census));
}

function writeCensusReports(repoRootPath, census) {
  const reportRoot = path.resolve(repoRootPath, REPORT_DIR);
  if (!pathInside(repoRootPath, reportRoot)) {
    throw new Error(`asset census: report directory escaped repository: ${reportRoot}`);
  }
  const markdownPath = path.resolve(reportRoot, `${REPORT_BASENAME}.md`);
  const jsonPath = path.resolve(reportRoot, `${REPORT_BASENAME}.json`);
  if (!pathInside(reportRoot, markdownPath) || !pathInside(reportRoot, jsonPath)) {
    throw new Error("asset census: report target escaped report directory");
  }
  fs.writeFileSync(markdownPath, censusMarkdown(census), "utf8");
  fs.writeFileSync(jsonPath, `${JSON.stringify(census, null, 2)}\n`, "utf8");
  process.stdout.write(`Wrote ${path.relative(repoRootPath, markdownPath)}\n`);
  process.stdout.write(`Wrote ${path.relative(repoRootPath, jsonPath)}\n`);
}

//============================================
// CLI arg parsing
//============================================

// Parses one explicit report mode from process.argv. Returns { mode, sceneName }.
function parseArgs() {
  const argv = process.argv.slice(2);

  if (argv.length === 0) {
    process.stderr.write(
      "Usage:\n" +
        "  node --import tsx tools/scene_scale_report.mjs --scene <name>\n" +
        "  node --import tsx tools/scene_scale_report.mjs --all\n" +
        "  node --import tsx tools/scene_scale_report.mjs --write-census-report\n",
    );
    process.exit(1);
  }

  if (argv.length === 1 && argv[0] === "--all") {
    return { mode: "all", sceneName: null };
  }

  if (argv.length === 1 && argv[0] === "--write-census-report") {
    return { mode: "write-census", sceneName: null };
  }

  if (argv.length === 2 && argv[0] === "--scene") {
    const name = argv[1];
    if (name.startsWith("-")) {
      process.stderr.write("Error: --scene requires a scene name argument\n");
      process.exit(1);
    }
    return { mode: "single", sceneName: name };
  }

  process.stderr.write(
    `Error: unrecognized arguments: ${argv.join(" ")}\n` +
      "Usage:\n" +
      "  node --import tsx tools/scene_scale_report.mjs --scene <name>\n" +
      "  node --import tsx tools/scene_scale_report.mjs --all\n" +
      "  node --import tsx tools/scene_scale_report.mjs --write-census-report\n",
  );
  process.exit(1);
}

//============================================
// Main
//============================================

function main() {
  // Resolve the repository from this tool's own location so reports do not
  // depend on the caller's cwd or on repository-control tooling.
  const top = repoRoot();

  const opts = parseArgs();

  if (opts.mode === "all") {
    reportAllScenes();
    reportAssetCensus(buildAssetCensus(top));
  } else if (opts.mode === "write-census") {
    writeCensusReports(top, buildAssetCensus(top));
  } else {
    // mode === "single", sceneName is non-null (parseArgs exits otherwise).
    reportSingleScene(opts.sceneName);
  }
}

const invokedPath = process.argv[1] === undefined ? null : path.resolve(process.argv[1]);
const thisPath = fileURLToPath(import.meta.url);
if (invokedPath === thisPath) {
  main();
}
