// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The task manager of one thread, the one synchronization tool: its ports,
// the owner table, one line dispatched at a time, sleeps and their wakes, and
// the verbose sink of the thread. Its message channel only turns a platform
// event into the next step.

namespace queue {
  // The names this module reads and writes and the level of its log lines.
  const constants = Object.freeze({
    error_type: "error",
    verbose_type: "verbose.put",
    type_field: "type",
    id_field: "id",
    reply_field: "reply",
    id_short: "i",
    full_marker: "type",
    debug_setting: "debug",
    forward_setting: "verbose_forward",
    log_level: 2,
  });

  // The owners a line can have: the threads, the server and the ports.
  export type ThreadName =
    | "ui"
    | "ai"
    | "server"
    | "http"
    | "media"
    | "console"
    | "dom";

  // A port carries lines one way each direction, in order.
  export interface Port {
    line_post(line: lines.Line, transfer: ArrayBuffer[]): void;
    line_receive(fn: (line: lines.Line) => void): void;
  }

  // Type prefix to owner, where the longest prefix that matches wins.
  export type OwnerTable = { [prefix: string]: ThreadName };

  // The request a task owes a reply to: its id and the port it came on.
  interface Owed {
    id: number;
    from: ThreadName;
  }

  // A sleeping task: state, wake type, replies so far and what it owes.
  interface SleepRecord {
    state: unknown;
    then_type: string;
    count: number;
    replies: Map<number, lines.Line>;
    owed: Owed | undefined;
  }

  // A request this queue sent: the port it went to and the sleep it wakes.
  interface PendingRequest {
    owner: ThreadName;
    sleep: SleepRecord;
  }

  // The handler run in progress: the requests it submitted, by id.
  interface HandlerRun {
    submitted: Map<number, ThreadName>;
  }

  // A line held to run, the port it came on, and what a wake owes.
  interface HeldItem {
    line: lines.Line;
    from: ThreadName;
    wake: boolean;
    owed: Owed | undefined;
  }

  // The type of a header, which must be text.
  function type_of(header: lines.LineHeader): string {
    const type = jslb.field_get(header, constants.type_field);
    if (typeof type === "string") {
      return type;
    }
    throw new Error(i18n("queue.type_invalid", utility.json_text(header)));
  }

  // A number field of a header, undefined when it is absent.
  function field_number(
    header: lines.LineHeader,
    name: string,
  ): number | undefined {
    const value = jslb.field_get(header, name);
    if (value === undefined || typeof value === "number") {
      return value;
    }
    throw new Error(
      i18n("queue.field_invalid", utility.json_text(header), name),
    );
  }

  // Says whether a header has an id or a reply.
  function header_marked(header: lines.LineHeader): boolean {
    return (
      field_number(header, constants.id_field) !== undefined ||
      field_number(header, constants.reply_field) !== undefined
    );
  }

  // The header of a line as JSON text, for the log and for messages.
  function header_text(line: lines.Line): string {
    return utility.json_text(line[0]);
  }

  // Says whether a handler result is a sleep, by its three fields.
  function sleep_is(result: object): result is dispatch.Sleep {
    return "state" in result && "wait_ids" in result && "then_type" in result;
  }

  // The blob headers of a line, 1 on.
  function blobs_of(line: lines.Line): lines.BlobHeader[] {
    return jslb.headers_of(line).slice(1) as lines.BlobHeader[];
  }

  // The bytes of the blobs of a line that are held in memory.
  function arrays_of(line: lines.Line): Uint8Array[] {
    const arrays: Uint8Array[] = [];
    for (const blob of blobs_of(line)) {
      const data = blob.d;
      if (data instanceof Uint8Array) {
        arrays.push(data);
      }
    }
    return arrays;
  }

  // The buffers under the arrays, each once, which a post moves.
  function buffers_of(arrays: Uint8Array[]): ArrayBuffer[] {
    const buffers: ArrayBuffer[] = [];
    for (const array of arrays) {
      const buffer = array.buffer;
      if (!(buffer instanceof ArrayBuffer)) {
        throw new Error(i18n("queue.buffer_shared"));
      }
      if (!buffers.includes(buffer)) {
        buffers.push(buffer);
      }
    }
    return buffers;
  }

  // A copy of a line whose blob headers hold their bytes moved, not copied.
  function blobs_move(line: lines.Line): lines.Line {
    const arrays = arrays_of(line);
    if (arrays.length === 0) {
      return line;
    }
    const moved = structuredClone(arrays, { transfer: buffers_of(arrays) });
    const copy: lines.Line = { ...line };
    const blobs = blobs_of(line);
    for (let index = 0; index < blobs.length; index += 1) {
      const blob = blobs[index];
      const data = blob.d;
      if (data instanceof Uint8Array) {
        copy[index + 1] = { ...blob, d: moved[arrays.indexOf(data)] };
      }
    }
    return copy;
  }

  // Reads a message of a thread port, which must be a line.
  function message_read(data: unknown): lines.Line {
    if (typeof data !== "object" || data === null || !Object.hasOwn(data, 0)) {
      throw new Error(i18n("queue.message_invalid"));
    }
    return data as lines.Line;
  }

  // Same thread: a posted line goes as it is to the one receiver.
  export class LocalPort implements Port {
    private receiver: ((line: lines.Line) => void) | undefined;

    // Hands the line on, as the queue moved its blob bytes before the post.
    line_post(line: lines.Line, _transfer: ArrayBuffer[]): void {
      const receiver = this.receiver;
      if (receiver === undefined) {
        throw new Error(i18n("queue.receiver_missing"));
      }
      receiver(line);
    }

    // Sets the one receiver of the lines posted here.
    line_receive(fn: (line: lines.Line) => void): void {
      if (this.receiver !== undefined) {
        throw new Error(i18n("queue.receiver_twice"));
      }
      this.receiver = fn;
    }
  }

  // A `MessagePort` to another thread, the blob buffers in the transfer list.
  export class ThreadPort implements Port {
    private readonly port: MessagePort;
    private receiving = false;

    // Takes the port, on which a message that cannot be read throws.
    constructor(port: MessagePort) {
      this.port = port;
      port.onmessageerror = () => {
        throw new Error(i18n("queue.message_error"));
      };
    }

    // Posts the line and moves the buffers of the transfer list with it.
    line_post(line: lines.Line, transfer: ArrayBuffer[]): void {
      this.port.postMessage(line, transfer);
    }

    // Sets the one receiver, and the port starts to deliver lines.
    line_receive(fn: (line: lines.Line) => void): void {
      if (this.receiving) {
        throw new Error(i18n("queue.receiver_twice"));
      }
      this.receiving = true;
      this.port.onmessage = (event: MessageEvent<unknown>) => {
        fn(message_read(event.data));
      };
    }
  }

  // The verbose lines of a thread waiting to go out as one `verbose.put`.
  export class VerboseBatch {
    private readonly thread: "ui" | "ai";
    private readonly settings_get: (id: string) => unknown;
    private kept: lines.VerboseLine[] = [];
    private sending = false;

    // Takes the thread, `ui` or `ai`, and the reader of the settings.
    constructor(thread: ThreadName, settings_get: (id: string) => unknown) {
      if (thread !== "ui" && thread !== "ai") {
        throw new Error(i18n("queue.sink_thread", thread));
      }
      this.thread = thread;
      this.settings_get = settings_get;
    }

    // Keeps a line while forwarding is on and no batch is going out.
    line_add(line: lines.VerboseLine): void {
      if (!this.sending && this.forward_on()) {
        this.kept.push(line);
      }
    }

    // Posts the kept lines as one `verbose.put`, keeping out its own lines.
    batch_send(post: (line: lines.Line) => void): void {
      if (this.kept.length === 0) {
        return;
      }
      const header = jslb.header_make(constants.verbose_type, { full: true });
      const line = jslb.line_make(header, [], {
        thread: this.thread,
        lines: this.kept,
      });
      this.kept = [];
      this.sending = true;
      post(line);
      this.sending = false;
    }

    // Whether the settings `debug` and `verbose_forward` are both true.
    private forward_on(): boolean {
      return (
        this.settings_get(constants.debug_setting) === true &&
        this.settings_get(constants.forward_setting) === true
      );
    }
  }

  // The task manager of one thread: one line at a time, sleeps and wakes.
  export class TaskQueue {
    private readonly thread: ThreadName;
    private readonly owners: OwnerTable;
    private readonly synchronous: boolean;
    private readonly ports = new Map<ThreadName, Port>();
    private readonly local: HeldItem[] = [];
    private readonly inbox: HeldItem[] = [];
    private readonly pending = new Map<number, PendingRequest>();
    private readonly tick = new MessageChannel();
    private id_last = 0;
    private sleeping = 0;
    private draining = false;
    private scheduled = false;
    private current: HandlerRun | undefined;
    private batch: VerboseBatch | undefined;
    private fault: { cause: unknown } | undefined;

    // Takes the thread, its owner table and the mode, and adds its own port.
    constructor(
      thread: ThreadName,
      owners: OwnerTable,
      synchronous: boolean,
    ) {
      this.thread = thread;
      this.owners = owners;
      this.synchronous = synchronous;
      this.tick.port1.onmessage = () => {
        this.step_take();
      };
      this.port_add(thread, new LocalPort());
    }

    // Connects the port that reaches the named thread and receives from it.
    port_add(thread: ThreadName, port: Port): void {
      if (this.ports.has(thread)) {
        throw new Error(i18n("queue.port_twice", this.thread, thread));
      }
      this.ports.set(thread, port);
      port.line_receive((line: lines.Line) => {
        this.line_arrive(thread, line);
      });
    }

    // Submits a request from a handler to the owner given, else the table's.
    task_submit(line: lines.Line, owner?: ThreadName): number {
      const header = line[0];
      const type = type_of(header);
      const run = this.current;
      if (run === undefined) {
        throw new Error(i18n("queue.submit_outside", this.thread, type));
      }
      if (header_marked(header)) {
        throw new Error(i18n("queue.submit_marked", header_text(line)));
      }
      const target = owner ?? this.owner_find(type);
      this.id_last += 1;
      const id = this.id_last;
      const name = Object.hasOwn(header, constants.full_marker)
        ? constants.id_field
        : constants.id_short;
      Object.assign(header, { [name]: id });
      run.submitted.set(id, target);
      this.log_write("queue.submit", target, header_text(line));
      this.line_send(target, blobs_move(line));
      return id;
    }

    // Posts a notification to the owner given, else the table's, bytes moved.
    line_notify(line: lines.Line, owner?: ThreadName): void {
      const header = line[0];
      const type = type_of(header);
      if (header_marked(header)) {
        throw new Error(i18n("queue.notify_marked", header_text(line)));
      }
      const target = owner ?? this.owner_find(type);
      this.log_write("queue.notify", target, header_text(line));
      this.line_send(target, blobs_move(line));
    }

    // Passes a line another thread owns to that owner's port unchanged.
    line_forward(line: lines.Line): void {
      const header = line[0];
      const owner = this.owner_find(type_of(header));
      if (owner === this.thread) {
        throw new Error(
          i18n("queue.forward_local", this.thread, header_text(line)),
        );
      }
      if (header_marked(header)) {
        throw new Error(
          i18n("queue.forward_marked", this.thread, header_text(line)),
        );
      }
      this.log_write("queue.forward", owner, header_text(line));
      this.line_send(owner, line);
    }

    // The number of tasks waiting, running and sleeping.
    depth(): number {
      const running = this.current === undefined ? 0 : 1;
      return this.local.length + this.inbox.length + running + this.sleeping;
    }

    // Installs the verbose sink, whose batch goes out after each task.
    sink_attach(
      sink_set: (fn: (line: lines.VerboseLine) => void) => void,
      settings_get: (id: string) => unknown,
    ): void {
      if (this.batch !== undefined) {
        throw new Error(i18n("queue.sink_twice", this.thread));
      }
      if (this.owner_find(constants.verbose_type) === this.thread) {
        throw new Error(i18n("queue.sink_owner", this.thread));
      }
      const batch = new VerboseBatch(this.thread, settings_get);
      sink_set((line: lines.VerboseLine) => {
        batch.line_add(line);
      });
      this.batch = batch;
    }

    // The owner of a type: the thread of its longest matching prefix.
    private owner_find(type: string): ThreadName {
      let best: string | undefined;
      for (const prefix of Object.keys(this.owners)) {
        if (
          type.startsWith(prefix) &&
          (best === undefined || prefix.length > best.length)
        ) {
          best = prefix;
        }
      }
      if (best === undefined) {
        throw new Error(i18n("queue.owner_missing", this.thread, type));
      }
      return this.owners[best];
    }

    // Posts a line on the port of a thread with its blob buffers to move.
    private line_send(thread: ThreadName, line: lines.Line): void {
      const port = this.ports.get(thread);
      if (port === undefined) {
        throw new Error(i18n("queue.port_missing", this.thread, thread));
      }
      port.line_post(line, buffers_of(arrays_of(line)));
    }

    // Holds a line that came on a port and starts the tasks.
    private line_arrive(from: ThreadName, line: lines.Line): void {
      this.fault_check();
      const item = { line, from, wake: false, owed: undefined };
      this.item_push(item, from === this.thread);
      this.run_start();
    }

    // Holds an item, in synchronous mode its own ahead of the inputs.
    private item_push(item: HeldItem, own: boolean): void {
      if (this.synchronous && own) {
        this.local.push(item);
      } else {
        this.inbox.push(item);
      }
    }

    // Runs the held items now in synchronous mode, else asks for a step.
    private run_start(): void {
      if (!this.synchronous) {
        this.step_schedule();
      } else if (!this.draining) {
        this.tasks_drain();
      }
    }

    // Runs every held item, its own ones first, until none is left.
    private tasks_drain(): void {
      this.draining = true;
      for (
        let item = this.item_next();
        item !== undefined;
        item = this.item_next()
      ) {
        this.item_run(item);
      }
      this.draining = false;
    }

    // Asks the message channel for one step unless one is asked for.
    private step_schedule(): void {
      if (!this.scheduled) {
        this.scheduled = true;
        this.tick.port2.postMessage(null);
      }
    }

    // One step: the next held item, then another step if any is left.
    private step_take(): void {
      this.scheduled = false;
      this.fault_check();
      const item = this.item_next();
      if (item === undefined) {
        throw new Error(i18n("queue.step_empty", this.thread));
      }
      this.item_run(item);
      if (this.inbox.length > 0) {
        this.step_schedule();
      }
    }

    // The next held item, its own ones first.
    private item_next(): HeldItem | undefined {
      return this.local.shift() ?? this.inbox.shift();
    }

    // Runs one item, then sends the verbose batch, keeping the first fault.
    private item_run(item: HeldItem): void {
      try {
        this.item_route(item);
        this.batch_flush();
      } catch (error) {
        this.fault = { cause: error };
        throw error;
      }
    }

    // Throws once a fault has stopped this queue.
    private fault_check(): void {
      const fault = this.fault;
      if (fault !== undefined) {
        throw utility.error_wrap(
          i18n("queue.stopped", this.thread),
          fault.cause,
        );
      }
    }

    // Runs a wake or routes an input, and a line posted here always runs here.
    private item_route(item: HeldItem): void {
      const { line, from } = item;
      if (item.wake) {
        this.task_run(line, from, item.owed);
        return;
      }
      const header = line[0];
      const type = type_of(header);
      if (type === constants.error_type) {
        const payload = jslb.payload_of(line);
        throw new Error(
          i18n(
            "queue.error_line",
            this.thread,
            from,
            payload.message,
            payload.stack,
          ),
        );
      }
      const reply = field_number(header, constants.reply_field);
      if (reply !== undefined) {
        this.reply_receive(from, reply, line);
        return;
      }
      if (from !== this.thread && this.owner_find(type) !== this.thread) {
        this.line_forward(line);
        return;
      }
      const id = field_number(header, constants.id_field);
      this.task_run(line, from, id === undefined ? undefined : { id, from });
    }

    // Runs the handler of a line and takes what it returns.
    private task_run(
      line: lines.Line,
      from: ThreadName,
      owed: Owed | undefined,
    ): void {
      this.log_write("queue.dispatch", from, header_text(line));
      const run: HandlerRun = { submitted: new Map<number, ThreadName>() };
      this.current = run;
      const result = dispatch.line_dispatch(line);
      this.current = undefined;
      this.result_take(line, run, result, owed);
    }

    // Starts a sleep, posts a reply, or checks that nothing was owed.
    private result_take(
      line: lines.Line,
      run: HandlerRun,
      result: dispatch.Reply | dispatch.Sleep,
      owed: Owed | undefined,
    ): void {
      if (result !== undefined && sleep_is(result)) {
        this.sleep_start(line, run, result, owed);
        return;
      }
      this.waits_check(line, run, new Set<number>());
      if (result === undefined) {
        if (owed !== undefined) {
          throw new Error(
            i18n(
              "queue.reply_missing",
              type_of(line[0]),
              this.thread,
              owed.id,
              owed.from,
            ),
          );
        }
        return;
      }
      this.reply_post(line, result as lines.Line, owed);
    }

    // Throws for a request the handler submitted and does not sleep on.
    private waits_check(
      line: lines.Line,
      run: HandlerRun,
      waits: Set<number>,
    ): void {
      for (const id of run.submitted.keys()) {
        if (!waits.has(id)) {
          throw new Error(
            i18n("queue.wait_missing", type_of(line[0]), this.thread, id),
          );
        }
      }
    }

    // Records a sleep on the requests its handler submitted, or wakes it.
    private sleep_start(
      line: lines.Line,
      run: HandlerRun,
      sleep: dispatch.Sleep,
      owed: Owed | undefined,
    ): void {
      const type = type_of(line[0]);
      const waits = new Set<number>();
      for (const id of sleep.wait_ids) {
        if (waits.has(id)) {
          throw new Error(i18n("queue.wait_twice", type, this.thread, id));
        }
        if (!run.submitted.has(id)) {
          throw new Error(i18n("queue.wait_unknown", type, this.thread, id));
        }
        waits.add(id);
      }
      this.waits_check(line, run, waits);
      const record: SleepRecord = {
        state: sleep.state,
        then_type: sleep.then_type,
        count: waits.size,
        replies: new Map<number, lines.Line>(),
        owed,
      };
      for (const [id, owner] of run.submitted) {
        this.pending.set(id, { owner, sleep: record });
      }
      this.sleeping += 1;
      this.log_write(
        "queue.sleep",
        utility.json_text(sleep.wait_ids),
        sleep.then_type,
      );
      if (record.count === 0) {
        this.wake_start(record);
      }
    }

    // Gives a reply to the sleep that waits for it, waking it at the last.
    private reply_receive(
      from: ThreadName,
      reply: number,
      line: lines.Line,
    ): void {
      const request = this.pending.get(reply);
      if (request === undefined || request.owner !== from) {
        throw new Error(
          i18n("queue.reply_unknown", this.thread, header_text(line), from),
        );
      }
      this.pending.delete(reply);
      this.log_write("queue.reply_received", from, header_text(line));
      const sleep = request.sleep;
      sleep.replies.set(reply, line);
      if (sleep.replies.size === sleep.count) {
        this.wake_start(sleep);
      }
    }

    // Holds the wake of a sleep: its state and its replies in submit order.
    private wake_start(sleep: SleepRecord): void {
      this.sleeping -= 1;
      const entries = [...sleep.replies.entries()].sort(
        (first, second) => first[0] - second[0],
      );
      const ids = entries.map((entry) => entry[0]);
      const replies = entries.map((entry) => entry[1]);
      const header = jslb.header_make(sleep.then_type);
      const line = jslb.line_make(header, [], { state: sleep.state, replies });
      this.log_write("queue.wake", sleep.then_type, utility.json_text(ids));
      const item = { line, from: this.thread, wake: true, owed: sleep.owed };
      this.item_push(item, true);
    }

    // Posts a reply line on the port of the request it answers, if owed.
    private reply_post(
      line: lines.Line,
      reply: lines.Line,
      owed: Owed | undefined,
    ): void {
      const answers = field_number(reply[0], constants.reply_field);
      if (owed === undefined || answers !== owed.id) {
        throw new Error(
          i18n(
            "queue.reply_unowed",
            type_of(line[0]),
            this.thread,
            header_text(reply),
          ),
        );
      }
      this.log_write("queue.reply", owed.from, header_text(reply));
      this.line_send(owed.from, reply);
    }

    // Sends the verbose lines kept since the last task, once a sink is in.
    private batch_flush(): void {
      const batch = this.batch;
      if (batch !== undefined) {
        batch.batch_send((line: lines.Line) => {
          this.line_notify(line);
        });
      }
    }

    // Writes one verbose line at level 2 with this thread as its first value.
    private log_write(name: string, ...values: unknown[]): void {
      verbose.log(constants.log_level, i18n(name, this.thread, ...values));
    }
  }
}

Object.freeze(queue);
