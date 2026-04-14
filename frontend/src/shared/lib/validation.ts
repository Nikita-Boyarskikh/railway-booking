/**
 * Flattens an arbitrarily nested DRF-style error payload into a flat
 * `{ "dot.separated.path": "joined message" }` map.
 *
 * - Strings become `path → message`.
 * - Arrays of strings are treated as the list of messages for `path` and joined.
 * - Arrays of objects are walked with numeric indices (e.g. `items.0.passenger.name`).
 * - Objects are walked by key; numeric-string keys are preserved as-is, so
 *   DRF's `{ "items": { "0": {...} } }` produces the same shape as `{ "items": [...] }`.
 * - null/undefined nodes are skipped.
 *
 * Result paths match React Hook Form's field paths when the form schema mirrors
 * the request shape, so errors can be handed directly to `form.setError(path, ...)`.
 */
export function parseValidationErrors(data: unknown): Record<string, string> {
  const out: Record<string, string> = {};
  walk(data, [], out);
  return out;
}

function walk(node: unknown, path: string[], out: Record<string, string>): void {
  if (node == null) return;
  if (typeof node === 'string' || typeof node === 'number' || typeof node === 'boolean') {
    out[path.join('.')] = String(node);
    return;
  }
  if (Array.isArray(node)) {
    if (node.every((x) => typeof x === 'string')) {
      out[path.join('.')] = node.join(' ');
      return;
    }
    node.forEach((item, i) => { walk(item, [...path, String(i)], out); });
    return;
  }
  if (typeof node === 'object') {
    for (const [k, v] of Object.entries(node as Record<string, unknown>)) {
      walk(v, [...path, k], out);
    }
  }
}
