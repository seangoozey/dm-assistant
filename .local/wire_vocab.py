import io
p = 'App.tsx'
s = io.open(p, encoding='utf-8').read()
old = '  const [locationTrail, setLocationTrail] = useState<string[]>([]);'
assert old in s
addition = old + '''
  // TKT-0129: template vocabularies for the profile editors' selects.
  const [templateVocabularies, setTemplateVocabularies] = useState<Partial<Record<"location_type" | "status" | "race" | "sex", string[]>>>({});
  useEffect(() => {
    const load = async (vocabulary: "location_type" | "status" | "race" | "sex") => {
      try {
        const items = await campaignClient.getTemplateVocabulary(vocabulary);
        setTemplateVocabularies((current) => ({ ...current, [vocabulary]: items.filter((item) => !item.retired).map((item) => item.value) }));
      } catch { /* selects fall back to Not set + current */ }
    };
    for (const vocabulary of ["location_type", "status", "race", "sex"] as const) void load(vocabulary);
  }, [campaignClient]);'''
s = s.replace(old, addition, 1)
count = 0
while True:
    idx = s.find('<EntityProfileEditor entry={selectedEntry}')
    if idx < 0:
        break
    insert_at = s.find(' />', idx)
    s = s[:insert_at] + ' vocabularies={templateVocabularies} locationNames={libraryEntries.filter((item) => item.entity_kind === "location").map((item) => item.canonical_name)}' + s[insert_at:]
    count += 1
assert count == 2, count
io.open(p, 'w', encoding='utf-8', newline='').write(s)
print('call sites wired:', count)
