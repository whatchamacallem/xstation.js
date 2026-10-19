// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Tests of the settings module.

namespace test_settings {
  // A complete settings object with `debug` as given, the example values.
  function settings_make(debug: boolean): settings.Settings {
    return {
      debug,
      queue_synchronous: false,
      verbose_level: 1,
      verbose_ring: 1000,
      verbose_forward: true,
      line_max: 1048576,
      blob_max: 1073741824,
      overflow_bytes: 131072,
      chunk_bytes: 1048576,
      srv_buf_size: 1048576,
      media_db_bytes: 268435456,
      files_browser_bytes: 1073741824,
      turn_compact_tokens: 65536,
      long_task_ms: 5,
      provider: {
        scripted: true,
        base_url: "https://api.x.ai/v1",
        chat_model: "grok-4",
        image_model: "grok-2-image",
        timeout_seconds: 120,
      },
    };
  }

  // One store for each test, so no test leaves a state behind.
  export class TestValueStore extends unittest.TestCase {
    // Reading an id before the settings are set throws.
    test_get_unset(): void {
      const store = new settings.ValueStore();
      this.assertRaises(Error, () => store.value_get("debug"));
    }

    // An id that names no key throws, at any depth.
    test_unknown_id(): void {
      const store = new settings.ValueStore();
      store.value_set(settings_make(false));
      const ids = [
        "test.no_such_id",
        "provider.no_such_id",
        "debug.no_such_id",
        "provider.",
        ".provider",
        "",
      ];
      for (const id of ids) {
        this.assertRaises(Error, () => store.value_get(id));
      }
    }

    // Top level and nested ids return their values.
    test_nested_ids(): void {
      const store = new settings.ValueStore();
      store.value_set(settings_make(false));
      this.assertEqual(store.value_get("debug"), false);
      this.assertEqual(store.value_get("line_max"), 1048576);
      this.assertEqual(store.value_get("provider.scripted"), true);
      this.assertEqual(store.value_get("provider.chat_model"), "grok-4");
      this.assertEqual(store.value_get("provider.timeout_seconds"), 120);
      const provider = store.value_get("provider") as { base_url: string };
      this.assertEqual(provider.base_url, "https://api.x.ai/v1");
    }

    // Outside debug mode the whole object is frozen and refuses a write.
    test_frozen_write(): void {
      const store = new settings.ValueStore();
      const value = settings_make(false);
      store.value_set(value);
      this.assertTrue(Object.isFrozen(value));
      this.assertTrue(Object.isFrozen(value.provider));
      this.assertRaises(TypeError, () => {
        value.debug = true;
      });
      this.assertRaises(TypeError, () => {
        value.provider.base_url = "https://example.invalid";
      });
      this.assertEqual(store.value_get("debug"), false);
    }

    // A second set throws and leaves the first settings in place.
    test_set_twice(): void {
      const store = new settings.ValueStore();
      store.value_set(settings_make(false));
      this.assertRaises(Error, () => store.value_set(settings_make(true)));
      this.assertEqual(store.value_get("debug"), false);
    }

    // In debug mode the object is not frozen and shows a change at once.
    test_debug_mutable(): void {
      const store = new settings.ValueStore();
      const value = settings_make(true);
      store.value_set(value);
      this.assertFalse(Object.isFrozen(value));
      this.assertFalse(Object.isFrozen(value.provider));
      value.provider.chat_model = "changed";
      this.assertEqual(store.value_get("provider.chat_model"), "changed");
    }

    // A put outside debug mode throws, sends nothing and changes nothing.
    test_put_denied(): void {
      const sent: lines.SettingsPut[] = [];
      const store = new settings.ValueStore();
      store.value_set(settings_make(false));
      store.sender_register((payload) => {
        sent.push(payload);
      });
      this.assertRaises(Error, () => store.value_put("line_max", 2048));
      this.assertEqual(store.value_get("line_max"), 1048576);
      this.assertEqual(sent.length, 0);
    }

    // A put before the settings are set throws.
    test_put_unset(): void {
      const store = new settings.ValueStore();
      store.sender_register(() => {});
      this.assertRaises(Error, () => store.value_put("line_max", 2048));
    }

    // A put in debug mode changes the live value and sends all settings.
    test_put_sent(): void {
      const sent: lines.SettingsPut[] = [];
      const store = new settings.ValueStore();
      store.value_set(settings_make(true));
      store.sender_register((payload) => {
        sent.push(payload);
      });
      store.value_put("provider.chat_model", "grok-x");
      store.value_put("line_max", 2048);
      this.assertEqual(store.value_get("provider.chat_model"), "grok-x");
      this.assertEqual(store.value_get("line_max"), 2048);
      this.assertEqual(sent.length, 2);
      this.assertEqual(sent[0].settings.provider.chat_model, "grok-x");
      this.assertEqual(sent[0].settings.line_max, 1048576);
      this.assertEqual(sent[1].settings.line_max, 2048);
      this.assertEqual(sent[1].settings.debug, true);
      this.assertEqual(sent[1].settings.provider.timeout_seconds, 120);
    }

    // A put of an unknown id throws and sends nothing.
    test_put_unknown(): void {
      const sent: lines.SettingsPut[] = [];
      const store = new settings.ValueStore();
      store.value_set(settings_make(true));
      store.sender_register((payload) => {
        sent.push(payload);
      });
      this.assertRaises(Error, () => store.value_put("test.no_such_id", 1));
      this.assertEqual(sent.length, 0);
    }

    // A put with no sender registered throws and changes nothing.
    test_sender_missing(): void {
      const store = new settings.ValueStore();
      store.value_set(settings_make(true));
      this.assertRaises(Error, () => store.value_put("line_max", 2048));
      this.assertEqual(store.value_get("line_max"), 1048576);
    }

    // A second sender registration throws.
    test_sender_twice(): void {
      const store = new settings.ValueStore();
      store.sender_register(() => {});
      this.assertRaises(Error, () => store.sender_register(() => {}));
    }
  }

  // The functions of the module, on whatever state the thread has.
  export class TestLiveSettings extends unittest.TestCase {
    // An unknown id throws whether or not the settings were set.
    test_get_unknown(): void {
      const id = "test.no_such_id";
      this.assertRaises(Error, () => settings.settings_get(id));
    }

    // A put of an unknown id throws in every state and sends nothing.
    test_put_unknown(): void {
      const id = "test.no_such_id";
      this.assertRaises(Error, () => settings.settings_put(id, 1));
    }
  }
}

Object.freeze(test_settings);
