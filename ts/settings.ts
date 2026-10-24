// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The settings the server sent in `tap.start`, set once per thread, read by
// id and, in debug mode, changed by id. The file also holds the constants of
// the PowerShell scripts, under `powershell`, which the browser receives and
// does not read. `names_full()` is the one choice of the name form of the
// lines a thread builds: full names until the settings are set, then full
// names when `debug` is true and short names otherwise.

namespace settings {
  // The constants of this module.
  const constants = Object.freeze({
    id_separator: ".",
  });

  // The shape of settings.json, sent in `tap.start` unmodified.
  export interface Settings {
    debug: boolean;
    queue_synchronous: boolean;
    verbose_level: number;
    verbose_ring: number;
    line_max: number;
    blob_max: number;
    overflow_bytes: number;
    chunk_bytes: number;
    srv_buf_size: number;
    media_db_bytes: number;
    // The compaction threshold, 64, a default chosen by its writer.
    turn_compact_turns: number;
    provider: {
      scripted: boolean;
      timeout_seconds: number;
      variable: string;
    };
    powershell: {
      windows_port: number;
      linux_port: number;
      bind_address: string;
      bootstrap_script: string;
      engine_page: string;
      ttyd_build: string;
      ttyd_archive: string;
      ttyd_patches: string;
      terminal_type: string;
      linux_folder: string;
      distribution: string;
      task_name: string;
      firewall_rule: string;
      state_folder: string;
      certificate_file: string;
      key_file: string;
      certificate_days: number;
      runner_file: string;
      ttyd_log_file: string;
      poll_tries: number;
      poll_milliseconds: number;
      output_width: number;
      root_files: string[];
      runtime_modules: string[];
      build_tools: { [tool: string]: string };
      build_headers: { [header: string]: string };
    };
  }

  // An id is a key, nested keys joined by `.`, as `provider.timeout_seconds`.
  export type Id = string;

  // Submits the payload of one `settings.put` line to the server.
  export type Sender = (payload: lines.SettingsPut) => void;

  // The object that holds the last key of an id, and that key.
  interface SettingLeaf {
    holder: { [key: string]: unknown };
    key: string;
  }

  // Freezes a value and everything it holds.
  function value_freeze(value: unknown): void {
    if (typeof value === "object" && value !== null) {
      for (const child of Object.values(value)) {
        value_freeze(child);
      }
      Object.freeze(value);
    }
  }

  // The own key of an object, throwing for an unknown id.
  function child_find(holder: unknown, key: string, id: Id): unknown {
    if (
      typeof holder !== "object" ||
      holder === null ||
      !Object.hasOwn(holder, key)
    ) {
      throw new Error(i18n("settings.unknown_id", id));
    }
    return Reflect.get(holder, key);
  }

  // Walks an id down from the settings, throwing for an unknown id.
  function leaf_find(root: Settings, id: Id): SettingLeaf {
    const keys = id.split(constants.id_separator);
    const last = id.slice(id.lastIndexOf(constants.id_separator) + 1);
    let holder: unknown = root;
    for (const key of keys.slice(0, -1)) {
      holder = child_find(holder, key, id);
    }
    child_find(holder, last, id);
    return { holder: holder as { [key: string]: unknown }, key: last };
  }

  // The settings of one thread, set once, read and changed by id.
  export class ValueStore {
    private value: Settings | undefined;
    private sender: Sender | undefined;

    // Stores the settings once, deep frozen unless `debug` is true.
    value_set(value: Settings): void {
      if (this.value !== undefined) {
        throw new Error(i18n("settings.already_set"));
      }
      if (value.debug !== true) {
        value_freeze(value);
      }
      this.value = value;
    }

    // Returns the value of an id, throwing if unset or unknown.
    value_get(id: Id): unknown {
      const leaf = leaf_find(this.value_live(), id);
      return leaf.holder[leaf.key];
    }

    // Debug mode only: changes the live value and sends `settings.put`.
    value_put(id: Id, value: unknown): void {
      const live = this.value_live();
      const sender = this.sender;
      if (live.debug !== true) {
        throw new Error(i18n("settings.put_denied"));
      }
      if (sender === undefined) {
        throw new Error(i18n("settings.no_sender"));
      }
      const leaf = leaf_find(live, id);
      leaf.holder[leaf.key] = value;
      // A copy, so a later change cannot alter a line already submitted.
      sender({ settings: JSON.parse(utility.json_text(live)) });
    }

    // Registers the function that sends `settings.put`, once.
    sender_register(sender: Sender): void {
      if (this.sender !== undefined) {
        throw new Error(i18n("settings.sender_twice"));
      }
      this.sender = sender;
    }

    // Full names while the value is unset, then whether `debug` is true.
    names_full(): boolean {
      if (this.value === undefined) {
        return true;
      }
      return this.value.debug === true;
    }

    // The settings, throwing when they were not yet set.
    private value_live(): Settings {
      if (this.value === undefined) {
        throw new Error(i18n("settings.not_set"));
      }
      return this.value;
    }
  }

  // The settings of this thread, behind the functions below.
  const store = new ValueStore();

  // Stores the settings `tap.start` carried, once per thread.
  export function settings_set(value: Settings): void {
    store.value_set(value);
  }

  // Returns the value of an id, throwing before the set and for unknown ids.
  export function settings_get(id: Id): unknown {
    return store.value_get(id);
  }

  // Debug mode only: changes the live value and sends `settings.put`.
  export function settings_put(id: Id, value: unknown): void {
    store.value_put(id, value);
  }

  // Registers the function that sends `settings.put` for this thread.
  export function sender_register(sender: Sender): void {
    store.sender_register(sender);
  }

  // Whether this thread builds its lines in full names, as described above.
  export function names_full(): boolean {
    return store.names_full();
  }
}

Object.freeze(settings);
