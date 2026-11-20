// How each transcription code looks in Zodiac's letters, for Z13 and Z32.
// Codes follow David Oranchak's ASCII convention (see NOTICE.md); descriptions are
// condensed from data/ciphers/z13.json and z32.json (verified against scans by winchxyz).
// Drawings are our own approximations from those descriptions, not traced from scans.

export type GlyphKind =
  | { kind: "letter"; ch: string; mirror?: boolean; serif?: boolean }
  | { kind: "shape"; shape: Shape; mark?: string };

export type Shape =
  | "crosshair" | "circle8" | "hookT" | "perpT" | "triOpen" | "triFilled" | "bar"
  | "squareFilled" | "squareHalf" | "omega" | "circleDot" | "tau";

export type GlyphInfo = GlyphKind & { name: string; desc: string };

const L = (ch: string, desc = `Capital ${ch}, written normally.`): GlyphInfo => ({ kind: "letter", ch, name: ch, desc });

export const GLYPHS: Record<string, GlyphInfo> = {
  A: L("A"), C: L("C"), D: L("D"), E: L("E"), F: L("F"), H: L("H"), J: L("J", "Capital J with a short top bar."),
  K: L("K"), L: L("L"), M: L("M"), N: L("N"), O: L("O", "Capital O: an open oval with no inner mark."), P: L("P"),
  R: L("R"), T: L("T"), V: L("V"), W: L("W"), X: L("X"),
  G: L("G", "Capital G drawn with an inward curl, so it resembles a 6."),
  I: { kind: "letter", ch: "I", serif: true, name: "serifed I", desc: "Capital I with serifs, as in Z408. (Variant reading of Z32's bar.)" },
  k: { kind: "letter", ch: "K", mirror: true, name: "backwards K", desc: "Mirror-reversed capital K (arms point left)." },
  f: { kind: "letter", ch: "F", mirror: true, name: "backwards F", desc: "Mirror-reversed capital F (bars point left)." },
  z: { kind: "shape", shape: "crosshair", name: "crosshair", desc: "Zodiac's signature: a small circle crossed by a vertical and a horizontal stroke that extend past it." },
  "0": { kind: "shape", shape: "circle8", name: "circled 8", desc: "Heavy circle with an inner figure like an 8 or the Taurus sign. Z13's three copies differ slightly inside." },
  "{": { kind: "shape", shape: "circle8", mark: "2", name: "circled 8 (2nd)", desc: "Z13's second circled glyph, treated as a different symbol in the 'circles distinct' reading." },
  "}": { kind: "shape", shape: "circle8", mark: "3", name: "circled 8 (3rd)", desc: "Z13's third circled glyph, treated as a different symbol in the 'circles distinct' reading." },
  "[": { kind: "shape", shape: "hookT", name: "hooked upside-down T", desc: "Upside-down T whose base curls up into a hook at the right (also read as an anchor or the Aries sign)." },
  t: { kind: "shape", shape: "perpT", name: "upside-down T", desc: "Plain upside-down T, as in Z408/Z340. (Variant reading of the hooked T.)" },
  "9": { kind: "shape", shape: "triOpen", name: "open triangle", desc: "Outline triangle, point up." },
  "8": { kind: "shape", shape: "triFilled", name: "filled triangle", desc: "Solid triangle, point up." },
  "|": { kind: "shape", shape: "bar", name: "bar", desc: "Plain vertical stroke with no serifs, like the Z340 bar." },
  "#": { kind: "shape", shape: "squareFilled", name: "filled square", desc: "Solid filled square." },
  "%": { kind: "shape", shape: "squareHalf", name: "half-filled square", desc: "Outlined square with its lower-right diagonal half filled in." },
  "?": { kind: "shape", shape: "omega", name: "omega", desc: "Greek capital omega: a horseshoe arch on two feet. Appears in no other Zodiac cipher." },
  "6": { kind: "shape", shape: "circleDot", name: "dotted circle", desc: "Circle with a solid dot at its centre." },
  j: { kind: "shape", shape: "tau", name: "backwards J / tau", desc: "Backwards J with a top bar, so it looks like a Greek tau." },
  $: { kind: "shape", shape: "tau", mark: "′", name: "tau (separate)", desc: "The same tau-like glyph, treated as its own symbol in the 'tau distinct' reading." },
};

export function glyphInfo(code: string): GlyphInfo | undefined {
  return GLYPHS[code];
}
