// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The line cases of the store's crash, a block of the side `workers` of
// `test_headless`, with a fresh AI worker for each case. A worker on a cleared
// pool and cleared slots runs `test_substrate_store.kill_put`, which holds
// inside the transaction of a put of a value over `overflow_bytes`, after the
// value's cache file is written and its `_kv` row inserted, but before the
// commit. On its pause it sends the notice `test_substrate_crash.paused`, and
// the page terminates it at the next case's start. A worker on what that
// worker left runs `test_substrate_store.kill_check`, which lists the rows of
// the value and removes the cache files no row names, then sends
// `test_substrate_crash.checked` with the count of each.

namespace test_substrate_crash {
  // The initialized sqlite3.wasm module, a global the bring up sets.
  declare const test_sqlite3: substrate.SqliteModule;

  // The installed OPFS SAH pool, a global the bring up sets.
  declare const test_pool: substrate.SqlitePool;

  // The test slots, cleared at start unless the start keeps them.
  declare const test_slots: substrate.SlotHandle[];

  // The gold, the settings of the store's sizes, the notices and their owner.
  const constants = Object.freeze({
    root_id: "typescript.test_substrate_crash.root",
    overflow_setting: "overflow_bytes",
    blob_setting: "blob_max",
    compact_setting: "turn_compact_turns",
    paused_type: "test_substrate_crash.paused",
    checked_type: "test_substrate_crash.checked",
    server_owner: "server" as const,
  });

  // A notice of this file's own type, in the form the settings pick.
  function notice_make(
    type: string,
    payload: { [key: string]: unknown },
  ): lines.Line {
    const header = jslb.header_make(type, { full: settings.names_full() });
    return jslb.line_make(header, [], payload);
  }

  // Holds a put inside its transaction, or checks what the held one left.
  export function worker_run(
    tasks: queue.TaskQueue,
    start: boot.HeadlessStart,
  ): void {
    const store = new substrate.Store(
      test_sqlite3,
      test_pool,
      new substrate.CacheFiles([...test_slots]),
      harness.gold_get(constants.root_id) as string,
      harness.setting_get(constants.overflow_setting) as number,
      harness.setting_get(constants.blob_setting) as number,
      harness.setting_get(constants.compact_setting) as number,
      tasks,
    );
    if (start.clear) {
      test_substrate_store.kill_put(store, () => {
        tasks.line_notify(
          notice_make(constants.paused_type, {}),
          constants.server_owner,
        );
      });
    } else {
      const checked = test_substrate_store.kill_check(store);
      tasks.line_notify(
        notice_make(constants.checked_type, { ...checked }),
        constants.server_owner,
      );
    }
  }
}

Object.freeze(test_substrate_crash);
