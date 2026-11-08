// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The producer of the wire test, run on the AI worker when the gold's
// `typescript.test_all.run` is "wire"; python/test_wire.py is its consumer.
// TypeScript's `unittest` is synchronous and a rung waits on the network, so a
// rung is a task chain on the worker's queue: `rungs.next`, a push of the
// worker to itself, runs the next rung.
//
// The console and lines rungs drive their own `wire.ConsolePort`, since the
// worker's owner table routes `console.output` to the UI thread, which runs
// nothing in a wire run. The first failed check writes its `not ok` point,
// then `Bail out!`, and the chain stops: the failure is reported in the
// stream, not thrown on. After its last push the restart rung posts the gold's
// `restart_after`, a TAP comment that the port holds, so that a post the port
// let through would reach the restarted server before the page's refusal of
// its `tap.start`. A rung the gold's `held_rungs` names is held until the
// driver releases it on the gold's `release_channel`, so that the driver reads
// the server before it execs.

namespace test_wire_rungs {
  // The gold's id, the stream's text, the line types, owners and kinds.
  const constants = Object.freeze({
    gold_id: "typescript.test_wire_rungs",
    module_name: "test_wire_rungs",
    blob_setting: "blob_max",
    version_line: "TAP version 14",
    block_indent: "    ",
    bail_prefix: "Bail out! ",
    line_type: "tap.line",
    language: "typescript" as const,
    next_type: "rungs.next",
    reply_type: "rungs.reply",
    handler_version: 0,
    self_owner: "ai" as const,
    server_owner: "server" as const,
    first_type: "tap.start",
    first_id: 101,
    first_keys: Object.freeze(["settings", "switches"]),
    echo_type: "echo",
    tail_type: "audit.tail",
    record_type: "audit.line",
    note_type: "audit.note",
    sync_type: "db.sync",
    restore_type: "db.restore",
    file_type: "db.file",
    source_type: "source.put",
    restart_type: "system.restart",
    open_type: "console.open",
    input_type: "console.input",
    socket_path: "ws",
    socket_scheme: "ws:",
    subprotocol: "tty",
    close_normal: 1000,
    console_port: "console",
    output_kind: 0x30,
    input_kind: 0x30,
    byte_values: 256,
    line_end: "\r\n",
    command_end: "\n",
    text_type: "text",
    mcp_name: "test_wire_rungs",
    mcp_version: "1",
    second_ms: 1000,
    // The rungs that end the session, which must be the last of a run.
    ending_rungs: Object.freeze(["unknown", "restart"]),
  });

  // One push line of the commits rung, as the gold lists it.
  interface CommitEntry {
    type: string;
    key?: string;
    text?: string;
    payload?: { [key: string]: unknown };
  }

  // The tool call of the mcp rung, as the gold names it.
  interface McpCall {
    name: string;
    arguments: { [key: string]: unknown };
  }

  // The size of tty 0 that the first message of the console gives.
  interface ConsoleSize {
    columns: number;
    rows: number;
  }

  // What a rung's sleep keeps: the rung and the step its replies answer.
  interface RungState {
    rung: string;
    step: string;
  }

  // A failed check, written as the rung's `not ok` point, never thrown on.
  class RungFailure extends Error {}

  // Fails the rung with the reason unless the condition holds.
  function check(condition: boolean, reason: string): void {
    if (!condition) {
      throw new RungFailure(reason);
    }
  }

  // A value of this module's gold, which must be there.
  function gold_value(name: string): unknown {
    return harness.gold_get(`${constants.gold_id}.${name}`);
  }

  // Sends one line of the stream at once, as a `tap.line` to its owner.
  function line_send(tasks: queue.TaskQueue, text: string): void {
    const header = jslb.header_make(constants.line_type, {
      full: settings.names_full(),
    });
    const payload = { language: constants.language, text };
    tasks.line_notify(jslb.line_make(header, [], payload));
  }

  // A line of the type in this thread's name form, its blobs and payload.
  function line_build(
    type: string,
    blobs: lines.BlobHeader[],
    payload: { [key: string]: unknown },
  ): lines.Line {
    const header = jslb.header_make(type, { full: settings.names_full() });
    return jslb.line_make(header, blobs, payload);
  }

  // Bytes of the size given, byte i being i modulo 256.
  function bytes_counted(size: number): Uint8Array {
    const data = new Uint8Array(size);
    for (let index = 0; index < size; index += 1) {
      data[index] = index % constants.byte_values;
    }
    return data;
  }

  // Bytes of the size given, the digests of the numbers, which do not repeat.
  function bytes_varied(size: number): Uint8Array {
    let text = "";
    for (let number = 0; text.length < size; number += 1) {
      text += utility.sha256_hex(utility.utf8_encode(String(number)));
    }
    return utility.utf8_encode(text.slice(0, size));
  }

  // A message of ttyd's client: the kind byte, then the text as `UTF-8`.
  function message_make(kind: number, text: string): Uint8Array {
    const body = utility.utf8_encode(text);
    const message = new Uint8Array(body.length + 1);
    message[0] = kind;
    message.set(body, 1);
    return message;
  }

  // The blob headers of a line, 1 on.
  function blobs_of(line: lines.Line): lines.BlobHeader[] {
    return jslb.headers_of(line).slice(1) as lines.BlobHeader[];
  }

  // The digest of a reply's blob: the sink's when streamed, else its bytes'.
  function blob_digest(blob: lines.BlobHeader): unknown {
    const data = jslb.field_get(blob, "data");
    if (typeof data === "string") {
      return blob.sha256;
    }
    return utility.sha256_hex(data as Uint8Array);
  }

  // The type of a line.
  function type_of(line: lines.Line): unknown {
    return jslb.field_get(line[0], "type");
  }

  // One drive of tty 0 by its own port: opened, its first message, a typing.
  class ConsoleRun {
    // The output since the typing, its bytes, and the time of the typing.
    after = "";
    after_bytes = 0;
    typed_at = 0;
    readonly #port: wire.ConsolePort;
    readonly #prompt: string;
    readonly #typing: string;
    readonly #size: ConsoleSize;
    readonly #after_take: () => void;
    readonly #decoder = new TextDecoder("utf-8", { fatal: true });
    // The output before the typing, and whether the typing was sent.
    #before = "";
    #typed = false;

    // Opens tty 0, then types `typing` once the output ends with the prompt.
    constructor(
      base_url: string,
      prompt: string,
      typing: string,
      after_take: () => void,
      close_take: (code: number) => void,
    ) {
      this.#prompt = prompt;
      this.#typing = typing;
      this.#size = gold_value("console_size") as ConsoleSize;
      this.#after_take = after_take;
      this.#port = new wire.ConsolePort(base_url);
      this.#port.line_receive((line) => this.#line_take(line));
      this.#port.close_receive(close_take);
      const header = jslb.header_make(constants.open_type, {
        id: dispatch.id_next(constants.console_port),
        full: settings.names_full(),
      });
      this.#port.line_post(jslb.line_make(header, [], {}), []);
    }

    // Ends tty 0, whose end the close function hears.
    console_close(): void {
      this.#port.console_close();
    }

    // Takes the answer to the opening, or one message of tty 0's output.
    #line_take(line: lines.Line): void {
      if (type_of(line) === constants.open_type) {
        const token = jslb.payload_of(line).token;
        const text = utility.json_text({
          AuthToken: token,
          columns: this.#size.columns,
          rows: this.#size.rows,
        });
        this.#input_post(utility.utf8_encode(text));
        return;
      }
      const blob = line[1] as lines.BlobHeader;
      const data = jslb.field_get(blob, "data") as Uint8Array;
      // The title and the preferences are not output.
      if (data[0] !== constants.output_kind) {
        return;
      }
      const text = this.#decoder.decode(data.subarray(1), { stream: true });
      if (this.#typed) {
        this.after += text;
        this.after_bytes += data.length - 1;
        this.#after_take();
        return;
      }
      this.#before += text;
      if (this.#before.endsWith(this.#prompt)) {
        this.#typed = true;
        this.typed_at = utility.time_now();
        this.#input_post(message_make(constants.input_kind, this.#typing));
      }
    }

    // Sends one message of ttyd's client to tty 0.
    #input_post(message: Uint8Array): void {
      const blob = jslb.blob_make(message);
      this.#port.line_post(line_build(constants.input_type, [blob], {}), []);
    }
  }

  // The chain of the rungs: the stream's block, the rung running, its steps.
  class RungChain {
    readonly #tasks: queue.TaskQueue;
    readonly #start: boot.WorkerStart;
    readonly #names: string[];
    readonly #block: tap_producer.Tracker;
    readonly #parent: tap_producer.Tracker;
    // What each rung runs first, by its gold name.
    readonly #starts: { [name: string]: () => dispatch.Sleep | undefined };
    // What each step of a sleeping rung does with its replies.
    readonly #steps: {
      [step: string]: (
        rung: string,
        replies: lines.Line[],
      ) => dispatch.Sleep | undefined;
    };
    // The rung running, as an index of the names.
    #index = 0;
    // Set by the first failed check, after which nothing more is written.
    #stopped = false;
    // The rung held until the driver releases it, if any.
    #held: string | undefined = undefined;
    // The size and digest of the blob the last blob echo sent.
    #sent_size = 0;
    #sent_sha256 = "";
    // The client of the mcp rung.
    #client: mcp.Client | undefined = undefined;
    // The restore and file lines of the sync, in the order they came.
    readonly #sync_lines: lines.Line[] = [];
    // When the rungs started, and when the rung running started.
    readonly #chain_started = performance.now();
    #rung_started = 0;

    // Takes the queue, the start, and the rungs, checked before any line.
    constructor(
      tasks: queue.TaskQueue,
      start: boot.WorkerStart,
      names: unknown,
    ) {
      this.#tasks = tasks;
      this.#start = start;
      this.#block = new tap_producer.Tracker((text) =>
        line_send(tasks, constants.block_indent + text),
      );
      this.#parent = new tap_producer.Tracker((text) =>
        line_send(tasks, text),
      );
      this.#starts = {
        first: () => this.#first_run(),
        echo: () => this.#echo_run(),
        extensions: () => this.#extensions_run(),
        control: () => this.#blob_run("control", gold_value("control_bytes")),
        // The same frame twice, which ended a ttyd that offered compression.
        repeat: () => this.#repeat_run("repeat"),
        repeated: () => this.#repeat_run("repeated"),
        fit: () =>
          this.#blob_run("fit", harness.setting_get(constants.blob_setting)),
        mcp: () => this.#mcp_run(),
        sync: () => this.#sync_run(),
        commits: () => this.#commits_run(),
        audit: () => this.#audit_run(),
        console: () => this.#console_run(),
        lines: () => this.#lines_run(),
        unknown: () => this.#unknown_run(),
        restart: () => this.#restart_run(),
      };
      this.#steps = {
        echo: (rung, replies) => this.#echo_take(rung, replies),
        blob: (rung, replies) => this.#blob_take(rung, replies),
        initialize: (rung, replies) => this.#initialize_take(rung, replies),
        call: (rung, replies) => this.#call_take(rung, replies),
        sync: (rung, replies) => this.#sync_take(rung, replies),
        audit: (rung, replies) => this.#audit_take(rung, replies),
        restart: (rung, replies) => this.#restart_take(rung, replies),
      };
      this.#names = this.#names_check(names);
    }

    // Writes the block's plan, one point per rung.
    plan_write(): void {
      this.#block.set_plan(this.#names.length);
    }

    // Notifies `rungs.next` to this thread, which runs the next rung.
    next_notify(): void {
      const line = line_build(constants.next_type, [], {});
      this.#tasks.line_notify(line, constants.self_owner);
    }

    // Runs the next rung, or holds it when the gold names it held.
    rung_follow(): void {
      this.#rung_started = performance.now();
      const rung = this.#names[this.#index];
      const held = gold_value("held_rungs") as string[];
      if (held.includes(rung)) {
        this.#held = rung;
        return;
      }
      this.next_notify();
    }

    // The driver's release of the held rung, which then runs.
    release_take(data: unknown): void {
      const rung = this.#held ?? this.#names[this.#index];
      this.#guard(rung, () => {
        check(
          this.#held !== undefined && data === this.#held,
          `the driver released ${String(data)} while ${String(this.#held)}` +
            " was held",
        );
        this.#held = undefined;
        this.next_notify();
        return undefined;
      });
    }

    // The handler of `rungs.next`: runs the next rung.
    next_take(): dispatch.Sleep | undefined {
      const rung = this.#names[this.#index];
      return this.#guard(rung, this.#starts[rung]);
    }

    // The handler of `rungs.reply`: the step of the rung its state names.
    reply_take(wake: lines.Line): dispatch.Sleep | undefined {
      const state = wake.state as RungState;
      const replies = wake.replies as lines.Line[];
      const step = this.#steps[state.step];
      return this.#guard(state.rung, () => step(state.rung, replies));
    }

    // The handler of `db.restore` and `db.file`: keeps the line for the rung.
    sync_keep(line: lines.Line): undefined {
      this.#sync_lines.push(line);
      return undefined;
    }

    // The rung names, each one of a rung, a session's end only last.
    #names_check(names: unknown): string[] {
      if (
        !Array.isArray(names) ||
        names.length === 0 ||
        !names.every((name) => typeof name === "string")
      ) {
        throw new Error(
          `the gold's rungs ${String(names)} are not a list of rung names`,
        );
      }
      for (let index = 0; index < names.length; index += 1) {
        const name = names[index] as string;
        if (!Object.hasOwn(this.#starts, name)) {
          throw new Error(`the gold names ${name}, which is not a rung`);
        }
        const last = index === names.length - 1;
        if (constants.ending_rungs.includes(name) && !last) {
          throw new Error(`the rung ${name} ends the session but is not last`);
        }
      }
      return names as string[];
    }

    // Runs a step of a rung, a failed check written as its point.
    #guard(
      rung: string,
      fn: () => dispatch.Sleep | undefined,
    ): dispatch.Sleep | undefined {
      // A console port may still call after the chain stopped.
      if (this.#stopped) {
        return undefined;
      }
      try {
        return fn();
      } catch (error) {
        if (!(error instanceof RungFailure)) {
          throw error;
        }
        this.#fail(rung, error);
        return undefined;
      }
    }

    // Writes the failed point and the bail out, and stops the chain.
    #fail(rung: string, error: Error): void {
      const diagnostics = `${error.message}\n${error.stack ?? ""}`;
      const duration_ms = performance.now() - this.#rung_started;
      this.#block.add_not_ok(rung, rung, duration_ms, "", diagnostics);
      line_send(this.#tasks, constants.bail_prefix + rung);
      this.#stopped = true;
    }

    // Writes the passing point, then runs on: the next rung, or the end.
    #pass(rung: string, diagnostics?: string): undefined {
      const duration_ms = performance.now() - this.#rung_started;
      this.#block.add_ok(rung, rung, duration_ms, "", diagnostics);
      this.#index += 1;
      if (this.#index < this.#names.length) {
        this.rung_follow();
        return undefined;
      }
      this.#parent.add_ok(
        constants.module_name,
        constants.module_name,
        performance.now() - this.#chain_started,
      );
      this.#parent.generate_tap_reports();
      return undefined;
    }

    // Submits a request to the server and sleeps on it for the step given.
    #submit(rung: string, step: string, line: lines.Line): dispatch.Sleep {
      const id = this.#tasks.task_submit(line, constants.server_owner);
      const state: RungState = { rung, step };
      return dispatch.task_sleep(state, [id], constants.reply_type);
    }

    // The one reply of a step, which must be of the type given.
    #reply_one(replies: lines.Line[], type: string): lines.Line {
      check(replies.length === 1, `${replies.length} replies came, not 1`);
      const reply = replies[0];
      check(
        type_of(reply) === type,
        `the reply is a ${String(type_of(reply))} line, not ${type}`,
      );
      return reply;
    }

    // first: `tap.start` in full names, id 101, its settings and gold.
    #first_run(): undefined {
      const first = this.#start.first;
      check(
        Object.hasOwn(first[0], "type"),
        "the first line is not in full names",
      );
      check(
        type_of(first) === constants.first_type,
        `the first line is ${String(type_of(first))}, not tap.start`,
      );
      const id = jslb.field_get(first[0], "id");
      check(id === constants.first_id, `the first line's id is ${String(id)}`);
      check(
        !Object.hasOwn(first[0], "reply"),
        "the first line answers a line",
      );
      check(blobs_of(first).length === 0, "the first line has blobs");
      const payload = jslb.payload_of(first);
      const keys = utility.json_text(Object.keys(payload).sort());
      check(
        keys === utility.json_text([...constants.first_keys]),
        `the first line's payload has the keys ${keys}`,
      );
      return this.#pass("first");
    }

    // echo: an `echo` line comes back equal.
    #echo_run(): dispatch.Sleep {
      const payload = gold_value("echo_payload") as { [key: string]: unknown };
      const line = line_build(constants.echo_type, [], payload);
      return this.#submit("echo", "echo", line);
    }

    // The echo's reply: no blob, the payload sent.
    #echo_take(rung: string, replies: lines.Line[]): undefined {
      const reply = this.#reply_one(replies, constants.echo_type);
      check(blobs_of(reply).length === 0, "the echo's reply has blobs");
      const sent = utility.json_text(gold_value("echo_payload"));
      const came = utility.json_text(jslb.payload_of(reply));
      check(came === sent, `the echo's payload is ${came}, not ${sent}`);
      return this.#pass(rung);
    }

    // extensions: a socket of its own sends nothing, so no program starts.
    #extensions_run(): undefined {
      const url = new URL(constants.socket_path, this.#start.base_url);
      url.protocol = constants.socket_scheme;
      const socket = new WebSocket(url.href, constants.subprotocol);
      let negotiated: string | undefined = undefined;
      socket.addEventListener("open", () => {
        negotiated = socket.extensions;
        socket.close(constants.close_normal);
      });
      socket.addEventListener("close", () => {
        this.#guard("extensions", () => {
          check(
            negotiated === "",
            `ttyd negotiated the extensions ${String(negotiated)}`,
          );
          return this.#pass("extensions");
        });
      });
      return undefined;
    }

    // repeat and repeated: the bytes of the gold's size, echoed.
    #repeat_run(rung: string): dispatch.Sleep {
      const size = gold_value("repeat_bytes") as number;
      return this.#blob_echo(rung, bytes_varied(size));
    }

    // control and fit: one blob of the size given, echoed.
    #blob_run(rung: string, size: unknown): dispatch.Sleep {
      return this.#blob_echo(rung, bytes_counted(size as number));
    }

    // One blob sent as an echo, its size and digest kept for the reply.
    #blob_echo(rung: string, data: Uint8Array): dispatch.Sleep {
      this.#sent_size = data.length;
      this.#sent_sha256 = utility.sha256_hex(data);
      const line = line_build(constants.echo_type, [jslb.blob_make(data)], {});
      return this.#submit(rung, "blob", line);
    }

    // The blob echo's reply: one blob of the size and digest sent.
    #blob_take(rung: string, replies: lines.Line[]): undefined {
      const reply = this.#reply_one(replies, constants.echo_type);
      const blobs = blobs_of(reply);
      check(blobs.length === 1, `the echo's reply has ${blobs.length} blobs`);
      const size = jslb.field_get(blobs[0], "size");
      check(
        size === this.#sent_size,
        `the echoed blob has ${String(size)} bytes`,
      );
      const digest = blob_digest(blobs[0]);
      check(
        digest === this.#sent_sha256,
        `the echoed blob's digest is ${String(digest)}`,
      );
      return this.#pass(rung);
    }

    // mcp: `initialize`, then `notifications/initialized` and the call.
    #mcp_run(): dispatch.Sleep {
      const client = new mcp.Client(
        constants.mcp_name,
        constants.mcp_version,
        this.#tasks,
        constants.server_owner,
      );
      this.#client = client;
      const id = client.initialize_send();
      const state: RungState = { rung: "mcp", step: "initialize" };
      return dispatch.task_sleep(state, [id], constants.reply_type);
    }

    // The reply to `initialize`: the revision checked, then the tool call.
    #initialize_take(rung: string, replies: lines.Line[]): dispatch.Sleep {
      const client = this.#client as mcp.Client;
      client.initialized_send(replies[0]);
      const call = gold_value("mcp_call") as McpCall;
      const id = client.tool_call(call.name, call.arguments);
      const state: RungState = { rung, step: "call" };
      return dispatch.task_sleep(state, [id], constants.reply_type);
    }

    // The call's result: no error, one text whose JSON holds the digest.
    #call_take(rung: string, replies: lines.Line[]): undefined {
      const result = (this.#client as mcp.Client).result_of(replies[0]);
      const shown = utility.json_text(result);
      check(result.isError !== true, `the tool call failed: ${shown}`);
      const content = result.content;
      check(
        content.length === 1 && content[0].type === constants.text_type,
        `the tool call's result is not one text: ${shown}`,
      );
      const text = (content[0] as { text: string }).text;
      const came = utility.json_text(jslb.json_decode(text));
      const sha256 = utility.json_text({ sha256: gold_value("mcp_sha256") });
      check(came === sha256, `the tool call's text is ${came}, not ${sha256}`);
      return this.#pass(rung);
    }

    // sync: `db.sync`, whose pushes `sync_keep` takes before the reply.
    #sync_run(): dispatch.Sleep {
      const line = line_build(constants.sync_type, [], {});
      return this.#submit("sync", "sync", line);
    }

    // The reply: the gold's databases named, each one's lines in that order.
    #sync_take(rung: string, replies: lines.Line[]): undefined {
      const reply = this.#reply_one(replies, constants.sync_type);
      check(blobs_of(reply).length === 0, "the sync's reply has blobs");
      const databases = gold_value("sync_databases") as string[];
      const named = utility.json_text({ databases });
      const came = utility.json_text(jslb.payload_of(reply));
      check(came === named, `the sync's reply is ${came}, not ${named}`);
      let index = 0;
      for (const db of databases) {
        index = this.#database_check(db, index);
      }
      const count = this.#sync_lines.length;
      check(index === count, `the sync sent ${count} lines, not ${index}`);
      return this.#pass(rung);
    }

    // The lines of a database from the index, returning the index after them.
    #database_check(db: string, start: number): number {
      const restore = this.#sync_line(start, constants.restore_type, db);
      const files = jslb.payload_of(restore).files as number;
      for (let number = 1; number <= files; number += 1) {
        this.#sync_line(start + number, constants.file_type, db);
      }
      return start + files + 1;
    }

    // The line at the index: of the type and database, with one blob.
    #sync_line(index: number, type: string, db: string): lines.Line {
      const what = `the ${type} line of ${db}`;
      check(index < this.#sync_lines.length, `${what} did not come`);
      const line = this.#sync_lines[index];
      const came = String(jslb.payload_of(line).db);
      check(
        type_of(line) === type && came === db,
        `${what} is a ${String(type_of(line))} line of ${came}`,
      );
      const blobs = blobs_of(line);
      check(blobs.length === 1, `${what} has ${blobs.length} blobs`);
      const size = jslb.field_get(blobs[0], "size");
      check(size !== 0, `${what}'s blob is empty`);
      return line;
    }

    // commits: each push line the gold lists, sent to the server in order.
    #commits_run(): undefined {
      for (const entry of gold_value("commits") as CommitEntry[]) {
        const options: { key?: string; full: boolean } = {
          full: settings.names_full(),
        };
        if (Object.hasOwn(entry, "key")) {
          options.key = entry.key;
        }
        const blobs: lines.BlobHeader[] = [];
        if (Object.hasOwn(entry, "text")) {
          const text = entry.text as string;
          blobs.push(jslb.blob_make(utility.utf8_encode(text)));
        }
        const payload = Object.hasOwn(entry, "payload")
          ? (entry.payload as { [key: string]: unknown })
          : {};
        const header = jslb.header_make(entry.type, options);
        const line = jslb.line_make(header, blobs, payload);
        this.#tasks.line_notify(line, constants.server_owner);
      }
      return this.#pass("commits");
    }

    // audit: a record and a note of the rung's own, then the audit's end.
    #audit_run(): dispatch.Sleep {
      const at = gold_value("audit_at");
      const text = utility.json_text(gold_value("audit_line"));
      const blob = jslb.blob_make(utility.utf8_encode(text));
      const record = { sender: "ui", receiver: "ai", at };
      const note = { thread: "ai", at, text: gold_value("audit_note") };
      for (const line of [
        line_build(constants.record_type, [blob], record),
        line_build(constants.note_type, [], note),
      ]) {
        this.#tasks.line_notify(line, constants.server_owner);
      }
      const count = gold_value("audit_count");
      const tail = line_build(constants.tail_type, [], { count });
      return this.#submit("audit", "audit", tail);
    }

    // The end: only `text`, the record laid out, then the note under it.
    #audit_take(rung: string, replies: lines.Line[]): undefined {
      const reply = this.#reply_one(replies, constants.tail_type);
      const payload = jslb.payload_of(reply);
      const keys = utility.json_text(Object.keys(payload));
      check(keys === '["text"]', `the tail's payload has the keys ${keys}`);
      const text = payload.text as string;
      const body = (gold_value("audit_body") as string[]).join("\n");
      const record = text.indexOf(`, ui to ai\n${body}\n\n`);
      const note = text.indexOf(
        `, note of ai\n  ${gold_value("audit_note")}\n\n`,
      );
      check(
        record >= 0,
        `the tail ${utility.json_text(text)} lacks the record`,
      );
      check(
        note > record,
        `the tail ${utility.json_text(text)} lacks the note`,
      );
      return this.#pass(rung);
    }

    // console: tty 0 opened, `console_typed` typed at the prompt, its end.
    #console_run(): undefined {
      const run = new ConsoleRun(
        this.#start.base_url,
        gold_value("console_prompt") as string,
        gold_value("console_typed") as string,
        () => undefined,
        (code) => {
          this.#guard("console", () => this.#console_closed(run, code));
        },
      );
      return undefined;
    }

    // The close of tty 0 after the typing: the last line read before it.
    #console_closed(run: ConsoleRun, code: number): undefined {
      const last = gold_value("console_last") as string;
      check(
        run.after.endsWith(last),
        `the output since the typing, ${utility.json_text(run.after)},` +
          ` does not end with ${utility.json_text(last)}`,
      );
      return this.#pass("console", `the close code was ${code}`);
    }

    // lines: the subshell's numbers, every one in order, then the prompt.
    #lines_run(): undefined {
      const prompt = gold_value("console_prompt") as string;
      const command = gold_value("lines_command") as string;
      const count = gold_value("lines_count") as number;
      const parts = [command, constants.line_end];
      for (let number = 1; number <= count; number += 1) {
        parts.push(String(number), constants.line_end);
      }
      parts.push(prompt);
      const expected = parts.join("");
      // When the output came back whole, and how long it took.
      const ended = { at: 0, compared: false };
      const run = new ConsoleRun(
        this.#start.base_url,
        prompt,
        command + constants.command_end,
        () => {
          this.#guard("lines", () => {
            if (
              !ended.compared &&
              run.after.length >= expected.length &&
              run.after.endsWith(prompt)
            ) {
              ended.compared = true;
              ended.at = utility.time_now();
              check(
                run.after === expected,
                `the output since the typing is not the command's echo,` +
                  ` 1 to ${count} and the prompt: it has` +
                  ` ${run.after.length} characters for ${expected.length}`,
              );
              run.console_close();
            }
            return undefined;
          });
        },
        (code) => {
          this.#guard("lines", () => {
            check(
              ended.compared,
              `tty 0 closed with code ${code} before the prompt came back`,
            );
            const seconds = (ended.at - run.typed_at) / constants.second_ms;
            return this.#pass(
              "lines",
              `${run.after_bytes} bytes in ${seconds} s from the typing`,
            );
          });
        },
      );
      return undefined;
    }

    // unknown: its point and the parent lines, then an unknown push.
    #unknown_run(): undefined {
      this.#pass("unknown");
      const type = gold_value("unknown_type") as string;
      const line = line_build(type, [], {});
      this.#tasks.line_notify(line, constants.server_owner);
      return undefined;
    }

    // restart: `source.put` of the main loop the restart runs.
    #restart_run(): dispatch.Sleep {
      const text = gold_value("restart_text") as string;
      const blob = jslb.blob_make(utility.utf8_encode(text));
      const line = line_build(constants.source_type, [blob], {
        name: gold_value("restart_name"),
      });
      return this.#submit("restart", "restart", line);
    }

    // Its digest, then the point, the parent lines and `system.restart`.
    #restart_take(rung: string, replies: lines.Line[]): undefined {
      const reply = this.#reply_one(replies, constants.source_type);
      const digest = jslb.payload_of(reply).sha256;
      const expected = gold_value("restart_sha256");
      check(
        digest === expected,
        `the stored main loop's digest is ${String(digest)}`,
      );
      this.#pass(rung);
      const line = line_build(constants.restart_type, [], {
        main_loop: gold_value("restart_name"),
      });
      this.#tasks.line_notify(line, constants.server_owner);
      line_send(this.#tasks, gold_value("restart_after") as string);
      return undefined;
    }
  }

  // Runs the rungs the gold names as one TAP stream, the chain on `tasks`.
  export function rungs_run(
    tasks: queue.TaskQueue,
    start: boot.WorkerStart,
  ): void {
    const chain = new RungChain(tasks, start, gold_value("rungs"));
    const releases = new BroadcastChannel(
      gold_value("release_channel") as string,
    );
    releases.onmessage = (event: MessageEvent<unknown>) =>
      chain.release_take(event.data);
    line_send(tasks, constants.version_line);
    chain.plan_write();
    dispatch.handler_register(
      constants.next_type,
      constants.handler_version,
      () => chain.next_take(),
    );
    dispatch.handler_register(
      constants.reply_type,
      constants.handler_version,
      (wake) => chain.reply_take(wake),
    );
    // A wire run has no store, so the sync's pushes come to the chain.
    for (const type of [constants.restore_type, constants.file_type]) {
      dispatch.handler_register(type, constants.handler_version, (line) =>
        chain.sync_keep(line),
      );
    }
    chain.rung_follow();
  }
}

Object.freeze(test_wire_rungs);
