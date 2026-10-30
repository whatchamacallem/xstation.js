// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The line cases of the task manager on real thread ports. A queue on thread
// `ai`, in the mode of the setting `queue_synchronous`, owns the type prefix
// `queue_test.`; a second real queue on `server`, in the same mode, owns
// `queue_far.`; and lines of `queue_ui.` go to `ui`, the test's end. Each
// lane is a MessageChannel with a `queue.ThreadPort` at each end, so every
// post moves its blob bytes in the transfer list. The handlers are this
// file's own functions. The cases, the gold of the block's id, are a request
// answered, a blob carried by a submit and its reply, two replies in submit
// order, a blob forwarded both ways, blobs over one buffer moved once,
// replies in the order of their requests, and a notification that nothing
// answers.

namespace test_integrate_queue {
  // The threads, the type prefixes and types, and the handlers' version.
  const constants = Object.freeze({
    thread: "ai" as const,
    far_thread: "server" as const,
    test_thread: "ui" as const,
    owner_prefix: "queue_test.",
    far_prefix: "queue_far.",
    test_prefix: "queue_ui.",
    echo_type: "queue_test.echo",
    relay_type: "queue_test.relay",
    relay_wake: "queue_test.relay_wake",
    pair_type: "queue_test.pair",
    pair_wake: "queue_test.pair_wake",
    halves_type: "queue_test.halves",
    note_type: "queue_test.note",
    far_echo: "queue_far.echo",
    far_keep: "queue_far.keep",
    kept_type: "queue_ui.kept",
    halves_out: "queue_ui.halves",
    pair_texts: ["first", "second"],
    handler_version: 0,
    synchronous_setting: "queue_synchronous",
  });

  // The request a wake answers, which its sleep kept.
  interface WaitState {
    request: lines.Line;
  }

  // The blob headers of a line, 1 on.
  function blobs_of(line: lines.Line): lines.BlobHeader[] {
    return jslb.headers_of(line).slice(1) as lines.BlobHeader[];
  }

  // A line of the type in the name form the settings pick.
  function line_new(
    type: string,
    blobs: lines.BlobHeader[],
    payload: { [key: string]: unknown },
  ): lines.Line {
    const header = jslb.header_make(type, { full: settings.names_full() });
    return jslb.line_make(header, blobs, payload);
  }

  // The reply to a line with its own payload and blobs.
  function echo_make(line: lines.Line): lines.Line {
    return dispatch.reply_make(line, jslb.payload_of(line), blobs_of(line));
  }

  // Registers one handler of the tests at their version.
  function handler_add(type: string, fn: dispatch.Handler): void {
    dispatch.handler_register(type, constants.handler_version, fn);
  }

  // Registers the handlers of both queues, the test's own functions.
  function handlers_register(
    tasks: queue.TaskQueue,
    far: queue.TaskQueue,
  ): void {
    handler_add(constants.echo_type, echo_make);
    handler_add(constants.note_type, () => undefined);
    handler_add(constants.relay_type, (line) => {
      const asked = line_new(
        constants.far_echo,
        blobs_of(line),
        jslb.payload_of(line),
      );
      const id = tasks.task_submit(asked);
      const state: WaitState = { request: line };
      return dispatch.task_sleep(state, [id], constants.relay_wake);
    });
    handler_add(constants.relay_wake, (line) => {
      const [reply] = line.replies as lines.Line[];
      const { request } = line.state as WaitState;
      return dispatch.reply_make(
        request,
        jslb.payload_of(reply),
        blobs_of(reply),
      );
    });
    handler_add(constants.pair_type, (line) => {
      const ids = constants.pair_texts.map((text) =>
        tasks.task_submit(line_new(constants.far_echo, [], { text })),
      );
      const state: WaitState = { request: line };
      return dispatch.task_sleep(state, ids.reverse(), constants.pair_wake);
    });
    handler_add(constants.pair_wake, (line) => {
      const replies = line.replies as lines.Line[];
      const { request } = line.state as WaitState;
      const texts = replies.map((reply) => reply.text);
      return dispatch.reply_make(request, { texts });
    });
    handler_add(constants.halves_type, (line) => {
      const data = blobs_of(line)[0].d as Uint8Array;
      const middle = Math.floor(data.length / 2);
      const halves = [
        jslb.blob_make(data.subarray(0, middle)),
        jslb.blob_make(data.subarray(middle)),
      ];
      tasks.line_notify(line_new(constants.halves_out, halves, {}));
      return undefined;
    });
    handler_add(constants.far_echo, echo_make);
    handler_add(constants.far_keep, (line) => {
      const payload = jslb.payload_of(line);
      far.line_notify(line_new(constants.kept_type, blobs_of(line), payload));
      return undefined;
    });
  }

  // The queues joined by a thread port pair, and the test's end of `ui`.
  export function topology_build(): queue.ThreadPort {
    const synchronous = harness.setting_get(
      constants.synchronous_setting,
    ) as boolean;
    const owners: queue.OwnerTable = {
      [constants.owner_prefix]: constants.thread,
      [constants.far_prefix]: constants.far_thread,
      [constants.test_prefix]: constants.test_thread,
    };
    const far_owners: queue.OwnerTable = {
      [constants.owner_prefix]: constants.thread,
      [constants.far_prefix]: constants.far_thread,
      [constants.test_prefix]: constants.thread,
    };
    const tasks = new queue.TaskQueue(constants.thread, owners, synchronous);
    const far = new queue.TaskQueue(
      constants.far_thread,
      far_owners,
      synchronous,
    );
    handlers_register(tasks, far);
    const link = new MessageChannel();
    tasks.port_add(constants.far_thread, new queue.ThreadPort(link.port1));
    far.port_add(constants.thread, new queue.ThreadPort(link.port2));
    const lane = new MessageChannel();
    tasks.port_add(constants.test_thread, new queue.ThreadPort(lane.port2));
    return new queue.ThreadPort(lane.port1);
  }
}
Object.freeze(test_integrate_queue);
