// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The line cases of the agent: the player's turns through a real queue of
// thread `ai` on which the agent is registered with a real
// `substrate.Store` on the realm's sqlite3 module and pool and a real
// `mcp.ClientSet`, whose client reaches `tools_browser` on a real
// `mcp.Server` over the same store, its handshake run when the topology is
// built. The provider is the scripted AI, a real `provider_script.ScriptPort`
// that the queue owns as `http`, walking the script of this block's gold
// under `script`: the castle turn, whose tool calls build the castle's
// gatehouse scene through the tools, then the turn after it. The store is
// in the hyperposition when the cases start. A queue sends a request only
// from a handler's submit, so each case sends an `ask` line to a second real
// queue of thread `ui`, whose handler of this file's own submits its
// `request` to the agent and replies to the `ask` with the turn's reply as
// its `answer`; that queue also keeps the images and renders the tools send,
// answering each as the UI does, and a third real queue of thread `server`
// takes the store's pushes. The test's end is a real `queue.ThreadPort` over
// a MessageChannel whose other end the `ui` queue owns as its DOM port.

namespace test_integrate_agent {
  // The initialized sqlite3.wasm module, a global the test page sets.
  declare const test_sqlite3: substrate.SqliteModule;

  // Its installed OPFS SAH pool, a global the test page sets.
  declare const test_pool: substrate.SqlitePool;

  // The test slots, files cleared at start that no cache holds.
  declare const test_slots: substrate.SlotHandle[];

  // The gold, the threads, the owners, the types and their version.
  const constants = Object.freeze({
    gold_id: "typescript.test_integrate_agent",
    thread: "ai" as const,
    ui_thread: "ui" as const,
    test_thread: "dom" as const,
    http_thread: "http" as const,
    server_thread: "server" as const,
    owners: Object.freeze<queue.OwnerTable>({
      mcp: "ai",
      "ai.": "ai",
      "tools.": "ai",
      "test_integrate_agent.": "ai",
    }),
    line_type: "mcp",
    handler_version: 0,
    handshake_type: "test_integrate_agent.handshake",
    initialized_type: "test_integrate_agent.initialized",
    listed_type: "test_integrate_agent.listed",
    ask_type: "test_integrate_agent_ui.ask",
    answer_type: "test_integrate_agent_ui.answer",
    ui_types: Object.freeze(["media.store", "render"]),
    store_type: "media.store",
    push_types: Object.freeze([
      "db.create",
      "db.drop",
      "kv.put",
      "kv.delete",
      "doc.put",
      "turn.append",
      "sql.run",
    ]),
    overflow_setting: "overflow_bytes",
    compact_setting: "turn_compact_turns",
    root: "/test_integrate_agent",
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
    // The hyperposition scene, on screen when the castle turn starts.
    scene: "/metaverse/hyperposition/1",
    // The ref of the bootstrap script, which the castle turn runs.
    bootstrap_ref: "/_files/script/bootstrap.js",
    // The universe table and its trigger, as API/sql/metaverse.sql has them.
    universe_sql:
      "CREATE TABLE universe (name TEXT PRIMARY KEY, title TEXT NOT NULL," +
      " player TEXT NOT NULL, world TEXT NOT NULL) WITHOUT ROWID, STRICT",
    trigger_sql:
      "CREATE TRIGGER universe_world_insert BEFORE INSERT ON universe" +
      " WHEN EXISTS (SELECT 1 FROM universe" +
      " WHERE world = NEW.world AND name <> NEW.name)" +
      " BEGIN SELECT RAISE(ABORT, 'agent.content_ambiguous'); END",
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

  // A far queue of the thread, joined to the agent's queue by linked ports.
  function far_join(
    tasks: queue.TaskQueue,
    thread: queue.ThreadName,
    types: readonly string[],
  ): queue.TaskQueue {
    const owners = Object.fromEntries(types.map((type) => [type, thread]));
    const far = new queue.TaskQueue(thread, owners, true);
    const port = new queue.LocalPort();
    tasks.port_add(thread, port);
    far.port_add(constants.thread, new queue.LocalPort(port));
    return far;
  }

  // The UI's answer to the tools: an image kept by its bytes, a render shown.
  function ui_answer(line: lines.Line): lines.Line {
    if (jslb.field_get(line[0], "type") !== constants.store_type) {
      return dispatch.reply_make(line, {});
    }
    const blob = line[1] as lines.BlobHeader;
    const data = jslb.field_get(blob, "data") as Uint8Array;
    const { k } = jslb.payload_of(line);
    const sha256 = utility.sha256_hex(data);
    return dispatch.reply_make(line, { k, size: data.length, sha256 });
  }

  // Registers the handlers of the far queues, this file's own functions.
  function far_register(ui: queue.TaskQueue): void {
    const version = constants.handler_version;
    for (const type of constants.ui_types) {
      dispatch.handler_register(type, version, ui_answer);
    }
    for (const type of constants.push_types) {
      dispatch.handler_register(type, version, () => undefined);
    }
    dispatch.handler_register(constants.ask_type, version, (line) => {
      const request = jslb.payload_of(line).request as lines.Line;
      const id = ui.task_submit(request, constants.thread);
      return dispatch.task_sleep(line, [id], constants.answer_type);
    });
    dispatch.handler_register(constants.answer_type, version, (line) => {
      const ask = line.state as lines.Line;
      const [answer] = line.replies as lines.Line[];
      return dispatch.reply_make(ask, { answer });
    });
  }

  // Registers the steps of the client's handshake, this file's own handlers.
  function handshake_register(client: mcp.Client): void {
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
      return undefined;
    });
  }

  // Writes the hyperposition: its world, scene, prompt, table and script.
  function hyperposition_write(store: substrate.Store): void {
    store.db_create("metaverse");
    store.db_create("_files");
    store.sql_run("metaverse", [
      { sql: constants.universe_sql, params: [] },
      { sql: constants.trigger_sql, params: [] },
    ]);
    store.kv_put("/metaverse/world", utility.utf8_encode("metaverse"));
    store.kv_put("/metaverse/scene", utility.utf8_encode(constants.scene));
    store.doc_put("metaverse", "prompt", {
      0: { t: "prompt" },
      text: gold_value("analyst") as string,
    });
    const bootstrap = gold_value("bootstrap_script") as string;
    store.kv_put(constants.bootstrap_ref, utility.utf8_encode(bootstrap));
  }

  // The agent and the tools on real parts, the scripted AI, the test's end.
  export function topology_build(): queue.ThreadPort {
    provider.key_set(constants.key);
    const tasks = new queue.TaskQueue(
      constants.thread,
      constants.owners,
      true,
    );
    const script = structuredClone(
      gold_value("script"),
    ) as provider_script.Script;
    tasks.port_add(
      constants.http_thread,
      new provider_script.ScriptPort(script),
    );
    const ui = far_join(tasks, constants.ui_thread, [
      ...constants.ui_types,
      constants.ask_type,
      constants.answer_type,
    ]);
    far_join(tasks, constants.server_thread, constants.push_types);
    far_register(ui);
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
    handshake_register(client);
    tasks.line_notify(line_typed(constants.handshake_type));
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
    const channel = new MessageChannel();
    ui.port_add(constants.test_thread, new queue.ThreadPort(channel.port2));
    return new queue.ThreadPort(channel.port1);
  }
}

Object.freeze(test_integrate_agent);
