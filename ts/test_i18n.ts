// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Tests of the strings function and its placeholder rule.

namespace test_i18n {
  // The pattern that picks an entry of the real table with no braces.
  const constants = Object.freeze({
    plain: /^[^{}]*$/,
  });

  // The first table entry whose text matches the pattern.
  function entry_find(pattern: RegExp): { name: string; text: string } {
    for (const name of Object.keys(ui_strings.table)) {
      const text = ui_strings.table[name];
      if (pattern.test(text)) {
        return { name, text };
      }
    }
    throw new Error(`No table entry matches ${pattern}.`);
  }

  // The lookup of a name in the real table.
  export class TestStringCall extends unittest.TestCase {
    // A name that is not in the table throws, with or without arguments.
    test_missing_name(): void {
      const name = "test.no_such_name";
      this.assertRaises(Error, () => i18n(name));
      this.assertRaises(Error, () => i18n(name, "text"));
    }

    // A name only the object prototype has is missing too.
    test_inherited_name(): void {
      this.assertRaises(Error, () => i18n("constructor"));
      this.assertRaises(Error, () => i18n("toString"));
    }

    // A text with no braces is returned as the table holds it.
    test_plain_text(): void {
      const entry = entry_find(constants.plain);
      this.assertEqual(i18n(entry.name), entry.text);
    }

    // An argument given to a text with no placeholder throws.
    test_plain_extra(): void {
      const entry = entry_find(constants.plain);
      this.assertRaises(Error, () => i18n(entry.name, "text"));
    }
  }

  // The placeholder rule, applied to texts the test supplies.
  export class TestStringFormat extends unittest.TestCase {
    // Braces that are not a canonical index stay literal, as `{01}` does.
    test_literal_braces(): void {
      const text = "{x} {} { 0 } {-1} {00} {01}";
      this.assertEqual(i18n_format("test.name", text, []), text);
      this.assertEqual(i18n_format("test.name", "{0} {01}", ["a"]), "a {01}");
    }

    // The arguments fill the placeholders by index.
    test_fill_indices(): void {
      const text = "{1} then {0}";
      this.assertEqual(i18n_format("test.name", text, ["a", "b"]), "b then a");
    }

    // An index may repeat and counts once.
    test_repeat_index(): void {
      const text = "{1} {0} {1}";
      this.assertEqual(i18n_format("test.name", text, ["a", "b"]), "b a b");
      this.assertEqual(i18n_format("test.name", "{0}{0}", ["x"]), "xx");
    }

    // A gap in the indices throws, at any argument count.
    test_gap_index(): void {
      const text = "{0} {2}";
      this.assertRaises(Error, () =>
        i18n_format("test.name", text, ["a", "b"])
      );
      this.assertRaises(Error, () =>
        i18n_format("test.name", text, ["a", "b", "c"])
      );
    }

    // An index at or past the argument count throws.
    test_index_range(): void {
      this.assertRaises(Error, () => i18n_format("test.name", "{1}", ["a"]));
    }

    // Fewer or more arguments than the placeholders throw.
    test_count_mismatch(): void {
      this.assertRaises(Error, () => i18n_format("test.name", "{0}", []));
      this.assertRaises(Error, () =>
        i18n_format("test.name", "{0}", ["a", "b"])
      );
      this.assertRaises(Error, () => i18n_format("test.name", "text", ["a"]));
    }

    // A text with no placeholder and no arguments is returned as it is.
    test_no_placeholder(): void {
      this.assertEqual(i18n_format("test.name", "text", []), "text");
    }

    // The fill is one pass: braces and dollars in an argument stay as given.
    test_argument_literal(): void {
      const text = "{0} {1}";
      this.assertEqual(i18n_format("test.name", text, ["{1}", "b"]), "{1} b");
      this.assertEqual(i18n_format("test.name", "{0}", ["$&"]), "$&");
    }

    // A number is filled as its text.
    test_number_argument(): void {
      this.assertEqual(i18n_format("test.name", "n{0}", [42]), "n42");
    }
  }
}

Object.freeze(test_i18n);
