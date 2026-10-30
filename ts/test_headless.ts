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
// A block of the side `lanes` runs on the main thread over a fresh worker
// brought up as a worker block's is, with the same start: the settings and
// the harness's values are set and an Empty reply answers `tap.start`, as
// for a UI block, then `line_case.block_run` runs the cases of the gold
// `typescript.BLOCK` with a topology that calls the block's `LanesBuild`
// with the first line, the page's ends of the worker's two channels and the
// writer of a line to the driver, which returns the test's end. The page
// writes the TAP, and the worker runs no block.
//
// A block of the side `workers` runs on the main thread over a fresh worker
// for each of its cases. The settings and the harness's values are set and
// an Empty reply answers `tap.start`, as for a UI block, then
// `line_case.block_run` runs the cases of the gold `typescript.BLOCK` with
// a topology of this file's own, whose junction takes each line the cases
// send. Each case sends first the notice `test_headless.worker_start`, whose
// payload is `{clear}`, with `wait_seconds` too when `clear` is false: the
// junction ends the worker of the case before and brings up a fresh one with
// the page's start and those, which tell its bring up whether to clear the
// test pool and the test slots, and if not how long it may wait for files
// the worker before it still holds. Each other
// line a case sends is held, then posted in order on the worker's UI
// channel once the worker has sent the notice `test_headless.worker_ready`
// on its lane to the server, which the block's `WorkerRun` sends by calling
// `ready` once its topology is up, since a topology whose set up takes
// tasks of the worker's queue would take the case's lines first. Every line
// of the server lane goes to the test's end but each `verbose.put`, which
// goes to the driver, and every line of the UI channel but `settings.set`,
// which goes to the driver, as a worker block's lines do. The `fault` line
// the worker's error overlay posts after its report keeps no order with the
// server lane, so it is held and checked against the worker's `error` line,
// the same message, stack and cause chain; one that differs, or that has no
// `error` line by the worker's end, goes to the driver, which fails the
// block. A worker is ended by `Worker.terminate`, at once, unless it sent an
// `error` line whose `fault` line has not come, then when it comes, and the
// last one at the block's end, before the stream's last line. In the worker
// the block's `WorkerRun` runs in the task of `worker.tests`, with the
// queue, the start and `ready`, and no TAP block runs there.
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
    fault_type: "fault",
    notice_type: "settings.set",
    verbose_type: "verbose.put",
    // The notices of a block of `workers`: a case's start, a worker's ready.
    start_type: "test_headless.worker_start",
    ready_type: "test_headless.worker_ready",
    server_owner: "server" as const,
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

  // Builds the far ends of a fresh worker's channels, the test's end of them.
  export type LanesBuild = (
    first: lines.Line,
    server: MessagePort,
    ui: MessagePort,
    relay: (line: lines.Line) => void,
  ) => queue.ThreadPort;

  // Runs a block's part in each fresh worker, `ready` once its topology is up.
  export type WorkerRun = (
    tasks: queue.TaskQueue,
    start: boot.HeadlessStart,
    ready: () => void,
  ) => void;

  // A block: a unittest module or line cases on a thread, or of a side.
  type Block =
    | {
        readonly side: Side;
        readonly module: () => { [name: string]: unknown };
      }
    | { readonly side: Side; readonly topology: line_case.TopologyBuild }
    | { readonly side: "lanes"; readonly lanes: LanesBuild }
    | { readonly side: "workers"; readonly worker: WorkerRun };

  // The blocks of group B by name.
  const blocks = Object.freeze<{ readonly [name: string]: Block }>({
    test_error_overlay: { side: "ui", module: () => test_error_overlay },
    test_error_overlay_worker: {
      side: "worker",
      module: () => test_error_overlay_worker,
    },
    test_overlay: { side: "ui", module: () => test_overlay },
    test_console_view: { side: "ui", module: () => test_console_view },
    test_integrate_console_view: {
      side: "ui",
      topology: test_integrate_console_view.topology_build,
    },
    test_page: { side: "ui", module: () => test_page },
    test_integrate_page: {
      side: "ui",
      topology: test_integrate_page.topology_build,
    },
    test_substrate_store: {
      side: "worker",
      module: () => test_substrate_store,
    },
    test_integrate_substrate: {
      side: "worker",
      topology: test_integrate_substrate.topology_build,
    },
    test_jslb_decode: { side: "worker", module: () => test_jslb_decode },
    test_script: { side: "worker", module: () => test_script },
    test_tools_browser: { side: "worker", module: () => test_tools_browser },
    test_integrate_tools_browser: {
      side: "worker",
      topology: test_integrate_tools_browser.topology_build,
    },
    test_agent: { side: "worker", module: () => test_agent },
    test_integrate_agent: {
      side: "worker",
      topology: test_integrate_agent.topology_build,
    },
    test_worker_ai: { side: "ui", module: () => test_worker_ai },
    test_boot: { side: "ui", module: () => test_boot },
    test_integrate_worker_ai: {
      side: "lanes",
      lanes: test_integrate_worker_ai.lanes_build,
    },
    test_media_cache: { side: "ui", module: () => test_media_cache },
    test_integrate_media: {
      side: "ui",
      topology: test_integrate_media.topology_build,
    },
    test_substrate_crash: {
      side: "workers",
      worker: test_substrate_crash.worker_run,
    },
    test_agent_faults: {
      side: "workers",
      worker: test_agent_faults.worker_run,
    },
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
    } else if ("topology" in block) {
      const id = `${constants.gold_prefix}${name}`;
      line_case.block_run(runner, name, id, block.topology, done);
    } else {
      throw new Error("internal error");
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
        "the first line is not tap.start with i 101: " +
          jslb.line_render(first),
      );
    }
    const payload = jslb.payload_of(first) as unknown as lines.TapStart;
    if (payload.test_settings === undefined) {
      throw new Error("tap.start carries no test_settings: not debug mode");
    }
    return first;
  }

  // Sets the settings and the harness's values here, and answers `tap.start`.
  function start_answer(start: boot.HeadlessStart): void {
    const payload = jslb.payload_of(start.first) as unknown as lines.TapStart;
    settings.settings_set(payload.settings);
    harness.values_set(
      payload.settings,
      payload.test_settings as harness.Gold,
    );
    line_write(dispatch.reply_make(start.first, {}));
  }

  // Runs a UI block here: the values set, `tap.start` answered, then the run.
  function main_run(start: boot.HeadlessStart): void {
    start_answer(start);
    const runner = new tap_producer.TAPTestRunner(start.failfast);
    runner.set_stream((text) => line_write(text_line(text)));
    block_launch(runner, start.block, () => {
      runner.run_end();
    });
  }

  // Makes the worker from the texts of the worker scripts, faults to `fault`.
  function worker_make(fault: (line: lines.Line) => void): Worker {
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
      fault(event.data as lines.Line);
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

  // Posts a fresh worker its start, and returns the page's ends.
  function worker_start(
    worker: Worker,
    start: boot.HeadlessStart,
  ): [MessagePort, MessagePort] {
    const realm = new MessageChannel();
    const ui = new MessageChannel();
    const message: boot.HeadlessMessage = {
      server: realm.port2,
      ui: ui.port2,
      start,
    };
    worker.postMessage(message, [realm.port2, ui.port2]);
    return [realm.port1, ui.port1];
  }

  // Runs a worker block in a fresh worker, relaying both of its channels.
  function worker_launch(start: boot.HeadlessStart): void {
    const [realm, ui] = worker_start(worker_make(line_write), start);
    const realm_port = new queue.ThreadPort(realm);
    realm_port.line_receive(line_write);
    const ui_port = new queue.ThreadPort(ui);
    ui_port.line_receive(line_write);
  }

  // Runs a block of `lanes` here, over the channels of a fresh worker.
  function lanes_run(start: boot.HeadlessStart, lanes: LanesBuild): void {
    start_answer(start);
    const [server, ui] = worker_start(worker_make(line_write), start);
    const runner = new tap_producer.TAPTestRunner(start.failfast);
    runner.set_stream((text) => line_write(text_line(text)));
    const id = `${constants.gold_prefix}${start.block}`;
    const build = () => lanes(start.first, server, ui, line_write);
    line_case.block_run(runner, start.block, id, build, () => {
      runner.run_end();
    });
  }

  // The type of a line.
  function type_of(line: lines.Line): unknown {
    return jslb.field_get(line[0], "type");
  }

  // The cascade of an `error` or a `fault` line, as text to compare.
  function cascade_text(line: lines.Line): string {
    const { message, stack, cause } = jslb.payload_of(line);
    return utility.json_text({ message, stack, cause });
  }

  // One fresh worker of a block of `workers`: its lines, its fault, its end.
  class CaseWorker {
    // The junction's end of the test's lane, which takes the worker's lines.
    readonly #end: queue.ThreadPort;
    readonly #worker: Worker;
    readonly #ui: queue.ThreadPort;
    // The lines the case sent it before it was ready, then nothing.
    #held: lines.Line[] | undefined = [];
    // Its first `error` line and its `fault` line, each once it came.
    #error: lines.Line | undefined = undefined;
    #fault: lines.Line | undefined = undefined;
    // What runs once it is terminated, set when it is retired.
    #ended: (() => void) | undefined = undefined;
    // Whether it was terminated, after which its `fault` line is the driver's.
    #terminated = false;

    // Brings up a fresh worker with the start, its lines to `end`.
    constructor(start: boot.HeadlessStart, end: queue.ThreadPort) {
      this.#end = end;
      this.#worker = worker_make((line) => this.#fault_take(line));
      const [server, ui] = worker_start(this.#worker, start);
      const server_port = new queue.ThreadPort(server);
      server_port.line_receive((line) => this.#lane_take(line));
      this.#ui = new queue.ThreadPort(ui);
      this.#ui.line_receive((line) => this.#channel_take(line));
    }

    // Posts a line of the case on the UI channel, or holds it until ready.
    line_send(line: lines.Line): void {
      if (this.#held === undefined) {
        this.#ui.line_post(line, []);
      } else {
        this.#held.push(line);
      }
    }

    // Terminates it now, or once its `fault` line follows its `error` line.
    worker_end(ended: () => void): void {
      if (this.#ended !== undefined) {
        throw new Error("internal error");
      }
      this.#ended = ended;
      if (this.#error === undefined || this.#fault !== undefined) {
        this.#worker_terminate();
      }
    }

    // Terminates it, a `fault` line with no `error` line sent to the driver.
    #worker_terminate(): void {
      if (this.#fault !== undefined && this.#error === undefined) {
        line_write(this.#fault);
      }
      this.#terminated = true;
      this.#worker.terminate();
      (this.#ended as () => void)();
    }

    // A line of the server lane, to the test's end but a `verbose.put`.
    #lane_take(line: lines.Line): void {
      const type = type_of(line);
      if (type === constants.verbose_type) {
        line_write(line);
        return;
      }
      this.#end.line_post(line, []);
      if (type === constants.ready_type) {
        this.#ready_take();
      } else if (type === constants.error_type && this.#error === undefined) {
        this.#error = line;
        this.#cascade_check();
      }
    }

    // A line of the UI channel, to the test's end but `settings.set`.
    #channel_take(line: lines.Line): void {
      if (type_of(line) === constants.notice_type) {
        line_write(line);
        return;
      }
      this.#end.line_post(line, []);
    }

    // Posts the lines held for the worker, which is now ready, in order.
    #ready_take(): void {
      const held = this.#held;
      if (held === undefined) {
        throw new Error(`the worker sent ${constants.ready_type} twice`);
      }
      this.#held = undefined;
      for (const line of held) {
        this.#ui.line_post(line, []);
      }
    }

    // The `fault` line, checked against the `error` line, ends a retired one.
    #fault_take(line: lines.Line): void {
      if (
        this.#terminated ||
        type_of(line) !== constants.fault_type ||
        this.#fault !== undefined
      ) {
        line_write(line);
        return;
      }
      this.#fault = line;
      this.#cascade_check();
      if (this.#ended !== undefined) {
        this.#worker_terminate();
      }
    }

    // Sends the `fault` line to the driver when its cascade is not the error.
    #cascade_check(): void {
      const error = this.#error;
      const fault = this.#fault;
      if (
        error !== undefined &&
        fault !== undefined &&
        cascade_text(error) !== cascade_text(fault)
      ) {
        line_write(fault);
      }
    }
  }

  // The junction of a block of `workers`: a fresh worker for each case.
  class CaseJunction {
    readonly #start: boot.HeadlessStart;
    // The junction's end of the test's lane.
    readonly #end: queue.ThreadPort;
    // The worker of the case that runs, if any.
    #current: CaseWorker | undefined = undefined;
    // The number of retired workers not yet terminated.
    #retiring = 0;
    // What runs once the block has ended and every worker is terminated.
    #finished: (() => void) | undefined = undefined;

    // Takes the page's start and the junction's end of the test's lane.
    constructor(start: boot.HeadlessStart, end: queue.ThreadPort) {
      this.#start = start;
      this.#end = end;
      end.line_receive((line) => this.#line_take(line));
    }

    // Retires the last worker, then calls `finished` once all are ended.
    block_end(finished: () => void): void {
      this.#finished = finished;
      this.#current_retire();
      this.#finish_check();
    }

    // A line a case sent: a start, or a line for the case's worker.
    #line_take(line: lines.Line): void {
      if (type_of(line) === constants.start_type) {
        this.#current_retire();
        this.#current = new CaseWorker(this.#start_read(line), this.#end);
        return;
      }
      const current = this.#current;
      if (current === undefined) {
        throw new Error(
          `a case sent ${jslb.line_render(line)} before` +
            ` ${constants.start_type}`,
        );
      }
      current.line_send(line);
    }

    // The worker's start: the page's, with the notice's clear and its wait.
    #start_read(line: lines.Line): boot.HeadlessStart {
      const { clear, wait_seconds } = jslb.payload_of(line);
      const { first, block, failfast } = this.#start;
      if (clear === true && wait_seconds === undefined) {
        return { first, block, failfast, clear };
      }
      if (clear === false && typeof wait_seconds === "number") {
        return { first, block, failfast, clear, wait_seconds };
      }
      throw new Error(
        `${constants.start_type} needs clear true, or clear false with` +
          ` wait_seconds: ${jslb.line_render(line)}`,
      );
    }

    // Retires the worker of the case before, if any.
    #current_retire(): void {
      const current = this.#current;
      if (current === undefined) {
        return;
      }
      this.#current = undefined;
      this.#retiring += 1;
      current.worker_end(() => {
        this.#retiring -= 1;
        this.#finish_check();
      });
    }

    // Calls `finished` once the block has ended and no worker is left.
    #finish_check(): void {
      const finished = this.#finished;
      if (finished !== undefined && this.#retiring === 0) {
        this.#finished = undefined;
        finished();
      }
    }
  }

  // Runs a block of `workers` here, a fresh worker for each of its cases.
  function workers_run(start: boot.HeadlessStart): void {
    start_answer(start);
    const runner = new tap_producer.TAPTestRunner(start.failfast);
    runner.set_stream((text) => line_write(text_line(text)));
    const id = `${constants.gold_prefix}${start.block}`;
    const lane = new MessageChannel();
    const junction = new CaseJunction(start, new queue.ThreadPort(lane.port2));
    const build = () => new queue.ThreadPort(lane.port1);
    line_case.block_run(runner, start.block, id, build, () => {
      junction.block_end(() => {
        runner.run_end();
      });
    });
  }

  // The notice that a worker's topology is up, in the form the settings pick.
  function ready_line(): lines.Line {
    const header = jslb.header_make(constants.ready_type, {
      full: settings.names_full(),
    });
    return jslb.line_make(header, [], {});
  }

  // Runs the worker's block once `tap_start` has answered `tap.start`.
  function worker_run(
    tasks: queue.TaskQueue,
    start: boot.HeadlessStart,
  ): void {
    const block = block_find(start.block);
    // A block of `lanes` runs on the page, so the worker runs none.
    if (block.side === "lanes") {
      return;
    }
    // A block of `workers` runs its part here, its TAP on the page.
    if (block.side === "workers") {
      block.worker(tasks, start, () => {
        tasks.line_notify(ready_line(), constants.server_owner);
      });
      return;
    }
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
      clear: true,
    };
    const found = block_find(block);
    if (found.side === "lanes") {
      lanes_run(start, found.lanes);
    } else if (found.side === "workers") {
      workers_run(start);
    } else if (found.side === "ui") {
      main_run(start);
    } else {
      worker_launch(start);
    }
  }
}

Object.freeze(test_headless);
