// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The strings function of the page and the placeholder rule it applies.

// Returns the text of a name with its placeholders filled by the arguments.
function i18n(name: string, ...args: unknown[]): string {
  if (!Object.hasOwn(ui_strings.table, name)) {
    throw new Error(`The strings table has no name ${name}.`);
  }
  return i18n_format(name, ui_strings.table[name], args);
}

// Fills the placeholders of a text, which must match the arguments exactly.
function i18n_format(name: string, text: string, args: unknown[]): string {
  const placeholder = /\{(0|[1-9][0-9]*)\}/g;
  const indices = new Set<number>();
  for (const match of text.matchAll(placeholder)) {
    indices.add(Number(match[1]));
  }
  const count = args.length;
  if (indices.size !== count || Math.max(...indices) >= count) {
    throw new Error(
      `The string ${name} has the placeholder indices ` +
        `[${[...indices].join(", ")}] but ${count} arguments were given.`,
    );
  }
  return text.replace(placeholder, (_match: string, digits: string) =>
    String(args[Number(digits)]),
  );
}

Object.freeze(i18n);
