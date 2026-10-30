// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The line cases of the browser's tools: `mcp` lines through a real queue of
// thread `ai`, whose `mcp` handler hands each one to a real `mcp.Server`
// that holds the tools of `tools_browser` over a real `substrate.Store` on
// the realm's sqlite3 module and pool. The test's end is the queue's lane to
// `server`, a real `queue.ThreadPort` over a MessageChannel, on which an
// external agent's `mcp` lines arrive, and on which the store's pushes go
// out, so each case expects the pushes of the operations a tool commits, then
// the tool's reply. The far ends of the image a tool asks for are second real
// queues whose handlers are this file's own functions: `http`, the scripted
// AI, answers the image request with the gold's `image_answer`, and `ui`
// answers the keeping of the image with the gold's `media_store_reply`.

namespace test_integrate_tools_browser {
  // The initialized sqlite3.wasm module, a global the test page sets.
  declare const test_sqlite3: substrate.SqliteModule;

  // Its installed OPFS SAH pool, a global the test page sets.
  declare const test_pool: substrate.SqlitePool;

  // The test slots, files cleared at start that no cache holds.
  declare const test_slots: substrate.SlotHandle[];

  // The gold, the threads, the owners, the types and their version.
  const constants = Object.freeze({
    gold_id: "typescript.test_integrate_tools_browser",
    thread: "ai" as const,
    test_thread: "server" as const,
    http_thread: "http" as const,
    ui_thread: "ui" as const,
    owners: Object.freeze<queue.OwnerTable>({ mcp: "ai", "tools.": "ai" }),
    line_type: "mcp",
    request_type: "http.request",
    store_type: "media.store",
    handler_version: 0,
    synchronous_setting: "queue_synchronous",
    overflow_setting: "overflow_bytes",
    compact_setting: "turn_compact_turns",
    root: "/test_integrate_tools_browser",
    server_name: "xsjs-browser",
    version: "0",
    // The provider's address and models a hello carries when not scripted.
    info: Object.freeze<lines.ProviderInfo>({
      base_url: "https://api.x.ai/v1",
      chat_model: "grok-4",
      image_model: "grok-2-image",
    }),
    key: "xai-SYNTHETIC-KEY",
  });

  // A far queue of the thread, joined to the tools' queue by linked ports.
  function far_join(
    tasks: queue.TaskQueue,
    thread: queue.ThreadName,
    type: string,
    synchronous: boolean,
  ): void {
    const far = new queue.TaskQueue(thread, { [type]: thread }, synchronous);
    const port = new queue.LocalPort();
    tasks.port_add(thread, port);
    far.port_add(constants.thread, new queue.LocalPort(port));
  }

  // The far end's answer to a request: the reply line of the gold named.
  function answer_make(name: string): dispatch.Handler {
    return (line: lines.Line) => {
      const frame = structuredClone(
        harness.gold_get(`${constants.gold_id}.far.${name}`),
      ) as lines.Line;
      return dispatch.reply_make(line, jslb.payload_of(frame));
    };
  }

  // The tools on a real server, store and queue, and the test's end.
  export function topology_build(): queue.ThreadPort {
    provider.key_set(constants.key);
    const synchronous = harness.setting_get(
      constants.synchronous_setting,
    ) as boolean;
    const tasks = new queue.TaskQueue(
      constants.thread,
      constants.owners,
      synchronous,
    );
    const version = constants.handler_version;
    far_join(
      tasks,
      constants.http_thread,
      constants.request_type,
      synchronous,
    );
    far_join(tasks, constants.ui_thread, constants.store_type, synchronous);
    dispatch.handler_register(
      constants.request_type,
      version,
      answer_make("image_answer"),
    );
    dispatch.handler_register(
      constants.store_type,
      version,
      answer_make("media_store_reply"),
    );
    const store = new substrate.Store(
      test_sqlite3,
      test_pool,
      new substrate.CacheFiles([...test_slots]),
      constants.root,
      harness.setting_get(constants.overflow_setting) as number,
      harness.setting_get(constants.compact_setting) as number,
      tasks,
    );
    const server = new mcp.Server(constants.server_name, constants.version);
    tools_browser.tools_register(
      server,
      store,
      tasks,
      constants.http_thread,
      constants.info,
      harness.setting_get,
    );
    dispatch.handler_register(constants.line_type, version, (line) =>
      server.line_handle(line),
    );
    const channel = new MessageChannel();
    tasks.port_add(constants.test_thread, new queue.ThreadPort(channel.port2));
    return new queue.ThreadPort(channel.port1);
  }
}

Object.freeze(test_integrate_tools_browser);
