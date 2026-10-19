declare namespace ui_strings {
  // The strings table: the text of i18n/en-US.json, substituted into
  // this module by page_build.py unmodified. Loaded after utility and
  // before settings. `i18n` reads it.
  const table: { readonly [name: string]: string };
}
