/**
 * test_clipboard_guard.test.ts
 *
 * Unit tests for the sanitiseForClipboard helper used in app/admin/page.tsx.
 * These tests run in Node/jsdom via Vitest and do NOT require a browser.
 *
 * The helper must strip invisible Unicode characters used in clipboard-hijack
 * attacks (RTL overrides, zero-width spaces, null bytes, BOM) while leaving
 * ordinary multi-script text (Hindi, Tamil, etc.) completely intact.
 */

import { describe, it, expect } from "vitest";

// ── Inline the helper so we can test it without a full Next.js render ──────
const sanitiseForClipboard = (text: string): string =>
  text.replace(
    /[\u0000-\u0008\u000B\u000C\u000E-\u001F\u200B-\u200F\u202A-\u202E\uFEFF]/g,
    ""
  );

// ── Tests ──────────────────────────────────────────────────────────────────

describe("sanitiseForClipboard — clipboard hijack guard", () => {
  // ── Dangerous characters that MUST be removed ──────────────────────────

  it("strips RTL override character (U+202E)", () => {
    expect(sanitiseForClipboard("pay\u202Eyxp")).toBe("payyxp");
  });

  it("strips all RTL/LTR embedding chars (U+202A–U+202E)", () => {
    const dangerous = "\u202A\u202B\u202C\u202D\u202E";
    expect(sanitiseForClipboard(`abc${dangerous}xyz`)).toBe("abcxyz");
  });

  it("strips zero-width space (U+200B)", () => {
    expect(sanitiseForClipboard("hello\u200Bworld")).toBe("helloworld");
  });

  it("strips zero-width non-joiner (U+200C) and joiner (U+200D)", () => {
    expect(sanitiseForClipboard("a\u200Cb\u200Dc")).toBe("abc");
  });

  it("strips BOM (U+FEFF)", () => {
    expect(sanitiseForClipboard("\uFEFFstart")).toBe("start");
  });

  it("strips null byte (U+0000)", () => {
    expect(sanitiseForClipboard("no\u0000null")).toBe("nonull");
  });

  it("strips other C0 control chars except tab and newline", () => {
    // \u0007 = BEL, \u001B = ESC — both dangerous
    expect(sanitiseForClipboard("a\u0007b\u001Bc")).toBe("abc");
  });

  // ── Safe characters that MUST be preserved ─────────────────────────────

  it("preserves standard tab (\\t) and newline (\\n)", () => {
    const text = "line1\n\tindented\nline2";
    expect(sanitiseForClipboard(text)).toBe(text);
  });

  it("preserves Hindi text", () => {
    const hi = "दवाई लें — रोज़ सुबह";
    expect(sanitiseForClipboard(hi)).toBe(hi);
  });

  it("preserves Tamil text", () => {
    const ta = "மருந்தை உட்கொள்ளுங்கள்";
    expect(sanitiseForClipboard(ta)).toBe(ta);
  });

  it("preserves Arabic text (legitimate right-to-left script)", () => {
    const ar = "تناول الدواء يومياً";
    expect(sanitiseForClipboard(ar)).toBe(ar);
  });

  it("preserves emoji", () => {
    const text = "⚕️ Sanjeevani AI 💊";
    expect(sanitiseForClipboard(text)).toBe(text);
  });

  it("passes empty string through unchanged", () => {
    expect(sanitiseForClipboard("")).toBe("");
  });

  // ── Idempotency ────────────────────────────────────────────────────────

  it("is idempotent — applying twice gives the same result", () => {
    const dirty = "abc\u202Exyz\u200Bfoo\uFEFF";
    expect(sanitiseForClipboard(sanitiseForClipboard(dirty))).toBe(
      sanitiseForClipboard(dirty)
    );
  });

  // ── Realistic payload ──────────────────────────────────────────────────

  it("cleans a realistic hijacked clipboard payload", () => {
    // Attacker embeds RTL override to visually flip displayed text
    const payload =
      "Send 1 BTC to 1ABC\u202Exxx_legit_address\u202Cxxx";
    const cleaned = sanitiseForClipboard(payload);
    expect(cleaned).not.toContain("\u202E");
    expect(cleaned).not.toContain("\u202C");
    expect(cleaned).toBe("Send 1 BTC to 1ABCxxx_legit_addressxxx");
  });
});
