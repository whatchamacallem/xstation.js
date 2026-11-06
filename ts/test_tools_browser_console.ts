// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The line cases of the browser's console tools, group C, in a fresh worker of
// the headless page that the block's own ttyd serves, its parts real down to
// dash on ttyd's tty 0. A case's `mcp` line goes on the `server` lane and
// every other line on the `ui` lane, so tty 0 is opened from the UI's side as
// the console view opens it. `console.output`, tty 0's output, is not
// compared.
//
// The junction holds the cases' `mcp` lines until dash's first prompt has
// shown, so that each command's read starts after it. It then watches the
// output for the gold's `released`, the output of the view's line, and sends
// the test's end the gold's `view_released`.

namespace test_tools_browser_console {
  // The initialized sqlite3.wasm module, a global the test page sets.
  declare const test_sqlite3: substrate.SqliteModule;

  // Its installed OPFS SAH pool, a global the test page sets.
  declare const test_pool: substrate.SqlitePool;

  // The test slots, files cleared at start that no cache holds.
  declare const test_slots: substrate.SlotHandle[];

  // The gold, the threads, the types, the settings and the store's names.
  const constants = Object.freeze({
    gold_id: "typescript.test_tools_browser_console",
    thread: "ai" as const,
    server_thread: "server" as const,
    ui_thread: "ui" as const,
    provider_thread: "http" as const,
    line_type: "mcp",
    permit_type: "permit.ask",
    show_type: "console.show",
    output_type: "console.output",
    handler_version: 0,
    synchronous_setting: "queue_synchronous",
    overflow_setting: "overflow_bytes",
    blob_setting: "blob_max",
    compact_setting: "turn_compact_turns",
    root: "/test_tools_browser_console",
    server_name: "xsjs-browser",
    version: "0",
    // The path of the page that ttyd serves, below the origin.
    page_path: "/",
  });

  // A copy of a value of this block's gold, which the harness keeps frozen.
  function gold_value(name: string): unknown {
    return structuredClone(harness.gold_get(`${constants.gold_id}.${name}`));
  }

  // The payload of a reply line of the gold that the scripted UI answers.
  function far_payload(name: string): { [key: string]: unknown } {
    return jslb.payload_of(gold_value(`far.${name}`) as lines.Line);
  }

  // The type of a line.
  function type_of(line: lines.Line): unknown {
    return jslb.field_get(line[0], "type");
  }

  // The scripted UI, a real queue in synchronous mode, and the junction's port.
  function far_make(): queue.LocalPort {
    const owners: queue.OwnerTable = {
      [constants.permit_type]: constants.ui_thread,
      [constants.show_type]: constants.ui_thread,
    };
    const far = new queue.TaskQueue(constants.ui_thread, owners, true);
    const version = constants.handler_version;
    // Answers an ask with the gold's choice for its number, the number kept.
    dispatch.handler_register(constants.permit_type, version, (line) => {
      const permit = jslb.payload_of(line).permit;
      const name = gold_value(`far.choices.${String(permit)}`) as string;
      return dispatch.reply_make(line, { ...far_payload(name), permit });
    });
    // Answers a show with the gold's Empty reply, as the shown console does.
    dispatch.handler_register(constants.show_type, version, (line) =>
      dispatch.reply_make(line, far_payload("show_reply")),
    );
    const near = new queue.LocalPort();
    far.port_add(constants.thread, new queue.LocalPort(near));
    return near;
  }

  // Joins the test's end to the queue's two lanes and to the scripted UI.
  function lanes_join(
    end: queue.ThreadPort,
    server: queue.LocalPort,
    ui: queue.LocalPort,
    far: queue.LocalPort,
  ): void {
    const kind = gold_value("output_kind") as string;
    const prompt = gold_value("prompt") as string;
    const released = gold_value("released") as string;
    // tty 0's output until dash's first prompt has shown in it, then nothing.
    let output: string | undefined = "";
    // The output after that prompt until the view's line released shows.
    let watched: string | undefined = "";
    // The cases' `mcp` lines that wait for that prompt, in order.
    const held: lines.Line[] = [];
    // Keeps the output of a message of tty 0, then posts the held lines.
    const output_scan = (line: lines.Line): void => {
      const blob = line[1] as lines.BlobHeader;
      const data = jslb.field_get(blob, "data") as Uint8Array;
      if (String.fromCharCode(data[0]) !== kind) {
        return;
      }
      let added = "";
      for (const byte of data.subarray(1)) {
        added += String.fromCharCode(byte);
      }
      if (output === undefined) {
        watch_scan(added);
        return;
      }
      const text = output + added;
      if (!text.includes(prompt)) {
        output = text;
        return;
      }
      output = undefined;
      for (const waiting of held.splice(0)) {
        server.line_post(waiting, []);
      }
    };
    // Tells the test's end once the view's held line has run in tty 0.
    const watch_scan = (added: string): void => {
      if (watched === undefined) {
        return;
      }
      watched += added;
      if (watched.includes(released)) {
        watched = undefined;
        end.line_post(gold_value("lines.view_released") as lines.Line, []);
      }
    };
    // A case's `mcp` line goes on the server lane once the prompt showed.
    end.line_receive((line) => {
      if (type_of(line) !== constants.line_type) {
        ui.line_post(line, []);
      } else if (output === undefined) {
        server.line_post(line, []);
      } else {
        held.push(line);
      }
    });
    server.line_receive((line) => {
      end.line_post(line, []);
    });
    // A line of the UI lane: a request to the test's end and the scripted UI.
    ui.line_receive((line) => {
      if (type_of(line) === constants.output_type) {
        output_scan(line);
        return;
      }
      end.line_post(line, []);
      if (jslb.field_get(line[0], "id") !== undefined) {
        far.line_post(line, []);
      }
    });
    far.line_receive((line) => {
      ui.line_post(line, []);
    });
  }

  // The tool and the relays on a real queue, store, server and console port.
  export function topology_build(): queue.ThreadPort {
    const synchronous = harness.setting_get(
      constants.synchronous_setting,
    ) as boolean;
    const owners: queue.OwnerTable = {
      ...worker_ai.owners_make(),
      [constants.line_type]: constants.thread,
    };
    const tasks = new queue.TaskQueue(constants.thread, owners, synchronous);
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
    const server = new mcp.Server(constants.server_name, constants.version);
    tools_browser.tools_register(
      server,
      store,
      tasks,
      constants.provider_thread,
      gold_value("info") as lines.ProviderInfo,
      harness.setting_get,
      switches.debug_on,
    );
    dispatch.handler_register(
      constants.line_type,
      constants.handler_version,
      (line) => server.line_handle(line),
    );
    // The page's address: the origin a worker made from a Blob URL shares.
    const page = new URL(constants.page_path, location.origin).href;
    worker_ai.console_attach(tasks, new wire.ConsolePort(page));
    const server_lane = new queue.LocalPort();
    tasks.port_add(constants.server_thread, new queue.LocalPort(server_lane));
    const ui_lane = new queue.LocalPort();
    tasks.port_add(constants.ui_thread, new queue.LocalPort(ui_lane));
    const lane = new MessageChannel();
    lanes_join(
      new queue.ThreadPort(lane.port2),
      server_lane,
      ui_lane,
      far_make(),
    );
    return new queue.ThreadPort(lane.port1);
  }
}

Object.freeze(test_tools_browser_console);
