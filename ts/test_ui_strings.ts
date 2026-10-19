// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Tests of the strings table module.

namespace test_ui_strings {
  // The table and its module object are frozen.
  export class TestTableFrozen extends unittest.TestCase {
    // Both the table and the module object report frozen.
    test_table_frozen(): void {
      this.assertTrue(Object.isFrozen(ui_strings.table));
      this.assertTrue(Object.isFrozen(ui_strings));
    }

    // Adding a name to the table throws.
    test_table_write(): void {
      const table = ui_strings.table as { [name: string]: string };
      this.assertRaises(TypeError, () => {
        table["test.no_such_name"] = "text";
      });
    }
  }
}

Object.freeze(test_ui_strings);
