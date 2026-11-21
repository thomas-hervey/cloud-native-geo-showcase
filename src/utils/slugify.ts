/**
 * Converts a heading string to a URL-safe anchor slug.
 * Matches the logic used in ModuleContent's custom h2 renderer.
 */
export function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9\s-]/g, '')
    .trim()
    .replace(/\s+/g, '-');
}
