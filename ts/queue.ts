// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The task manager of one thread, the one synchronization tool.
// API/ts/queue.d.ts holds its rules. Its message channel only turns a platform
// event into the next step.

namespace queue {
  // The names and settings this module reads and writes.
  const constants = Object.freeze({
    error_type: "error",
    type_field: "type",
    id_field: "id",
    reply_field: "reply",
    id_short: "i",
    full_marker: "type",
    limit_setting: "blob_max",
    // The two credentials the audit never holds, and what shows for them.
    http_type: "http.request",
    key_header: "Authorization",
    open_type: "console.open",
    token_field: "token",
    mask_text: "<masked>",
    // The audit's own types, never recorded, and the owners that are no queue.
    audit_prefix: "audit.",
    audit_line: "audit.line",
    audit_note: "audit.note",
    server_owner: "server",
    port_owners: Object.freeze(["http", "media", "console", "dom"]),
    id_gap: ", ",
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

  // The audit of a queue: whether it posts, and the lines held until it does.
  interface AuditRecord {
    open: boolean;
    held: lines.Line[];
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

  // The header of a line as JSON text, for messages.
  function header_text(line: lines.Line): string {
    return utility.json_text(line[0]);
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

  // A copy of the object with the field masked, the object itself without it.
  function field_masked<Holder extends object>(
    holder: Holder,
    name: string,
  ): Holder {
    return Object.hasOwn(holder, name)
      ? { ...holder, [name]: constants.mask_text }
      : holder;
  }

  // The line the audit records, a copy when a credential of it is masked.
  function line_masked(line: lines.Line): lines.Line {
    const type = type_of(line[0]);
    if (type === constants.open_type) {
      return field_masked(line, constants.token_field);
    }
    if (type === constants.http_type && line.headers !== undefined) {
      const headers = line.headers as object;
      return {
        ...line,
        headers: field_masked(headers, constants.key_header),
      };
    }
    return line;
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

  // Same thread: a posted line goes as it is to the receiver of the far end.
  export class LocalPort implements Port {
    private receiver: ((line: lines.Line) => void) | undefined;
    private far: LocalPort;

    // Links the port given back to this one as its far end, else is its own.
    constructor(far?: LocalPort) {
      if (far === undefined) {
        this.far = this;
        return;
      }
      if (far.far !== far) {
        throw new Error(i18n("queue.port_linked"));
      }
      far.far = this;
      this.far = far;
    }

    // Hands the line on, as the queue moved its blob bytes before the post.
    line_post(line: lines.Line, _transfer: ArrayBuffer[]): void {
      const receiver = this.far.receiver;
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
    private settings_get: ((id: string) => unknown) | undefined;
    private audit: AuditRecord | undefined;
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
      this.line_send(owner, line);
    }

    // The number of tasks waiting, running and sleeping.
    depth(): number {
      const running = this.current === undefined ? 0 : 1;
      return this.local.length + this.inbox.length + running + this.sleeping;
    }

    // Installs the reader of the settings whose `blob_max` bounds what it holds.
    limit_attach(settings_get: (id: string) => unknown): void {
      if (this.settings_get !== undefined) {
        throw new Error(i18n("queue.limit_twice", this.thread));
      }
      this.settings_get = settings_get;
    }

    // Records lines and notes sleeps as API/ts/queue.d.ts says, held.
    audit_attach(): void {
      if (this.audit !== undefined) {
        throw new Error(i18n("queue.audit_twice", this.thread));
      }
      if (this.owner_find(constants.audit_line) === this.thread) {
        throw new Error(i18n("queue.audit_owner", this.thread));
      }
      this.audit = { open: false, held: [] };
    }

    // Posts the held records and notes in order, and each later one at once.
    audit_open(): void {
      const audit = this.audit;
      if (audit === undefined || audit.open) {
        throw new Error(i18n("queue.audit_closed", this.thread));
      }
      audit.open = true;
      for (const line of audit.held.splice(0)) {
        this.audit_post(line);
      }
    }

    // Posts a line of the audit on the port of its owner, or holds it.
    private audit_post(line: lines.Line): void {
      const audit = this.audit as AuditRecord;
      if (!audit.open) {
        audit.held.push(line);
        return;
      }
      const owner = this.owner_find(constants.audit_line);
      const port = this.ports.get(owner);
      if (port === undefined) {
        throw new Error(i18n("queue.port_missing", this.thread, owner));
      }
      port.line_post(line, buffers_of(arrays_of(line)));
    }

    // Records a line between two owners, its credentials masked, if audited.
    private record_make(
      sender: ThreadName,
      receiver: ThreadName,
      line: lines.Line,
    ): void {
      if (
        this.audit === undefined ||
        type_of(line[0]).startsWith(constants.audit_prefix)
      ) {
        return;
      }
      const text = jslb.line_json(line_masked(line));
      const header = jslb.header_make(constants.audit_line, {
        full: settings.names_full(),
      });
      const blob = jslb.blob_make(utility.utf8_encode(text));
      const at = utility.time_now();
      this.audit_post(
        jslb.line_make(header, [blob], { sender, receiver, at }),
      );
    }

    // Notes a sleep by its replies' ids and its wake, unless the audit's own.
    private sleep_note(sleep: dispatch.Sleep): void {
      if (
        this.audit === undefined ||
        sleep.then_type.startsWith(constants.audit_prefix)
      ) {
        return;
      }
      const ids = sleep.wait_ids.join(constants.id_gap);
      const header = jslb.header_make(constants.audit_note, {
        full: settings.names_full(),
      });
      const payload = {
        thread: this.thread,
        at: utility.time_now(),
        text: i18n("queue.sleep_note", ids, sleep.then_type),
      };
      this.audit_post(jslb.line_make(header, [], payload));
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
      if (thread !== constants.server_owner) {
        this.record_make(this.thread, thread, line);
      }
      port.line_post(line, buffers_of(arrays_of(line)));
    }

    // Counts and holds a line that came on a port and starts the tasks.
    private line_arrive(from: ThreadName, line: lines.Line): void {
      this.fault_check();
      if (constants.port_owners.includes(from)) {
        this.audit_take(from, line);
      }
      const bytes = this.hold_take(line);
      const item = { line, from, wake: false, owed: undefined, bytes };
      this.item_push(item, from === this.thread);
      this.run_start();
    }

    // Records a line a port sent, a fault stopping the queue.
    private audit_take(from: ThreadName, line: lines.Line): void {
      try {
        this.record_make(from, this.thread, line);
      } catch (error) {
        this.fault_stop(error);
      }
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

    // Runs one item, a throw stopping the queue.
    private item_run(item: HeldItem): void {
      try {
        this.item_route(item);
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
        this.task_run(line, from, item.owed, true);
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
        const owed = id === undefined ? undefined : { id, from };
        this.task_run(line, from, owed, false);
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
      wake: boolean,
    ): void {
      const run: HandlerRun = { submitted: new Map<number, ThreadName>() };
      this.current = run;
      const result = dispatch.line_dispatch(line);
      this.current = undefined;
      this.result_take(line, run, result, owed, wake);
    }

    // Sleeps, posts a reply, fails after a failure's, or checks nothing owed.
    private result_take(
      line: lines.Line,
      run: HandlerRun,
      result: dispatch.Reply | dispatch.Sleep | dispatch.Failure,
      owed: OwedRequest | undefined,
      wake: boolean,
    ): void {
      if (result !== undefined && sleep_is(result)) {
        this.sleep_start(line, run, result, owed, wake);
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

    // Posts a failure's reply, then throws under the handler's first request.
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
      wake: boolean,
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
      this.sleep_note(sleep);
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
      const replies = entries.map((entry) => entry[1]);
      const header = jslb.header_make(sleep.then_type, {
        full: settings.names_full(),
      });
      const line = jslb.line_make(header, [], { state: sleep.state, replies });
      const item = {
        line,
        from: this.thread,
        wake: true,
        owed: sleep.owed,
        bytes: sleep.bytes,
      };
      // The wake takes its reply's place, before what came after the reply.
      if (this.synchronous) {
        this.local.push(item);
      } else {
        this.inbox.unshift(item);
      }
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
      this.line_send(owed.from, reply);
    }
  }
}

Object.freeze(queue);
