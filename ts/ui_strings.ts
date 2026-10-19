// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The strings table of the page, frozen. The build replaces the declared
// constant below by the text of the strings file.

// The text of the strings file, put in by the build.
declare const I18N_TABLE_JSON: { [name: string]: string };

namespace ui_strings {
  // The strings table, one text for each name.
  export const table: { readonly [name: string]: string } =
    Object.freeze(I18N_TABLE_JSON);
}

Object.freeze(ui_strings);
