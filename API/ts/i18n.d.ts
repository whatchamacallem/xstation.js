// The strings of ui_strings.table, `{0}` placeholders. Throws on a
// missing name or when the placeholder count differs from the argument
// count. The module object is the function, so calls read `i18n("name")`.
declare function i18n(name: string, ...args: unknown[]): string;

// Fills the placeholders of a text, which must match the arguments exactly.
declare function i18n_format(
  name: string,
  text: string,
  args: unknown[],
): string;
