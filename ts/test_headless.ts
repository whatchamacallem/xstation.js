// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The headless realm of one block of group B, on the page whose last
// script, a worker script, is `test_headless.realm_open()`: it runs on both
// threads and reads `self.name`, as `test_all.suites_run()` does on the ttyd
// page, "ai" in the worker, "" on the main thread.
//
// The main thread opens the lane `realm` to the driver, over DevTools. The
// driver adds the binding `realm_line` by `Runtime.addBinding` before the
// page loads, and `realm_open()` throws without it. Each line the realm
// sends is one call of `realm_line` with the base64 of its bytes by
// `jslb.line_encode`. The driver then calls, by `Runtime.evaluate`,
//
//     test_headless.realm_start(BLOCK, FAILFAST, LINE)
//
// with the name of a block of the table below, a boolean, true when the
// first failure ends the stream with a bail out, and the base64 of the bytes
// of the first line, which must be `tap.start` with `i` 101, carrying the
// settings and the test settings. It is decoded by `jslb.LineDecoder` over
// an empty `substrate.CacheFiles`, under the bounds the wire reads the
// page's first line with. A throw while `realm_start` runs, as at any other
// first line, an unknown block, a call before `realm_open()` or after a
// first call, or in a UI block's synchronous run, is the exception of the
// `Runtime.evaluate` call, and not a line of the lane.
//
// A UI block runs on the main thread, in its own page load: the settings and
// the harness's values are set, an Empty reply answers `tap.start`, and the
// block runs as the one block of a TAP stream, each line sent as a
// `tap.line` push the moment it is made. A block is a unittest module, run
// through `TAPTestRunner.module_run`, or a block of line cases, whose
// suite's topology `line_case.block_run` runs on the gold
// `typescript.BLOCK`.
//
// A worker block runs in a fresh Worker made from the texts of the
// `data-worker` scripts and named "ai", which `boot.headless_worker` brings
// up. The page posts it the worker's ends of two channels, the realm lane
// and the UI channel, and the start: `tap.start`, the block and failfast.
// Its `worker_ai.tap_start` sets its settings, sends `settings.set` on the
// UI channel, answers `tap.start` with an Empty reply on the realm lane, and
// runs the block in its `worker.tests` task, each TAP line a `tap.line` to
// its queue's server, the realm lane, which in debug mode also carries the
// worker's `verbose.put` pushes. The page holds a `queue.ThreadPort` at its
// end of each channel and relays every line that comes on either to the
// driver, and the `fault` lines the worker posts to the page.
//
// A fault of the main thread goes to the driver as an `error` line of its
// cascade by `dispatch.cause_make`, from the stop function of the error
// overlay. A fault of the worker goes as `tap_start`'s report function sends
// it, an `error` line on the realm lane, then its `fault` line; before
// `tap_start`, its `fault` line alone. The realm's last line ends its TAP
// stream, and the driver ends the realm by its next page load.

namespace test_headless {
  // The binding the driver adds by `Runtime.addBinding`, one call per line.
  declare const realm_line: (text: string) => void;

  // The worker, the lane's line types and numbers, and the first decoder.
  const constants = Object.freeze({
    worker_name: "ai",
    worker_scripts: "script[data-worker]",
    strict_line: '"use strict";\n',
    script_join: "\n",
    script_media: "text/javascript",
    first_type: "tap.start",
    first_id: 101,
    line_type: "tap.line",
    error_type: "error",
    language: "typescript" as const,
    gold_prefix: "typescript.",
    // The longest first line: 10 MiB, as the wire reads the page's first.
    first_line_max: 10485760,
    // The blob bytes of the first line: none, as it has none.
    first_blob_max: 0,
    first_overflow_bytes: 0,
    // The bytes given to one `String.fromCharCode`, below its argument limit.
    chunk_bytes: 32768,
  });

  // The thread a block runs on: the main thread or a fresh worker.
  type Side = "ui" | "worker";

  // A block: a unittest module or a block of line cases, and its thread.
  type Block =
    | {
        readonly side: Side;
        readonly module: () => { [name: string]: unknown };
      }
    | { readonly side: Side; readonly topology: line_case.TopologyBuild };

  // The blocks of group B by name.
  const blocks = Object.freeze<{ readonly [name: string]: Block }>({
    test_error_overlay: { side: "ui", module: () => test_error_overlay },
    test_overlay: { side: "ui", module: () => test_overlay },
    test_console_view: { side: "ui", module: () => test_console_view },
    test_page: { side: "ui", module: () => test_page },
    test_substrate_store: {
      side: "worker",
      module: () => test_substrate_store,
    },
    test_jslb_decode: { side: "worker", module: () => test_jslb_decode },
    test_script: { side: "worker", module: () => test_script },
    test_tools_browser: { side: "worker", module: () => test_tools_browser },
    test_agent: { side: "worker", module: () => test_agent },
    test_worker_ai: { side: "worker", module: () => test_worker_ai },
    test_boot: { side: "ui", module: () => test_boot },
    test_integrate_media: { side: "ui", module: () => test_integrate_media },
  });

  // Where the lane stands: not yet open, open, then started by the driver.
  let phase: "closed" | "open" | "started" = "closed";

  // Sends a line to the driver, one call of the binding with its bytes.
  function line_write(line: lines.Line): void {
    let binary = "";
    for (const piece of jslb.line_encode(line)) {
      if (typeof piece === "string") {
        throw new Error("internal error");
      }
      for (let at = 0; at < piece.length; at += constants.chunk_bytes) {
        const chunk = piece.subarray(at, at + constants.chunk_bytes);
        binary += String.fromCharCode(...chunk);
      }
    }
    realm_line(btoa(binary));
  }

  // A line of the stream, as a `tap.line` push.
  function text_line(text: string): lines.Line {
    const header = jslb.header_make(constants.line_type, {
      full: settings.names_full(),
    });
    const payload = { language: constants.language, text };
    return jslb.line_make(header, [], payload);
  }

  // The `error` line of a fault of the main thread, holding its cascade.
  function error_line(thrown: unknown): lines.Line {
    const header = jslb.header_make(constants.error_type, {
      full: settings.names_full(),
    });
    return jslb.line_make(header, [], { ...dispatch.cause_make(thrown) });
  }

  // The block of the table by its name, which must be there.
  function block_find(name: string): Block {
    if (!Object.hasOwn(blocks, name)) {
      throw new Error(`test_headless has no block ${JSON.stringify(name)}`);
    }
    return blocks[name];
  }

  // Runs the block as the one block of the stream, then `done`.
  function block_launch(
    runner: tap_producer.TAPTestRunner,
    name: string,
    done: (passed: boolean) => void,
  ): void {
    const block = block_find(name);
    if ("module" in block) {
      const loader = new unittest.TestLoader();
      done(
        runner.module_run(name, () =>
          loader.loadTestsFromModule(block.module()),
        ),
      );
    } else {
      const id = `${constants.gold_prefix}${name}`;
      line_case.block_run(runner, name, id, block.topology, done);
    }
  }

  // Decodes the driver's first line: `tap.start` with `i` 101, in debug mode.
  function first_read(text: string): lines.Line {
    const decoder = new jslb.LineDecoder(
      constants.first_line_max,
      constants.first_blob_max,
      constants.first_overflow_bytes,
      new substrate.CacheFiles([]),
    );
    const found = decoder.bytes_feed(utility.base64_decode(text));
    if (found.length !== 1 || !decoder.idle()) {
      throw new Error(
        `the driver's bytes hold ${found.length} whole lines, not tap.start`,
      );
    }
    const first = found[0];
    const header = first[0];
    if (
      jslb.field_get(header, "type") !== constants.first_type ||
      jslb.field_get(header, "id") !== constants.first_id
    ) {
      throw new Error(
        `the first line is not tap.start with i 101: ${jslb.line_render(first)}`,
      );
    }
    const payload = jslb.payload_of(first) as unknown as lines.TapStart;
    if (payload.test_settings === undefined) {
      throw new Error("tap.start carries no test_settings: not debug mode");
    }
    return first;
  }

  // Runs a UI block here: the values set, `tap.start` answered, then the run.
  function main_run(start: boot.HeadlessStart): void {
    const payload = jslb.payload_of(start.first) as unknown as lines.TapStart;
    settings.settings_set(payload.settings);
    harness.values_set(
      payload.settings,
      payload.test_settings as harness.Gold,
    );
    line_write(dispatch.reply_make(start.first, {}));
    const runner = new tap_producer.TAPTestRunner(start.failfast);
    runner.set_stream((text) => line_write(text_line(text)));
    block_launch(runner, start.block, () => {
      runner.run_end();
    });
  }

  // Makes the worker from the texts of the worker scripts, faults relayed.
  function worker_make(): Worker {
    const scripts = document.querySelectorAll<HTMLScriptElement>(
      constants.worker_scripts,
    );
    const texts = Array.from(scripts, (script) => script.text);
    const source = constants.strict_line + texts.join(constants.script_join);
    const blob = new Blob([source], { type: constants.script_media });
    const worker = new Worker(URL.createObjectURL(blob), {
      name: constants.worker_name,
    });
    // The `fault` line of the worker's error overlay, after any report sent.
    worker.onmessage = (event: MessageEvent<unknown>) => {
      line_write(event.data as lines.Line);
    };
    worker.onerror = (event: ErrorEvent) => {
      const { filename, lineno, colno, message } = event;
      throw new Error(
        `the worker failed at ${filename}:${lineno}:${colno}: ${message}`,
      );
    };
    worker.onmessageerror = () => {
      throw new Error("a message of the worker could not be read");
    };
    return worker;
  }

  // Runs a worker block in a fresh worker, relaying both of its channels.
  function worker_launch(start: boot.HeadlessStart): void {
    const worker = worker_make();
    const realm = new MessageChannel();
    const ui = new MessageChannel();
    const realm_port = new queue.ThreadPort(realm.port1);
    realm_port.line_receive(line_write);
    const ui_port = new queue.ThreadPort(ui.port1);
    ui_port.line_receive(line_write);
    const message: boot.HeadlessMessage = {
      server: realm.port2,
      ui: ui.port2,
      start,
    };
    worker.postMessage(message, [realm.port2, ui.port2]);
  }

  // Runs the worker's block once `tap_start` has answered `tap.start`.
  function worker_run(
    tasks: queue.TaskQueue,
    start: boot.HeadlessStart,
  ): void {
    const runner = new tap_producer.TAPTestRunner(start.failfast);
    runner.set_stream((text) => tasks.line_notify(text_line(text)));
    block_launch(runner, start.block, () => {
      runner.run_end();
    });
  }

  // Opens the realm lane on the main thread, or brings the worker up.
  export function realm_open(): void {
    if (self.name === constants.worker_name) {
      boot.headless_worker(worker_run);
      return;
    }
    if (typeof realm_line !== "function") {
      throw new Error("the driver added no binding realm_line before load");
    }
    error_overlay.stop_register((thrown) => line_write(error_line(thrown)));
    phase = "open";
  }

  // Takes the driver's block, failfast and first line, and runs the block.
  export function realm_start(
    block: string,
    failfast: boolean,
    line: string,
  ): void {
    if (phase !== "open") {
      throw new Error(`realm_start was called with the lane ${phase}`);
    }
    phase = "started";
    const start: boot.HeadlessStart = {
      first: first_read(line),
      block,
      failfast,
    };
    if (block_find(block).side === "ui") {
      main_run(start);
    } else {
      worker_launch(start);
    }
  }
}

Object.freeze(test_headless);
