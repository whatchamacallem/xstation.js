// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The line cases of the agent's faults, a block of the side `workers` of
// `test_headless`, with a fresh AI worker for each case, since each case fails
// the agent's queue, as fail loud intends, and a realm holds one agent. In
// each worker this file's part registers the agent on the bring up's own queue
// with real parts and the scripted AI, a real `provider_script.ScriptPort`
// walking this block's gold under `script`, behind this file's relay, which the
// queue owns as `http`: the relay checks that every id of a reply carries its
// one digest and writes it as zeros, so the gold pins the id an error names,
// and a case asks the model once, as the scripted AI holds no zeroed id. The
// server holds this file's tool `picture`, whose image no call output carries.
// The part writes the hyperposition, runs the client's handshake by this file's
// own handlers, and at its end calls `ready`. The page compares the `error`
// line of the queue's fault by its message and the first line of each stack
// down its cause chain.

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
    blob_setting: "blob_max",
    compact_setting: "turn_compact_turns",
    root: "/test_agent_faults",
    server_name: "xsjs-browser",
    client_name: "hyperposition-engine",
    version: "0",
    prefix: "browser",
    // A scripted run's request as xAI takes it, its address never resolving.
    info: Object.freeze<lines.ProviderInfo>({
      base_url: "https://scripted.invalid/v1",
      chat_model: "grok-4.7",
      image_model: "grok-imagine-image",
    }),
    key: "xai-SYNTHETIC-KEY",
    // The hyperposition scene, on screen when each case's turn starts.
    scene: "/metaverse/hyperposition/1",
    // The universe table, as API/sql/metaverse.sql has it.
    universe_sql:
      "CREATE TABLE universe (name TEXT PRIMARY KEY, title TEXT NOT NULL," +
      " player TEXT NOT NULL, world TEXT NOT NULL) WITHOUT ROWID, STRICT",
    // A scripted response's id, which carries 16 hexadecimal digits of digest.
    response_id: /^resp_([0-9a-f]{16})$/,
    // A scripted output item's id, which carries its response's digest.
    item_id: /^(?:rs|msg|fc)_([0-9a-f]{16})(?:_[1-9][0-9]*)?$/,
    // The digit that stands for each digit of the digest in the gold.
    zero_digit: "0",
  });

  // An object of fields by name, as a reply's JSON body holds them.
  type FieldTable = { [key: string]: unknown };

  // A value of this block's gold.
  function gold_value(name: string): unknown {
    return harness.gold_get(`${constants.gold_id}.${name}`);
  }

  // A line of this file's own type, in the form the settings pick.
  function line_typed(type: string): lines.Line {
    const header = jslb.header_make(type, { full: settings.names_full() });
    return jslb.line_make(header, [], {});
  }

  // A copy of the scripted AI's reply, the one digest of its ids as zeros.
  function digest_zeroed(line: lines.Line): lines.Line {
    const copy = structuredClone(line);
    const json = copy.json as FieldTable;
    const id = String(json.id);
    const found = constants.response_id.exec(id);
    if (found === null) {
      throw new Error(`the scripted reply's id ${id} carries no digest`);
    }
    const digest = found[1];
    const zeros = constants.zero_digit.repeat(digest.length);
    json.id = id.replace(digest, zeros);
    for (const item of json.output as FieldTable[]) {
      const item_id = String(item.id);
      const parts = constants.item_id.exec(item_id);
      if (parts === null || parts[1] !== digest) {
        throw new Error(`the scripted item's id ${item_id} lacks ${digest}`);
      }
      item.id = item_id.replace(digest, zeros);
    }
    return copy;
  }

  // The lane `http`: the scripted AI's port, each reply's digest zeroed.
  class ZeroedPort implements queue.Port {
    // The scripted AI's port, which answers a request before its post ends.
    readonly #port: queue.Port;

    // Takes the port it relays.
    constructor(port: queue.Port) {
      this.#port = port;
    }

    // Posts the request to the scripted AI as it is.
    line_post(line: lines.Line, transfer: ArrayBuffer[]): void {
      this.#port.line_post(line, transfer);
    }

    // Hands each reply to the receiver with its digest zeroed.
    line_receive(fn: (line: lines.Line) => void): void {
      this.#port.line_receive((line) => {
        fn(digest_zeroed(line));
      });
    }
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
      new ZeroedPort(
        new provider_script.ScriptPort(script, switches.debug_on),
      ),
    );
    const store = new substrate.Store(
      test_sqlite3,
      test_pool,
      new substrate.CacheFiles([...test_slots]),
      constants.root,
      harness.setting_get(constants.overflow_setting) as number,
      harness.setting_get(constants.blob_setting) as number,
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
      switches.debug_on,
    );
    // Its result is an image, which the agent refuses as a call's output.
    const picture = structuredClone(gold_value("picture_tool")) as mcp.Tool;
    server.tool_register(picture, () => ({
      content: [{ type: "image", data: "", mimeType: "image/png" }],
    }));
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
      switches.debug_on,
    );
    tasks.line_notify(line_typed(constants.handshake_type), constants.thread);
  }
}

Object.freeze(test_agent_faults);
