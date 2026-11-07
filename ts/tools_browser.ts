// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The browser's MCP tools. API/ts/tools_browser.d.ts holds their contract.

namespace tools_browser {
  // Finishes a tool's result from the state and replies of its wake.
  type WakeFinish = (
    state: unknown,
    replies: lines.Line[],
  ) => mcp.ToolResult | dispatch.Sleep;

  // The state of a wake that keeps an image under its ref.
  interface KeyState {
    key: string;
  }

  // The state of a wake that renders once the UI holds the image.
  interface RenderState {
    payload: { [key: string]: unknown };
  }

  // The state of a wake of a console tool: its name, its text and timeout.
  interface ConsoleState {
    tool: string;
    text: string;
    timeout_seconds: number;
  }

  // The names, refs, texts, owners, line types and tools of the tools.
  const constants = Object.freeze({
    // The prefix the agent lists this server's tools under.
    tool_prefix: "browser.",
    // The console's tools, each run only with the player's permit.
    run_tool: "console_run",
    write_tool: "console_write",
    read_tool: "console_read",
    // The start of the ref of an image, its key in `_files`.
    files_prefix: "/_files/",
    // The ref that names the database of the current world.
    world_ref: "/metaverse/world",
    // The key of the ref of the current scene in the world's database.
    scene_key: "scene",
    // The prompt of the console's dash, which ends a command's output.
    prompt_text: "$ ",
    // The end of a command line, and of a line of output once trimmed.
    line_end: "\n",
    // The end of a line as the console's pty writes it.
    pty_end: "\r\n",
    // The number of images an image request asks for.
    image_count: 1,
    // The form an image request asks the images in.
    image_format: "b64_json" as const,
    // The choices of a permit that do not simply accept.
    deny_choice: "deny",
    always_choice: "always",
    // The owners the tools submit to, beside the provider's.
    ui_owner: "ui" as const,
    console_owner: "console" as const,
    server_owner: "server" as const,
    // The line types the tools submit and notify.
    render_type: "render",
    store_type: "media.store",
    fetch_type: "media.fetch",
    permit_type: "permit.ask",
    write_type: "console.write",
    read_type: "console.read",
    tail_type: "verbose.tail",
    show_type: "console.show",
    busy_type: "console.busy",
    idle_type: "console.idle",
    // The wake types of the tools, one per reply they sleep on.
    image_wake: "tools.image_reply",
    media_wake: "tools.media_reply",
    fetch_wake: "tools.fetch_reply",
    stored_wake: "tools.stored_reply",
    render_wake: "tools.render_reply",
    permit_wake: "tools.permit_reply",
    console_wake: "tools.console_reply",
    tail_wake: "tools.tail_reply",
    show_wake: "tools.show_reply",
    // The tools of this server, in the order `tools/list` lists them.
    tools: Object.freeze<readonly mcp.Tool[]>([
      {
        name: "sql_run",
        description:
          "Run SQL statements in one transaction on a database. DDL is" +
          " allowed: your scripts are the database administrator.",
        inputSchema: {
          type: "object",
          properties: {
            db: { type: "string" },
            statements: {
              type: "array",
              items: {
                type: "object",
                properties: {
                  sql: { type: "string" },
                  params: { type: "array" },
                },
                required: ["sql", "params"],
              },
            },
          },
          required: ["db", "statements"],
        },
      },
      {
        name: "db_create",
        description: "Create an empty database. The name is a C identifier.",
        inputSchema: schema_strings(["db"]),
      },
      {
        name: "db_drop",
        description: "Delete a database and everything in it.",
        inputSchema: schema_strings(["db"]),
      },
      {
        name: "kv_get",
        description:
          "Read the value a Key-Value-Ref names, /$db/$key, as text.",
        inputSchema: schema_strings(["ref"]),
      },
      {
        name: "kv_put",
        description:
          "Write text under a Key-Value-Ref, /$db/$key, and return its" +
          " sha256. A script is the row /_files/script/<name>.js.",
        inputSchema: schema_strings(["ref", "text"]),
      },
      {
        name: "kv_delete",
        description: "Delete the row a Key-Value-Ref names.",
        inputSchema: schema_strings(["ref"]),
      },
      {
        name: "kv_list",
        description:
          "List the keys of a database under a prefix with sizes and" +
          " hashes.",
        inputSchema: schema_strings(["db", "prefix"]),
      },
      {
        name: "doc_get",
        description:
          "Read a document by Document-Ref, /$db/$id/$version, in its" +
          ' encoded form: header 0, references at 1 on, {"$ref": n} in' +
          " the body.",
        inputSchema: schema_strings(["ref"]),
      },
      {
        name: "doc_put",
        description:
          "Write a new version of document $id in database $db and move" +
          " its head. Returns the new Document-Ref.",
        inputSchema: {
          type: "object",
          properties: {
            db: { type: "string" },
            id: { type: "string" },
            body: { type: "object" },
          },
          required: ["db", "id", "body"],
        },
      },
      {
        name: "doc_head",
        description:
          "The current Document-Ref of document $id in database $db.",
        inputSchema: schema_strings(["db", "id"]),
      },
      {
        name: "script_run",
        description:
          "Run the script /_files/script/<name>.js with args as a task in" +
          " this worker. Returns its value or exception and the verbose" +
          " lines it wrote.",
        inputSchema: {
          type: "object",
          properties: { name: { type: "string" }, args: { type: "object" } },
          required: ["name", "args"],
        },
      },
      {
        name: "script_debug",
        description:
          "Run the script as script_run does, tracing every substrate call" +
          " it makes first.",
        inputSchema: {
          type: "object",
          properties: { name: { type: "string" }, args: { type: "object" } },
          required: ["name", "args"],
        },
      },
      {
        name: "image_make",
        description:
          "Generate an image from a prompt and keep it under" +
          " /_files/<key>. Returns the key, size and sha256.",
        inputSchema: schema_strings(["prompt", "key"]),
      },
      {
        name: "render",
        description:
          "Show an image by its Key-Value-Ref with a subtitle. No image" +
          " means black.",
        inputSchema: {
          type: "object",
          properties: {
            image: { type: "string" },
            subtitle: { type: "string" },
          },
          required: ["subtitle"],
        },
      },
      {
        name: "console_run",
        description:
          "Show the debug console as ctrl-0 does, run one command line in" +
          " its dash and return its output until the next prompt or the" +
          " timeout. Debug mode.",
        inputSchema: {
          type: "object",
          properties: {
            text: { type: "string" },
            timeout_seconds: { type: "number" },
          },
          required: ["text", "timeout_seconds"],
        },
        _meta: { xsjs: { permit: true } },
      },
      {
        name: "console_write",
        description:
          "Show the debug console as ctrl-0 does and type text into its" +
          " dash, returning at once. A line goes when a newline ends it, and" +
          " the text after the last newline waits for a later write. The" +
          " console is yours from the first write until console_read sees" +
          " the prompt. Debug mode.",
        inputSchema: {
          type: "object",
          properties: { text: { type: "string" } },
          required: ["text"],
        },
        _meta: { xsjs: { permit: true } },
      },
      {
        name: "console_read",
        description:
          "Show the debug console as ctrl-0 does and read its output from" +
          " where the last read ended until the text until shows or the" +
          " timeout, and whether it timed out. A read whose output ends with" +
          " the prompt ends your turn at the console. Debug mode.",
        inputSchema: {
          type: "object",
          properties: {
            until: { type: "string" },
            timeout_seconds: { type: "number" },
          },
          required: ["until", "timeout_seconds"],
        },
        _meta: { xsjs: { permit: true } },
      },
      {
        name: "verbose_tail",
        description:
          "The last lines of a thread's verbose ring: ui, ai or server." +
          " count is a maximum, as a reply holds the newest lines that fit" +
          " below line_max.",
        inputSchema: {
          type: "object",
          properties: {
            thread: { type: "string" },
            count: { type: "integer" },
          },
          required: ["thread", "count"],
        },
      },
    ]),
  });

  // The input schema of text arguments, every one of them required.
  function schema_strings(names: string[]): mcp.Tool["inputSchema"] {
    return {
      type: "object",
      properties: Object.fromEntries(
        names.map((name) => [name, { type: "string" }]),
      ),
      required: names,
    };
  }

  // A tool result holding text as it is.
  function result_text(text: string): mcp.ToolResult {
    return { content: [{ type: "text", text }] };
  }

  // A tool result holding the JSON text of a value.
  function result_json(value: unknown): mcp.ToolResult {
    return result_text(utility.json_text(value));
  }

  // A refusal for the AI to read, marked as an error, failing nothing.
  function result_refused(text: string): mcp.ToolResult {
    return { ...result_text(text), isError: true };
  }

  // The tool result of a script run, marked as an error when it threw.
  function script_result(run: script.ScriptResult): mcp.ToolResult {
    const result = result_json(run);
    if (run.error !== undefined) {
      result.isError = true;
    }
    return result;
  }

  // A line of a type with its payload and blobs, in this thread's name form.
  function line_build(
    type: string,
    payload: { [key: string]: unknown },
    blobs: lines.BlobHeader[] = [],
  ): lines.Line {
    const header = jslb.header_make(type, { full: settings.names_full() });
    return jslb.line_make(header, blobs, payload);
  }

  // The payload of the one reply a wake carries.
  function reply_payload(replies: lines.Line[]): { [key: string]: unknown } {
    return jslb.payload_of(replies[0]);
  }

  // The data of blob 1 of the one reply a wake carries: bytes or a handle.
  function reply_data(replies: lines.Line[]): Uint8Array | string {
    const blob = replies[0][1] as lines.BlobHeader;
    return jslb.field_get(blob, "data") as Uint8Array | string;
  }

  // A command's output with LF line ends, its echo and its prompt cut off.
  function output_trim(
    received: string,
    command: string,
    timed_out: boolean,
  ): string {
    const { line_end, prompt_text } = constants;
    let output = received.split(constants.pty_end).join(line_end);
    const echo = command + line_end;
    if (output.startsWith(echo)) {
      output = output.slice(echo.length);
    }
    if (!timed_out && output.endsWith(prompt_text)) {
      output = output.slice(0, output.length - prompt_text.length);
    }
    return output;
  }

  // What the tools of one server share, with the permits of the tab.
  class ToolContext {
    readonly store: substrate.Store;
    readonly tasks: queue.TaskQueue;
    readonly provider_owner: queue.ThreadName;
    // The provider's address and the model every image request names.
    readonly info: lines.ProviderInfo;
    readonly settings_get: (id: string) => unknown;
    // The reader of debug mode, which the debug tools need.
    readonly debug_on: () => boolean;
    // The tools the player allowed always, for the life of the tab.
    readonly allowed = new Set<string>();
    // The number of the last permit asked.
    permit_count = 0;
    // Whether the AI's turn holds the console, from its first write.
    turn_on = false;

    // Keeps what the tools use, one context per server.
    constructor(
      store: substrate.Store,
      tasks: queue.TaskQueue,
      provider_owner: queue.ThreadName,
      info: lines.ProviderInfo,
      settings_get: (id: string) => unknown,
      debug_on: () => boolean,
    ) {
      this.store = store;
      this.tasks = tasks;
      this.provider_owner = provider_owner;
      this.info = info;
      this.settings_get = settings_get;
      this.debug_on = debug_on;
    }

    // The bytes of a KV value, read from the cache when it is held there.
    bytes_read(ref: string): Uint8Array {
      const value = this.store.kv_get(ref);
      const cache = this.store.sink() as substrate.CacheFiles;
      return typeof value.data === "string"
        ? cache.cache_read(value.data, 0, value.size)
        : value.data;
    }

    // The text of a KV value.
    text_read(ref: string): string {
      return utility.utf8_decode(this.bytes_read(ref));
    }

    // Asks the UI to paint a render's payload and sleeps until it has.
    render_show(payload: { [key: string]: unknown }): dispatch.Sleep {
      return this.request_sleep(
        line_build(constants.render_type, payload),
        constants.ui_owner,
        {},
        constants.render_wake,
      );
    }

    // Submits a request to its owner and returns the sleep on its reply.
    request_sleep(
      line: lines.Line,
      owner: queue.ThreadName,
      state: unknown,
      then_type: string,
    ): dispatch.Sleep {
      const id = this.tasks.task_submit(line, owner);
      return dispatch.task_sleep(state, [id], then_type);
    }

    // In debug mode asks the tool's permit unless always allowed, then shows.
    console_ask(
      state: ConsoleState,
      args: unknown,
    ): mcp.ToolResult | dispatch.Sleep {
      const name = constants.tool_prefix + state.tool;
      if (!this.debug_on()) {
        return result_refused(i18n("tools_browser.debug_off", name));
      }
      if (this.allowed.has(name)) {
        return this.console_show(state);
      }
      this.permit_count += 1;
      const ask = line_build(constants.permit_type, {
        permit: this.permit_count,
        tool: name,
        input: args,
      });
      return this.request_sleep(
        ask,
        constants.ui_owner,
        state,
        constants.permit_wake,
      );
    }

    // Asks the UI to show the console as ctrl 0 does and sleeps until open.
    console_show(state: ConsoleState): dispatch.Sleep {
      return this.request_sleep(
        line_build(constants.show_type, {}),
        constants.ui_owner,
        state,
        constants.show_wake,
      );
    }

    // Starts the AI's turn unless one is on: the keys held, the output kept.
    turn_start(): void {
      if (this.turn_on) {
        return;
      }
      this.turn_on = true;
      this.turn_notify(constants.busy_type);
    }

    // Ends the AI's turn: the view's keys and held lines freed.
    turn_end(): void {
      this.turn_on = false;
      this.turn_notify(constants.idle_type);
    }

    // Notifies the turn's start or end to tty 0's writer, which tells the UI.
    turn_notify(type: string): void {
      this.tasks.line_notify(line_build(type, {}), constants.console_owner);
    }

    // Gives the AI's text to tty 0's writer, which types it line by line.
    text_write(text: string): void {
      this.tasks.line_notify(
        line_build(constants.write_type, { text }),
        constants.console_owner,
      );
    }

    // Reads tty 0's output until a text or the timeout, asleep till then.
    output_read(state: ConsoleState, until: string): dispatch.Sleep {
      const read = line_build(constants.read_type, {
        until,
        timeout_seconds: state.timeout_seconds,
      });
      return this.request_sleep(
        read,
        constants.console_owner,
        state,
        constants.console_wake,
      );
    }
  }

  // The functions of the tools, by name.
  function runs_make(context: ToolContext): { [name: string]: mcp.ToolFn } {
    const store = context.store;
    return {
      // Runs the statements and returns their results.
      sql_run: (args) => {
        const db = args.db as string;
        const statements = args.statements as lines.SqlStatement[];
        return result_json({ results: store.sql_run(db, statements) });
      },
      // Creates an empty database.
      db_create: (args) => {
        store.db_create(args.db as string);
        return result_json({});
      },
      // Deletes a database and everything in it.
      db_drop: (args) => {
        store.db_drop(args.db as string);
        return result_json({});
      },
      // Reads a value of this side's store as text.
      kv_get: (args) => result_text(context.text_read(args.ref as string)),
      // Writes text as its bytes and returns the row's digest.
      kv_put: (args) => {
        const data = utility.utf8_encode(args.text as string);
        const row = store.kv_put(args.ref as string, data);
        return result_json({ sha256: row.sha256 });
      },
      // Deletes a row.
      kv_delete: (args) => {
        store.kv_delete(args.ref as string);
        return result_json({});
      },
      // Lists the rows under a prefix.
      kv_list: (args) => {
        const keys = store.kv_list(args.db as string, args.prefix as string);
        return result_json({ keys });
      },
      // Reads a document of this side's store, encoded.
      doc_get: (args) => result_json(store.doc_get(args.ref as string)),
      // Writes the next version of a document and returns its ref.
      doc_put: (args) => {
        const body = args.body as lines.Document;
        const put = store.doc_put(args.db as string, args.id as string, body);
        return result_json({ ref: put.ref });
      },
      // Reads the ref of a document's head.
      doc_head: (args) => {
        const ref = store.doc_head(args.db as string, args.id as string);
        return result_json({ ref });
      },
      // Runs a script untraced.
      script_run: (args) => {
        const name = args.name as string;
        const run = script.script_run(store, name, args.args, false);
        return script_result(run);
      },
      // Runs a script with its calls of the store traced first.
      script_debug: (args) => {
        const name = args.name as string;
        const run = script.script_run(store, name, args.args, true);
        return script_result(run);
      },
      // Asks the provider for an image and sleeps on its reply.
      image_make: (args) => {
        const { base_url, image_model } = context.info;
        const request = provider.image_request(base_url, provider.key_get(), {
          model: image_model,
          prompt: args.prompt as string,
          n: constants.image_count,
          response_format: constants.image_format,
        });
        const state: KeyState = {
          key: constants.files_prefix + (args.key as string),
        };
        return context.request_sleep(
          request,
          context.provider_owner,
          state,
          constants.image_wake,
        );
      },
      // Shows the image and subtitle in the current scene, asleep till shown.
      render: (args) => {
        const world = context.text_read(constants.world_ref);
        const scene = context.text_read(`/${world}/${constants.scene_key}`);
        const image = args.image as string | undefined;
        const payload: { [key: string]: unknown } = {
          scene,
          subtitle: args.subtitle,
        };
        if (image === undefined) {
          return context.render_show(payload);
        }
        payload.image = image;
        // The UI's cache may not hold it, and this side alone has its bytes.
        const kept = line_build(constants.store_type, { k: image }, [
          jslb.blob_make(context.bytes_read(image)),
        ]);
        const state: RenderState = { payload };
        return context.request_sleep(
          kept,
          constants.ui_owner,
          state,
          constants.stored_wake,
        );
      },
      // Runs one command line to the next prompt, behind the permit.
      console_run: (args) =>
        context.console_ask(
          {
            tool: constants.run_tool,
            text: args.text as string,
            timeout_seconds: args.timeout_seconds as number,
          },
          args,
        ),
      // Types text into the console, behind the permit, returning at once.
      console_write: (args) =>
        context.console_ask(
          {
            tool: constants.write_tool,
            text: args.text as string,
            timeout_seconds: 0,
          },
          args,
        ),
      // Reads the console's output to a text, behind the permit.
      console_read: (args) =>
        context.console_ask(
          {
            tool: constants.read_tool,
            text: args.until as string,
            timeout_seconds: args.timeout_seconds as number,
          },
          args,
        ),
      // Asks the server for the last lines of a thread and sleeps on them.
      verbose_tail: (args) => {
        const tail = line_build(constants.tail_type, {
          thread: args.thread,
          count: args.count,
        });
        return context.request_sleep(
          tail,
          constants.server_owner,
          {},
          constants.tail_wake,
        );
      },
    };
  }

  // The functions that finish the tools that sleep, by wake type.
  function wakes_make(context: ToolContext): { [type: string]: WakeFinish } {
    const store = context.store;
    return {
      // Keeps the image the provider sent, or asks the UI to download it.
      [constants.image_wake]: (state, replies) => {
        const { key } = state as KeyState;
        const image = provider.image_response(replies[0]).data[0];
        if (image.b64_json === undefined) {
          const download = line_build(constants.fetch_type, {
            url: image.url,
            k: key,
          });
          const keeping: KeyState = { key };
          return context.request_sleep(
            download,
            constants.ui_owner,
            keeping,
            constants.fetch_wake,
          );
        }
        const data = utility.base64_decode(image.b64_json);
        store.kv_put(key, data);
        const kept = line_build(constants.store_type, { k: key }, [
          jslb.blob_make(data),
        ]);
        return context.request_sleep(
          kept,
          constants.ui_owner,
          {},
          constants.media_wake,
        );
      },
      // Returns the key, size and digest the UI kept the image under.
      [constants.media_wake]: (_state, replies) => {
        const { k, size, sha256 } = reply_payload(replies);
        return result_json({ key: k, size, sha256 });
      },
      // Keeps the bytes the UI downloaded and returns their key and digest.
      [constants.fetch_wake]: (state, replies) => {
        const { key } = state as KeyState;
        const row = store.kv_put(key, reply_data(replies));
        return result_json({ key, size: row.size, sha256: row.sha256 });
      },
      // Renders once the UI has decoded the image the render names.
      [constants.stored_wake]: (state) =>
        context.render_show((state as RenderState).payload),
      // Ends the render once the UI has shown it.
      [constants.render_wake]: () => result_json({}),
      // Answers a denial with an error, else shows the console.
      [constants.permit_wake]: (state, replies) => {
        const asked = state as ConsoleState;
        const name = constants.tool_prefix + asked.tool;
        const choice = reply_payload(replies).choice;
        if (choice === constants.deny_choice) {
          return result_refused(i18n("tools_browser.permit_denied", name));
        }
        if (choice === constants.always_choice) {
          context.allowed.add(name);
        }
        return context.console_show(asked);
      },
      // Once tty 0 is open: types and reads, types alone, or reads alone.
      [constants.show_wake]: (state) => {
        const shown = state as ConsoleState;
        if (shown.tool === constants.read_tool) {
          return context.output_read(shown, shown.text);
        }
        context.turn_start();
        if (shown.tool === constants.write_tool) {
          context.text_write(shown.text);
          return result_json({});
        }
        context.text_write(shown.text + constants.line_end);
        return context.output_read(shown, constants.prompt_text);
      },
      // Ends the turn as the read says, returns its output and its timeout.
      [constants.console_wake]: (state, replies) => {
        const { tool, text } = state as ConsoleState;
        const reply = reply_payload(replies);
        const timed_out = reply.timed_out as boolean;
        const received = reply.text as string;
        if (tool === constants.run_tool) {
          context.turn_end();
          const output = output_trim(received, text, timed_out);
          return result_json({ output, timed_out });
        }
        const output = received
          .split(constants.pty_end)
          .join(constants.line_end);
        if (context.turn_on && output.endsWith(constants.prompt_text)) {
          context.turn_end();
        }
        return result_json({ output, timed_out });
      },
      // Returns the lines the server sent.
      [constants.tail_wake]: (_state, replies) =>
        result_json({ lines: reply_payload(replies).lines }),
    };
  }

  // Registers the tools and their wakes on the server, run through the store.
  export function tools_register(
    server: mcp.Server,
    store: substrate.Store,
    tasks: queue.TaskQueue,
    provider_owner: queue.ThreadName,
    info: lines.ProviderInfo,
    settings_get: (id: string) => unknown,
    debug_on: () => boolean,
  ): void {
    const context = new ToolContext(
      store,
      tasks,
      provider_owner,
      info,
      settings_get,
      debug_on,
    );
    const runs = runs_make(context);
    for (const tool of constants.tools) {
      server.tool_register(tool, runs[tool.name]);
    }
    for (const [type, fn] of Object.entries(wakes_make(context))) {
      server.wake_register(type, fn);
    }
  }
}

Object.freeze(tools_browser);
