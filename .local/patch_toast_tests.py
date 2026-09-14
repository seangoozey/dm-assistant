from pathlib import Path
import re

p = Path("windmill/f/dm_assistant/apps/library.raw_app/App.test.tsx")
text = p.read_text(encoding="utf-8")

fixes = [
    # Text collisions: in-page message and its toast mirror both match — assert presence.
    ('expect(screen.getByText(/Removed Coreferra from Carpet Rollers/)).toBeInTheDocument();',
     'expect(screen.getAllByText(/Removed Coreferra from Carpet Rollers/).length).toBeGreaterThan(0);'),
    ('expect(await screen.findByText(/Kind corrected to worldbuilding/)).toBeInTheDocument();',
     'expect((await screen.findAllByText(/Kind corrected to worldbuilding/)).length).toBeGreaterThan(0);'),
    ('expect(await screen.findByText(/Seated Romulus as Inquisitor/)).toBeInTheDocument();',
     'expect((await screen.findAllByText(/Seated Romulus as Inquisitor/)).length).toBeGreaterThan(0);'),
    ('expect(await screen.findByText(/Seated Eustice as High Confessor ★/)).toBeInTheDocument();',
     'expect((await screen.findAllByText(/Seated Eustice as High Confessor ★/)).length).toBeGreaterThan(0);'),
    ('expect(await screen.findByText(/Defined Grand Inquisitor ★ for Inquisitors/)).toBeInTheDocument();',
     'expect((await screen.findAllByText(/Defined Grand Inquisitor ★ for Inquisitors/)).length).toBeGreaterThan(0);'),
    ('expect(await screen.findByText(/Seated Eustice as Grand Inquisitor ★/)).toBeInTheDocument();',
     'expect((await screen.findAllByText(/Seated Eustice as Grand Inquisitor ★/)).length).toBeGreaterThan(0);'),
    ('expect(await screen.findByText(/Linked Grand Inquisitor ★ to Inquisitors/)).toBeInTheDocument();',
     'expect((await screen.findAllByText(/Linked Grand Inquisitor ★ to Inquisitors/)).length).toBeGreaterThan(0);'),
    # Editor refusal alert now coexists with its toast alert.
    ('expect(await screen.findByRole("alert")).toHaveTextContent("already a member");',
     'const alerts = await screen.findAllByRole("alert");\n    expect(alerts.some((alert) => alert.textContent?.includes("already a member"))).toBe(true);'),
]
for old, new in fixes:
    count = text.count(old)
    assert count == 1, f"{count}: {old[:70]}"
    text = text.replace(old, new, 1)
    print("fixed:", old[:70])

# role="status" collisions in the two extraction-monitor tests and the
# save-or-discard test: scope to the in-page status elements, excluding toasts.
matches = list(re.finditer(r'getByRole\("status"\)', text))
print("remaining getByRole status sites:", len(matches))

p.write_text(text, encoding="utf-8")
print("done")
