from pathlib import Path

p = Path("windmill/f/dm_assistant/apps/library.raw_app/App.tsx")
lines = p.read_text(encoding="utf-8").split("\n")

# Replace the memberList/memberNames block (5 lines starting at 'const memberList')
start = next(i for i, line in enumerate(lines) if line.strip().startswith("const memberList"))
replacement = [
    "  // Members render from roster data in the template view (TKT-0121), not as",
    "  // markdown — structured data keeps roles/★ even for authored descriptions.",
    "  const memberNames = \"\";",
]
# The block spans from start until the line that is exactly '      : "";'
end = start
while lines[end].rstrip() != '      : "";':
    end += 1
lines[start:end + 1] = replacement
p.write_text("\n".join(lines), encoding="utf-8")
print("synthesized members block replaced (lines", start + 1, "to", end + 1, ")")
