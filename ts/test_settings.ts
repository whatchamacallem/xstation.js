// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Tests of the settings module: the value store's reads, the name form, the
// freezing outside debug mode and the puts, each thrown text compared to its
// entry in the gold record, test_settings.json.

namespace test_settings {
  // The values the tests put.
  const constants = Object.freeze({
    // A changed `provider.timeout_seconds`, its writer's choice.
    timeout_changed: 60,
    // A changed `line_max`, its writer's choice.
    line_changed: 2048,
  });

  // A complete settings object with `debug` as given, the example values.
  function settings_make(debug: boolean): settings.Settings {
    return {
      debug,
      queue_synchronous: false,
      verbose_level: 1,
      verbose_ring: 1000,
      line_max: 1048576,
      blob_max: 2147483391,
      overflow_bytes: 131072,
      chunk_bytes: 1048576,
      srv_buf_size: 1048576,
      media_db_bytes: 268435456,
      turn_compact_turns: 64,
      provider: {
        scripted: true,
        timeout_seconds: 120,
        variable: "XSJS_PROVIDER_KEY",
      },
      powershell: {
        windows_port: 5768,
        linux_port: 5769,
        bind_address: "127.0.0.1",
        bootstrap_script: "bootstrap.py",
        engine_page: "hyperposition-engine.html",
        ttyd_build: "build/ttyd",
        ttyd_archive: "third_party/ttyd-1.7.7.tar.gz",
        ttyd_patches: "third_party/ttyd",
        terminal_type: "dumb",
        linux_folder: ".cache/xsjs",
        distribution: "Ubuntu",
        task_name: "xstation.js",
        firewall_rule: "xstation.js",
        state_folder: "xstation.js",
        certificate_file: "_cached_cert.pem",
        key_file: "_cached_key.pem",
        certificate_days: 825,
        runner_file: "serve.ps1",
        ttyd_log_file: "ttyd.log",
        poll_tries: 30,
        poll_milliseconds: 500,
        output_width: 200,
        root_files: ["settings.json", "test_settings.json", "provider.json"],
        runtime_modules: ["internationalization", "jslb", "settings"],
        build_tools: { cmake: "cmake" },
        build_headers: { "uv.h": "libuv1-dev" },
      },
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
      store.value_set(settings_make(false));
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
      store.value_set(settings_make(false));
      this.assertEqual(store.value_get("debug"), false);
      this.assertEqual(store.value_get("line_max"), 1048576);
      this.assertEqual(store.value_get("provider.scripted"), true);
      this.assertEqual(store.value_get("provider.timeout_seconds"), 120);
      this.assertEqual(
        store.value_get("provider.variable"),
        "XSJS_PROVIDER_KEY",
      );
      this.assertEqual(store.value_get("powershell.poll_tries"), 30);
      const provider = store.value_get("provider") as { scripted: boolean };
      this.assertEqual(provider.scripted, true);
    }

    // Full names before the settings are set, then as `debug` says.
    test_names_full(): void {
      const unset = new settings.ValueStore();
      this.assertTrue(unset.names_full());
      const debug = new settings.ValueStore();
      debug.value_set(settings_make(true));
      this.assertTrue(debug.names_full());
      const release = new settings.ValueStore();
      release.value_set(settings_make(false));
      this.assertFalse(release.names_full());
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
        value.provider.timeout_seconds = constants.timeout_changed;
      });
      this.assertEqual(store.value_get("debug"), false);
    }

    // A second set throws and leaves the first settings in place.
    test_set_twice(): void {
      const store = new settings.ValueStore();
      store.value_set(settings_make(false));
      const second = settings_make(true);
      const message = message_thrown(this, () => store.value_set(second));
      this.assertEqual(message, gold_text("settings_already_set"));
      this.assertEqual(store.value_get("debug"), false);
    }

    // In debug mode the object is not frozen and shows a change at once.
    test_debug_mutable(): void {
      const store = new settings.ValueStore();
      const value = settings_make(true);
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
      store.value_set(settings_make(false));
      store.sender_register((payload) => {
        sent.push(payload);
      });
      const message = message_thrown(this, () => {
        store.value_put("line_max", constants.line_changed);
      });
      this.assertEqual(message, gold_text("settings_put_denied"));
      this.assertEqual(store.value_get("line_max"), 1048576);
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
      store.value_set(settings_make(true));
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
      this.assertEqual(sent[0].settings.line_max, 1048576);
      this.assertEqual(sent[1].settings.line_max, constants.line_changed);
      this.assertEqual(sent[1].settings.debug, true);
      this.assertEqual(sent[1].settings.provider.scripted, true);
    }

    // A put of an unknown id throws and sends nothing.
    test_put_unknown(): void {
      const sent: lines.SettingsPut[] = [];
      const store = new settings.ValueStore();
      store.value_set(settings_make(true));
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
      store.value_set(settings_make(true));
      const message = message_thrown(this, () => {
        store.value_put("line_max", constants.line_changed);
      });
      this.assertEqual(message, gold_text("settings_no_sender"));
      this.assertEqual(store.value_get("line_max"), 1048576);
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
