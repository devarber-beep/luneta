/** Best-effort BCP 47 tag for user-authored scenario text (page chrome stays English). */
export function contentLanguage(text: string): "en" | "es" {
  const sample = text.trim();
  if (!sample) return "en";
  if (/[áéíóúÁÉÍÓÚñÑüÜ¿¡]/.test(sample)) return "es";
  if (
    /\b(el|la|los|las|un|una|unos|unas|de|del|para|por|con|que|como|niño|niña|escenario)\b/i.test(
      sample,
    )
  ) {
    return "es";
  }
  return "en";
}
