declare namespace boot {
  // The one bundle runs on three threads. `boot_run` reads `self.name`:
  // undefined on the main thread, "ai" or "wasm" in a worker.
  function boot_run(): void;

  // UI: builds the DOM, creates the workers from the bundle's Blob URL,
  // installs log capture, routes input, paints renders, hosts the
  // console view and the fault display.
  function page_main(): void;

  // AI: owner table, store proxy, wire, MCP servers and clients, agent,
  // replication scheduler.
  function worker_ai_main(): void;

  // WASM: sqlite3.wasm, the store, its handlers.
  function worker_wasm_main(): void;
}
