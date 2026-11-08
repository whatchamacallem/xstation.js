// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The line cases of the task manager on real thread ports. A queue on thread
// `ai`, in the mode of the setting `queue_synchronous`, owns the type prefix
// `queue_test.`; a second real queue on `server`, in the same mode, owns
// `queue_far.` and takes `ai`'s audit; and lines of `queue_ui.` go to `ui`, the
// test's end. Each lane is a MessageChannel with a `queue.ThreadPort` at each
// end, so every post moves its blob bytes in the transfer list. The handlers
// are this file's own functions. The cases, the gold of the block's id, are a
// request answered, a blob carried by a submit and its reply, two replies in
// submit order, a blob forwarded both ways, blobs over one buffer moved once,
// replies in the order of their requests, a notification that nothing answers,
// a wake run in its reply's place, and the audit of a traced relay, its sleep's
// note and its reply's record, which `server` sends back whole. For the wake
// the lane of thread `http` is one of a linked pair of local ports whose other
// end's receiver, owning `queue_end.`, keeps the request it gets, and at
// `queue_end.go` posts that request's reply and then a `queue_test.after`, both
// within the forward, so that both are held before the reply's step runs.

namespace test_integrate_queue {
  // The threads, the type prefixes and types, and the handlers' version.
  const constants = Object.freeze({
    thread: "ai" as const,
    far_thread: "server" as const,
    test_thread: "ui" as const,
    end_thread: "http" as const,
    owner_prefix: "queue_test.",
    far_prefix: "queue_far.",
    test_prefix: "queue_ui.",
    end_prefix: "queue_end.",
    audit_prefix: "audit.",
    audit_line: "audit.line",
    audit_note: "audit.note",
    echo_type: "queue_test.echo",
    relay_type: "queue_test.relay",
    relay_wake: "queue_test.relay_wake",
    pair_type: "queue_test.pair",
    pair_wake: "queue_test.pair_wake",
    halves_type: "queue_test.halves",
    note_type: "queue_test.note",
    order_type: "queue_test.order",
    order_wake: "queue_test.order_wake",
    after_type: "queue_test.after",
    end_ask: "queue_end.ask",
    end_go: "queue_end.go",
    after_out: "queue_ui.after",
    far_echo: "queue_far.echo",
    far_keep: "queue_far.keep",
    kept_type: "queue_ui.kept",
    halves_out: "queue_ui.halves",
    traced_type: "queue_test.traced",
    traced_wake: "queue_test.traced_wake",
    far_traced: "queue_far.traced",
    traced_mark: "traced",
    audit_go: "queue_test.audit_go",
    far_audit: "queue_far.audit",
    audit_out: "queue_ui.audit",
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
    handler_add(constants.order_type, (line) => {
      const id = tasks.task_submit(line_new(constants.end_ask, [], {}));
      const state: WaitState = { request: line };
      return dispatch.task_sleep(state, [id], constants.order_wake);
    });
    handler_add(constants.order_wake, (line) => {
      const { request } = line.state as WaitState;
      return dispatch.reply_make(request, {});
    });
    handler_add(constants.after_type, () => {
      tasks.line_notify(line_new(constants.after_out, [], {}));
      return undefined;
    });
    handler_add(constants.far_echo, echo_make);
    handler_add(constants.far_keep, (line) => {
      const payload = jslb.payload_of(line);
      far.line_notify(line_new(constants.kept_type, blobs_of(line), payload));
      return undefined;
    });
  }

  // Keeps the text of an audit entry when it holds the mark.
  function entry_keep(kept: string[], text: string): undefined {
    if (text.includes(constants.traced_mark)) {
      kept.push(text);
    }
    return undefined;
  }

  // Registers the traced relay and `server`'s keeping of its audit.
  function audit_register(tasks: queue.TaskQueue, far: queue.TaskQueue): void {
    const kept: string[] = [];
    handler_add(constants.traced_type, (line) => {
      const payload = jslb.payload_of(line);
      const asked = line_new(constants.far_traced, blobs_of(line), payload);
      const id = tasks.task_submit(asked);
      const state: WaitState = { request: line };
      return dispatch.task_sleep(state, [id], constants.traced_wake);
    });
    handler_add(constants.traced_wake, (line) => {
      const [reply] = line.replies as lines.Line[];
      const { request } = line.state as WaitState;
      tasks.line_notify(line_new(constants.audit_go, [], {}));
      return dispatch.reply_make(
        request,
        jslb.payload_of(reply),
        blobs_of(reply),
      );
    });
    // Runs after the wake's reply went out, so `server` holds its record.
    handler_add(constants.audit_go, () => {
      tasks.line_notify(line_new(constants.far_audit, [], {}));
      return undefined;
    });
    handler_add(constants.far_traced, echo_make);
    handler_add(constants.audit_line, (line) => {
      const record = jslb.payload_of(line) as unknown as lines.AuditLine;
      const text = utility.utf8_decode(blobs_of(line)[0].d as Uint8Array);
      const label = `${record.sender} to ${record.receiver}`;
      return entry_keep(kept, `${label}: ${text}`);
    });
    handler_add(constants.audit_note, (line) => {
      const note = jslb.payload_of(line) as unknown as lines.AuditNote;
      return entry_keep(kept, `note of ${note.thread}: ${note.text}`);
    });
    handler_add(constants.far_audit, () => {
      far.line_notify(line_new(constants.audit_out, [], { texts: kept }));
      return undefined;
    });
  }

  // The end of `http`, which posts the kept request's reply, then an after.
  function end_add(tasks: queue.TaskQueue): void {
    const near = new queue.LocalPort();
    tasks.port_add(constants.end_thread, near);
    const end = new queue.LocalPort(near);
    let kept: lines.Line | undefined = undefined;
    end.line_receive((line) => {
      const type = jslb.field_get(line[0], "type");
      if (type === constants.end_ask) {
        kept = line;
        return;
      }
      if (type !== constants.end_go || kept === undefined) {
        throw new Error("internal error");
      }
      end.line_post(dispatch.reply_make(kept, {}), []);
      end.line_post(line_new(constants.after_type, [], {}), []);
      kept = undefined;
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
      [constants.end_prefix]: constants.end_thread,
      [constants.audit_prefix]: constants.far_thread,
    };
    const far_owners: queue.OwnerTable = {
      [constants.owner_prefix]: constants.thread,
      [constants.far_prefix]: constants.far_thread,
      [constants.test_prefix]: constants.thread,
      [constants.audit_prefix]: constants.far_thread,
    };
    const tasks = new queue.TaskQueue(constants.thread, owners, synchronous);
    const far = new queue.TaskQueue(
      constants.far_thread,
      far_owners,
      synchronous,
    );
    tasks.limit_attach(settings.settings_get);
    tasks.audit_attach();
    handlers_register(tasks, far);
    audit_register(tasks, far);
    end_add(tasks);
    const link = new MessageChannel();
    tasks.port_add(constants.far_thread, new queue.ThreadPort(link.port1));
    far.port_add(constants.thread, new queue.ThreadPort(link.port2));
    const lane = new MessageChannel();
    tasks.port_add(constants.test_thread, new queue.ThreadPort(lane.port2));
    tasks.audit_open();
    return new queue.ThreadPort(lane.port1);
  }
}
Object.freeze(test_integrate_queue);
