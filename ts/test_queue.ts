// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Tests of the task manager with port, ring and settings doubles: routing,
// ids, replies, sleeps and wakes, the name form of a wake, faults, a
// handler's failure, an error line's cascade, depth, blob moves, the bound on
// the blob bytes it holds and `line_bytes`, the trace in debug mode, the
// verbose sink and its batches, and `entry_fits`. The lines and sleeps the
// tests build and the texts they expect are the gold of test_settings.json,
// the parts known only at run time, as a fresh type, an id the queue gave, a
// blob's bytes or an error's stack, set by the test on its copy.

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

  // A copy of a value of this module's gold, which the harness keeps frozen.
  function gold_value(name: string): unknown {
    return structuredClone(harness.gold_get(`typescript.test_queue.${name}`));
  }

  // A text of this module's gold, a run time `{n}` left for the test to fill.
  function gold_text(name: string): string {
    return harness.gold_get(`typescript.test_queue.texts.${name}`) as string;
  }

  // A copy of a line of this module's gold, a run time part set on the copy.
  function gold_line(name: string): lines.Line {
    return gold_value(`lines.${name}`) as lines.Line;
  }

  // A gold text with each run time placeholder `{n}` replaced by its value.
  function text_fill(name: string, values: { [n: string]: unknown }): string {
    let text = gold_text(name);
    for (const [n, value] of Object.entries(values)) {
      text = text.replaceAll(`{${n}}`, String(value));
    }
    return text;
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
      this.trace.push(`${this.name} ${JSON.stringify(line)}`);
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

  // A verbose ring double that keeps each line it makes and hands it on.
  class RingDouble {
    readonly logged: lines.VerboseLine[] = [];
    private sink: ((line: lines.VerboseLine) => void) | undefined;

    // Takes the one sink: a second throws.
    sink_set(fn: (line: lines.VerboseLine) => void): void {
      if (this.sink !== undefined) {
        throw new Error("The ring double has a sink already.");
      }
      this.sink = fn;
    }

    // Makes a verbose line of the text now, keeps it, and hands it on.
    log(text: string): void {
      const sink = this.sink;
      if (sink === undefined) {
        throw new Error("The ring double has no sink.");
      }
      const line = { at: Date.now(), text };
      this.logged.push(line);
      sink(line);
    }
  }

  // A synchronous queue on the thread `ai` with doubles of `ui` and `server`.
  interface QueueBench {
    tasks: queue.TaskQueue;
    ui: PortDouble;
    server: PortDouble;
    trace: string[];
  }

  // Makes a bench with the owner table given.
  function bench_make(owners: queue.OwnerTable): QueueBench {
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

  // A copy of a gold line with the type first in its header, short or full.
  function line_build(type: string, name = "bare", full = false): lines.Line {
    const line = gold_line(name);
    const field = full ? "type" : "t";
    line[0] = { [field]: type, ...line[0] } as lines.LineHeader;
    return line;
  }

  // Sets the `d` of each blob header of a line to zeros of its size.
  function blobs_fill(line: lines.Line): lines.Line {
    for (let number = 1; Object.hasOwn(line, number); number += 1) {
      const blob = line[number] as lines.BlobHeader;
      blob.d = new Uint8Array(blob.s);
    }
    return line;
  }

  // A gold notification of the type whose blobs hold zeros.
  function blob_line(type: string, name: string): lines.Line {
    return blobs_fill(line_build(type, name));
  }

  // A gold reply copy to a request, `t` and `r` first from its `t` and `i`.
  function reply_build(request: lines.Line, name: string): lines.Line {
    const reply = gold_line(name);
    const asked = request[0];
    reply[0] = { t: asked.t, r: asked.i, ...reply[0] };
    return reply;
  }

  // The gold reply to a request that carries one blob of zeros.
  function reply_blob(request: lines.Line): lines.Line {
    return blobs_fill(reply_build(request, "reply_held"));
  }

  // A copy of a gold sleep, woken by the type, on the ids when they are given.
  function sleep_build(
    name: string,
    then_type: string,
    wait_ids?: number[],
  ): dispatch.Sleep {
    const sleep = gold_value(`lines.${name}`) as dispatch.Sleep;
    sleep.then_type = then_type;
    if (wait_ids !== undefined) {
      sleep.wait_ids = wait_ids;
    }
    return sleep;
  }

  // A copy of the gold sleep whose state keeps the request it will answer.
  function sleep_asked(
    request: lines.Line,
    then_type: string,
    wait_ids: number[],
  ): dispatch.Sleep {
    const sleep = sleep_build("sleep_request", then_type, wait_ids);
    (sleep.state as { request: lines.Line }).request = request;
    return sleep;
  }

  // The cascade of an error as an error line carries it, its causes nested.
  function cascade_of(error: Error): lines.ErrorCause {
    const entry: lines.ErrorCause = {
      message: error.message,
      stack: error.stack as string,
    };
    if (error.cause !== undefined) {
      entry.cause = cascade_of(error.cause as Error);
    }
    return entry;
  }

  // The gold error line of no line, carrying the cascade of the error.
  function error_build(error: Error): lines.Line {
    return Object.assign(gold_line("error_bare"), cascade_of(error));
  }

  // A field of the header of a line, read by its key.
  function field_read(line: lines.Line, key: string): unknown {
    return (line[0] as unknown as { [field: string]: unknown })[key];
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

  // A settings reader double: the test's own values, else `settings.json`.
  function reader_make(values: {
    [id: string]: unknown;
  }): (id: string) => unknown {
    return (id: string) =>
      Object.hasOwn(values, id) ? values[id] : harness.setting_get(id);
  }

  // A bench whose queue holds blobs of at most the bytes given, `blob_max`.
  function bench_bounded(far: queue.OwnerTable, limit: number): QueueBench {
    const bench = bench_make(owners_make({ "verbose.": "server", ...far }));
    const reader = reader_make({ debug: false, blob_max: limit });
    bench.tasks.sink_attach(() => {}, reader);
    return bench;
  }

  // The bytes of the JSON text of a value in `UTF-8`.
  function text_bytes(value: unknown): number {
    return new TextEncoder().encode(JSON.stringify(value)).length;
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

  // A ring double whose sink is the batch.
  function ring_make(batch: queue.VerboseBatch): RingDouble {
    const ring = new RingDouble();
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
      for (const name of ["n_1", "n_2", "n_3"]) {
        bench.ui.line_send(line_build(note, name));
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
      const line = line_build(far, "forward_kept");
      (line[1] as lines.BlobHeader).d = data;
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
        text_fill("queue_forward_local", { 1: JSON.stringify(own[0]) }),
      );
      const request = line_build(far, "request_4");
      const error = thrown_get(() => bench.ui.line_send(request));
      this.assertEqual(
        error.message,
        text_fill("queue_forward_marked", { 1: JSON.stringify(request[0]) }),
      );
      this.assertEqual(bench.server.posted.length, 0);
    }

    // A type that no prefix of the owner table matches throws.
    test_owner_missing(): void {
      const bench = bench_make(owners_make({}));
      const line = line_build(constants.unrouted_type);
      const error = thrown_get(() => bench.ui.line_send(line));
      this.assertEqual(error.message, gold_text("queue_owner_missing"));
    }

    // A local port hands a post to its one receiver as the same object.
    test_local_port(): void {
      const port = new queue.LocalPort();
      const line = line_build(type_fresh());
      const missing = thrown_get(() => port.line_post(line, []));
      this.assertEqual(missing.message, gold_text("queue_receiver_missing"));
      const seen: lines.Line[] = [];
      port.line_receive((got) => {
        seen.push(got);
      });
      const twice = thrown_get(() => port.line_receive(() => {}));
      this.assertEqual(twice.message, gold_text("queue_receiver_twice"));
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
      this.assertEqual(twice.message, gold_text("queue_port_twice_ui"));
      const own = thrown_get(() =>
        bench.tasks.port_add("ai", new queue.LocalPort()),
      );
      this.assertEqual(own.message, gold_text("queue_port_twice_own"));
    }

    // A line whose owner is the port it came on throws and is not sent back.
    test_forward_back(): void {
      const far = type_fresh();
      const bench = bench_make(owners_make({ [far]: "ui" }));
      const line = line_build(far);
      const error = thrown_get(() => bench.ui.line_send(line));
      this.assertEqual(
        error.message,
        text_fill("queue_forward_back", { 1: JSON.stringify(line[0]) }),
      );
      this.assertEqual(bench.ui.posted.length, 0);
    }

    // A thread port takes one receiver, and a second one throws.
    test_thread_receiver(): void {
      const channel = new MessageChannel();
      const port = new queue.ThreadPort(channel.port1);
      port.line_receive(() => {});
      const twice = thrown_get(() => port.line_receive(() => {}));
      this.assertEqual(twice.message, gold_text("queue_receiver_twice"));
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
        const full = line_build(to_server, "bare", true);
        ids.push(bench.tasks.task_submit(full));
        return sleep_build("sleep_null", wake, ids);
      });
      bench.ui.line_send(line_build(start));
      this.assertEqual(ids.join(","), "1,2,3");
      const [first, third] = bench.server.posted;
      this.assertEqual(field_read(first, "i"), 1);
      this.assertEqual(field_read(bench.ui.posted[0], "i"), 2);
      this.assertEqual(field_read(third, "id"), 3);
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
        made.push(reply_build(line, "reply_done"));
        return made[0];
      });
      bench.ui.line_send(line_build(ask, "request_5"));
      this.assertEqual(bench.ui.posted.length, 1);
      this.assertTrue(bench.ui.posted[0] === made[0]);
      this.assertEqual(field_read(bench.ui.posted[0], "r"), 5);
      this.assertEqual(bench.server.posted.length, 0);
    }

    // A wake answers the request that slept, on the port it came on.
    test_wake_answers(): void {
      const far = type_fresh();
      const bench = bench_make(owners_make({ [far]: "server" }));
      const done = handler_fresh((line) => {
        const state = line.state as { request: lines.Line };
        const replies = line.replies as lines.Line[];
        const answer = reply_build(state.request, "bare");
        answer.got = replies[0].n;
        return answer;
      });
      const ask = handler_fresh((line) => {
        const id = bench.tasks.task_submit(line_build(far));
        return sleep_asked(line, done, [id]);
      });
      bench.ui.line_send(line_build(ask, "request_9"));
      this.assertEqual(bench.ui.posted.length, 0);
      const request = bench.server.posted[0];
      bench.server.line_send(reply_build(request, "reply_seven"));
      this.assertEqual(bench.ui.posted.length, 1);
      const answer = bench.ui.posted[0];
      this.assertEqual(field_read(answer, "t"), ask);
      this.assertEqual(field_read(answer, "r"), 9);
      this.assertEqual(answer.got, 7);
      this.assertEqual(bench.tasks.depth(), 0);
    }

    // A reply that answers no request sent on its own port throws.
    test_reply_unknown(): void {
      const far = type_fresh();
      const owners = owners_make({ [far]: "server" });
      const empty = bench_make(owners);
      const stray = reply_build(line_build(far, "request_99"), "bare");
      const stray_text = JSON.stringify(stray[0]);
      const unknown = thrown_get(() => empty.server.line_send(stray));
      this.assertEqual(
        unknown.message,
        text_fill("queue_reply_unknown_server", { 1: stray_text }),
      );
      const bench = bench_make(owners);
      const idle = handler_fresh(() => undefined);
      const start = handler_fresh(() => {
        const id = bench.tasks.task_submit(line_build(far));
        return sleep_build("sleep_null", idle, [id]);
      });
      bench.ui.line_send(line_build(start));
      const reply = reply_build(bench.server.posted[0], "bare");
      const wrong = thrown_get(() => bench.ui.line_send(reply));
      this.assertEqual(
        wrong.message,
        text_fill("queue_reply_unknown_ui", { 1: JSON.stringify(reply[0]) }),
      );
    }

    // An error line from a port stops the queue with its message and stack.
    test_error_line(): void {
      const bench = bench_make(owners_make({}));
      const failure = new Error("It failed.");
      const line = error_build(failure);
      const thrown = thrown_get(() => bench.server.line_send(line));
      this.assertEqual(
        thrown.message,
        text_fill("queue_error_line", { 3: failure.stack }),
      );
      this.assertFalse(Object.hasOwn(thrown, "cause"));
      const later = thrown_get(() =>
        bench.ui.line_send(line_build(type_fresh())),
      );
      this.assertEqual(
        later.message,
        text_fill("queue_stopped", { 1: thrown.message, 2: thrown.stack }),
      );
      this.assertTrue(later.cause === thrown);
    }

    // An error line's cascade is rebuilt as Errors under the queue's error.
    test_error_cascade(): void {
      const bench = bench_make(owners_make({}));
      const first = new Error("It began.");
      const second = new Error("It spread.", { cause: first });
      const third = new Error("It failed.", { cause: second });
      const line = error_build(third);
      const thrown = thrown_get(() => bench.server.line_send(line));
      this.assertEqual(
        thrown.message,
        text_fill("queue_error_line", { 3: third.stack }),
      );
      const chain: Error[] = [];
      for (let cause = thrown.cause; cause !== undefined;) {
        if (!(cause instanceof Error)) {
          throw new TypeError("a cause is no Error", { cause });
        }
        chain.push(cause);
        cause = cause.cause;
      }
      this.assertEqual(chain.length, 2);
      for (const [index, sent] of [second, first].entries()) {
        this.assertEqual(chain[index].message, sent.message);
        this.assertEqual(chain[index].stack, sent.stack);
      }
    }

    // A wake must answer the request it owes, and only a request it owes.
    test_reply_owed(): void {
      const far = type_fresh();
      const owners = owners_make({ [far]: "server" });
      let bench = bench_make(owners);
      const mute = handler_fresh(() => undefined);
      const ask = handler_fresh((line) => {
        const id = bench.tasks.task_submit(line_build(far));
        return sleep_asked(line, mute, [id]);
      });
      bench.ui.line_send(line_build(ask, "request_3"));
      const first = reply_build(bench.server.posted[0], "bare");
      const missing = thrown_get(() => bench.server.line_send(first));
      this.assertEqual(
        missing.message,
        text_fill("queue_reply_missing", { 0: mute }),
      );
      bench = bench_make(owners);
      const stray = reply_build(line_build(far, "request_8"), "bare");
      const loose = handler_fresh(() => stray);
      const note = handler_fresh(() => {
        const id = bench.tasks.task_submit(line_build(far));
        return sleep_build("sleep_null", loose, [id]);
      });
      bench.ui.line_send(line_build(note));
      const second = reply_build(bench.server.posted[0], "bare");
      const unowed = thrown_get(() => bench.server.line_send(second));
      this.assertEqual(
        unowed.message,
        text_fill("queue_reply_unowed", {
          0: loose,
          2: JSON.stringify(stray[0]),
        }),
      );
      this.assertEqual(bench.ui.posted.length, 0);
    }

    // A type that is not text, or an id that is not a number, throws.
    test_header_kinds(): void {
      const bench = bench_make(owners_make({}));
      const untyped = { 0: { t: 5 } } as unknown as lines.Line;
      const typed = thrown_get(() => bench.tasks.line_notify(untyped));
      this.assertEqual(typed.message, gold_text("queue_type_invalid"));
      const header = { t: type_fresh(), i: "7" };
      const unnumbered = { 0: header } as unknown as lines.Line;
      const numbered = thrown_get(() => bench.tasks.line_notify(unnumbered));
      this.assertEqual(
        numbered.message,
        text_fill("queue_field_invalid", { 0: JSON.stringify(header) }),
      );
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
        bench.tasks.line_notify(line_build(far, "note_true"), "ui");
        return sleep_build("sleep_null", wake, [id]);
      });
      bench.ui.line_send(line_build(start));
      this.assertEqual(bench.server.posted.length, 0);
      this.assertEqual(bench.ui.posted.length, 2);
      const request = bench.ui.posted[0];
      this.assertEqual(field_read(request, "i"), 1);
      this.assertEqual(bench.ui.posted[1].note, true);
      this.assertEqual(field_read(bench.ui.posted[1], "i"), undefined);
      bench.ui.line_send(reply_build(request, "bare"));
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
        return sleep_build("sleep_null", idle, [id]);
      });
      bench.ui.line_send(line_build(start));
      const reply = reply_build(bench.ui.posted[0], "bare");
      const reply_text = JSON.stringify(reply[0]);
      const wrong = thrown_get(() => bench.server.line_send(reply));
      this.assertEqual(
        wrong.message,
        text_fill("queue_reply_unknown_server", { 1: reply_text }),
      );
    }

    // A given owner with no port throws as an owner from the table would.
    test_owner_unconnected(): void {
      const far = type_fresh();
      const bench = bench_make(owners_make({ [far]: "server" }));
      const notice = thrown_get(() =>
        bench.tasks.line_notify(line_build(far), "media"),
      );
      this.assertEqual(notice.message, gold_text("queue_port_missing_media"));
      const start = handler_fresh(() => {
        bench.tasks.task_submit(line_build(far), "http");
        return undefined;
      });
      const submit = thrown_get(() => bench.ui.line_send(line_build(start)));
      this.assertEqual(submit.message, gold_text("queue_port_missing_http"));
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
      bench.tasks.line_notify(line_build(near, "n_1"), "ai");
      this.assertEqual(seen.join(","), "1");
      this.assertEqual(bench.server.posted.length, 0);
      bench.tasks.line_notify(line_build(near, "n_2"));
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
        return sleep_build("sleep_kept", wake, [second, first]);
      });
      for (const server_first of [true, false]) {
        bench = bench_make(owners);
        woken.length = 0;
        bench.ui.line_send(line_build(start));
        const server_reply = reply_build(bench.server.posted[0], "bare");
        const ui_reply = reply_build(bench.ui.posted[0], "bare");
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
        this.assertEqual(field_read(woken[0], "type"), wake);
        this.assertEqual(field_read(woken[0], "id"), undefined);
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
        return sleep_build("sleep_empty", wake);
      });
      bench.ui.line_send(line_build(start));
      this.assertEqual(seen.join(","), "start,wake 0");
      this.assertEqual(bench.tasks.depth(), 0);
    }

    // A wake line is built in full names in debug mode, else in short names.
    test_wake_form(): void {
      const bench = bench_make(owners_make({}));
      const woken: lines.Line[] = [];
      const wake = handler_fresh((line) => {
        woken.push(line);
        return undefined;
      });
      const start = handler_fresh(() => sleep_build("sleep_empty", wake));
      bench.ui.line_send(line_build(start));
      this.assertEqual(woken.length, 1);
      const full = harness.setting_get("debug") === true;
      this.assertEqual(Object.hasOwn(woken[0][0], "type"), full);
      this.assertEqual(Object.hasOwn(woken[0][0], "t"), !full);
    }

    // A sleep names every request its handler submitted, each once.
    test_wait_rules(): void {
      const far = type_fresh();
      const owners = owners_make({ [far]: "server" });
      const wake = handler_fresh(() => undefined);
      let bench = bench_make(owners);
      const unknown = handler_fresh(() => sleep_build("sleep_unknown", wake));
      let error = thrown_get(() => bench.ui.line_send(line_build(unknown)));
      this.assertEqual(
        error.message,
        text_fill("queue_wait_unknown", { 0: unknown }),
      );
      bench = bench_make(owners);
      const partial = handler_fresh(() => {
        const first = bench.tasks.task_submit(line_build(far));
        bench.tasks.task_submit(line_build(far));
        return sleep_build("sleep_null", wake, [first]);
      });
      error = thrown_get(() => bench.ui.line_send(line_build(partial)));
      this.assertEqual(
        error.message,
        text_fill("queue_wait_missing_second", { 0: partial }),
      );
      bench = bench_make(owners);
      const twice = handler_fresh(() => {
        const id = bench.tasks.task_submit(line_build(far));
        return sleep_build("sleep_null", wake, [id, id]);
      });
      error = thrown_get(() => bench.ui.line_send(line_build(twice)));
      this.assertEqual(
        error.message,
        text_fill("queue_wait_twice", { 0: twice }),
      );
      bench = bench_make(owners);
      const careless = handler_fresh(() => {
        bench.tasks.task_submit(line_build(far));
        return undefined;
      });
      error = thrown_get(() => bench.ui.line_send(line_build(careless)));
      this.assertEqual(
        error.message,
        text_fill("queue_wait_missing_first", { 0: careless }),
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
        text_fill("queue_submit_outside", { 1: far }),
      );
      const marked = line_build(far, "request_2");
      const inner: Error[] = [];
      const start = handler_fresh(() => {
        inner.push(thrown_get(() => bench.tasks.task_submit(marked)));
        return undefined;
      });
      bench.ui.line_send(line_build(start));
      this.assertEqual(
        inner[0].message,
        text_fill("queue_submit_marked", { 0: JSON.stringify(marked[0]) }),
      );
      const notified = thrown_get(() => bench.tasks.line_notify(marked));
      this.assertEqual(
        notified.message,
        text_fill("queue_notify_marked", { 0: JSON.stringify(marked[0]) }),
      );
      this.assertEqual(bench.server.posted.length, 0);
      this.assertEqual(bench.tasks.depth(), 0);
    }
  }

  // The synchronous mode: the same run twice, faults and the depth.
  export class TestSynchronousMode extends unittest.TestCase {
    // The same inputs give the same posts, handler order and trace twice.
    test_run_twice(): void {
      const to_server = type_fresh();
      const to_ui = type_fresh();
      const owners = owners_make({
        [to_server]: "server",
        [to_ui]: "ui",
        "verbose.": "server",
      });
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
        const answer = reply_build(state.request, "bare");
        answer.count = (line.replies as lines.Line[]).length;
        return answer;
      });
      const say = handler_fresh((line) => {
        bench.trace.push("run say");
        bench.server.line_send(line_build(late));
        bench.tasks.line_notify(line_build(note));
        const first = bench.tasks.task_submit(line_build(to_server));
        const second = bench.tasks.task_submit(line_build(to_ui));
        return sleep_asked(line, done, [first, second]);
      });
      const runs: string[] = [];
      const logs: string[] = [];
      for (let index = 0; index < 2; index += 1) {
        bench = bench_make(owners);
        bench.tasks.sink_attach(() => {}, reader_make({ debug: true }));
        const mark = mark_take();
        bench.ui.line_send(line_build(say, "say_1"));
        const request = bench.server.posted[0];
        bench.ui.line_send(reply_build(bench.ui.posted[0], "bare"));
        bench.server.line_send(reply_build(request, "bare"));
        const handlers = bench.trace.filter((entry) =>
          entry.startsWith("run "),
        );
        this.assertEqual(
          handlers.join(","),
          "run say,run note,run late,run done",
        );
        this.assertEqual(bench.ui.posted.length, 2);
        this.assertEqual(field_read(bench.ui.posted[1], "r"), 1);
        this.assertEqual(bench.ui.posted[1].count, 2);
        this.assertEqual(bench.tasks.depth(), 0);
        runs.push(bench.trace.join("\n"));
        logs.push(texts_after(mark).join("\n"));
      }
      this.assertEqual(runs[0], runs[1]);
      this.assertTrue(logs[0].length > 0);
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
        text_fill("queue_stopped", { 1: failure.message, 2: failure.stack }),
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
      ui.line_send(line_build(note, "n_1"));
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
        return sleep_build("sleep_null", wake, [first, second]);
      });
      this.assertEqual(bench.tasks.depth(), 0);
      bench.ui.line_send(line_build(start));
      this.assertEqual(during.join(","), "1,3");
      this.assertEqual(bench.tasks.depth(), 1);
      bench.server.line_send(reply_build(bench.server.posted[0], "bare"));
      this.assertEqual(bench.tasks.depth(), 1);
      bench.server.line_send(reply_build(bench.server.posted[1], "bare"));
      this.assertEqual(during.join(","), "1,3,1");
      this.assertEqual(bench.tasks.depth(), 0);
    }
  }

  // A handler's failure: its reply is posted, then the queue fails.
  export class TestFailure extends unittest.TestCase {
    // The reply goes out, then the queue throws the error and stays stopped.
    test_failure_posted(): void {
      const bench = bench_make(owners_make({}));
      const failure = new Error("The tool failed.");
      const made: lines.Line[] = [];
      const ask = handler_fresh((line) => {
        made.push(reply_build(line, "reply_failed"));
        const failed: dispatch.Failure = { reply: made[0], error: failure };
        return failed;
      });
      const thrown = thrown_get(() =>
        bench.ui.line_send(line_build(ask, "request_5")),
      );
      this.assertTrue(thrown === failure);
      this.assertEqual(bench.ui.posted.length, 1);
      this.assertTrue(bench.ui.posted[0] === made[0]);
      this.assertEqual(field_read(bench.ui.posted[0], "r"), 5);
      this.assertEqual(bench.tasks.depth(), 0);
      const later = thrown_get(() =>
        bench.ui.line_send(line_build(ask, "request_6")),
      );
      this.assertEqual(
        later.message,
        text_fill("queue_stopped", { 1: failure.message, 2: failure.stack }),
      );
      this.assertTrue(later.cause === failure);
      this.assertEqual(bench.ui.posted.length, 1);
    }

    // A failure after a submit posts the reply, then fails on the wait.
    test_failure_submitted(): void {
      const far = type_fresh();
      const bench = bench_make(owners_make({ [far]: "server" }));
      const failure = new Error("The tool failed.");
      const ask = handler_fresh((line) => {
        bench.tasks.task_submit(line_build(far));
        const failed: dispatch.Failure = {
          reply: reply_build(line, "bare"),
          error: failure,
        };
        return failed;
      });
      const thrown = thrown_get(() =>
        bench.ui.line_send(line_build(ask, "request_5")),
      );
      this.assertEqual(
        thrown.message,
        text_fill("queue_wait_missing_first", { 0: ask }),
      );
      this.assertTrue(thrown.cause === failure);
      this.assertEqual(bench.server.posted.length, 1);
      this.assertEqual(bench.ui.posted.length, 1);
      this.assertEqual(field_read(bench.ui.posted[0], "r"), 5);
    }
  }

  // Blob bytes move with a submit or a notification and are never copied.
  export class TestBlobTransfer extends unittest.TestCase {
    // After a submit the caller's bytes are detached and the post holds them.
    test_submit_detaches(): void {
      const far = type_fresh();
      const bench = bench_make(owners_make({ [far]: "server" }));
      const data = Uint8Array.from([0, 13, 10, 3, 4, 255]);
      const line = line_build(far, "submit_six");
      (line[1] as lines.BlobHeader).d = data;
      const wake = handler_fresh(() => undefined);
      const start = handler_fresh(() => {
        const id = bench.tasks.task_submit(line);
        return sleep_build("sleep_null", wake, [id]);
      });
      bench.ui.line_send(line_build(start));
      this.assertEqual(data.byteLength, 0);
      this.assertEqual(bytes_of(line[1]).byteLength, 0);
      this.assertEqual(field_read(line, "i"), 1);
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
      const line = line_build(far, "shared_halves");
      const head = line[1] as lines.BlobHeader;
      const tail = line[2] as lines.BlobHeader;
      head.d = whole.subarray(0, 2);
      tail.d = whole.subarray(2, 4);
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

  // The bound `blob_max` puts on the blob bytes of the lines a queue holds.
  export class TestQueueLimit extends unittest.TestCase {
    // A line counts the bytes its blobs hold in memory, a handle none.
    test_line_bytes(): void {
      const type = type_fresh();
      const held = line_build(type, "held_two");
      (held[1] as lines.BlobHeader).d = Uint8Array.from([1, 2]);
      (held[2] as lines.BlobHeader).d = Uint8Array.from([3, 4, 5]);
      this.assertEqual(queue.line_bytes(held), 5);
      const cached = line_build(type, "cached_two");
      (cached[2] as lines.BlobHeader).d = Uint8Array.from([1, 2]);
      this.assertEqual(queue.line_bytes(cached), 2);
      this.assertEqual(queue.line_bytes(line_build(type)), 0);
    }

    // A held line whose blob streamed to a cache file passes the bound.
    test_handle_unheld(): void {
      const seen: unknown[] = [];
      const note = handler_fresh((line) => {
        seen.push(line.text);
        return undefined;
      });
      const bench = bench_bounded({}, 5);
      bench.ui.line_send(line_build(note, "handle_x"));
      this.assertEqual(seen, ["x"]);
      this.assertEqual(bench.tasks.depth(), 0);
    }

    // A line counts the bytes of its blobs in memory, not its text.
    test_line_measured(): void {
      const note = handler_fresh(() => undefined);
      const bench = bench_bounded({}, 5);
      bench.ui.line_send(line_build(note, "text_long"));
      const line = line_build(note, "measured_two");
      (line[1] as lines.BlobHeader).d = Uint8Array.from([1, 2]);
      (line[2] as lines.BlobHeader).d = Uint8Array.from([3, 4, 5, 6]);
      const error = thrown_get(() => bench.ui.line_send(line));
      const header_text = JSON.stringify(line[0]);
      this.assertEqual(
        error.message,
        text_fill("queue_queue_over_measured", { 1: header_text }),
      );
      this.assertEqual(bench.tasks.depth(), 0);
    }

    // Blobs filling the bound are held, then freed, one byte more is not.
    test_limit_exact(): void {
      const seen: unknown[] = [];
      const note = handler_fresh((line) => {
        seen.push(line.text);
        return undefined;
      });
      const bench = bench_bounded({}, 4);
      bench.ui.line_send(blob_line(note, "blob_ab"));
      bench.ui.line_send(blob_line(note, "blob_cd"));
      this.assertEqual(seen.join(","), "ab,cd");
      const over = blob_line(note, "blob_efg");
      const error = thrown_get(() => bench.ui.line_send(over));
      const over_text = JSON.stringify(over[0]);
      this.assertEqual(
        error.message,
        text_fill("queue_queue_over_exact", { 1: over_text }),
      );
      const later = thrown_get(() =>
        bench.ui.line_send(blob_line(note, "blob_hi")),
      );
      this.assertEqual(
        later.message,
        text_fill("queue_stopped", { 1: error.message, 2: error.stack }),
      );
      this.assertTrue(later.cause === error);
      this.assertEqual(seen.join(","), "ab,cd");
    }

    // Doubles past `2 ** 53`, which Python sends, are held and run.
    test_double_held(): void {
      const seen: unknown[] = [];
      const note = handler_fresh((line) => {
        seen.push(line.n);
        return undefined;
      });
      const line = line_build(note);
      // Not gold: an encoder may write `1e16` as digits the decoder refuses.
      line.n = 1e16;
      line.m = -1e300;
      const bench = bench_bounded({}, 0);
      bench.server.line_send(line);
      this.assertEqual(seen, [1e16]);
      this.assertEqual(bench.tasks.depth(), 0);
    }

    // A reply's blobs stay held until its wake runs, and then they are free.
    test_replies_held(): void {
      const far = type_fresh();
      const seen: unknown[] = [];
      const note = handler_fresh((line) => {
        seen.push(line.text);
        return undefined;
      });
      const extra = blob_line(note, "blob_held");
      const held = 4;
      const limit = held + 3 - 1;
      let bench = bench_bounded({ [far]: "server" }, limit);
      const wake = handler_fresh(() => undefined);
      const start = handler_fresh(() => {
        const first = bench.tasks.task_submit(line_build(far));
        const second = bench.tasks.task_submit(line_build(far));
        return sleep_build("sleep_null", wake, [first, second]);
      });
      bench.ui.line_send(line_build(start));
      bench.server.line_send(reply_blob(bench.server.posted[0]));
      const error = thrown_get(() => bench.ui.line_send(extra));
      const extra_text = JSON.stringify(extra[0]);
      this.assertEqual(
        error.message,
        text_fill("queue_queue_over_replies", { 1: extra_text }),
      );
      bench = bench_bounded({ [far]: "server" }, limit);
      bench.ui.line_send(line_build(start));
      const [asked, also] = bench.server.posted;
      bench.server.line_send(reply_blob(asked));
      bench.server.line_send(reply_build(also, "bare"));
      this.assertEqual(bench.tasks.depth(), 0);
      bench.ui.line_send(extra);
      this.assertEqual(seen.join(","), "held back");
    }
  }

  // The trace of the thread's timeline, which only debug mode writes.
  export class TestTraceDebug extends unittest.TestCase {
    // With `debug` true a dispatch and its reply are traced, else nothing.
    test_trace_gated(): void {
      const echo = handler_fresh((line) => reply_build(line, "bare"));
      for (const debug of [false, true]) {
        const bench = bench_make(owners_make({ "verbose.": "server" }));
        bench.tasks.sink_attach(() => {}, reader_make({ debug }));
        const request = line_build(echo, "request_1");
        const mark = mark_take();
        bench.ui.line_send(request);
        const asked = JSON.stringify(request[0]);
        const answered = JSON.stringify(bench.ui.posted[0][0]);
        const expected = debug
          ? [
              text_fill("queue_dispatch", { 2: asked }),
              text_fill("queue_reply", { 2: answered }),
            ]
          : [];
        this.assertEqual(texts_after(mark), expected);
      }
    }

    // A queue that has no settings reader yet traces nothing.
    test_trace_unread(): void {
      const echo = handler_fresh((line) => reply_build(line, "bare"));
      const bench = bench_make(owners_make({}));
      const mark = mark_take();
      bench.ui.line_send(line_build(echo, "request_1"));
      this.assertEqual(bench.ui.posted.length, 1);
      this.assertEqual(texts_after(mark), []);
    }
  }

  // The batch of verbose lines a thread forwards.
  export class TestVerboseBatch extends unittest.TestCase {
    // Nothing is kept unless `debug` is true.
    test_forward_off(): void {
      const reader = reader_make({ debug: false });
      const batch = new queue.VerboseBatch("ui", reader);
      ring_make(batch).log("dropped");
      this.assertEqual(batch_take(batch).length, 0);
    }

    // The kept lines go out as one `verbose.put` of the thread, then none.
    test_batch_sent(): void {
      const batch = new queue.VerboseBatch("ai", reader_make({ debug: true }));
      const ring = ring_make(batch);
      ring.log("a");
      ring.log("b");
      ring.log("c");
      const posted = batch_take(batch);
      this.assertEqual(posted.length, 1);
      const put = posted[0];
      this.assertEqual(field_read(put, "type"), "verbose.put");
      this.assertTrue(Object.hasOwn(put[0], "type"));
      this.assertEqual(put.thread, "ai");
      const sent = put.lines as lines.VerboseLine[];
      const kept = ring.logged;
      this.assertEqual(sent.length, 3);
      for (let index = 0; index < kept.length; index += 1) {
        this.assertTrue(sent[index] === kept[index]);
      }
      this.assertEqual(batch_take(batch).length, 0);
    }

    // Lines logged while a batch goes out stay out of every batch.
    test_sending_excluded(): void {
      const batch = new queue.VerboseBatch("ui", reader_make({ debug: true }));
      const ring = ring_make(batch);
      ring.log("before");
      const posted: lines.Line[] = [];
      batch.batch_send((line) => {
        ring.log("sending");
        posted.push(line);
      });
      this.assertEqual(posted.length, 1);
      this.assertEqual(texts_of(posted[0]), "before");
      this.assertEqual(batch_take(batch).length, 0);
      ring.log("after");
      this.assertEqual(texts_of(batch_take(batch)[0]), "after");
    }

    // The kept lines go out in order as `verbose.put` lines below `line_max`.
    test_batch_split(): void {
      const value: { [id: string]: unknown } = { debug: true };
      const batch = new queue.VerboseBatch("ai", reader_make(value));
      const ring = ring_make(batch);
      for (const text of ["a", "b", "c", "d", "e"]) {
        ring.log(text);
      }
      const [first, second] = ring.logged;
      const empty = text_bytes(gold_line("put_empty_ai"));
      const pair = empty + text_bytes(first) + 1 + text_bytes(second);
      const limit = pair + 1;
      value.line_max = limit;
      const posted = batch_take(batch);
      const texts = posted.map((line) => texts_of(line));
      this.assertEqual(texts.join(" "), "a,b c,d e");
      for (const line of posted) {
        this.assertTrue(text_bytes(line) < limit);
      }
      this.assertEqual(text_bytes(posted[0]), pair);
    }

    // A line too long for a `verbose.put` of its own throws, and nothing goes.
    test_entry_over(): void {
      const value: { [id: string]: unknown } = { debug: true };
      const batch = new queue.VerboseBatch("ui", reader_make(value));
      const ring = ring_make(batch);
      ring.log("a");
      ring.log("a longer line");
      const longer = ring.logged[1];
      const bytes = text_bytes(gold_line("put_empty_ui")) + text_bytes(longer);
      value.line_max = bytes;
      const posted: lines.Line[] = [];
      const error = thrown_get(() =>
        batch.batch_send((line) => {
          posted.push(line);
        }),
      );
      this.assertEqual(
        error.message,
        text_fill("queue_entry_over_ui", { 1: bytes, 2: bytes }),
      );
      this.assertEqual(posted.length, 0);
    }

    // A text fits one byte below the size at which a batch refuses it.
    test_entry_fits(): void {
      const text = "a longer line";
      for (const thread of ["ui", "ai"] as const) {
        const value: { [id: string]: unknown } = { debug: true };
        const batch = new queue.VerboseBatch(thread, reader_make(value));
        ring_make(batch).log(text);
        const entry = { at: Date.now(), text };
        const empty = text_bytes(gold_line(`put_empty_${thread}`));
        const bytes = empty + text_bytes(entry);
        value.line_max = bytes;
        const error = thrown_get(() => batch_take(batch));
        this.assertEqual(
          error.message,
          text_fill(`queue_entry_over_${thread}`, { 1: bytes, 2: bytes }),
          thread,
        );
        this.assertFalse(queue.entry_fits(thread, text, bytes), thread);
        this.assertTrue(queue.entry_fits(thread, text, bytes + 1), thread);
        const fitting = reader_make({ debug: true, line_max: bytes + 1 });
        const sent = new queue.VerboseBatch(thread, fitting);
        ring_make(sent).log(text);
        this.assertEqual(batch_take(sent).length, 1, thread);
      }
    }

    // Only the threads `ui` and `ai` forward verbose lines.
    test_thread_refused(): void {
      const error = thrown_get(
        () => new queue.VerboseBatch("server", reader_make({ debug: true })),
      );
      this.assertEqual(error.message, gold_text("queue_sink_thread"));
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
      const ring = new RingDouble();
      tasks.sink_attach(
        (fn) => {
          ring.sink_set(fn);
        },
        reader_make({ debug: true }),
      );
      ring.log("before");
      this.assertEqual(ai.posted.length, 0);
      const note = handler_fresh(() => {
        ring.log("during");
        return undefined;
      });
      ai.line_send(line_build(note));
      this.assertEqual(ai.posted.length, 1);
      const put = ai.posted[0];
      this.assertEqual(field_read(put, "type"), "verbose.put");
      this.assertEqual(field_read(put, "id"), undefined);
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
      const ring = new RingDouble();
      tasks.sink_attach(
        (fn) => {
          ring.sink_set(fn);
        },
        reader_make({ debug: true }),
      );
      const failure = new Error("The handler failed.");
      const boom = handler_fresh(() => {
        ring.log("during");
        throw failure;
      });
      const thrown = thrown_get(() => ai.line_send(line_build(boom)));
      this.assertTrue(thrown === failure);
      this.assertEqual(ai.posted.length, 0);
    }

    // A second sink, or a sink where the thread owns `verbose.put`, throws.
    test_attach_refused(): void {
      const ring = new RingDouble();
      const reader = reader_make({ debug: true });
      const tasks = new queue.TaskQueue("ui", { "verbose.": "ai" }, true);
      tasks.sink_attach((fn) => {
        ring.sink_set(fn);
      }, reader);
      const twice = thrown_get(() => tasks.sink_attach(() => {}, reader));
      this.assertEqual(twice.message, gold_text("queue_sink_twice"));
      const own = new queue.TaskQueue("ai", { "verbose.": "ai" }, true);
      const looped = thrown_get(() => own.sink_attach(() => {}, reader));
      this.assertEqual(looped.message, gold_text("queue_sink_owner"));
    }
  }
}

Object.freeze(test_queue);
