import { describe, expect, it } from "vitest";
import { evidenceTitle } from "./evidenceTitle";

describe("evidenceTitle", () => {
  it("uses known display spelling and cleans redundant layout labels", () => {
    expect(evidenceTitle("encounters/Ishirala/ishirala-floor3.md#The Statue Rooms — Layout", [{ canonical_name: "Ishi'ra'la-Floor 3", aliases: [] }])).toBe("Ishi'ra'la-Floor 3: The Statue Rooms");
  });
  it("falls back to a filename without inventing proper spelling", () => {
    expect(evidenceTitle("lore/cosmology.md#Ley Lines (Canonical)", [])).toBe("Cosmology: Ley Lines");
    expect(evidenceTitle("lore/old-world.md#War — Aftermath", [])).toBe("Old World: War — Aftermath");
  });
});
