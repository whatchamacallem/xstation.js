// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The line cases of the store, a block of group B in the AI worker: the
// requests of the ui-ai lane, their replies and the pushes of their commits,
// on real parts. The cache takes the `overflow_bytes` of the gold, so that a
// value of a few bytes goes to a cache file and the gold stays small. The lane
// `server` is a linked pair of `queue.LocalPort`s whose far end is the test's
// own receiver, which posts each push on the queue's end of the ui lane, so
// that a case reads the pushes of a commit and its reply in the order the
// store sent them.

namespace test_integrate_substrate {
  // The initialized sqlite3.wasm module, a global the bring up sets.
  declare const test_sqlite3: substrate.SqliteModule;

  // The installed OPFS SAH pool, a global the bring up sets.
  declare const test_pool: substrate.SqlitePool;

  // The open OPFS files of this block, cleared, a global the bring up sets.
  declare const test_slots: readonly substrate.SlotHandle[];

  // The block's gold, the threads of its lanes, its root and its settings.
  const constants = Object.freeze({
    gold_id: "typescript.test_integrate_substrate",
    thread: "ai" as const,
    ui_thread: "ui" as const,
    server_thread: "server" as const,
    root: "/test_integrate_substrate",
    synchronous_setting: "queue_synchronous",
    blob_setting: "blob_max",
    compact_setting: "turn_compact_turns",
  });

  // A value of the block's gold.
  function gold_value(name: string): unknown {
    return structuredClone(harness.gold_get(`${constants.gold_id}.${name}`));
  }

  // The first files of `test_slots`, as many as the gold names.
  function slots_get(): substrate.SlotHandle[] {
    const count = gold_value("slot_count") as number;
    if (test_slots.length < count) {
      throw new Error(
        `test_slots holds ${test_slots.length} files, fewer than ${count}`,
      );
    }
    return test_slots.slice(0, count);
  }

  // The store on its queue, the server lane joined, the test's end of `ui`.
  export function topology_build(): queue.ThreadPort {
    const synchronous = harness.setting_get(
      constants.synchronous_setting,
    ) as boolean;
    const owners = gold_value("owners") as queue.OwnerTable;
    const tasks = new queue.TaskQueue(constants.thread, owners, synchronous);
    const lane = new MessageChannel();
    const ui = new queue.ThreadPort(lane.port2);
    tasks.port_add(constants.ui_thread, ui);
    const far = new queue.LocalPort();
    // A push goes on the ui lane after every line the queue posted before it.
    far.line_receive((line) => {
      ui.line_post(line, []);
    });
    tasks.port_add(constants.server_thread, new queue.LocalPort(far));
    const store = new substrate.Store(
      test_sqlite3,
      test_pool,
      new substrate.CacheFiles(slots_get()),
      constants.root,
      gold_value("overflow_bytes") as number,
      harness.setting_get(constants.blob_setting) as number,
      harness.setting_get(constants.compact_setting) as number,
      tasks,
    );
    store.handlers_register(dispatch.handler_register);
    return new queue.ThreadPort(lane.port1);
  }
}
Object.freeze(test_integrate_substrate);
