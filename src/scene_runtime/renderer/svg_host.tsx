// src/scene_runtime/renderer/svg_host.tsx
//
// Shared tiered SVG host for production scenes and runtime review surfaces.
// The generated manifest owns the render-mode decision. Static assets use an
// opaque <img>; DOM-required assets use the production fetch, namespace, and
// injection path.

import type { JSXElement } from "solid-js";
import { createEffect, createMemo, createResource, createSignal, Show } from "solid-js";

import { injectSvgFromManifest } from "./inject_svg.js";
import { resolveSvgUrl, requiresDomSvg } from "./svg_manifest_loader.js";

const SVG_HOST_BOX_STYLE: Record<string, string> = { width: "100%", height: "100%" };

function DomSvgHost(props: {
  asset: string;
  svgInstanceKey: string;
  onDomSvgHostReady?: (host: HTMLElement) => void;
}): JSXElement {
  let hostEl: HTMLDivElement | undefined;
  const [hostReady, setHostReady] = createSignal<boolean>(false);

  const [injected] = createResource(
    () => ({ asset: props.asset, key: props.svgInstanceKey, ready: hostReady() }),
    async (request: { asset: string; key: string; ready: boolean }): Promise<boolean> => {
      if (!request.ready || hostEl === undefined) {
        return false;
      }
      await injectSvgFromManifest(hostEl, request.asset, request.key);
      props.onDomSvgHostReady?.(hostEl);
      return true;
    },
  );

  const loadError = createMemo<string>(() => {
    const error: unknown = injected.error;
    if (error === undefined) {
      return "";
    }
    if (error instanceof Error) {
      return error.message;
    }
    if (typeof error === "string") {
      return error;
    }
    return JSON.stringify(error);
  });

  let lastLoggedError = "";
  createEffect(() => {
    const message = loadError();
    if (message.length > 0 && message !== lastLoggedError) {
      // eslint-disable-next-line no-console
      console.error(`SVG load failed for asset "${props.asset}": ${message}`);
    }
    lastLoggedError = message;
  });

  return (
    <div
      style={SVG_HOST_BOX_STYLE}
      data-svg-render-mode="dom-svg"
      data-svg-load-error={loadError().length > 0 ? loadError() : undefined}
      ref={(element: HTMLDivElement) => {
        hostEl = element;
        setHostReady(true);
      }}
    >
      <Show when={loadError().length > 0}>
        <span class="svg-load-error">{`SVG load failed: ${props.asset}`}</span>
      </Show>
    </div>
  );
}

export function ImgSvgHost(props: { asset: string }): JSXElement {
  const url = createMemo<string>(() => resolveSvgUrl(props.asset));
  return (
    <img
      src={url()}
      alt=""
      data-svg-render-mode="img"
      style={{
        ...SVG_HOST_BOX_STYLE,
        "object-fit": "contain",
        "pointer-events": "none",
        display: "block",
      }}
    />
  );
}

export function SvgHost(props: {
  asset: string;
  svgInstanceKey: string;
  onDomSvgHostReady?: (host: HTMLElement) => void;
}): JSXElement {
  const isDomSvg = createMemo<boolean>(() => requiresDomSvg(props.asset));
  const domSvgProps: {
    asset: string;
    svgInstanceKey: string;
    onDomSvgHostReady?: (host: HTMLElement) => void;
  } = {
    asset: props.asset,
    svgInstanceKey: props.svgInstanceKey,
  };
  if (props.onDomSvgHostReady !== undefined) {
    domSvgProps.onDomSvgHostReady = props.onDomSvgHostReady;
  }
  return (
    <Show when={isDomSvg()} fallback={<ImgSvgHost asset={props.asset} />}>
      <DomSvgHost {...domSvgProps} />
    </Show>
  );
}
