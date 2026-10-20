// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Tests of the task manager with port doubles: routing, ids, replies, sleeps
// and wakes, faults, depth, blob moves, the bound on the bytes it holds, and
// the verbose sink and its batches.

namespace test_queue {
  // The type prefix the tests own and a type that no owner table matches.
  const constants = Object.freeze({
    type_prefix: "queue_test.",
    unrouted_type: "queue_unrouted.type",
  });

  // How many types the tests have made, so that each one is new.
  let types_made = 0;

  // A type that no other test registers.
  function type_fresh(): string {
    types_made += 1;
    return `${constants.type_prefix}${types_made}`;
  }

  // Registers a handler for a new type and returns that type.
  function handler_fresh(fn: dispatch.Handler): string {
    const type = type_fresh();
    dispatch.handler_register(type, 0, fn);
    return type;
  }

  // A port double: it keeps what the queue posts and hands it lines.
  class PortDouble implements queue.Port {
    readonly posted: lines.Line[] = [];
    readonly transfers: ArrayBuffer[][] = [];
    private readonly name: string;
    private readonly trace: string[];
    private receiver: ((line: lines.Line) => void) | undefined;

    // Takes the name it writes in the trace and the trace it shares.
    constructor(name: string, trace: string[]) {
      this.name = name;
      this.trace = trace;
    }

    // Keeps a posted line and its transfer list, and traces the line.
    line_post(line: lines.Line, transfer: ArrayBuffer[]): void {
      this.posted.push(line);
      this.transfers.push(transfer);
      this.trace.push(`${this.name} ${utility.json_text(line)}`);
    }

    // Takes the receiver, which is the queue.
    line_receive(fn: (line: lines.Line) => void): void {
      this.receiver = fn;
    }

    // Hands a line to the queue as if it came on this port.
    line_send(line: lines.Line): void {
      const receiver = this.receiver;
      if (receiver === undefined) {
        throw new Error("The port double has no receiver.");
      }
      receiver(line);
    }
  }

  // A synchronous queue on the thread `ai` with doubles of `ui` and `server`.
  interface Bench {
    tasks: queue.TaskQueue;
    ui: PortDouble;
    server: PortDouble;
    trace: string[];
  }

  // Makes a bench with the owner table given.
  function bench_make(owners: queue.OwnerTable): Bench {
    const trace: string[] = [];
    const tasks = new queue.TaskQueue("ai", owners, true);
    const ui = new PortDouble("ui", trace);
    const server = new PortDouble("server", trace);
    tasks.port_add("ui", ui);
    tasks.port_add("server", server);
    return { tasks, ui, server, trace };
  }

  // An owner table: the test prefix here, and each far type to its owner.
  function owners_make(far: queue.OwnerTable): queue.OwnerTable {
    return { [constants.type_prefix]: "ai", ...far };
  }

  // Builds a line with no blobs from its type, header options and payload.
  function line_build(
    type: string,
    options: { id?: number; full?: boolean } = {},
    payload: { [key: string]: unknown } = {},
  ): lines.Line {
    return jslb.line_make(jslb.header_make(type, options), [], payload);
  }

  // A field of the header of a line, by its full name.
  function field_of(line: lines.Line, name: string): unknown {
    return jslb.field_get(line[0], name);
  }

  // The bytes a blob header holds, which must be in memory.
  function bytes_of(blob: unknown): Uint8Array {
    const data = (blob as lines.BlobHeader).d;
    if (!(data instanceof Uint8Array)) {
      throw new Error("The blob holds no bytes in memory.");
    }
    return data;
  }

  // The error the function throws, and an error of its own when it doesn't.
  function thrown_get(fn: () => unknown): Error {
    try {
      fn();
    } catch (error) {
      if (error instanceof Error) {
        return error;
      }
      throw error;
    }
    throw new Error("Nothing was thrown.");
  }

  // A complete settings object with `debug` and `verbose_forward` as given.
  function settings_make(
    debug: boolean,
    verbose_forward: boolean,
  ): settings.Settings {
    return {
      debug,
      queue_synchronous: true,
      verbose_level: 2,
      verbose_ring: 1000,
      verbose_forward,
      line_max: 1048576,
      blob_max: 10485760,
      message_max: 10485760,
      queue_max: 104857600,
      overflow_bytes: 131072,
      chunk_bytes: 1048576,
      srv_buf_size: 1048576,
      media_db_bytes: 268435456,
      files_browser_bytes: 1073741824,
      db_soft_bytes: 1073741824,
      turn_compact_tokens: 65536,
      long_task_ms: 5,
      provider: {
        scripted: true,
        base_url: "https://api.x.ai/v1",
        chat_model: "grok-4",
        image_model: "grok-2-image",
        timeout_seconds: 120,
      },
    };
  }

  // The reader of a settings store holding the settings given.
  function reader_from(value: settings.Settings): (id: string) => unknown {
    const store = new settings.ValueStore();
    store.value_set(value);
    return (id: string) => store.value_get(id);
  }

  // The reader of settings with `debug` and `verbose_forward` as given.
  function reader_make(
    debug: boolean,
    verbose_forward: boolean,
  ): (id: string) => unknown {
    return reader_from(settings_make(debug, verbose_forward));
  }

  // A bench whose queue holds at most the bytes given, its `queue_max`.
  function bench_bounded(far: queue.OwnerTable, limit: number): Bench {
    const bench = bench_make(owners_make({ "verbose.": "server", ...far }));
    const value = settings_make(false, false);
    value.queue_max = limit;
    bench.tasks.sink_attach(() => {}, reader_from(value));
    return bench;
  }

  // The bytes of the JSON text of a value in `UTF-8`.
  function text_bytes(value: unknown): number {
    return utility.utf8_encode(utility.json_text(value)).length;
  }

  // A `verbose.put` of the thread with no lines, as a batch builds it.
  function put_empty(thread: "ui" | "ai"): lines.Line {
    const header = jslb.header_make("verbose.put", { full: true });
    return jslb.line_make(header, [], { thread, lines: [] });
  }

  // The newest verbose line of this thread, none when its ring is empty.
  function mark_take(): lines.VerboseLine | undefined {
    return verbose.history_get(1).at(0);
  }

  // The texts of the verbose lines of this thread written after the mark.
  function texts_after(mark: lines.VerboseLine | undefined): string[] {
    const history = verbose.history_get(Number.MAX_SAFE_INTEGER);
    const start = mark === undefined ? 0 : history.indexOf(mark) + 1;
    if (mark !== undefined && start === 0) {
      throw new Error("The mark has left the verbose ring.");
    }
    return history.slice(start).map((line) => line.text);
  }

  // A ring of ten lines whose sink is the batch.
  function ring_make(batch: queue.VerboseBatch): verbose.LineRing {
    const ring = new verbose.LineRing(() => 10);
    ring.sink_set((line) => {
      batch.line_add(line);
    });
    return ring;
  }

  // The lines one call of `batch_send` posts.
  function batch_take(batch: queue.VerboseBatch): lines.Line[] {
    const posted: lines.Line[] = [];
    batch.batch_send((line) => {
      posted.push(line);
    });
    return posted;
  }

  // The texts of the verbose lines of a `verbose.put`, joined by commas.
  function texts_of(line: lines.Line): string {
    const sent = line.lines as lines.VerboseLine[];
    return sent.map((entry) => entry.text).join(",");
  }

  // Routing by the owner table: what runs here and what is passed on.
  export class TestOwnerRouting extends unittest.TestCase {
    // Lines from a port are dispatched one at a time in the order they came.
    test_order_kept(): void {
      const seen: unknown[] = [];
      const note = handler_fresh((line) => {
        seen.push(line.n);
        return undefined;
      });
      const bench = bench_make(owners_make({}));
      for (const n of [1, 2, 3]) {
        bench.ui.line_send(line_build(note, {}, { n }));
      }
      this.assertEqual(seen.join(","), "1,2,3");
      this.assertEqual(bench.tasks.depth(), 0);
    }

    // A task posted to itself runs before an input that came during a task.
    test_own_first(): void {
      const seen: string[] = [];
      const bench = bench_make(owners_make({}));
      const inner = handler_fresh(() => {
        seen.push("inner");
        return undefined;
      });
      const second = handler_fresh(() => {
        seen.push("second");
        return undefined;
      });
      const first = handler_fresh(() => {
        seen.push("first");
        bench.ui.line_send(line_build(second));
        bench.tasks.line_notify(line_build(inner));
        return undefined;
      });
      bench.ui.line_send(line_build(first));
      this.assertEqual(seen.join(","), "first,inner,second");
    }

    // A line another thread owns goes to that port as the same object.
    test_forward_unchanged(): void {
      const far = type_fresh();
      const bench = bench_make(owners_make({ [far]: "server" }));
      const data = Uint8Array.from([1, 2, 3]);
      const header = jslb.header_make(far);
      const line = jslb.line_make(header, [jslb.blob_make(data)], {
        text: "kept",
      });
      bench.ui.line_send(line);
      this.assertEqual(bench.server.posted.length, 1);
      this.assertTrue(bench.server.posted[0] === line);
      this.assertEqual(bench.server.posted[0].text, "kept");
      this.assertEqual(bench.server.transfers[0].length, 1);
      this.assertTrue(bench.server.transfers[0][0] === data.buffer);
      this.assertEqual(bench.ui.posted.length, 0);
      this.assertEqual(bench.tasks.depth(), 0);
    }

    // Forwarding a line the thread owns, or a request, throws.
    test_forward_refused(): void {
      const far = type_fresh();
      const own = line_build(type_fresh());
      const bench = bench_make(owners_make({ [far]: "server" }));
      const local = thrown_get(() => bench.tasks.line_forward(own));
      this.assertEqual(
        local.message,
        i18n("queue.forward_local", "ai", utility.json_text(own[0])),
      );
      const request = line_build(far, { id: 4 });
      const error = thrown_get(() => bench.ui.line_send(request));
      this.assertEqual(
        error.message,
        i18n("queue.forward_marked", "ai", utility.json_text(request[0])),
      );
      this.assertEqual(bench.server.posted.length, 0);
    }

    // A type that no prefix of the owner table matches throws.
    test_owner_missing(): void {
      const bench = bench_make(owners_make({}));
      const line = line_build(constants.unrouted_type);
      const error = thrown_get(() => bench.ui.line_send(line));
      this.assertEqual(
        error.message,
        i18n("queue.owner_missing", "ai", constants.unrouted_type),
      );
    }

    // A local port hands a post to its one receiver as the same object.
    test_local_port(): void {
      const port = new queue.LocalPort();
      const line = line_build(type_fresh());
      const missing = thrown_get(() => port.line_post(line, []));
      this.assertEqual(missing.message, i18n("queue.receiver_missing"));
      const seen: lines.Line[] = [];
      port.line_receive((got) => {
        seen.push(got);
      });
      const twice = thrown_get(() => port.line_receive(() => {}));
      this.assertEqual(twice.message, i18n("queue.receiver_twice"));
      port.line_post(line, []);
      this.assertEqual(seen.length, 1);
      this.assertTrue(seen[0] === line);
    }

    // A second port to a thread throws, the thread's own port included.
    test_port_twice(): void {
      const bench = bench_make(owners_make({}));
      const twice = thrown_get(() =>
        bench.tasks.port_add("ui", new PortDouble("ui", [])),
      );
      this.assertEqual(twice.message, i18n("queue.port_twice", "ai", "ui"));
      const own = thrown_get(() =>
        bench.tasks.port_add("ai", new queue.LocalPort()),
      );
      this.assertEqual(own.message, i18n("queue.port_twice", "ai", "ai"));
    }

    // A line whose owner is the port it came on throws and is not sent back.
    test_forward_back(): void {
      const far = type_fresh();
      const bench = bench_make(owners_make({ [far]: "ui" }));
      const line = line_build(far);
      const error = thrown_get(() => bench.ui.line_send(line));
      this.assertEqual(
        error.message,
        i18n("queue.forward_back", "ai", utility.json_text(line[0]), "ui"),
      );
      this.assertEqual(bench.ui.posted.length, 0);
    }

    // A thread port takes one receiver, and a second one throws.
    test_thread_receiver(): void {
      const channel = new MessageChannel();
      const port = new queue.ThreadPort(channel.port1);
      port.line_receive(() => {});
      const twice = thrown_get(() => port.line_receive(() => {}));
      this.assertEqual(twice.message, i18n("queue.receiver_twice"));
      channel.port1.close();
      channel.port2.close();
    }
  }

  // Requests, their ids and the replies that answer them.
  export class TestRequestReply extends unittest.TestCase {
    // One counter numbers the requests to every port, from 1, in its form.
    test_ids_shared(): void {
      const to_server = type_fresh();
      const to_ui = type_fresh();
      const owners = owners_make({ [to_server]: "server", [to_ui]: "ui" });
      const bench = bench_make(owners);
      const ids: number[] = [];
      const wake = handler_fresh(() => undefined);
      const start = handler_fresh(() => {
        ids.push(bench.tasks.task_submit(line_build(to_server)));
        ids.push(bench.tasks.task_submit(line_build(to_ui)));
        const full = line_build(to_server, { full: true });
        ids.push(bench.tasks.task_submit(full));
        return dispatch.task_sleep(null, ids, wake);
      });
      bench.ui.line_send(line_build(start));
      this.assertEqual(ids.join(","), "1,2,3");
      const [first, third] = bench.server.posted;
      this.assertEqual(field_of(first, "id"), 1);
      this.assertEqual(field_of(bench.ui.posted[0], "id"), 2);
      this.assertEqual(field_of(third, "id"), 3);
      this.assertTrue(Object.hasOwn(first[0], "i"));
      this.assertTrue(Object.hasOwn(third[0], "id"));
      this.assertFalse(Object.hasOwn(third[0], "i"));
      this.assertEqual(bench.tasks.depth(), 1);
    }

    // A request is answered on its port by the line its handler returns.
    test_request_answered(): void {
      const bench = bench_make(owners_make({}));
      const made: lines.Line[] = [];
      const ask = handler_fresh((line) => {
        made.push(dispatch.reply_make(line, { done: true }));
        return made[0];
      });
      bench.ui.line_send(line_build(ask, { id: 5 }));
      this.assertEqual(bench.ui.posted.length, 1);
      this.assertTrue(bench.ui.posted[0] === made[0]);
      this.assertEqual(field_of(bench.ui.posted[0], "reply"), 5);
      this.assertEqual(bench.server.posted.length, 0);
    }

    // A wake answers the request that slept, on the port it came on.
    test_wake_answers(): void {
      const far = type_fresh();
      const bench = bench_make(owners_make({ [far]: "server" }));
      const done = handler_fresh((line) => {
        const state = line.state as { request: lines.Line };
        const replies = line.replies as lines.Line[];
        return dispatch.reply_make(state.request, { got: replies[0].n });
      });
      const ask = handler_fresh((line) => {
        const id = bench.tasks.task_submit(line_build(far));
        return dispatch.task_sleep({ request: line }, [id], done);
      });
      bench.ui.line_send(line_build(ask, { id: 9 }));
      this.assertEqual(bench.ui.posted.length, 0);
      const request = bench.server.posted[0];
      bench.server.line_send(dispatch.reply_make(request, { n: 7 }));
      this.assertEqual(bench.ui.posted.length, 1);
      const answer = bench.ui.posted[0];
      this.assertEqual(field_of(answer, "type"), ask);
      this.assertEqual(field_of(answer, "reply"), 9);
      this.assertEqual(answer.got, 7);
      this.assertEqual(bench.tasks.depth(), 0);
    }

    // A reply that answers no request sent on its own port throws.
    test_reply_unknown(): void {
      const far = type_fresh();
      const owners = owners_make({ [far]: "server" });
      const empty = bench_make(owners);
      const stray = dispatch.reply_make(line_build(far, { id: 99 }), {});
      const stray_text = utility.json_text(stray[0]);
      const unknown = thrown_get(() => empty.server.line_send(stray));
      this.assertEqual(
        unknown.message,
        i18n("queue.reply_unknown", "ai", stray_text, "server"),
      );
      const bench = bench_make(owners);
      const idle = handler_fresh(() => undefined);
      const start = handler_fresh(() => {
        const id = bench.tasks.task_submit(line_build(far));
        return dispatch.task_sleep(null, [id], idle);
      });
      bench.ui.line_send(line_build(start));
      const reply = dispatch.reply_make(bench.server.posted[0], {});
      const wrong = thrown_get(() => bench.ui.line_send(reply));
      this.assertEqual(
        wrong.message,
        i18n("queue.reply_unknown", "ai", utility.json_text(reply[0]), "ui"),
      );
    }

    // An error line from a port stops the queue with its message and stack.
    test_error_line(): void {
      const bench = bench_make(owners_make({}));
      const line = dispatch.error_make(undefined, new Error("It failed."));
      const thrown = thrown_get(() => bench.server.line_send(line));
      this.assertEqual(
        thrown.message,
        i18n("queue.error_line", "ai", "server", line.message, line.stack),
      );
      const later = thrown_get(() =>
        bench.ui.line_send(line_build(type_fresh())),
      );
      this.assertEqual(
        later.message,
        i18n("queue.stopped", "ai", thrown.message, thrown.stack),
      );
      this.assertTrue(later.cause === thrown);
    }

    // A wake must answer the request it owes, and only a request it owes.
    test_reply_owed(): void {
      const far = type_fresh();
      const owners = owners_make({ [far]: "server" });
      let bench = bench_make(owners);
      const mute = handler_fresh(() => undefined);
      const ask = handler_fresh((line) => {
        const id = bench.tasks.task_submit(line_build(far));
        return dispatch.task_sleep({ request: line }, [id], mute);
      });
      bench.ui.line_send(line_build(ask, { id: 3 }));
      const first = dispatch.reply_make(bench.server.posted[0], {});
      const missing = thrown_get(() => bench.server.line_send(first));
      this.assertEqual(
        missing.message,
        i18n("queue.reply_missing", mute, "ai", 3, "ui"),
      );
      bench = bench_make(owners);
      const stray = dispatch.reply_make(line_build(far, { id: 8 }), {});
      const loose = handler_fresh(() => stray);
      const note = handler_fresh(() => {
        const id = bench.tasks.task_submit(line_build(far));
        return dispatch.task_sleep(null, [id], loose);
      });
      bench.ui.line_send(line_build(note));
      const second = dispatch.reply_make(bench.server.posted[0], {});
      const unowed = thrown_get(() => bench.server.line_send(second));
      this.assertEqual(
        unowed.message,
        i18n("queue.reply_unowed", loose, "ai", utility.json_text(stray[0])),
      );
      this.assertEqual(bench.ui.posted.length, 0);
    }
  }

  // An owner given to a submit or a notification instead of the table's.
  export class TestOwnerGiven extends unittest.TestCase {
    // A given owner overrides the table, and the reply comes on its port.
    test_owner_override(): void {
      const far = type_fresh();
      const bench = bench_make(owners_make({ [far]: "server" }));
      const woken: lines.Line[] = [];
      const wake = handler_fresh((line) => {
        woken.push(line);
        return undefined;
      });
      const start = handler_fresh(() => {
        const id = bench.tasks.task_submit(line_build(far), "ui");
        bench.tasks.line_notify(line_build(far, {}, { note: true }), "ui");
        return dispatch.task_sleep(null, [id], wake);
      });
      bench.ui.line_send(line_build(start));
      this.assertEqual(bench.server.posted.length, 0);
      this.assertEqual(bench.ui.posted.length, 2);
      const request = bench.ui.posted[0];
      this.assertEqual(field_of(request, "id"), 1);
      this.assertEqual(bench.ui.posted[1].note, true);
      this.assertEqual(field_of(bench.ui.posted[1], "id"), undefined);
      bench.ui.line_send(dispatch.reply_make(request, {}));
      this.assertEqual(woken.length, 1);
      this.assertEqual(bench.tasks.depth(), 0);
    }

    // A reply to a request sent to a given owner must come on that port.
    test_owner_reply(): void {
      const far = type_fresh();
      const bench = bench_make(owners_make({ [far]: "server" }));
      const idle = handler_fresh(() => undefined);
      const start = handler_fresh(() => {
        const id = bench.tasks.task_submit(line_build(far), "ui");
        return dispatch.task_sleep(null, [id], idle);
      });
      bench.ui.line_send(line_build(start));
      const reply = dispatch.reply_make(bench.ui.posted[0], {});
      const reply_text = utility.json_text(reply[0]);
      const wrong = thrown_get(() => bench.server.line_send(reply));
      this.assertEqual(
        wrong.message,
        i18n("queue.reply_unknown", "ai", reply_text, "server"),
      );
    }

    // A given owner with no port throws as an owner from the table would.
    test_owner_unconnected(): void {
      const far = type_fresh();
      const bench = bench_make(owners_make({ [far]: "server" }));
      const notice = thrown_get(() =>
        bench.tasks.line_notify(line_build(far), "media"),
      );
      this.assertEqual(
        notice.message,
        i18n("queue.port_missing", "ai", "media"),
      );
      const start = handler_fresh(() => {
        bench.tasks.task_submit(line_build(far), "http");
        return undefined;
      });
      const submit = thrown_get(() => bench.ui.line_send(line_build(start)));
      this.assertEqual(
        submit.message,
        i18n("queue.port_missing", "ai", "http"),
      );
      this.assertEqual(bench.server.posted.length, 0);
    }

    // A line posted to this thread runs here whatever owner the table names.
    test_owner_own(): void {
      const seen: unknown[] = [];
      const near = handler_fresh((line) => {
        seen.push(line.n);
        return undefined;
      });
      const bench = bench_make(owners_make({ [near]: "server" }));
      bench.tasks.line_notify(line_build(near, {}, { n: 1 }), "ai");
      this.assertEqual(seen.join(","), "1");
      this.assertEqual(bench.server.posted.length, 0);
      bench.tasks.line_notify(line_build(near, {}, { n: 2 }));
      this.assertEqual(seen.join(","), "1");
      this.assertEqual(bench.server.posted.length, 1);
      this.assertEqual(bench.server.posted[0].n, 2);
    }
  }

  // Sleeps, the rules they follow and the wakes that end them.
  export class TestSleepWake extends unittest.TestCase {
    // Two replies wake the task once in either order, in submit order.
    test_either_order(): void {
      const to_server = type_fresh();
      const to_ui = type_fresh();
      const owners = owners_make({ [to_server]: "server", [to_ui]: "ui" });
      const woken: lines.Line[] = [];
      let bench = bench_make(owners);
      const wake = handler_fresh((line) => {
        woken.push(line);
        return undefined;
      });
      const start = handler_fresh(() => {
        const first = bench.tasks.task_submit(line_build(to_server));
        const second = bench.tasks.task_submit(line_build(to_ui));
        return dispatch.task_sleep({ tag: "kept" }, [second, first], wake);
      });
      for (const server_first of [true, false]) {
        bench = bench_make(owners);
        woken.length = 0;
        bench.ui.line_send(line_build(start));
        const server_reply = dispatch.reply_make(bench.server.posted[0], {});
        const ui_reply = dispatch.reply_make(bench.ui.posted[0], {});
        const server_send = () => bench.server.line_send(server_reply);
        const ui_send = () => bench.ui.line_send(ui_reply);
        const [early, late] = server_first
          ? [server_send, ui_send]
          : [ui_send, server_send];
        early();
        this.assertEqual(woken.length, 0);
        this.assertEqual(bench.tasks.depth(), 1);
        late();
        this.assertEqual(woken.length, 1);
        const replies = woken[0].replies as lines.Line[];
        this.assertEqual(replies.length, 2);
        this.assertTrue(replies[0] === server_reply);
        this.assertTrue(replies[1] === ui_reply);
        this.assertEqual((woken[0].state as { tag: string }).tag, "kept");
        this.assertEqual(field_of(woken[0], "type"), wake);
        this.assertEqual(field_of(woken[0], "id"), undefined);
        this.assertEqual(bench.tasks.depth(), 0);
      }
    }

    // A sleep on no id wakes at once, after its handler returned.
    test_sleep_empty(): void {
      const seen: string[] = [];
      const bench = bench_make(owners_make({}));
      const wake = handler_fresh((line) => {
        seen.push(`wake ${(line.replies as lines.Line[]).length}`);
        return undefined;
      });
      const start = handler_fresh(() => {
        seen.push("start");
        return dispatch.task_sleep(null, [], wake);
      });
      bench.ui.line_send(line_build(start));
      this.assertEqual(seen.join(","), "start,wake 0");
      this.assertEqual(bench.tasks.depth(), 0);
    }

    // A sleep names every request its handler submitted, each once.
    test_wait_rules(): void {
      const far = type_fresh();
      const owners = owners_make({ [far]: "server" });
      const wake = handler_fresh(() => undefined);
      let bench = bench_make(owners);
      const unknown = handler_fresh(() =>
        dispatch.task_sleep(null, [5], wake),
      );
      let error = thrown_get(() => bench.ui.line_send(line_build(unknown)));
      this.assertEqual(
        error.message,
        i18n("queue.wait_unknown", unknown, "ai", 5),
      );
      bench = bench_make(owners);
      const partial = handler_fresh(() => {
        const first = bench.tasks.task_submit(line_build(far));
        bench.tasks.task_submit(line_build(far));
        return dispatch.task_sleep(null, [first], wake);
      });
      error = thrown_get(() => bench.ui.line_send(line_build(partial)));
      this.assertEqual(
        error.message,
        i18n("queue.wait_missing", partial, "ai", 2),
      );
      bench = bench_make(owners);
      const twice = handler_fresh(() => {
        const id = bench.tasks.task_submit(line_build(far));
        return dispatch.task_sleep(null, [id, id], wake);
      });
      error = thrown_get(() => bench.ui.line_send(line_build(twice)));
      this.assertEqual(
        error.message,
        i18n("queue.wait_twice", twice, "ai", 1),
      );
      bench = bench_make(owners);
      const careless = handler_fresh(() => {
        bench.tasks.task_submit(line_build(far));
        return undefined;
      });
      error = thrown_get(() => bench.ui.line_send(line_build(careless)));
      this.assertEqual(
        error.message,
        i18n("queue.wait_missing", careless, "ai", 1),
      );
    }

    // A submit outside a handler, or of a line with an id, throws.
    test_submit_rules(): void {
      const far = type_fresh();
      const bench = bench_make(owners_make({ [far]: "server" }));
      const outside = thrown_get(() =>
        bench.tasks.task_submit(line_build(far)),
      );
      this.assertEqual(
        outside.message,
        i18n("queue.submit_outside", "ai", far),
      );
      const marked = line_build(far, { id: 2 });
      const inner: Error[] = [];
      const start = handler_fresh(() => {
        inner.push(thrown_get(() => bench.tasks.task_submit(marked)));
        return undefined;
      });
      bench.ui.line_send(line_build(start));
      this.assertEqual(
        inner[0].message,
        i18n("queue.submit_marked", utility.json_text(marked[0])),
      );
      const notified = thrown_get(() => bench.tasks.line_notify(marked));
      this.assertEqual(
        notified.message,
        i18n("queue.notify_marked", utility.json_text(marked[0])),
      );
      this.assertEqual(bench.server.posted.length, 0);
      this.assertEqual(bench.tasks.depth(), 0);
    }
  }

  // The synchronous mode: the same run twice, faults and the depth.
  export class TestSynchronousMode extends unittest.TestCase {
    // The same inputs give the same posts, handler order and log lines twice.
    test_run_twice(): void {
      const to_server = type_fresh();
      const to_ui = type_fresh();
      const owners = owners_make({ [to_server]: "server", [to_ui]: "ui" });
      let bench = bench_make(owners);
      const note = handler_fresh(() => {
        bench.trace.push("run note");
        return undefined;
      });
      const late = handler_fresh(() => {
        bench.trace.push("run late");
        return undefined;
      });
      const done = handler_fresh((line) => {
        bench.trace.push("run done");
        const state = line.state as { request: lines.Line };
        const count = (line.replies as lines.Line[]).length;
        return dispatch.reply_make(state.request, { count });
      });
      const say = handler_fresh((line) => {
        bench.trace.push("run say");
        bench.server.line_send(line_build(late));
        bench.tasks.line_notify(line_build(note));
        const first = bench.tasks.task_submit(line_build(to_server));
        const second = bench.tasks.task_submit(line_build(to_ui));
        return dispatch.task_sleep({ request: line }, [first, second], done);
      });
      const runs: string[] = [];
      const logs: string[] = [];
      for (let index = 0; index < 2; index += 1) {
        bench = bench_make(owners);
        const mark = mark_take();
        bench.ui.line_send(line_build(say, { id: 1 }, { text: "1" }));
        const request = bench.server.posted[0];
        bench.ui.line_send(dispatch.reply_make(bench.ui.posted[0], {}));
        bench.server.line_send(dispatch.reply_make(request, {}));
        const handlers = bench.trace.filter((entry) =>
          entry.startsWith("run "),
        );
        this.assertEqual(
          handlers.join(","),
          "run say,run note,run late,run done",
        );
        this.assertEqual(bench.ui.posted.length, 2);
        this.assertEqual(field_of(bench.ui.posted[1], "reply"), 1);
        this.assertEqual(bench.ui.posted[1].count, 2);
        this.assertEqual(bench.tasks.depth(), 0);
        runs.push(bench.trace.join("\n"));
        logs.push(texts_after(mark).join("\n"));
      }
      this.assertEqual(runs[0], runs[1]);
      this.assertEqual(logs[0], logs[1]);
    }

    // A handler that throws stops the queue, idle, and later inputs throw too.
    test_handler_throws(): void {
      const bench = bench_make(owners_make({}));
      const failure = new Error("The handler failed.");
      const boom = handler_fresh(() => {
        throw failure;
      });
      const thrown = thrown_get(() => bench.ui.line_send(line_build(boom)));
      this.assertTrue(thrown === failure);
      this.assertEqual(bench.tasks.depth(), 0);
      const later = thrown_get(() => bench.ui.line_send(line_build(boom)));
      this.assertEqual(
        later.message,
        i18n("queue.stopped", "ai", failure.message, failure.stack),
      );
      this.assertTrue(later.cause === failure);
    }

    // Without synchronous mode a line from a port waits for a later step.
    test_step_waits(): void {
      const seen: unknown[] = [];
      const note = handler_fresh((line) => {
        seen.push(line.n);
        return undefined;
      });
      const tasks = new queue.TaskQueue("ai", owners_make({}), false);
      const ui = new PortDouble("ui", []);
      tasks.port_add("ui", ui);
      ui.line_send(line_build(note, {}, { n: 1 }));
      this.assertEqual(seen.length, 0);
      this.assertEqual(tasks.depth(), 1);
    }

    // The depth counts the tasks waiting, the one running and the sleeping.
    test_depth_counts(): void {
      const far = type_fresh();
      const bench = bench_make(owners_make({ [far]: "server" }));
      const during: number[] = [];
      const idle = handler_fresh(() => undefined);
      const wake = handler_fresh(() => {
        during.push(bench.tasks.depth());
        return undefined;
      });
      const start = handler_fresh(() => {
        during.push(bench.tasks.depth());
        bench.ui.line_send(line_build(idle));
        bench.ui.line_send(line_build(idle));
        during.push(bench.tasks.depth());
        const first = bench.tasks.task_submit(line_build(far));
        const second = bench.tasks.task_submit(line_build(far));
        return dispatch.task_sleep(null, [first, second], wake);
      });
      this.assertEqual(bench.tasks.depth(), 0);
      bench.ui.line_send(line_build(start));
      this.assertEqual(during.join(","), "1,3");
      this.assertEqual(bench.tasks.depth(), 1);
      bench.server.line_send(dispatch.reply_make(bench.server.posted[0], {}));
      this.assertEqual(bench.tasks.depth(), 1);
      bench.server.line_send(dispatch.reply_make(bench.server.posted[1], {}));
      this.assertEqual(during.join(","), "1,3,1");
      this.assertEqual(bench.tasks.depth(), 0);
    }
  }

  // Blob bytes move with a submit or a notification and are never copied.
  export class TestBlobTransfer extends unittest.TestCase {
    // After a submit the caller's bytes are detached and the post holds them.
    test_submit_detaches(): void {
      const far = type_fresh();
      const bench = bench_make(owners_make({ [far]: "server" }));
      const data = Uint8Array.from([0, 13, 10, 3, 4, 255]);
      const blob = jslb.blob_make(data);
      const line = jslb.line_make(jslb.header_make(far), [blob], {});
      const wake = handler_fresh(() => undefined);
      const start = handler_fresh(() => {
        const id = bench.tasks.task_submit(line);
        return dispatch.task_sleep(null, [id], wake);
      });
      bench.ui.line_send(line_build(start));
      this.assertEqual(data.byteLength, 0);
      this.assertEqual(bytes_of(line[1]).byteLength, 0);
      this.assertEqual(field_of(line, "id"), 1);
      const posted = bench.server.posted[0];
      const moved = bytes_of(posted[1]);
      this.assertEqual(Array.from(moved).join(","), "0,13,10,3,4,255");
      this.assertTrue(posted[0] === line[0]);
      this.assertEqual(bench.server.transfers[0].length, 1);
      this.assertTrue(bench.server.transfers[0][0] === moved.buffer);
    }

    // Blobs over one buffer move it once and keep their own views.
    test_shared_buffer(): void {
      const far = type_fresh();
      const bench = bench_make(owners_make({ [far]: "ui" }));
      const whole = Uint8Array.from([1, 2, 3, 4]);
      const head = jslb.blob_make(whole.subarray(0, 2));
      const tail = jslb.blob_make(whole.subarray(2, 4));
      const line = jslb.line_make(jslb.header_make(far), [head, tail], {});
      bench.tasks.line_notify(line);
      this.assertEqual(whole.byteLength, 0);
      this.assertEqual(bytes_of(head).byteLength, 0);
      this.assertEqual(bytes_of(tail).byteLength, 0);
      const posted = bench.ui.posted[0];
      const transfer = bench.ui.transfers[0];
      const moved_head = bytes_of(posted[1]);
      const moved_tail = bytes_of(posted[2]);
      this.assertEqual(Array.from(moved_head).join(","), "1,2");
      this.assertEqual(Array.from(moved_tail).join(","), "3,4");
      this.assertEqual(transfer.length, 1);
      this.assertTrue(moved_head.buffer === transfer[0]);
      this.assertTrue(moved_tail.buffer === transfer[0]);
    }
  }

  // The bound `queue_max` puts on the bytes of the lines a queue holds.
  export class TestQueueLimit extends unittest.TestCase {
    // A line counts its JSON text in `UTF-8` without blob data, then sizes.
    test_line_measured(): void {
      const note = handler_fresh(() => undefined);
      const bench = bench_bounded({}, 1);
      const accent = String.fromCodePoint(0xe9);
      const data = Uint8Array.from([1, 2, 3, 4, 5, 6]);
      const header = jslb.header_make(note);
      const line = jslb.line_make(header, [jslb.blob_make(data)], {
        text: accent,
      });
      const text =
        `{"0":{"t":"${note}","b":1},"1":{"s":6},` + `"text":"${accent}"}`;
      const bytes = utility.utf8_encode(text).length + data.length;
      this.assertEqual(bytes, text.length + 1 + data.length);
      const error = thrown_get(() => bench.ui.line_send(line));
      const header_text = utility.json_text(line[0]);
      this.assertEqual(
        error.message,
        i18n("queue.queue_over", "ai", header_text, bytes, 0, 1),
      );
      this.assertEqual(bench.tasks.depth(), 0);
    }

    // A line filling the bound is held, then freed, one byte more is not.
    test_limit_exact(): void {
      const seen: unknown[] = [];
      const note = handler_fresh((line) => {
        seen.push(line.text);
        return undefined;
      });
      const fits = line_build(note, {}, { text: "ab" });
      const limit = text_bytes(fits);
      const bench = bench_bounded({}, limit);
      bench.ui.line_send(fits);
      bench.ui.line_send(line_build(note, {}, { text: "cd" }));
      this.assertEqual(seen.join(","), "ab,cd");
      const over = line_build(note, {}, { text: "efg" });
      const error = thrown_get(() => bench.ui.line_send(over));
      const over_text = utility.json_text(over[0]);
      this.assertEqual(
        error.message,
        i18n("queue.queue_over", "ai", over_text, limit + 1, 0, limit),
      );
      const later = thrown_get(() => bench.ui.line_send(fits));
      this.assertEqual(
        later.message,
        i18n("queue.stopped", "ai", error.message, error.stack),
      );
      this.assertTrue(later.cause === error);
      this.assertEqual(seen.join(","), "ab,cd");
    }

    // A reply stays held until its wake runs, and then its bytes are free.
    test_replies_held(): void {
      const far = type_fresh();
      const seen: unknown[] = [];
      const note = handler_fresh((line) => {
        seen.push(line.text);
        return undefined;
      });
      const extra = line_build(note, {}, { text: "held back" });
      const first_reply = dispatch.reply_make(line_build(far, { id: 1 }), {});
      const held = text_bytes(first_reply);
      const limit = held + text_bytes(extra) - 1;
      let bench = bench_bounded({ [far]: "server" }, limit);
      const wake = handler_fresh(() => undefined);
      const start = handler_fresh(() => {
        const first = bench.tasks.task_submit(line_build(far));
        const second = bench.tasks.task_submit(line_build(far));
        return dispatch.task_sleep(null, [first, second], wake);
      });
      bench.ui.line_send(line_build(start));
      bench.server.line_send(dispatch.reply_make(bench.server.posted[0], {}));
      const error = thrown_get(() => bench.ui.line_send(extra));
      const extra_text = utility.json_text(extra[0]);
      const extra_bytes = text_bytes(extra);
      this.assertEqual(
        error.message,
        i18n("queue.queue_over", "ai", extra_text, extra_bytes, held, limit),
      );
      bench = bench_bounded({ [far]: "server" }, limit);
      bench.ui.line_send(line_build(start));
      for (const request of bench.server.posted) {
        bench.server.line_send(dispatch.reply_make(request, {}));
      }
      this.assertEqual(bench.tasks.depth(), 0);
      bench.ui.line_send(extra);
      this.assertEqual(seen.join(","), "held back");
    }
  }

  // The batch of verbose lines a thread forwards.
  export class TestVerboseBatch extends unittest.TestCase {
    // Nothing is kept unless `debug` and `verbose_forward` are both true.
    test_forward_off(): void {
      const cases = [
        [false, true],
        [true, false],
        [false, false],
      ];
      for (const [debug, forward] of cases) {
        const reader = reader_make(debug, forward);
        const batch = new queue.VerboseBatch("ui", reader);
        ring_make(batch).log(0, "dropped");
        this.assertEqual(batch_take(batch).length, 0);
      }
    }

    // The kept lines go out as one `verbose.put` of the thread, then none.
    test_batch_sent(): void {
      const batch = new queue.VerboseBatch("ai", reader_make(true, true));
      const ring = ring_make(batch);
      ring.log(0, "a");
      ring.log(1, "b");
      ring.log(2, "c");
      const posted = batch_take(batch);
      this.assertEqual(posted.length, 1);
      const put = posted[0];
      this.assertEqual(field_of(put, "type"), "verbose.put");
      this.assertTrue(Object.hasOwn(put[0], "type"));
      this.assertEqual(put.thread, "ai");
      const sent = put.lines as lines.VerboseLine[];
      const kept = ring.history_get(3);
      this.assertEqual(sent.length, 3);
      for (let index = 0; index < kept.length; index += 1) {
        this.assertTrue(sent[index] === kept[index]);
      }
      this.assertEqual(batch_take(batch).length, 0);
    }

    // Lines logged while a batch goes out stay out of every batch.
    test_sending_excluded(): void {
      const batch = new queue.VerboseBatch("ui", reader_make(true, true));
      const ring = ring_make(batch);
      ring.log(2, "before");
      const posted: lines.Line[] = [];
      batch.batch_send((line) => {
        ring.log(2, "sending");
        posted.push(line);
      });
      this.assertEqual(posted.length, 1);
      this.assertEqual(texts_of(posted[0]), "before");
      this.assertEqual(batch_take(batch).length, 0);
      ring.log(2, "after");
      this.assertEqual(texts_of(batch_take(batch)[0]), "after");
      const texts = ring.history_get(3).map((line) => line.text);
      this.assertEqual(texts.join(","), "before,sending,after");
    }

    // The kept lines go out in order as `verbose.put` lines below `line_max`.
    test_batch_split(): void {
      const value = settings_make(true, true);
      const batch = new queue.VerboseBatch("ai", reader_from(value));
      const ring = ring_make(batch);
      for (const text of ["a", "b", "c", "d", "e"]) {
        ring.log(2, text);
      }
      const [first, second] = ring.history_get(5);
      const empty = text_bytes(put_empty("ai"));
      const pair = empty + text_bytes(first) + 1 + text_bytes(second);
      value.line_max = pair + 1;
      const posted = batch_take(batch);
      const texts = posted.map((line) => texts_of(line));
      this.assertEqual(texts.join(" "), "a,b c,d e");
      for (const line of posted) {
        this.assertTrue(text_bytes(line) < value.line_max);
      }
      this.assertEqual(text_bytes(posted[0]), pair);
    }

    // A line too long for a `verbose.put` of its own throws, and nothing goes.
    test_entry_over(): void {
      const value = settings_make(true, true);
      const batch = new queue.VerboseBatch("ui", reader_from(value));
      const ring = ring_make(batch);
      ring.log(2, "a");
      ring.log(2, "a longer line");
      const [longer] = ring.history_get(1);
      const bytes = text_bytes(put_empty("ui")) + text_bytes(longer);
      value.line_max = bytes;
      const posted: lines.Line[] = [];
      const error = thrown_get(() =>
        batch.batch_send((line) => {
          posted.push(line);
        }),
      );
      this.assertEqual(
        error.message,
        i18n("queue.entry_over", "ui", bytes, bytes),
      );
      this.assertEqual(posted.length, 0);
    }

    // Only the threads `ui` and `ai` forward verbose lines.
    test_thread_refused(): void {
      const error = thrown_get(
        () => new queue.VerboseBatch("server", reader_make(true, true)),
      );
      this.assertEqual(error.message, i18n("queue.sink_thread", "server"));
    }
  }

  // The verbose sink a queue installs and the batch it sends after a task.
  export class TestSinkAttach extends unittest.TestCase {
    // After a task the kept lines go to the owner of `verbose.` as a notice.
    test_batch_after(): void {
      const owners: queue.OwnerTable = {
        [constants.type_prefix]: "ui",
        "verbose.": "ai",
      };
      const tasks = new queue.TaskQueue("ui", owners, true);
      const ai = new PortDouble("ai", []);
      tasks.port_add("ai", ai);
      const ring = new verbose.LineRing(() => 10);
      tasks.sink_attach(
        (fn) => {
          ring.sink_set(fn);
        },
        reader_make(true, true),
      );
      ring.log(2, "before");
      this.assertEqual(ai.posted.length, 0);
      const note = handler_fresh(() => {
        ring.log(2, "during");
        return undefined;
      });
      ai.line_send(line_build(note));
      this.assertEqual(ai.posted.length, 1);
      const put = ai.posted[0];
      this.assertEqual(field_of(put, "type"), "verbose.put");
      this.assertEqual(field_of(put, "id"), undefined);
      this.assertEqual(put.thread, "ui");
      this.assertEqual(texts_of(put), "before,during");
    }

    // A task that throws stops the queue with its verbose lines unsent.
    test_fault_unsent(): void {
      const owners: queue.OwnerTable = {
        [constants.type_prefix]: "ui",
        "verbose.": "ai",
      };
      const tasks = new queue.TaskQueue("ui", owners, true);
      const ai = new PortDouble("ai", []);
      tasks.port_add("ai", ai);
      const ring = new verbose.LineRing(() => 10);
      tasks.sink_attach(
        (fn) => {
          ring.sink_set(fn);
        },
        reader_make(true, true),
      );
      const failure = new Error("The handler failed.");
      const boom = handler_fresh(() => {
        ring.log(2, "during");
        throw failure;
      });
      const thrown = thrown_get(() => ai.line_send(line_build(boom)));
      this.assertTrue(thrown === failure);
      this.assertEqual(ai.posted.length, 0);
    }

    // A second sink, or a sink where the thread owns `verbose.put`, throws.
    test_attach_refused(): void {
      const ring = new verbose.LineRing(() => 10);
      const reader = reader_make(true, true);
      const tasks = new queue.TaskQueue("ui", { "verbose.": "ai" }, true);
      tasks.sink_attach(
        (fn) => {
          ring.sink_set(fn);
        },
        reader,
      );
      const twice = thrown_get(() => tasks.sink_attach(() => {}, reader));
      this.assertEqual(twice.message, i18n("queue.sink_twice", "ui"));
      const own = new queue.TaskQueue("ai", { "verbose.": "ai" }, true);
      const looped = thrown_get(() => own.sink_attach(() => {}, reader));
      this.assertEqual(looped.message, i18n("queue.sink_owner", "ai"));
    }
  }
}

Object.freeze(test_queue);
