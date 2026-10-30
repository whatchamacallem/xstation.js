// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Tests of the settings module: the value store's reads, the name form, the
// freezing outside debug mode and the puts, each thrown text compared to its
// entry in the gold record, test_settings.json. Each store is given its own
// copy of the real settings.json, read through the harness.

namespace test_settings {
  // The values the tests put.
  const constants = Object.freeze({
    // A changed `provider.timeout_seconds`, its writer's choice.
    timeout_changed: 60,
    // A changed `line_max`, its writer's choice.
    line_changed: 2048,
  });

  // A copy of a value of `settings.json`, which the harness keeps frozen.
  function setting_copy(id: string): unknown {
    return structuredClone(harness.setting_get(id));
  }

  // A copy of `settings.json` through the harness, with `debug` as given.
  function settings_copy(debug: boolean): settings.Settings {
    return {
      debug,
      queue_synchronous: setting_copy("queue_synchronous") as boolean,
      verbose_level: setting_copy("verbose_level") as number,
      verbose_ring: setting_copy("verbose_ring") as number,
      line_max: setting_copy("line_max") as number,
      blob_max: setting_copy("blob_max") as number,
      overflow_bytes: setting_copy("overflow_bytes") as number,
      chunk_bytes: setting_copy("chunk_bytes") as number,
      srv_buf_size: setting_copy("srv_buf_size") as number,
      media_db_bytes: setting_copy("media_db_bytes") as number,
      turn_compact_turns: setting_copy("turn_compact_turns") as number,
      provider: setting_copy("provider") as settings.Settings["provider"],
      powershell: setting_copy(
        "powershell",
      ) as settings.Settings["powershell"],
    };
  }

  // A text of this module's gold, a run time `{n}` left for the test to fill.
  function gold_text(name: string): string {
    return harness.gold_get(
      `typescript.test_settings.texts.${name}`,
    ) as string;
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

  // One store for each test, so no test leaves a state behind.
  export class TestValueStore extends unittest.TestCase {
    // Reading an id before the settings are set throws.
    test_get_unset(): void {
      const store = new settings.ValueStore();
      const message = message_thrown(this, () => store.value_get("debug"));
      this.assertEqual(message, gold_text("settings_not_set"));
    }

    // An id that names no key throws, at any depth.
    test_unknown_id(): void {
      const store = new settings.ValueStore();
      store.value_set(settings_copy(false));
      // Each id and the name of its text in the gold.
      const cases: [string, string][] = [
        ["test.no_such_id", "settings_unknown_id_test"],
        ["provider.no_such_id", "settings_unknown_id_provider"],
        ["provider.base_url", "settings_unknown_id_base_url"],
        ["provider.chat_model", "settings_unknown_id_chat_model"],
        ["provider.image_model", "settings_unknown_id_image_model"],
        ["message_max", "settings_unknown_id_message_max"],
        ["queue_max", "settings_unknown_id_queue_max"],
        ["debug.no_such_id", "settings_unknown_id_debug"],
        ["provider.", "settings_unknown_id_trailing"],
        [".provider", "settings_unknown_id_leading"],
        ["", "settings_unknown_id_empty"],
      ];
      for (const [id, name] of cases) {
        const message = message_thrown(this, () => store.value_get(id));
        this.assertEqual(message, gold_text(name));
      }
    }

    // Top level and nested ids return their values.
    test_nested_ids(): void {
      const store = new settings.ValueStore();
      store.value_set(settings_copy(false));
      this.assertEqual(store.value_get("debug"), false);
      const ids = [
        "line_max",
        "provider.scripted",
        "provider.timeout_seconds",
        "provider.variable",
        "powershell.poll_tries",
        "provider",
      ];
      for (const id of ids) {
        this.assertEqual(store.value_get(id), harness.setting_get(id), id);
      }
    }

    // Full names before the settings are set, then as `debug` says.
    test_names_full(): void {
      const unset = new settings.ValueStore();
      this.assertTrue(unset.names_full());
      const debug = new settings.ValueStore();
      debug.value_set(settings_copy(true));
      this.assertTrue(debug.names_full());
      const release = new settings.ValueStore();
      release.value_set(settings_copy(false));
      this.assertFalse(release.names_full());
    }

    // Outside debug mode the whole object is frozen and refuses a write.
    test_frozen_write(): void {
      const store = new settings.ValueStore();
      const value = settings_copy(false);
      store.value_set(value);
      this.assertTrue(Object.isFrozen(value));
      this.assertTrue(Object.isFrozen(value.provider));
      this.assertRaises(TypeError, () => {
        value.debug = true;
      });
      this.assertRaises(TypeError, () => {
        value.provider.timeout_seconds = constants.timeout_changed;
      });
      this.assertEqual(store.value_get("debug"), false);
    }

    // A second set throws and leaves the first settings in place.
    test_set_twice(): void {
      const store = new settings.ValueStore();
      store.value_set(settings_copy(false));
      const second = settings_copy(true);
      const message = message_thrown(this, () => store.value_set(second));
      this.assertEqual(message, gold_text("settings_already_set"));
      this.assertEqual(store.value_get("debug"), false);
    }

    // In debug mode the object is not frozen and shows a change at once.
    test_debug_mutable(): void {
      const store = new settings.ValueStore();
      const value = settings_copy(true);
      store.value_set(value);
      this.assertFalse(Object.isFrozen(value));
      this.assertFalse(Object.isFrozen(value.provider));
      value.provider.timeout_seconds = constants.timeout_changed;
      this.assertEqual(
        store.value_get("provider.timeout_seconds"),
        constants.timeout_changed,
      );
    }

    // A put outside debug mode throws, sends nothing and changes nothing.
    test_put_denied(): void {
      const sent: lines.SettingsPut[] = [];
      const store = new settings.ValueStore();
      store.value_set(settings_copy(false));
      store.sender_register((payload) => {
        sent.push(payload);
      });
      const message = message_thrown(this, () => {
        store.value_put("line_max", constants.line_changed);
      });
      this.assertEqual(message, gold_text("settings_put_denied"));
      this.assertEqual(
        store.value_get("line_max"),
        harness.setting_get("line_max"),
      );
      this.assertEqual(sent.length, 0);
    }

    // A put before the settings are set throws.
    test_put_unset(): void {
      const store = new settings.ValueStore();
      store.sender_register(() => {});
      const message = message_thrown(this, () => {
        store.value_put("line_max", constants.line_changed);
      });
      this.assertEqual(message, gold_text("settings_not_set"));
    }

    // A put in debug mode changes the live value and sends all settings.
    test_put_sent(): void {
      const sent: lines.SettingsPut[] = [];
      const store = new settings.ValueStore();
      store.value_set(settings_copy(true));
      store.sender_register((payload) => {
        sent.push(payload);
      });
      store.value_put("provider.timeout_seconds", constants.timeout_changed);
      store.value_put("line_max", constants.line_changed);
      this.assertEqual(
        store.value_get("provider.timeout_seconds"),
        constants.timeout_changed,
      );
      this.assertEqual(store.value_get("line_max"), constants.line_changed);
      this.assertEqual(sent.length, 2);
      this.assertEqual(
        sent[0].settings.provider.timeout_seconds,
        constants.timeout_changed,
      );
      this.assertEqual(
        sent[0].settings.line_max,
        harness.setting_get("line_max"),
      );
      this.assertEqual(sent[1].settings.line_max, constants.line_changed);
      this.assertEqual(sent[1].settings.debug, true);
      this.assertEqual(
        sent[1].settings.provider.scripted,
        harness.setting_get("provider.scripted"),
      );
    }

    // A put of an unknown id throws and sends nothing.
    test_put_unknown(): void {
      const sent: lines.SettingsPut[] = [];
      const store = new settings.ValueStore();
      store.value_set(settings_copy(true));
      store.sender_register((payload) => {
        sent.push(payload);
      });
      const id = "test.no_such_id";
      const message = message_thrown(this, () => store.value_put(id, 1));
      this.assertEqual(message, gold_text("settings_unknown_id_test"));
      this.assertEqual(sent.length, 0);
    }

    // A put with no sender registered throws and changes nothing.
    test_sender_missing(): void {
      const store = new settings.ValueStore();
      store.value_set(settings_copy(true));
      const message = message_thrown(this, () => {
        store.value_put("line_max", constants.line_changed);
      });
      this.assertEqual(message, gold_text("settings_no_sender"));
      this.assertEqual(
        store.value_get("line_max"),
        harness.setting_get("line_max"),
      );
    }

    // A second sender registration throws.
    test_sender_twice(): void {
      const store = new settings.ValueStore();
      store.sender_register(() => {});
      const message = message_thrown(this, () => {
        store.sender_register(() => {});
      });
      this.assertEqual(message, gold_text("settings_sender_twice"));
    }
  }
}

Object.freeze(test_settings);
