// Perceptual liquid-shade derivation. Material identity still resolves to one
// scalar display color in material_color.ts; this module only applies the
// closed SVG paint-role grammar to that already-resolved color.

export type LiquidPaintRole = "base" | "highlight" | "shadow";

interface Rgb {
  r: number;
  g: number;
  b: number;
}

interface Oklch {
  l: number;
  c: number;
  h: number;
}

function srgb_to_linear(channel: number): number {
  return channel <= 0.04045 ? channel / 12.92 : Math.pow((channel + 0.055) / 1.055, 2.4);
}

function linear_to_srgb(channel: number): number {
  return channel <= 0.0031308 ? channel * 12.92 : 1.055 * Math.pow(channel, 1 / 2.4) - 0.055;
}

function parse_hex(color: string): Rgb {
  if (!/^#[0-9a-fA-F]{6}$/.test(color)) {
    throw new Error(`OKLCH shade: expected #rrggbb, got '${color}'`);
  }
  return {
    r: Number.parseInt(color.slice(1, 3), 16) / 255,
    g: Number.parseInt(color.slice(3, 5), 16) / 255,
    b: Number.parseInt(color.slice(5, 7), 16) / 255,
  };
}

function rgb_to_oklch(rgb: Rgb): Oklch {
  const r = srgb_to_linear(rgb.r);
  const g = srgb_to_linear(rgb.g);
  const b = srgb_to_linear(rgb.b);
  const l = Math.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b);
  const m = Math.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b);
  const s = Math.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b);
  const lightness = 0.2104542553 * l + 0.793617785 * m - 0.0040720468 * s;
  const a = 1.9779984951 * l - 2.428592205 * m + 0.4505937099 * s;
  const lab_b = 0.0259040371 * l + 0.7827717662 * m - 0.808675766 * s;
  return { l: lightness, c: Math.hypot(a, lab_b), h: Math.atan2(lab_b, a) };
}

function oklch_to_linear_rgb(color: Oklch): Rgb {
  const a = color.c * Math.cos(color.h);
  const lab_b = color.c * Math.sin(color.h);
  const l_root = color.l + 0.3963377774 * a + 0.2158037573 * lab_b;
  const m_root = color.l - 0.1055613458 * a - 0.0638541728 * lab_b;
  const s_root = color.l - 0.0894841775 * a - 1.291485548 * lab_b;
  const l = l_root * l_root * l_root;
  const m = m_root * m_root * m_root;
  const s = s_root * s_root * s_root;
  return {
    r: 4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
    g: -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
    b: -0.0041960863 * l - 0.7034186147 * m + 1.707614701 * s,
  };
}

function in_gamut(rgb: Rgb): boolean {
  const epsilon = 1e-7;
  return (
    rgb.r >= -epsilon &&
    rgb.r <= 1 + epsilon &&
    rgb.g >= -epsilon &&
    rgb.g <= 1 + epsilon &&
    rgb.b >= -epsilon &&
    rgb.b <= 1 + epsilon
  );
}

function fit_to_srgb(color: Oklch): Rgb {
  const direct = oklch_to_linear_rgb(color);
  if (in_gamut(direct)) {
    return direct;
  }
  let low = 0;
  let high = color.c;
  let fitted = oklch_to_linear_rgb({ ...color, c: 0 });
  for (let iteration = 0; iteration < 24; iteration += 1) {
    const candidate_chroma = (low + high) / 2;
    const candidate = oklch_to_linear_rgb({ ...color, c: candidate_chroma });
    if (in_gamut(candidate)) {
      low = candidate_chroma;
      fitted = candidate;
    } else {
      high = candidate_chroma;
    }
  }
  return fitted;
}

function serialize_channel(channel: number): string {
  const srgb = linear_to_srgb(Math.min(1, Math.max(0, channel)));
  return Math.round(Math.min(1, Math.max(0, srgb)) * 255)
    .toString(16)
    .padStart(2, "0");
}

export function oklch_lightness(color: string): number {
  return rgb_to_oklch(parse_hex(color)).l;
}

export function derive_oklch_shade(
  base_color: string,
  role: LiquidPaintRole,
  adjustment: number | null,
): string {
  const rgb = parse_hex(base_color);
  if (role === "base") {
    if (adjustment !== null) {
      throw new Error("OKLCH shade: base role cannot carry an adjustment");
    }
    return base_color.toLowerCase();
  }
  if (adjustment === null || !Number.isFinite(adjustment)) {
    throw new Error(`OKLCH shade: ${role} role requires a finite adjustment`);
  }
  if (role === "highlight" && (adjustment <= 0 || adjustment > 0.5)) {
    throw new Error("OKLCH shade: highlight adjustment must be in (0, 0.5]");
  }
  if (role === "shadow" && (adjustment < -0.5 || adjustment >= 0)) {
    throw new Error("OKLCH shade: shadow adjustment must be in [-0.5, 0)");
  }
  const source = rgb_to_oklch(rgb);
  const shifted = {
    l: Math.min(1, Math.max(0, source.l + adjustment)),
    c: source.c,
    h: source.h,
  };
  const output = fit_to_srgb(shifted);
  return `#${serialize_channel(output.r)}${serialize_channel(output.g)}${serialize_channel(output.b)}`;
}
