// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The entry of the ttyd test page on both threads. Each thread runs its share
// of the test modules as one TAP stream on the queue its bring up hands over.
// The three tables hold no block, as every block runs in group A or B, so
// each stream is a document of no block, the TAP version line and `1..0`,
// written through the page's real bring up, ttyd and the server. The
// worker's stream runs first: it runs in the task of `worker.tests`, which
// the worker notifies itself in debug mode, and once it has ended it sends
// the UI thread `ui.tests`, at which the UI thread's stream runs. Each line goes out as a `tap.line` the
// moment it is made, and the stream stops after the first module that fails.
// The UI thread also shows its own stream with the failed lines marked. The
// gold's `typescript.run` picks the run: "unit" runs both streams, "wire"
// runs the wire rungs only, on the worker, and the UI thread runs nothing.
// Whether a failing test ends a stream is the gold's
// `typescript.test_all.failfast`, a test suite setting.

namespace test_all {
  // The name of the AI worker's thread, the TAP line, the stream's element.
  const constants = Object.freeze({
    worker_name: "ai",
    line_type: "tap.line",
    language: "typescript" as const,
    output_id: "tap_output",
    // The gold's choice of whether a failing test ends the stream.
    failfast_id: "typescript.test_all.failfast",
    // The line that starts the UI's stream, sent when the worker's ends.
    tests_type: "ui.tests",
    // The owner of that line, the UI thread.
    tests_owner: "ui" as const,
    // The gold's choice of the run and its two values.
    run_id: "typescript.run",
    run_unit: "unit",
    run_wire: "wire",
  });

  // A reader of a test module's object, called when its block starts.
  type ModuleRead = () => { [name: string]: unknown };

  // Test modules by name, in the order their blocks run.
  type ModuleTable = { readonly [name: string]: ModuleRead };

  // The modules first on each thread: none, as each runs in group A or B.
  const first_modules = Object.freeze<ModuleTable>({});

  // The modules the AI worker runs: none, as each runs in group A or B.
  const worker_modules = Object.freeze<ModuleTable>({});

  // The modules the UI thread runs: none, as each runs in group A or B.
  const page_modules = Object.freeze<ModuleTable>({});

  // Sends one line of the stream at once, as a `tap.line` to its owner.
  function line_send(tasks: queue.TaskQueue, text: string): void {
    const header = jslb.header_make(constants.line_type, {
      full: settings.names_full(),
    });
    const payload = { language: constants.language, text };
    tasks.line_notify(jslb.line_make(header, [], payload));
  }

  // Runs the modules as blocks of one stream until one fails, then ends it.
  function stream_run(
    modules: ModuleTable,
    write: (text: string) => void,
  ): void {
    const failfast = harness.gold_get(constants.failfast_id) as boolean;
    const runner = new tap_producer.TAPTestRunner(failfast);
    runner.set_stream(write);
    const loader = new unittest.TestLoader();
    const entries = [
      ...Object.entries(first_modules),
      ...Object.entries(modules),
    ];
    for (const [name, module_read] of entries) {
      const passed = runner.module_run(name, () =>
        loader.loadTestsFromModule(module_read()),
      );
      if (!passed) {
        break;
      }
    }
    runner.run_end();
  }

  // Runs the UI thread's stream at `ui.tests` and shows it.
  function page_run(tasks: queue.TaskQueue): void {
    const output = document.getElementById(constants.output_id);
    if (output === null) {
      throw new Error(`the test page has no element ${constants.output_id}`);
    }
    const texts: string[] = [];
    stream_run(page_modules, (text) => {
      line_send(tasks, text);
      texts.push(text);
    });
    output.innerHTML = tap_producer.report_html(texts.join("\n"));
  }

  // Runs what the gold picks: the worker's stream, or the wire rungs alone.
  function worker_run(tasks: queue.TaskQueue, start: boot.TestStart): void {
    const run = harness.gold_get(constants.run_id);
    if (run === constants.run_wire) {
      test_wire_rungs.rungs_run(tasks, start);
      return;
    }
    if (run !== constants.run_unit) {
      throw new Error(
        `${constants.run_id} is ${String(run)}, neither unit nor wire`,
      );
    }
    stream_run(worker_modules, (text) => line_send(tasks, text));
    const header = jslb.header_make(constants.tests_type, {
      full: settings.names_full(),
    });
    // Behind every line of this stream, so the UI's lines follow them.
    tasks.line_notify(jslb.line_make(header, [], {}), constants.tests_owner);
  }

  // Runs this thread's tests through the bring up of the thread.
  export function suites_run(): void {
    if (self.name === constants.worker_name) {
      boot.test_worker(worker_run);
    } else {
      boot.test_page(page_run);
    }
  }
}

Object.freeze(test_all);
