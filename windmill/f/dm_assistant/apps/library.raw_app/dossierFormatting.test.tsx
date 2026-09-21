// @vitest-environment jsdom
// TKT-0121: the Dossier block must match the NPC dossier's section formatting
// under the real stylesheet cascade — not by eyeballing copied values.
import "@testing-library/jest-dom/vitest";
// @ts-expect-error vite raw import has no type declaration
import css from "./index.css?raw";
import { cleanup } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
// @ts-expect-error jsdom ships without type declarations here
import { JSDOM } from "jsdom";

afterEach(cleanup);

function computedStyles(html: string, pick: string[]) {
  const dom = new JSDOM(`<!doctype html><html><head><style>${css}</style></head><body>${html}</body>`, {
    // Let jsdom fetch/parse any url() references silently.
    resources: undefined,
  });
  const doc = dom.window.document;
  const element = doc.querySelector(pick[0]) as HTMLElement;
  const view = dom.window.getComputedStyle(element);
  return Object.fromEntries(pick.map((property) => [property, view.getPropertyValue(property)]));
}

describe("dossier formatting parity with the NPC dossier", () => {
  it("matches the fact line and heading typography under the same stylesheet", () => {
    const npc = computedStyles(
      `<div class="npc-dossier-body"><section><h3>Known facts</h3><p>The fact text.</p></section></div>`,
      ["h3", "font-family", "font-size", "font-weight", "line-height", "color"],
    );
    const npcFact = computedStyles(
      `<div class="npc-dossier-body"><section><h3>Known facts</h3><p>The fact text.</p></section></div>`,
      ["p", "font-size", "line-height", "color"],
    );
    const dossierHeading = computedStyles(
      `<article class="document-view entry-view location-entry"><section class="character-content">
        <section class="dossier-block" aria-label="Dossier"><h3>Dossier</h3>
        <div class="dossier-fact"><p>The fact text.</p></div></section></section></article>`,
      ["h3", "font-family", "font-size", "font-weight", "line-height", "color"],
    );
    const dossierFact = computedStyles(
      `<article class="document-view entry-view location-entry"><section class="character-content">
        <section class="dossier-block" aria-label="Dossier"><h3>Dossier</h3>
        <div class="dossier-fact"><p>The fact text.</p></div></section></section></article>`,
      ["p", "font-size", "line-height", "color"],
    );
    // The NPC dossier's h3 is unstyled beyond size/color — its weight is the
    // browser default (700). Match the visible values that matter.
    expect(dossierHeading["font-size"]).toBe(npc["font-size"]);
    expect(dossierHeading["font-weight"]).toBe(npc["font-weight"]);
    expect(dossierHeading["line-height"]).toBe(npc["line-height"]);
    expect(dossierHeading["color"]).toBe(npc["color"]);
    expect(dossierFact["font-size"]).toBe(npcFact["font-size"]);
    expect(dossierFact["line-height"]).toBe(npcFact["line-height"]);
    expect(dossierFact["color"]).toBe(npcFact["color"]);
    // Fact cards reuse the established character-dossier card (Aris Placidia)
    // style: same grid cell chrome and serif typography, asserted under the
    // real stylesheet.
    const card = computedStyles(
      `<article class="document-view entry-view"><section class="character-content character-dossier"><h2>Dossier</h2><div><section class="dossier-fact-card"><h3>Established</h3><div class="entry-text"><p>The fact text.</p></div></section></div></section></article>`,
      [".dossier-fact-card", "border-color", "background-color", "padding"],
    );
    const established = computedStyles(
      `<article class="document-view character-document"><section class="character-content character-dossier"><h2>Character dossier</h2><div><section><h3>Appearance</h3><div class="entry-text"><p>Text.</p></div></section></div></section></article>`,
      [".character-dossier > div > section", "border-color", "background-color", "padding"],
    );
    expect(card["border-color"]).toBe(established["border-color"]);
    expect(card["background-color"]).toBe(established["background-color"]);
    expect(card["padding"]).toBe(established["padding"]);
    const cardHeading = computedStyles(
      `<article class="document-view entry-view"><section class="character-content character-dossier"><div><section class="dossier-fact-card"><h3>Established</h3></section></div></section></article>`,
      ["h3", "font-family", "font-size", "font-weight", "color"],
    );
    const establishedHeading = computedStyles(
      `<article class="document-view character-document"><section class="character-content character-dossier"><div><section><h3>Appearance</h3></section></div></section></article>`,
      ["h3", "font-family", "font-size", "font-weight", "color"],
    );
    expect(cardHeading["font-family"]).toBe(establishedHeading["font-family"]);
    expect(cardHeading["font-size"]).toBe(establishedHeading["font-size"]);
    expect(cardHeading["font-weight"]).toBe(establishedHeading["font-weight"]);
    expect(cardHeading["color"]).toBe(establishedHeading["color"]);
  });
});
