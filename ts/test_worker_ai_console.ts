// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The line cases of the AI worker's relays of the console, group C, on the
// UI side of the headless page that the block's own ttyd serves: a real
// queue of thread `ai` in synchronous mode in the page's realm, with
// `worker_ai.console_register` registered through the real dispatch, its
// `console` owner a real `wire.ConsolePort` at the page's address, which
// reaches ttyd's tty 0, and its `ui` owner a `queue.ThreadPort` over a
// MessageChannel whose other end is the test's. The UI's `console.open` goes
// to the port, which fetches ttyd's token and opens tty 0, then the token
// comes back to the UI. The UI's `console.close` closes tty 0 through the
// port and is answered at once, then the socket's end comes back as the
// `console.exit` that the port's close receiver, the test's own, pushes to
// the UI with the close code, as the AI worker pushes it. No case sends
// ttyd a first message on tty 0, so ttyd starts no process. The lines the
// cases send and expect are the gold of test_settings.json.

namespace test_worker_ai_console {
  // The thread, the owners of its lanes, the type of the console's end.
  const constants = Object.freeze({
    thread: "ai" as const,
    ui_owner: "ui" as const,
    console_owner: "console" as const,
    exit_type: "console.exit",
  });

  // The relays on a real queue and a real console port, the test's lane end.
  export function topology_build(): queue.ThreadPort {
    const tasks = new queue.TaskQueue(
      constants.thread,
      worker_ai.owners_make(),
      true,
    );
    const lane = new MessageChannel();
    tasks.port_add(constants.ui_owner, new queue.ThreadPort(lane.port2));
    const port = new wire.ConsolePort(location.href);
    // The end of tty 0, pushed to the UI as the AI worker pushes it.
    port.close_receive((code) => {
      const header = jslb.header_make(constants.exit_type, {
        full: settings.names_full(),
      });
      tasks.line_notify(jslb.line_make(header, [], { code }));
    });
    tasks.port_add(constants.console_owner, port);
    worker_ai.console_register(tasks, dispatch.handler_register, () => {
      port.console_close();
    });
    return new queue.ThreadPort(lane.port1);
  }
}

Object.freeze(test_worker_ai_console);
