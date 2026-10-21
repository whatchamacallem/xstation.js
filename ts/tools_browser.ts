// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The browser's MCP tools, registered on the AI worker's server and run
// through the store inside the task of the `mcp` line: SQL, databases, values,
// documents, scripts, images, the render, the debug console after the
// player's permit, the verbose tail, and the measurement and
// administration of the databases against their soft limit. A value this
// side no longer holds is asked of the server before it is read, a snapshot
// comes as one blob whose digest is checked, and a render that leaves a
// scene frees the cached values of `_files` the new scene does not name
// until they fit `files_browser_bytes`. A tool that waits submits its one
// request to an explicit owner and sleeps, and its wake, registered on the
// server beside the tools, finishes the result or sleeps again.

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

  // The state of a wake that runs or ends a console command.
  interface ConsoleState {
    text: string;
    timeout_seconds: number;
  }

  // The state of a wake that fills a value back: its ref, whether a document.
  interface ValueState {
    ref: string;
    document: boolean;
  }

  // The state of a wake that opens a snapshot: its database.
  interface LoadState {
    db: string;
  }

  // The names, refs, texts, owners, line types and tools of the tools.
  const constants = Object.freeze({
    // The prefix the agent lists this server's tools under.
    tool_prefix: "browser.",
    // The tool that runs only with the player's permit.
    permit_tool: "console_run",
    // The start of the ref of an image, its key in `_files`.
    files_prefix: "/_files/",
    // The ref that names the database of the current world.
    world_ref: "/metaverse/world",
    // The key of the ref of the current scene in the world's database.
    scene_key: "scene",
    // The prompt of the console's dash, which ends a command's output.
    prompt_text: "$ ",
    // The command byte that starts each input message of ttyd's protocol.
    input_command: "0",
    // The end of a command line, and of a line of output once trimmed.
    line_end: "\n",
    // The end of a line as the console's pty writes it.
    pty_end: "\r\n",
    // The number of images an image request asks for.
    image_count: 1,
    // The form an image request asks the images in.
    image_format: "b64_json" as const,
    // The setting of the soft limit of the databases' bytes.
    soft_setting: "db_soft_bytes",
    // The setting of the budget of the browser's tier of `_files`.
    files_setting: "files_browser_bytes",
    // The database of media, scripts and blobs, the tier the render frees.
    files_db: "_files",
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
    input_type: "console.input",
    read_type: "console.read",
    tail_type: "verbose.tail",
    get_type: "kv.get",
    snapshot_type: "db.snapshot",
    // The wake types of the tools, one per reply they sleep on.
    image_wake: "tools.image_reply",
    media_wake: "tools.media_reply",
    fetch_wake: "tools.fetch_reply",
    render_wake: "tools.render_reply",
    permit_wake: "tools.permit_reply",
    console_wake: "tools.console_reply",
    tail_wake: "tools.tail_reply",
    snapshot_wake: "tools.snapshot_reply",
    value_wake: "tools.value_reply",
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
          "Write text under a Key-Value-Ref, /$db/$key. A script is the" +
          " row /_files/script/<name>.js.",
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
          "Run one command line in the debug console's dash and return" +
          " its output until the next prompt or the timeout. Debug mode.",
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
        name: "verbose_tail",
        description:
          "The last lines of a thread's verbose ring: ui, ai or server.",
        inputSchema: {
          type: "object",
          properties: {
            thread: { type: "string" },
            count: { type: "integer" },
          },
          required: ["thread", "count"],
        },
      },
      {
        name: "db_stats",
        description:
          "Measure the databases open in this worker by their pages and" +
          " cached values: for each its name, bytes, free_bytes," +
          " cache_bytes and seq, then total_bytes, soft_bytes and whether" +
          " the total is over the soft limit. Read only.",
        inputSchema: { type: "object", properties: {} },
      },
      {
        name: "db_compact",
        description:
          "Run VACUUM on this worker's copy of a database and return its" +
          " bytes before and after. The content and seq do not change and" +
          " nothing is sent to the server.",
        inputSchema: schema_strings(["db"]),
      },
      {
        name: "db_unload",
        description:
          "Close and delete this worker's copy of a database and the cache" +
          " files only it names. The server keeps its copy; an operation" +
          " on the database fails until db_load.",
        inputSchema: schema_strings(["db"]),
      },
      {
        name: "db_load",
        description:
          "Fetch the server's copy of a database and open it in this" +
          " worker, as at start. Returns its seq.",
        inputSchema: schema_strings(["db"]),
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

  // The tool result of a script run, marked as an error when it threw.
  function script_result(run: script.ScriptResult): mcp.ToolResult {
    const result = result_json(run);
    if (run.error !== undefined) {
      result.isError = true;
    }
    return result;
  }

  // A line of a type with its payload and blobs, in short names.
  function line_build(
    type: string,
    payload: { [key: string]: unknown },
    blobs: lines.BlobHeader[] = [],
  ): lines.Line {
    return jslb.line_make(jslb.header_make(type), blobs, payload);
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

  // Blob 1 of a `db.snapshot` reply, checked against the `sha256` it sent.
  function snapshot_data(
    db: string,
    replies: lines.Line[],
  ): Uint8Array | string {
    const blob = replies[0][1] as lines.BlobHeader;
    const data = reply_data(replies);
    // A streamed blob's digest is the one its cache file took as it came.
    const sha256 =
      typeof data === "string"
        ? (blob.sha256 as lines.Sha256)
        : utility.sha256_hex(data);
    const sent = reply_payload(replies).sha256 as lines.Sha256;
    if (sha256 !== sent) {
      throw new Error(i18n("substrate.snapshot_digest", db, sha256, sent));
    }
    return data;
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
    // The name the permit request shows for the permit tool.
    readonly permit_name: string;
    // The tools the player allowed always, for the life of the tab.
    readonly allowed = new Set<string>();
    // The number of the last permit asked.
    permit_count = 0;
    // The scene the last render showed, none before the first.
    scene_shown: string | undefined = undefined;

    // Keeps what the tools use, one context per server.
    constructor(
      store: substrate.Store,
      tasks: queue.TaskQueue,
      provider_owner: queue.ThreadName,
      info: lines.ProviderInfo,
      settings_get: (id: string) => unknown,
    ) {
      this.store = store;
      this.tasks = tasks;
      this.provider_owner = provider_owner;
      this.info = info;
      this.settings_get = settings_get;
      this.permit_name = constants.tool_prefix + constants.permit_tool;
    }

    // The text of a KV value, read from the cache when it is held there.
    text_read(ref: string): string {
      const value = this.store.kv_get(ref);
      const cache = this.store.sink() as substrate.CacheFiles;
      const data =
        typeof value.data === "string"
          ? cache.cache_read(value.data, 0, value.size)
          : value.data;
      return utility.utf8_decode(data);
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

    // Asks the server for a value this side does not hold and sleeps on it.
    value_fetch(ref: string, document: boolean): dispatch.Sleep {
      const header = jslb.header_make(constants.get_type, { key: ref });
      const state: ValueState = { ref, document };
      return this.request_sleep(
        jslb.line_make(header, [], {}),
        constants.server_owner,
        state,
        constants.value_wake,
      );
    }

    // Frees the cached values of `_files` the scene does not name, to fit.
    files_evict(scene: lines.DocRef, image: string | undefined): void {
      const open = this.store.db_list();
      // An unloaded `_files` holds no values to free.
      if (!open.includes(constants.files_db)) {
        return;
      }
      const keep: string[] = [];
      // The scene's refs are its headers, read when its database is open.
      if (open.includes(substrate.ref_split(scene).db as string)) {
        const document = this.store.doc_get(scene);
        keep.push(...(jslb.headers_of(document).slice(1) as string[]));
      }
      if (image !== undefined) {
        keep.push(image);
      }
      const budget = this.settings_get(constants.files_setting) as number;
      this.store.cache_evict(constants.files_db, keep, budget);
    }

    // Types a command line into the console and sleeps on reading its output.
    console_send(text: string, timeout_seconds: number): dispatch.Sleep {
      const typed = constants.input_command + text + constants.line_end;
      const blob = jslb.blob_make(utility.utf8_encode(typed));
      this.tasks.line_notify(
        line_build(constants.input_type, {}, [blob]),
        constants.console_owner,
      );
      const read = line_build(constants.read_type, {
        until: constants.prompt_text,
        timeout_seconds,
      });
      const state: ConsoleState = { text, timeout_seconds };
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
      // Runs the statements and returns their results and the `seq` after.
      sql_run: (args) => {
        const db = args.db as string;
        const statements = args.statements as lines.SqlStatement[];
        const results = store.sql_run(db, statements);
        return result_json({ results, seq: store.seq_get(db) });
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
      // Reads a value as text, asking the server first when it is not held.
      kv_get: (args) => {
        const ref = args.ref as string;
        if (!store.kv_held(ref)) {
          return context.value_fetch(ref, false);
        }
        return result_text(context.text_read(ref));
      },
      // Writes text as its bytes and returns their digest and the `seq`.
      kv_put: (args) => {
        const data = utility.utf8_encode(args.text as string);
        const written = store.kv_put(args.ref as string, data);
        return result_json({ sha256: written.row.sha256, seq: written.seq });
      },
      // Deletes a row and returns the `seq` after.
      kv_delete: (args) =>
        result_json({ seq: store.kv_delete(args.ref as string) }),
      // Lists the rows under a prefix.
      kv_list: (args) => {
        const keys = store.kv_list(args.db as string, args.prefix as string);
        return result_json({ keys });
      },
      // Reads a document encoded, asking the server first when it is not held.
      doc_get: (args) => {
        const ref = args.ref as string;
        if (!store.kv_held(ref)) {
          return context.value_fetch(ref, true);
        }
        return result_json(store.doc_get(ref));
      },
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
        // A render of another scene than the last one shown leaves that one.
        if (scene !== context.scene_shown) {
          context.files_evict(scene, image);
          context.scene_shown = scene;
        }
        const payload: { [key: string]: unknown } = {
          scene,
          subtitle: args.subtitle,
        };
        if (image !== undefined) {
          payload.image = image;
        }
        return context.request_sleep(
          line_build(constants.render_type, payload),
          constants.ui_owner,
          {},
          constants.render_wake,
        );
      },
      // Asks the player's permit unless always allowed, then runs the line.
      console_run: (args) => {
        const text = args.text as string;
        const timeout_seconds = args.timeout_seconds as number;
        if (context.allowed.has(context.permit_name)) {
          return context.console_send(text, timeout_seconds);
        }
        context.permit_count += 1;
        const ask = line_build(constants.permit_type, {
          permit: context.permit_count,
          tool: context.permit_name,
          input: args,
        });
        const state: ConsoleState = { text, timeout_seconds };
        return context.request_sleep(
          ask,
          constants.ui_owner,
          state,
          constants.permit_wake,
        );
      },
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
      // Measures the open databases against the soft limit.
      db_stats: () => {
        const soft = context.settings_get(constants.soft_setting) as number;
        return result_json(store.db_stats(soft));
      },
      // Compacts a database and returns its bytes before and after.
      db_compact: (args) => result_json(store.db_compact(args.db as string)),
      // Unloads this side's copy of a database.
      db_unload: (args) => {
        store.db_unload(args.db as string);
        return result_json({});
      },
      // Asks the server for a database's snapshot and sleeps on it.
      db_load: (args) => {
        const state: LoadState = { db: args.db as string };
        return context.request_sleep(
          line_build(constants.snapshot_type, { db: state.db }),
          constants.server_owner,
          state,
          constants.snapshot_wake,
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
        const { row } = store.kv_put(key, reply_data(replies));
        return result_json({ key, size: row.size, sha256: row.sha256 });
      },
      // Ends the render once the UI has shown it.
      [constants.render_wake]: () => result_json({}),
      // Answers a denial with an error, else runs the command line.
      [constants.permit_wake]: (state, replies) => {
        const { text, timeout_seconds } = state as ConsoleState;
        const choice = reply_payload(replies).choice;
        if (choice === constants.deny_choice) {
          const name = context.permit_name;
          const denied = i18n("tools_browser.permit_denied", name);
          return { ...result_text(denied), isError: true };
        }
        if (choice === constants.always_choice) {
          context.allowed.add(context.permit_name);
        }
        return context.console_send(text, timeout_seconds);
      },
      // Returns the command's output and whether the read timed out.
      [constants.console_wake]: (state, replies) => {
        const { text } = state as ConsoleState;
        const reply = reply_payload(replies);
        const timed_out = reply.timed_out as boolean;
        const output = output_trim(reply.text as string, text, timed_out);
        return result_json({ output, timed_out });
      },
      // Returns the lines the server sent.
      [constants.tail_wake]: (_state, replies) =>
        result_json({ lines: reply_payload(replies).lines }),
      // Checks the snapshot's digest and opens it at the `seq` it gave.
      [constants.snapshot_wake]: (state, replies) => {
        const { db } = state as LoadState;
        const seq = store.db_load(db, snapshot_data(db, replies));
        const sent = reply_payload(replies).seq as number;
        if (seq !== sent) {
          throw new Error(i18n("tools_browser.load_desync", db, seq, sent));
        }
        return result_json({ seq });
      },
      // Fills back the value the server sent, then reads it as asked.
      [constants.value_wake]: (state, replies) => {
        const { ref, document } = state as ValueState;
        store.cache_fill(ref, reply_data(replies));
        if (document) {
          return result_json(store.doc_get(ref));
        }
        return result_text(context.text_read(ref));
      },
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
  ): void {
    const context = new ToolContext(
      store,
      tasks,
      provider_owner,
      info,
      settings_get,
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
