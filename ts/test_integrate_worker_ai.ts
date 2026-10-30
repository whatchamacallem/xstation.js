// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The line cases of the AI worker's bring up: `worker_ai.tap_start` in a
// fresh worker as `boot.headless_worker` runs it, seen from the headless
// page's main thread, a realm whose dispatch table holds none of the
// worker's handlers. The test's end is joined to the worker's two channels,
// its lane to the server and its channel to the UI thread, by real thread
// ports whose receivers are this file's functions. Every line of the
// server's lane goes to the test's end, but each `verbose.put`, which goes
// to the driver uncompared, as its entries hold clock readings; a request
// also goes to the scripted server, a second real queue of thread `server`
// in synchronous mode joined by linked local ports, whose handler, this
// file's function, answers `settings.put` with the gold's reply, which goes
// back to the worker on its lane. The UI channel's `settings.set`, whose
// payload is the whole of `tap.start`, `test_settings.json` included, is
// compared with the first line by value, a difference thrown; any other
// line of it goes to the test's end. A line the cases send goes on the UI
// channel. Lines of two channels keep no order between them, so no case
// expects lines of both. The cases, the gold of the block's id, are the
// Empty reply to `tap.start`, a UI `settings.put` relayed to the server and
// answered, and a UI `fault` sent on as the `error` line of its cascade,
// last, as the worker then closes itself.

namespace test_integrate_worker_ai {
  // The threads, the line types, the gold reply, the handler's version.
  const constants = Object.freeze({
    far_thread: "server" as const,
    worker_thread: "ai" as const,
    put_type: "settings.put",
    notice_type: "settings.set",
    verbose_type: "verbose.put",
    reply_id: "typescript.test_integrate_worker_ai.lines.settings_put_reply",
    handler_version: 0,
  });

  // Whether the value is a plain object, from a literal or a clone of one.
  function object_plain(value: unknown): value is { [key: string]: unknown } {
    if (typeof value !== "object" || value === null) {
      return false;
    }
    const prototype: unknown = Object.getPrototypeOf(value);
    return prototype === Object.prototype || prototype === null;
  }

  // Whether two values are equal, arrays and plain objects by content.
  function value_equal(first: unknown, second: unknown): boolean {
    if (first === second) {
      return true;
    }
    if (Array.isArray(first) && Array.isArray(second)) {
      const items: readonly unknown[] = first;
      const others: readonly unknown[] = second;
      return (
        items.length === others.length &&
        items.every((item, index) => value_equal(item, others[index]))
      );
    }
    if (object_plain(first) && object_plain(second)) {
      const keys = Object.keys(first);
      return (
        keys.length === Object.keys(second).length &&
        keys.every(
          (key) =>
            Object.hasOwn(second, key) && value_equal(first[key], second[key]),
        )
      );
    }
    return false;
  }

  // The type of a line.
  function type_of(line: lines.Line): unknown {
    return jslb.field_get(line[0], "type");
  }

  // Throws unless the worker's `settings.set` carries what `tap.start` did.
  function notice_check(first: lines.Line, line: lines.Line): void {
    if (!value_equal(jslb.payload_of(line), jslb.payload_of(first))) {
      const text = jslb.line_render(line);
      throw new Error(
        `the worker's settings.set differs from tap.start: ${text}`,
      );
    }
  }

  // The scripted server, a real queue in synchronous mode, and its port.
  function server_make(): queue.LocalPort {
    const owners: queue.OwnerTable = {
      [constants.put_type]: constants.far_thread,
    };
    const far = new queue.TaskQueue(constants.far_thread, owners, true);
    // Answers the relayed `settings.put` with the payload of the gold reply.
    dispatch.handler_register(
      constants.put_type,
      constants.handler_version,
      (line) => {
        const reply = structuredClone(
          harness.gold_get(constants.reply_id),
        ) as lines.Line;
        return dispatch.reply_make(line, jslb.payload_of(reply));
      },
    );
    const near = new queue.LocalPort();
    far.port_add(constants.worker_thread, new queue.LocalPort(near));
    return near;
  }

  // Joins the test's end to the worker's channels and to the server.
  export function lanes_build(
    first: lines.Line,
    server: MessagePort,
    ui: MessagePort,
    relay: (line: lines.Line) => void,
  ): queue.ThreadPort {
    const lane = new MessageChannel();
    const junction = new queue.ThreadPort(lane.port2);
    const server_port = new queue.ThreadPort(server);
    const ui_port = new queue.ThreadPort(ui);
    const scripted = server_make();
    scripted.line_receive((line) => {
      server_port.line_post(line, []);
    });
    server_port.line_receive((line) => {
      if (type_of(line) === constants.verbose_type) {
        relay(line);
        return;
      }
      junction.line_post(line, []);
      if (jslb.field_get(line[0], "id") !== undefined) {
        scripted.line_post(line, []);
      }
    });
    ui_port.line_receive((line) => {
      if (type_of(line) === constants.notice_type) {
        notice_check(first, line);
        return;
      }
      junction.line_post(line, []);
    });
    junction.line_receive((line) => {
      ui_port.line_post(line, []);
    });
    return new queue.ThreadPort(lane.port1);
  }
}

Object.freeze(test_integrate_worker_ai);
