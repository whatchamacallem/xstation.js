// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The entry of the test page on both threads. Each thread runs its share of
// the test modules as one TAP stream on the queue the test page's hook of the
// thread hands over: the tests of the TAP producer and of the harness first,
// then the others in the order of the test bundle, those that need the
// document on the UI thread only. Each line goes out as a `tap.line` the
// moment it is made, and the stream stops after the first module that fails.
// The UI thread also shows its own stream with the failed lines marked. The
// UI thread runs first: once its stream has ended it sends the AI worker the
// `worker.tests` line that starts the worker's stream, so every UI line is
// ahead of the worker's suite on the way to the server, and a hang or fault of
// that suite loses none of them.

namespace test_all {
  // The name of the UI thread, the TAP line, and the element of the stream.
  const constants = Object.freeze({
    page_name: "",
    line_type: "tap.line",
    language: "typescript" as const,
    output_id: "tap_output",
    // Whether a failing test ends the stream: off, as Python's default.
    failfast: false,
    // The line that starts the AI worker's stream, sent when the UI's ends.
    tests_type: "worker.tests",
    // The owner of that line, the AI worker.
    tests_owner: "ai" as const,
  });

  // A reader of a test module's object, called when its block starts.
  type ModuleRead = () => { [name: string]: unknown };

  // Test modules by name, in the order their blocks run.
  type ModuleTable = { readonly [name: string]: ModuleRead };

  // The tests of the TAP producer and of the harness, first on each thread.
  const first_modules = Object.freeze<ModuleTable>({
    test_tap_producer: () => test_tap_producer,
    test_unittest: () => test_unittest,
  });

  // The modules the UI thread runs, in the order of the test bundle.
  const page_modules = Object.freeze<ModuleTable>({
    test_error_overlay: () => test_error_overlay,
    test_utility: () => test_utility,
    test_ui_strings: () => test_ui_strings,
    test_settings: () => test_settings,
    test_i18n: () => test_i18n,
    test_media: () => test_media,
    test_console_view: () => test_console_view,
    test_overlay: () => test_overlay,
    test_page: () => test_page,
  });

  // The modules the AI worker runs, in the order of the test bundle.
  const worker_modules = Object.freeze<ModuleTable>({
    test_verbose: () => test_verbose,
    test_jslb: () => test_jslb,
    test_dispatch: () => test_dispatch,
    test_queue: () => test_queue,
    test_http: () => test_http,
    test_wire: () => test_wire,
    test_substrate: () => test_substrate,
    test_provider: () => test_provider,
    test_provider_script: () => test_provider_script,
    test_mcp: () => test_mcp,
    test_script: () => test_script,
    test_tools_browser: () => test_tools_browser,
    test_agent: () => test_agent,
    test_worker_ai: () => test_worker_ai,
    test_boot: () => test_boot,
  });

  // Sends one line of the stream at once, as a `tap.line` to its owner.
  function line_send(tasks: queue.TaskQueue, text: string): void {
    const header = jslb.header_make(constants.line_type, {
      full: worker_ai.names_full(),
    });
    const payload = { language: constants.language, text };
    tasks.line_notify(jslb.line_make(header, [], payload));
  }

  // Runs the modules as blocks of one stream until one fails, then ends it.
  function stream_run(
    modules: ModuleTable,
    write: (text: string) => void,
  ): void {
    const runner = new tap_producer.TAPTestRunner(constants.failfast);
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

  // Runs the UI thread's stream and shows it, then starts the worker's stream.
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
    const header = jslb.header_make(constants.tests_type, {
      full: worker_ai.names_full(),
    });
    // Behind every line of this stream, so none waits for the worker's suite.
    tasks.line_notify(jslb.line_make(header, [], {}), constants.tests_owner);
  }

  // Runs the AI worker's stream.
  function worker_run(tasks: queue.TaskQueue): void {
    stream_run(worker_modules, (text) => line_send(tasks, text));
  }

  // Runs this thread's tests through the test page's hook of the thread.
  export function suites_run(): void {
    if (self.name === constants.page_name) {
      boot.test_page(page_run);
    } else {
      boot.test_worker(worker_run);
    }
  }
}

Object.freeze(test_all);
