// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The task manager of one thread, the one synchronization tool: its ports,
// the owner table, one line dispatched at a time, sleeps and their wakes, the
// bound on the blob bytes it holds, the verbose sink of the thread, and in
// debug mode the trace of every submit, dispatch, sleep, wake and reply. Its
// message channel only turns a platform event into the next step.
//
// The blob bytes it holds are bounded by `blob_max`, the largest database: a
// held line counts the blobs it holds in memory, `line_bytes`, so a blob
// streamed to a cache file counts nothing and a database of `blob_max` with
// its cache files passes through as long as the lines' bytes are streamed.
//
// A handler's `dispatch.Failure` is answered first: its reply is posted, then
// the queue fails with its error. When that handler submitted requests it
// does not sleep on, the queue fails with `queue.wait_missing` whose `cause`
// is the failure's error, so the handler's own message is kept.
//
// An `error` line that reaches a queue stops it with `queue.error_line`,
// which names the line's `message` and `stack` and holds the line's own
// `cause` entries rebuilt as Errors under its `cause`, so the sender's
// cascade is kept whole. A wake line is built in the form
// `settings.names_full()` picks.

namespace queue {
  // The names and settings this module reads and writes.
  const constants = Object.freeze({
    error_type: "error",
    verbose_type: "verbose.put",
    type_field: "type",
    id_field: "id",
    reply_field: "reply",
    id_short: "i",
    full_marker: "type",
    debug_setting: "debug",
    line_setting: "line_max",
    limit_setting: "blob_max",
  });

  // The owners a line can have: the threads, the server and the ports.
  export type ThreadName =
    "ui" | "ai" | "server" | "http" | "media" | "console" | "dom";

  // A port carries lines one way each direction, in order.
  export interface Port {
    line_post(line: lines.Line, transfer: ArrayBuffer[]): void;
    line_receive(fn: (line: lines.Line) => void): void;
  }

  // Type prefix to owner, where the longest prefix that matches wins.
  export type OwnerTable = { [prefix: string]: ThreadName };

  // The request a task owes a reply to: its id and the port it came on.
  interface OwedRequest {
    id: number;
    from: ThreadName;
  }

  // A sleeping task: state, wake type, replies so far, their bytes, the debt.
  interface SleepRecord {
    state: unknown;
    then_type: string;
    count: number;
    replies: Map<number, lines.Line>;
    bytes: number;
    owed: OwedRequest | undefined;
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

  // A line held to run, the port it came on, what a wake owes, its bytes.
  interface HeldItem {
    line: lines.Line;
    from: ThreadName;
    wake: boolean;
    owed: OwedRequest | undefined;
    bytes: number;
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

  // The bytes of the JSON text of a value in `UTF-8`.
  function json_bytes(value: unknown): number {
    return utility.utf8_encode(utility.json_text(value)).length;
  }

  // Says whether a handler result is a sleep, by its three fields.
  function sleep_is(result: object): result is dispatch.Sleep {
    return "state" in result && "wait_ids" in result && "then_type" in result;
  }

  // Says whether a handler result is a failure: its own reply and error.
  function failure_is(result: object): result is dispatch.Failure {
    return (
      Object.hasOwn(result, "reply") &&
      Object.hasOwn(result, "error") &&
      !Object.hasOwn(result, "0")
    );
  }

  // Rebuilds an entry of a received cascade, and those under it, as Errors.
  function cause_read(entry: lines.ErrorCause): Error {
    const error =
      entry.cause === undefined
        ? new Error(entry.message)
        : new Error(entry.message, { cause: cause_read(entry.cause) });
    error.stack = entry.stack;
    return error;
  }

  // The blob headers of a line, 1 on.
  function blobs_of(line: lines.Line): lines.BlobHeader[] {
    return jslb.headers_of(line).slice(1) as lines.BlobHeader[];
  }

  // The blob bytes a held line counts: its blobs whose `d` is bytes.
  export function line_bytes(line: lines.Line): number {
    let bytes = 0;
    for (const blob of blobs_of(line)) {
      const data = blob.d;
      if (data instanceof Uint8Array) {
        bytes += data.length;
      }
    }
    return bytes;
  }

  // A `verbose.put` of the thread holding the lines given, in full names.
  function put_make(
    thread: "ui" | "ai",
    entries: lines.VerboseLine[],
  ): lines.Line {
    const header = jslb.header_make(constants.verbose_type, { full: true });
    return jslb.line_make(header, [], { thread, lines: entries });
  }

  // Whether an entry of `size` bytes in a `verbose.put` of `empty` bytes with
  // no entries is below `line_max`: the one comparison of an entry alone.
  function alone_fits(empty: number, size: number, line_max: number): boolean {
    return empty + size < line_max;
  }

  // Whether a verbose line of the text fits one `verbose.put` of the thread.
  export function entry_fits(
    thread: "ui" | "ai",
    text: string,
    line_max: number,
  ): boolean {
    const empty = json_bytes(put_make(thread, []));
    const size = json_bytes({ at: utility.time_now(), text });
    return alone_fits(empty, size, line_max);
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

  // The verbose lines of a thread waiting to go out as `verbose.put` lines.
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

    // Posts the kept lines in order as `verbose.put` lines below `line_max`.
    batch_send(post: (line: lines.Line) => void): void {
      if (this.kept.length === 0) {
        return;
      }
      const groups = this.groups_split();
      this.kept = [];
      this.sending = true;
      for (const group of groups) {
        post(put_make(this.thread, group));
      }
      this.sending = false;
    }

    // Whether the setting `debug` is true, which alone turns forwarding on.
    private forward_on(): boolean {
      return this.settings_get(constants.debug_setting) === true;
    }

    // Splits the kept lines into groups whose `verbose.put` fits `line_max`.
    private groups_split(): lines.VerboseLine[][] {
      const limit = this.settings_get(constants.line_setting) as number;
      const empty = json_bytes(put_make(this.thread, []));
      const groups: lines.VerboseLine[][] = [];
      let group: lines.VerboseLine[] = [];
      // The bytes of the group's line: the empty line, each entry, the commas.
      let bytes = empty;
      for (const entry of this.kept) {
        const size = json_bytes(entry);
        if (!alone_fits(empty, size, limit)) {
          throw new Error(
            i18n("queue.entry_over", this.thread, empty + size, limit),
          );
        }
        if (group.length > 0 && bytes + 1 + size >= limit) {
          groups.push(group);
          group = [];
          bytes = empty;
        }
        bytes += group.length > 0 ? size + 1 : size;
        group.push(entry);
      }
      groups.push(group);
      return groups;
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
    private held_bytes = 0;
    private draining = false;
    private scheduled = false;
    private current: HandlerRun | undefined;
    private batch: VerboseBatch | undefined;
    private settings_get: ((id: string) => unknown) | undefined;
    private fault: Error | undefined;

    // Takes the thread, its owner table and the mode, and adds its own port.
    constructor(thread: ThreadName, owners: OwnerTable, synchronous: boolean) {
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
      this.log_write(
        i18n("queue.submit", this.thread, target, header_text(line)),
      );
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
      this.log_write(
        i18n("queue.notify", this.thread, target, header_text(line)),
      );
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
      this.log_write(
        i18n("queue.forward", this.thread, owner, header_text(line)),
      );
      this.line_send(owner, line);
    }

    // The number of tasks waiting, running and sleeping.
    depth(): number {
      const running = this.current === undefined ? 0 : 1;
      return this.local.length + this.inbox.length + running + this.sleeping;
    }

    // Installs the verbose sink and the settings that bound and trace it.
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
      this.settings_get = settings_get;
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

    // Counts and holds a line that came on a port and starts the tasks.
    private line_arrive(from: ThreadName, line: lines.Line): void {
      this.fault_check();
      const bytes = this.hold_take(line);
      const item = { line, from, wake: false, owed: undefined, bytes };
      this.item_push(item, from === this.thread);
      this.run_start();
    }

    // Counts the blob bytes of a line to hold, a fault when past `blob_max`.
    private hold_take(line: lines.Line): number {
      try {
        const bytes = line_bytes(line);
        this.limit_check(line, bytes);
        this.held_bytes += bytes;
        return bytes;
      } catch (error) {
        return this.fault_stop(error);
      }
    }

    // Throws when the blob bytes held would pass `blob_max`, once it is read.
    private limit_check(line: lines.Line, bytes: number): void {
      const settings_get = this.settings_get;
      if (settings_get === undefined) {
        return;
      }
      const limit = settings_get(constants.limit_setting) as number;
      if (this.held_bytes + bytes > limit) {
        throw new Error(
          i18n(
            "queue.queue_over",
            this.thread,
            header_text(line),
            bytes,
            this.held_bytes,
            limit,
          ),
        );
      }
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
      const item = this.item_next() as HeldItem;
      this.item_run(item);
      if (this.inbox.length > 0) {
        this.step_schedule();
      }
    }

    // The next held item, its own ones first.
    private item_next(): HeldItem | undefined {
      return this.local.shift() ?? this.inbox.shift();
    }

    // Runs one item, then sends the verbose batch, unsent after a fault.
    private item_run(item: HeldItem): void {
      try {
        this.item_route(item);
        this.batch_flush();
      } catch (error) {
        this.fault_stop(error);
      }
    }

    // Keeps the fault that stops this queue, no task running, and throws it.
    private fault_stop(error: unknown): never {
      this.current = undefined;
      this.fault = error as Error;
      throw error;
    }

    // Throws once a fault has stopped this queue, with its message and stack.
    private fault_check(): void {
      const fault = this.fault;
      if (fault !== undefined) {
        throw utility.error_wrap(
          i18n("queue.stopped", this.thread, fault.message, fault.stack),
          fault,
        );
      }
    }

    // Runs a wake or routes an input, and a line posted here always runs here.
    private item_route(item: HeldItem): void {
      const { line, from } = item;
      if (item.wake) {
        this.held_bytes -= item.bytes;
        this.task_run(line, from, item.owed);
        return;
      }
      const header = line[0];
      const type = type_of(header);
      if (type === constants.error_type) {
        const payload = jslb.payload_of(line) as unknown as lines.ErrorLine;
        const message = i18n(
          "queue.error_line",
          this.thread,
          from,
          payload.message,
          payload.stack,
        );
        if (payload.cause === undefined) {
          throw new Error(message);
        }
        throw new Error(message, { cause: cause_read(payload.cause) });
      }
      const reply = field_number(header, constants.reply_field);
      if (reply !== undefined) {
        this.reply_receive(from, reply, line, item.bytes);
        return;
      }
      this.held_bytes -= item.bytes;
      const owner = from === this.thread ? from : this.owner_find(type);
      if (owner === this.thread) {
        const id = field_number(header, constants.id_field);
        this.task_run(line, from, id === undefined ? undefined : { id, from });
        return;
      }
      if (owner === from) {
        throw new Error(
          i18n("queue.forward_back", this.thread, header_text(line), from),
        );
      }
      this.line_forward(line);
    }

    // Runs the handler of a line and takes what it returns.
    private task_run(
      line: lines.Line,
      from: ThreadName,
      owed: OwedRequest | undefined,
    ): void {
      this.log_write(
        i18n("queue.dispatch", this.thread, from, header_text(line)),
      );
      const run: HandlerRun = { submitted: new Map<number, ThreadName>() };
      this.current = run;
      const result = dispatch.line_dispatch(line);
      this.current = undefined;
      this.result_take(line, run, result, owed);
    }

    // Starts a sleep, posts a reply, fails after a failure's reply is posted,
    // or checks that nothing was owed.
    private result_take(
      line: lines.Line,
      run: HandlerRun,
      result: dispatch.Reply | dispatch.Sleep | dispatch.Failure,
      owed: OwedRequest | undefined,
    ): void {
      if (result !== undefined && sleep_is(result)) {
        this.sleep_start(line, run, result, owed);
        return;
      }
      if (result !== undefined && failure_is(result)) {
        return this.failure_raise(line, run, result, owed);
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

    // Posts a failure's reply, then throws its error, under the first request
    // the handler submitted when it submitted any, as it sleeps on none.
    private failure_raise(
      line: lines.Line,
      run: HandlerRun,
      failure: dispatch.Failure,
      owed: OwedRequest | undefined,
    ): never {
      this.reply_post(line, failure.reply, owed);
      if (run.submitted.size > 0) {
        const [first] = run.submitted.keys();
        throw new Error(
          i18n("queue.wait_missing", type_of(line[0]), this.thread, first),
          { cause: failure.error },
        );
      }
      throw failure.error;
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
      owed: OwedRequest | undefined,
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
        bytes: 0,
        owed,
      };
      for (const [id, owner] of run.submitted) {
        this.pending.set(id, { owner, sleep: record });
      }
      this.sleeping += 1;
      this.log_write(
        i18n(
          "queue.sleep",
          this.thread,
          utility.json_text(sleep.wait_ids),
          sleep.then_type,
        ),
      );
      if (record.count === 0) {
        this.wake_start(record);
      }
    }

    // Gives a reply and its bytes to the sleep that waits, waking it at last.
    private reply_receive(
      from: ThreadName,
      reply: number,
      line: lines.Line,
      bytes: number,
    ): void {
      const request = this.pending.get(reply);
      if (request === undefined || request.owner !== from) {
        throw new Error(
          i18n("queue.reply_unknown", this.thread, header_text(line), from),
        );
      }
      this.pending.delete(reply);
      this.log_write(
        i18n("queue.reply_received", this.thread, from, header_text(line)),
      );
      const sleep = request.sleep;
      sleep.replies.set(reply, line);
      sleep.bytes += bytes;
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
      const header = jslb.header_make(sleep.then_type, {
        full: settings.names_full(),
      });
      const line = jslb.line_make(header, [], { state: sleep.state, replies });
      this.log_write(
        i18n(
          "queue.wake",
          this.thread,
          sleep.then_type,
          utility.json_text(ids),
        ),
      );
      const item = {
        line,
        from: this.thread,
        wake: true,
        owed: sleep.owed,
        bytes: sleep.bytes,
      };
      this.item_push(item, true);
    }

    // Posts a reply line on the port of the request it answers, if owed.
    private reply_post(
      line: lines.Line,
      reply: lines.Line,
      owed: OwedRequest | undefined,
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
      this.log_write(
        i18n("queue.reply", this.thread, owed.from, header_text(reply)),
      );
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

    // Writes one line of the thread's timeline once the settings say debug.
    private log_write(text: string): void {
      const settings_get = this.settings_get;
      if (
        settings_get !== undefined &&
        settings_get(constants.debug_setting) === true
      ) {
        verbose.log(text);
      }
    }
  }
}

Object.freeze(queue);
