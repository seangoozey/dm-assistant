// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";
// @ts-expect-error vite raw import has no type declaration
import appSource from "./App.tsx?raw";
import { GLOSSARY_CATEGORIES, TERMS, Term } from "./glossary";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

afterEach(cleanup);

describe("glossary registry", () => {
  it("covers every category with complete entries", () => {
    const categories = new Set(Object.values(TERMS).map((entry) => entry.category));
    for (const category of categories) expect(GLOSSARY_CATEGORIES).toContain(category);
    for (const [key, entry] of Object.entries(TERMS)) {
      expect(entry.term.trim(), key).toBeTruthy();
      expect(entry.short.length, key).toBeGreaterThan(10);
      expect(entry.definition.length, key).toBeGreaterThan(entry.short.length);
    }
  });

  it("fails on any <Term> usage whose key has no glossary entry", () => {
    const used = [...appSource.matchAll(/<Term term="([a-z-]+)"/g)].map((match) => match[1]);
    expect(used.length).toBeGreaterThan(5);
    const unknown = used.filter((key) => !(key in TERMS));
    expect(unknown, `unknown term keys: ${unknown.join(", ")}`).toEqual([]);
  });

  it("renders the short definition in the tooltip", () => {
    render(<Term term="leadership">Leadership ★</Term>);
    expect(screen.getByText("Leadership ★")).toBeInTheDocument();
    expect(screen.getByRole("tooltip")).toHaveTextContent("exactly one holder");
  });

  it("marks unknown keys visibly instead of crashing", () => {
    render(<Term term="not-a-real-term">Broken</Term>);
    expect(screen.getByText("Broken")).toHaveClass("term-unknown");
  });
});
