// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The entry of the test engine page, which only the test bundle carries. In
// the AI worker it runs the engine's own worker. On the UI thread it runs the
// engine page and puts its live queue in the global `test_ui_tasks`, through
// which the browser test submits lines to the UI thread as the player would.

namespace test_hook {
  // The name of the AI worker's thread.
  const constants = Object.freeze({
    worker_name: "ai",
  });

  // Runs the engine's worker when the thread is the AI worker, else its page.
  export function engine_run(): void {
    if (self.name === constants.worker_name) {
      boot.worker_ai_main();
    } else {
      boot.test_engine((tasks: queue.TaskQueue) =>
        Object.assign(globalThis, { test_ui_tasks: tasks }),
      );
    }
  }
}

Object.freeze(test_hook);
