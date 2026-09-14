from pathlib import Path

p = Path("windmill/f/dm_assistant/apps/library.raw_app/App.tsx")
text = p.read_text(encoding="utf-8")

old = '''  const affinity = (source: { path: string }) => {
    const stemTokens = stemOf(source).split(/[^a-z0-9']+/);
    return stemTokens.filter((token) => nameTokens.has(token)).length;
  };
  // A document may represent an entity only when its filename carries the
  // entity's whole distinctive name. Queue-created identities reach claims
  // through documents about *other* subjects (Ruh's death is recorded in
  // Goodman's file), and a partial-token overlap ("Council of Unity" vs
  // heart-of-unity.md) means sibling subject matter, not this entry's page.
  // An exact filename match always wins when one exists.
  const exact = sources.filter((source) => stemOf(source).replace(/-/g, " ") === normalizedName);
  if (exact.length > 0) {
    const score = (source: { path: string }) =>
      (preferredRoot && source.path.toLocaleLowerCase().startsWith(preferredRoot) ? 1 : 0);
    return [...exact].sort((left, right) => score(right) - score(left) || left.path.localeCompare(right.path))[0];
  }
  const named = sources.filter((source) => affinity(source) === nameTokens.size && nameTokens.size > 0);
  if (named.length === 0) return undefined;
  const score = (source: { path: string }) =>
    (preferredRoot && source.path.toLocaleLowerCase().startsWith(preferredRoot) ? 2 : 0) + affinity(source);
  return [...named].sort((left, right) => score(right) - score(left) || left.path.localeCompare(right.path))[0];
}'''

new = '''  const distinctive = (tokens: string[]) =>
    tokens.filter((token) => token.length > 2 && !["the", "of", "and", "for"].includes(token));
  // A document may represent an entity only when its filename uses nothing
  // beyond the entity's own name. Dropping qualifier words is fine
  // ("Monastery of Arkin" -> monastery.md), but a foreign word means sibling
  // subject matter, not this entry's page ("Council of Unity" must not borrow
  // heart-of-unity.md; "Romulus" must not borrow the-wrath-of-romulus.md).
  // An exact filename match always wins when one exists.
  const exact = sources.filter((source) => stemOf(source).replace(/-/g, " ") === normalizedName);
  if (exact.length > 0) {
    const score = (source: { path: string }) =>
      (preferredRoot && source.path.toLocaleLowerCase().startsWith(preferredRoot) ? 1 : 0);
    return [...exact].sort((left, right) => score(right) - score(left) || left.path.localeCompare(right.path))[0];
  }
  const stemTokensOf = (source: { path: string }) => distinctive(stemOf(source).split(/[^a-z0-9']+/));
  const named = sources.filter((source) => {
    const stemTokens = stemTokensOf(source);
    return stemTokens.length > 0 && stemTokens.every((token) => nameTokens.has(token));
  });
  if (named.length === 0) return undefined;
  const score = (source: { path: string }) =>
    (preferredRoot && source.path.toLocaleLowerCase().startsWith(preferredRoot) ? 2 : 0) + stemTokensOf(source).length;
  return [...named].sort((left, right) => score(right) - score(left) || left.path.localeCompare(right.path))[0];
}'''

assert old in text
text = text.replace(old, new, 1)
p.write_text(text, encoding="utf-8")
print("matcher rewritten")
