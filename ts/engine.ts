// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The engine page's program, where the parts meet. API/ts/engine.d.ts holds
// its rules. The chain's handlers each do one step, so that a piece can be
// tested alone. `worker_run` reads `provider.scripted` off the first line,
// which carried the settings, so that a test gives it a false one through
// its argument. The store's sizes and the UI thread's parts read the settings.

namespace engine {
  // The names, owners, line types, refs and ids of the program.
  const constants = Object.freeze({
    worker_name: "ai",
    thread: "ai" as const,
    server_owner: "server" as const,
    ui_owner: "ui" as const,
    http_owner: "http" as const,
    media_owner: "media" as const,
    dom_owner: "dom" as const,
    handler_version: 0,
    root: "/engine",
    overflow_setting: "overflow_bytes",
    blob_setting: "blob_max",
    compact_setting: "turn_compact_turns",
    media_setting: "media_db_bytes",
    timeout_setting: "provider.timeout_seconds",
    line_setting: "line_max",
    // The bytes of a line per character of the box, past JSON's 6 at worst.
    text_bytes: 8,
    // The identities of the browser's server and of both clients.
    server_name: "xsjs-browser",
    client_name: "hyperposition-engine",
    version: "0",
    browser_prefix: "browser",
    server_prefix: "server",
    // The provider's address and models of a scripted run, empty.
    info: Object.freeze<lines.ProviderInfo>({
      base_url: "",
      chat_model: "",
      image_model: "",
    }),
    // The key the provider door needs, which the scripted port never reads.
    provider_key: "scripted",
    script_ref: "/_files/provider/script.json",
    world_ref: "/metaverse/world",
    scene_key: "scene",
    mcp_type: "mcp",
    sync_type: "db.sync",
    render_type: "render",
    store_type: "media.store",
    start_type: "engine.start",
    initialized_type: "engine.initialized",
    listed_type: "engine.listed",
    synced_type: "engine.synced",
    stored_type: "engine.stored",
    rendered_type: "engine.rendered",
    image_id: "image",
    subtitle_id: "subtitle",
    input_id: "input",
    permit_id: "permit",
    debug_id: "debug",
    overlays_id: "overlays",
  });

  // The two clients of the chain and the set the agent lists their tools from.
  export interface ToolParts {
    // The client of the browser's MCP server, under the prefix `browser`.
    browser: mcp.Client;
    // The client of the server's MCP server, under the prefix `server`.
    server: mcp.Client;
    clients: mcp.ClientSet;
  }

  // A line of a type, its payload and blobs, in the form the settings pick.
  function line_typed(
    type: string,
    payload: { [key: string]: unknown },
    blobs: lines.BlobHeader[] = [],
  ): lines.Line {
    const header = jslb.header_make(type, { full: settings.names_full() });
    return jslb.line_make(header, blobs, payload);
  }

  // The one reply a wake of the chain waited for.
  function reply_of(wake: lines.Line): lines.Line {
    return (wake.replies as lines.Line[])[0];
  }

  // The bytes of a value, read from the cache when it is held there.
  function bytes_read(store: substrate.Store, ref: lines.KvRef): Uint8Array {
    const value = store.kv_get(ref);
    const cache = store.sink() as substrate.CacheFiles;
    return typeof value.data === "string"
      ? cache.cache_read(value.data, 0, value.size)
      : value.data;
  }

  // The text of a value.
  function text_read(store: substrate.Store, ref: lines.KvRef): string {
    return utility.utf8_decode(bytes_read(store, ref));
  }

  // The browser's store under the root `/engine`, its handlers registered.
  export function store_build(
    tasks: queue.TaskQueue,
    start: boot.WorkerStart,
  ): substrate.Store {
    const store = new substrate.Store(
      start.sqlite3,
      start.pool,
      start.cache,
      constants.root,
      settings.settings_get(constants.overflow_setting) as number,
      settings.settings_get(constants.blob_setting) as number,
      settings.settings_get(constants.compact_setting) as number,
      tasks,
    );
    store.handlers_register(dispatch.handler_register);
    return store;
  }

  // The browser's MCP server and tools, the two clients, the agent on `http`.
  export function tools_build(
    tasks: queue.TaskQueue,
    store: substrate.Store,
  ): ToolParts {
    const server = new mcp.Server(constants.server_name, constants.version);
    tools_browser.tools_register(
      server,
      store,
      tasks,
      constants.http_owner,
      constants.info,
      settings.settings_get,
      switches.debug_on,
    );
    dispatch.handler_register(
      constants.mcp_type,
      constants.handler_version,
      (line) => server.line_handle(line),
    );
    const browser = new mcp.Client(
      constants.client_name,
      constants.version,
      tasks,
      constants.thread,
    );
    const remote = new mcp.Client(
      constants.client_name,
      constants.version,
      tasks,
      constants.server_owner,
    );
    const clients = new mcp.ClientSet();
    clients.client_add(constants.browser_prefix, browser);
    clients.client_add(constants.server_prefix, remote);
    agent.handlers_register(
      store,
      clients,
      tasks,
      constants.http_owner,
      constants.info,
      dispatch.handler_register,
    );
    return { browser, server: remote, clients };
  }

  // Sets the key `scripted` and adds the port of the script row as `http`.
  export function provider_attach(
    tasks: queue.TaskQueue,
    store: substrate.Store,
  ): void {
    provider.key_set(constants.provider_key);
    const text = text_read(store, constants.script_ref);
    const script = jslb.json_decode(text) as provider_script.Script;
    tasks.port_add(
      constants.http_owner,
      new provider_script.ScriptPort(script),
    );
  }

  // Throws `engine.sync_differs` unless the reply names the store's databases.
  export function sync_check(store: substrate.Store, reply: lines.Line): void {
    const sent = jslb.payload_of(reply) as unknown as lines.DbSyncReply;
    const named = utility.json_text(sent.databases);
    const held = utility.json_text(store.db_list());
    if (named !== held) {
      throw new Error(i18n("engine.sync_differs", named, held));
    }
  }

  // The `render` line of the scene on screen, else `engine.scene_invalid`.
  export function render_make(store: substrate.Store): lines.Line {
    const world = text_read(store, constants.world_ref);
    const scene = text_read(store, `/${world}/${constants.scene_key}`);
    const { subtitle, image } = substrate.doc_decode(store.doc_get(scene));
    if (
      typeof subtitle !== "string" ||
      (image !== undefined && typeof image !== "string")
    ) {
      throw new Error(i18n("engine.scene_invalid", scene));
    }
    const payload =
      image === undefined ? { scene, subtitle } : { scene, subtitle, image };
    return line_typed(constants.render_type, payload);
  }

  // The `media.store` line of the image, its bytes read out of the store.
  export function media_make(
    store: substrate.Store,
    image: lines.KvRef,
  ): lines.Line {
    const blob = jslb.blob_make(bytes_read(store, image));
    return line_typed(constants.store_type, { k: image }, [blob]);
  }

  // Submits the render and sleeps on its reply, which ends the chain.
  function render_submit(
    tasks: queue.TaskQueue,
    render: lines.Line,
  ): dispatch.Sleep {
    const id = tasks.task_submit(render, constants.ui_owner);
    return dispatch.task_sleep(null, [id], constants.rendered_type);
  }

  // Submits a client's `initialize`, its sleep holding the client's prefix.
  function handshake_open(client: mcp.Client, prefix: string): dispatch.Sleep {
    const id = client.initialize_send();
    return dispatch.task_sleep(prefix, [id], constants.initialized_type);
  }

  // Registers the handler of `engine.start` and the wakes of the chain.
  export function chain_register(
    tasks: queue.TaskQueue,
    store: substrate.Store,
    tools: ToolParts,
  ): void {
    const version = constants.handler_version;
    const client_of = (prefix: string): mcp.Client =>
      prefix === constants.browser_prefix ? tools.browser : tools.server;
    dispatch.handler_register(constants.start_type, version, () =>
      handshake_open(tools.browser, constants.browser_prefix),
    );
    // Sends `initialized` and submits `tools/list` of the sleep's client.
    dispatch.handler_register(constants.initialized_type, version, (line) => {
      const prefix = line.state as string;
      const client = client_of(prefix);
      client.initialized_send(reply_of(line));
      const id = client.tools_list();
      return dispatch.task_sleep(prefix, [id], constants.listed_type);
    });
    // Keeps the tools, then starts the server's client, or the sync after it.
    dispatch.handler_register(constants.listed_type, version, (line) => {
      const prefix = line.state as string;
      client_of(prefix).tools_read(reply_of(line));
      if (prefix === constants.browser_prefix) {
        return handshake_open(tools.server, constants.server_prefix);
      }
      // The owner table gives `db.` to this thread, whose store takes pushes.
      const sync = line_typed(constants.sync_type, {});
      const id = tasks.task_submit(sync, constants.server_owner);
      return dispatch.task_sleep(null, [id], constants.synced_type);
    });
    // Checks the databases, adds the provider port and shows the first scene.
    dispatch.handler_register(constants.synced_type, version, (line) => {
      sync_check(store, reply_of(line));
      provider_attach(tasks, store);
      const render = render_make(store);
      const { image } = jslb.payload_of(render) as unknown as lines.Render;
      if (image === undefined) {
        return render_submit(tasks, render);
      }
      // The UI's cache is empty at a load, and its decode takes its time.
      const kept = media_make(store, image);
      const id = tasks.task_submit(kept, constants.ui_owner);
      return dispatch.task_sleep(render, [id], constants.stored_type);
    });
    // The UI holds the image, so the render that names it can paint.
    dispatch.handler_register(constants.stored_type, version, (line) =>
      render_submit(tasks, line.state as lines.Line),
    );
    dispatch.handler_register(
      constants.rendered_type,
      version,
      () => undefined,
    );
  }

  // Notifies `engine.start` to this thread, outside any task.
  export function chain_start(tasks: queue.TaskQueue): void {
    tasks.line_notify(line_typed(constants.start_type, {}), constants.thread);
  }

  // The worker's program, run by the bring up once `tap.start` is answered.
  export function worker_run(
    tasks: queue.TaskQueue,
    start: boot.WorkerStart,
  ): void {
    const first = jslb.payload_of(start.first) as unknown as lines.TapStart;
    if (!first.settings.provider.scripted) {
      throw new Error(i18n("engine.scripted_off"));
    }
    const store = store_build(tasks, start);
    const tools = tools_build(tasks, store);
    chain_register(tasks, store, tools);
    chain_start(tasks);
  }

  // The element of the document with the id given, which must be there.
  function element_find(id: string): HTMLElement {
    const element = document.getElementById(id);
    if (element === null) {
      throw new Error(i18n("engine.element_missing", id));
    }
    return element;
  }

  // The UI thread's program, run by the bring up at `settings.set`.
  export function page_run(tasks: queue.TaskQueue): void {
    const canvas = element_find(constants.image_id) as HTMLCanvasElement;
    const subtitle = element_find(constants.subtitle_id);
    const input = element_find(constants.input_id) as HTMLInputElement;
    const permit = element_find(constants.permit_id);
    const debug = element_find(constants.debug_id);
    const overlays = element_find(constants.overlays_id);
    // A paste past this is cut by the box, so the turn it says fits one line.
    const line_max = settings.settings_get(constants.line_setting) as number;
    input.maxLength = Math.floor(line_max / constants.text_bytes);
    const images = new media.MediaPort(
      settings.settings_get(constants.media_setting) as number,
      settings.settings_get(constants.timeout_setting) as number,
    );
    tasks.port_add(constants.media_owner, images);
    tasks.port_add(constants.dom_owner, new page.DomPort(document.body));
    page.handlers_register(
      {
        tasks,
        canvas,
        subtitle,
        input,
        permit,
        images,
        view: new console_view.ConsoleView(debug, tasks),
        overlays: new overlay.Overlay(overlays),
        debug: switches.debug_on(),
      },
      dispatch.handler_register,
    );
  }

  // The last script of the engine page, on both threads, by `self.name`.
  export function engine_start(): void {
    if (self.name === constants.worker_name) {
      boot.engine_worker(worker_run);
    } else {
      page.engine_page(page_run);
    }
  }
}

Object.freeze(engine);
