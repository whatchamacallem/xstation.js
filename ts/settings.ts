// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The settings the server sent in hello, set once per thread, read by id
// and, in debug mode, changed by id.

namespace settings {
  // The constants of this module.
  const constants = Object.freeze({
    id_separator: ".",
  });

  // The shape of settings.json, sent in `hello` unmodified.
  export interface Settings {
    debug: boolean;
    queue_synchronous: boolean;
    verbose_level: number;
    verbose_ring: number;
    verbose_forward: boolean;
    line_max: number;
    blob_max: number;
    message_max: number;
    queue_max: number;
    overflow_bytes: number;
    chunk_bytes: number;
    srv_buf_size: number;
    media_db_bytes: number;
    files_browser_bytes: number;
    db_soft_bytes: number;
    turn_compact_tokens: number;
    long_task_ms: number;
    provider: {
      scripted: boolean;
      timeout_seconds: number;
    };
  }

  // An id is a key, nested keys joined by `.`, as `provider.timeout_seconds`.
  export type Id = string;

  // Submits the payload of one `settings.put` line to the server.
  export type Sender = (payload: lines.SettingsPut) => void;

  // The object that holds the last key of an id, and that key.
  interface Leaf {
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
  function leaf_find(root: Settings, id: Id): Leaf {
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

  // Stores the settings the hello carried, once per thread.
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
}

Object.freeze(settings);
