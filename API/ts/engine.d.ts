// The engine page's program, where the parts meet. The demo runs in scripted
// mode, `provider.scripted` true, the only mode built: a false setting throws
// `engine.scripted_off`, and `lines.d.ts` keeps the real provider's design.
// `tap_start` runs `worker_run` outside every task, where nothing can submit,
// so it builds the store and the tools, registers the chain and notifies
// `engine.start` to the worker itself.
//
// The chain of wakes: `engine.start` submits the browser's `initialize`, whose
// wake `engine.initialized` sends `initialized` and submits `tools/list`,
// whose wake `engine.listed` keeps the tools, each sleep holding its client's
// prefix as its state. The server's client then does the same over the wire.
// After it comes `db.sync` with the wake `engine.synced`, which checks the
// reply and adds the provider port. A scene's image then goes by `media.store`
// with the wake `engine.stored`; the render's wake `engine.rendered` ends it.
//
// The UI thread's program finds `image`, `subtitle`, `input`, `permit`,
// `debug` and `overlays` by id, else throws `engine.element_missing`. `debug`
// is the console view's container and holds `overlays`. The view fits its rows
// above the element after its container, so the band must follow `debug`, and
// `image` comes before `debug`, which shows over it by coming later.

declare namespace engine {
  // The two clients of the chain and the set the agent lists their tools from.
  interface ToolParts {
    // The client of the browser's MCP server, under the prefix `browser`.
    browser: mcp.Client;
    // The client of the server's MCP server, under the prefix `server`.
    server: mcp.Client;
    clients: mcp.ClientSet;
  }

  // The browser's store under the root `/engine`, its handlers registered.
  function store_build(
    tasks: queue.TaskQueue,
    start: boot.WorkerStart,
  ): substrate.Store;

  // The browser's MCP server and tools, the two clients, the agent on `http`.
  function tools_build(
    tasks: queue.TaskQueue,
    store: substrate.Store,
  ): ToolParts;

  // Sets the key `scripted` and adds the port of the script row as `http`.
  function provider_attach(
    tasks: queue.TaskQueue,
    store: substrate.Store,
  ): void;

  // Throws `engine.sync_differs` unless the reply names the store's databases.
  function sync_check(store: substrate.Store, reply: lines.Line): void;

  // The `render` line of the scene on screen, else `engine.scene_invalid`.
  function render_make(store: substrate.Store): lines.Line;

  // The `media.store` line of the image, its bytes read out of the store.
  function media_make(store: substrate.Store, image: lines.KvRef): lines.Line;

  // Registers the handler of `engine.start` and the wakes of the chain.
  function chain_register(
    tasks: queue.TaskQueue,
    store: substrate.Store,
    tools: ToolParts,
  ): void;

  // Notifies `engine.start` to this thread, outside any task.
  function chain_start(tasks: queue.TaskQueue): void;

  // The worker's program, run by the bring up once `tap.start` is answered.
  function worker_run(tasks: queue.TaskQueue, start: boot.WorkerStart): void;

  // The UI thread's program, run by the bring up at `settings.set`.
  function page_run(tasks: queue.TaskQueue): void;

  // The last script of the engine page, on both threads, by `self.name`.
  function engine_start(): void;
}
