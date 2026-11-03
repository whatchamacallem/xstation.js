// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The line cases of the browser's console tools, group C, in a fresh
// worker of the headless page that the block's own ttyd serves: `mcp` lines
// through a real queue of thread `ai`, whose `mcp` handler hands each one to
// a real `mcp.Server` that holds the tools of `tools_browser` over a real
// `substrate.Store` on the realm's sqlite3 module and pool, with a real
// `wire.ConsolePort` at the page's address attached to the same queue by
// `worker_ai.console_attach`, as the ttyd page's bring up attaches it, which
// types into dash on ttyd's tty 0 through the console's shell. The queue's
// owners are the AI thread's, with `mcp` its own. Its `server` and `ui`
// lanes each end in this file's junction, joined by linked local ports, and
// the test's end is a real `queue.ThreadPort` over a MessageChannel whose
// other end the junction holds. A case's `mcp` line goes on the `server`
// lane and every other line it sends on the `ui` lane, so tty 0 is opened
// from the UI's side as the console view opens it. Every line of the
// `server` lane goes to the test's end, and every line of the `ui` lane but
// `console.output`, tty 0's output, which is not compared; a request of the
// `ui` lane also goes to the scripted UI, a second real queue of thread `ui`
// in synchronous mode joined by linked local ports, whose handlers, this
// file's functions, answer `permit.ask` by its number with the gold's
// `permit_accept` or `permit_always` and `console.show` with the gold's
// Empty reply, which go back on the `ui` lane. The junction holds the
// cases' `mcp` lines until dash's first prompt has shown in tty 0's output,
// so that each command's read starts after it. `console_attach` pushes the
// end of tty 0 to the UI as `console.exit`, though no case closes it. Each
// command's `console.busy` before its typing and `console.idle` once its read
// ends come on the `ui` lane between the show and the tool's reply. Once
// dash's first prompt has shown, the junction watches the output for the
// gold's `released`, the output of the view's line, and then sends the
// test's end the gold's `view_released`. The cases, the gold of the
// block's id: tty 0 opened and ttyd's token back; ttyd's first message sent
// with the gold's size, then `echo hi` asked, accepted, shown, typed and
// read back to the prompt; `echo 2` asked again with the next number;
// `echo 3` allowed always; `pwd` with no ask; `console_write` of a command
// that prompts, a `console_read` timed out on its `read`, the answer
// written and a read to the prompt that ends the turn; a write with no
// newline, a read that finds nothing typed, the rest of the line and its
// read; the prompting command again with the view's line sent inside the
// turn, which waits until the turn's end, so that the program reads the
// AI's answer and the view's line runs after; the view's `sleep 2`, then
// `echo after` run, whose turn waits for the prompt after the sleep;
// `sleep 600` read until the tool's timeout; and `echo never` run while
// it sleeps, whose wait passes its timeout with no turn and nothing typed.

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
