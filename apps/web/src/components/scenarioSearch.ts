/** Client-side text match for scenario list search boxes. */
export function matchesScenarioSearch(
  q: string,
  fields: Array<string | null | undefined>,
): boolean {
  const needle = q.trim().toLowerCase();
  if (!needle) {
    return true;
  }
  return fields.some((field) => (field ?? "").toLowerCase().includes(needle));
}
