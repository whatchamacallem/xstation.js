// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The line cases of the agent's faults, a block of the side `workers` of
// `test_headless`, whose page brings up a fresh AI worker for each case and
// terminates it before the next, since each case fails the agent's queue,
// as fail loud intends, and a realm holds one agent. In each worker this
// file's part registers the agent on the bring up's own queue, the AI
// thread's real queue, with a real `substrate.Store` on the sqlite3.wasm
// module and the OPFS pool the bring up sets as globals, a cache over the
// test slots, and that queue as the store's queue, so that its pushes go to
// the server on the worker's lane; a real `mcp.ClientSet` whose client
// reaches `tools_browser` on a real `mcp.Server` over the same store; and
// the scripted AI, a real `provider_script.ScriptPort` that the queue owns
// as `http`, walking the script of this block's gold under `script`, whose
// start node answers each input with one case's reply. It writes the
// hyperposition the agent reads, the database `metaverse` with its universe
// table, world, scene and the analyst's prompt, runs the client's handshake
// by this file's own handlers, and at its end calls `ready`, after which
// the page posts the case's `ai.say` on the UI channel, as the UI thread
// does. The cases, the gold of the block's id, expect the Empty reply to
// `tap.start`, the hyperposition's pushes, the ready notice, the push of the
// player's turn, and then the `error` line of the queue's fault, which the
// page compares by its message and the first line of each stack down its
// cause chain: arguments that are not JSON, a number that overflows a
// double, four kinds of JSON that are not an object, a reply with neither
// tool calls nor content, and a round whose second tool throws after its
// first committed its push.

namespace test_agent_faults {
  // The initialized sqlite3.wasm module, a global the bring up sets.
  declare const test_sqlite3: substrate.SqliteModule;

  // The installed OPFS SAH pool, a global the bring up sets.
  declare const test_pool: substrate.SqlitePool;

  // The test slots, files cleared at start that no cache holds.
  declare const test_slots: substrate.SlotHandle[];

  // The gold, the threads, the types and their version, the provider.
  const constants = Object.freeze({
    gold_id: "typescript.test_agent_faults",
    thread: "ai" as const,
    http_thread: "http" as const,
    line_type: "mcp",
    handler_version: 0,
    handshake_type: "test_agent_faults.handshake",
    initialized_type: "test_agent_faults.initialized",
    listed_type: "test_agent_faults.listed",
    overflow_setting: "overflow_bytes",
    compact_setting: "turn_compact_turns",
    root: "/test_agent_faults",
    server_name: "xsjs-browser",
    client_name: "hyperposition-engine",
    version: "0",
    prefix: "browser",
    // The provider's address and models of a scripted run, empty.
    info: Object.freeze<lines.ProviderInfo>({
      base_url: "",
      chat_model: "",
      image_model: "",
    }),
    key: "xai-SYNTHETIC-KEY",
    // The hyperposition scene, on screen when each case's turn starts.
    scene: "/metaverse/hyperposition/1",
    // The universe table, as API/sql/metaverse.sql has it.
    universe_sql:
      "CREATE TABLE universe (name TEXT PRIMARY KEY, title TEXT NOT NULL," +
      " player TEXT NOT NULL, world TEXT NOT NULL) WITHOUT ROWID, STRICT",
  });

  // A value of this block's gold.
  function gold_value(name: string): unknown {
    return harness.gold_get(`${constants.gold_id}.${name}`);
  }

  // A line of this file's own type, in the form the settings pick.
  function line_typed(type: string): lines.Line {
    const header = jslb.header_make(type, { full: settings.names_full() });
    return jslb.line_make(header, [], {});
  }

  // Registers the steps of the client's handshake, `ready` called at its end.
  function handshake_register(client: mcp.Client, ready: () => void): void {
    const version = constants.handler_version;
    dispatch.handler_register(constants.handshake_type, version, () =>
      dispatch.task_sleep(
        null,
        [client.initialize_send()],
        constants.initialized_type,
      ),
    );
    dispatch.handler_register(constants.initialized_type, version, (line) => {
      client.initialized_send((line.replies as lines.Line[])[0]);
      const id = client.tools_list();
      return dispatch.task_sleep(null, [id], constants.listed_type);
    });
    dispatch.handler_register(constants.listed_type, version, (line) => {
      client.tools_read((line.replies as lines.Line[])[0]);
      ready();
      return undefined;
    });
  }

  // Writes the hyperposition: its world, its scene, its prompt and table.
  function hyperposition_write(store: substrate.Store): void {
    store.db_create("metaverse");
    store.sql_run("metaverse", [{ sql: constants.universe_sql, params: [] }]);
    store.kv_put("/metaverse/world", utility.utf8_encode("metaverse"));
    store.kv_put("/metaverse/scene", utility.utf8_encode(constants.scene));
    store.doc_put("metaverse", "prompt", {
      0: { t: "prompt" },
      text: gold_value("analyst") as string,
    });
  }

  // The agent and the tools on the bring up's queue, the scripted AI.
  export function worker_run(
    tasks: queue.TaskQueue,
    _start: boot.HeadlessStart,
    ready: () => void,
  ): void {
    provider.key_set(constants.key);
    const script = structuredClone(
      gold_value("script"),
    ) as provider_script.Script;
    tasks.port_add(
      constants.http_thread,
      new provider_script.ScriptPort(script),
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
    hyperposition_write(store);
    const server = new mcp.Server(constants.server_name, constants.version);
    tools_browser.tools_register(
      server,
      store,
      tasks,
      constants.http_thread,
      constants.info,
      harness.setting_get,
    );
    dispatch.handler_register(
      constants.line_type,
      constants.handler_version,
      (line) => server.line_handle(line),
    );
    const client = new mcp.Client(
      constants.client_name,
      constants.version,
      tasks,
      constants.thread,
    );
    handshake_register(client, ready);
    const clients = new mcp.ClientSet();
    clients.client_add(constants.prefix, client);
    agent.handlers_register(
      store,
      clients,
      tasks,
      constants.http_thread,
      constants.info,
      dispatch.handler_register,
    );
    tasks.line_notify(line_typed(constants.handshake_type), constants.thread);
  }
}

Object.freeze(test_agent_faults);
