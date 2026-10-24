// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Tests of the strings function and its placeholder rule. A text the real
// table holds is checked against its copy in the gold record.

namespace test_i18n {
  // A text of this module's gold, a run time `{n}` left for the test to fill.
  function gold_text(name: string): string {
    return harness.gold_get(`typescript.test_i18n.texts.${name}`) as string;
  }

  // The message of the error a function throws, failing the test if none.
  function message_thrown(test: unittest.TestCase, fn: () => unknown): string {
    try {
      fn();
    } catch (error) {
      return (error as Error).message;
    }
    return test.fail("Nothing was thrown.");
  }

  // The lookup of a name in the real table.
  export class TestStringCall extends unittest.TestCase {
    // A name that is not in the table throws, with or without arguments.
    test_missing_name(): void {
      const missing = "The strings table has no name test.no_such_name.";
      this.assertEqual(
        message_thrown(this, () => i18n("test.no_such_name")),
        missing,
      );
      this.assertEqual(
        message_thrown(this, () => i18n("test.no_such_name", "text")),
        missing,
      );
    }

    // A name only the object prototype has is missing too.
    test_inherited_name(): void {
      this.assertEqual(
        message_thrown(this, () => i18n("constructor")),
        "The strings table has no name constructor.",
      );
      this.assertEqual(
        message_thrown(this, () => i18n("toString")),
        "The strings table has no name toString.",
      );
    }

    // A text with no braces is returned as the table holds it.
    test_plain_text(): void {
      this.assertEqual(
        i18n("utility.bytes_refused"),
        gold_text("utility_bytes_refused"),
      );
    }

    // An argument given to a text with no placeholder throws.
    test_plain_extra(): void {
      this.assertEqual(
        message_thrown(this, () => i18n("utility.bytes_refused", "text")),
        "The string utility.bytes_refused has the placeholder indices [] " +
          "but 1 arguments were given.",
      );
    }
  }

  // The placeholder rule, applied to texts the test supplies.
  export class TestStringFormat extends unittest.TestCase {
    // Checks that filling the text throws the mismatch of indices and count.
    mismatch_thrown(text: string, args: unknown[], indices: string): void {
      this.assertEqual(
        message_thrown(this, () => i18n_format("test.name", text, args)),
        `The string test.name has the placeholder indices [${indices}] ` +
          `but ${args.length} arguments were given.`,
      );
    }

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
      this.mismatch_thrown("{0} {2}", ["a", "b"], "0, 2");
      this.mismatch_thrown("{0} {2}", ["a", "b", "c"], "0, 2");
    }

    // An index at or past the argument count throws.
    test_index_range(): void {
      this.mismatch_thrown("{1}", ["a"], "1");
    }

    // Fewer or more arguments than the placeholders throw.
    test_count_mismatch(): void {
      this.mismatch_thrown("{0}", [], "0");
      this.mismatch_thrown("{0}", ["a", "b"], "0");
      this.mismatch_thrown("text", ["a"], "");
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
