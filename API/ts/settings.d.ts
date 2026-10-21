declare namespace settings {
  // The shape of settings.json, sent in `hello` unmodified.
  interface Settings {
    debug: boolean;
    queue_synchronous: boolean;
    verbose_level: number;
    verbose_ring: number;
    line_max: number;
    blob_max: number;
    overflow_bytes: number;
    chunk_bytes: number;
    srv_buf_size: number;
    media_db_bytes: number;
    files_browser_bytes: number;
    db_soft_bytes: number;
    turn_compact_turns: number;
    long_task_ms: number;
    provider: {
      scripted: boolean;
      timeout_seconds: number;
    };
  }

  // The ids `settings_get` takes: every key, nested ones joined by `.`,
  // as `provider.timeout_seconds`.
  type Id = string;

  // Stores the settings the hello carried, once per thread; deep frozen
  // unless `debug` is true. A second call throws.
  function settings_set(value: Settings): void;

  // Throws before `settings_set` and on an unknown id.
  function settings_get(id: Id): unknown;

  // Debug mode only: changes the live value and submits `settings.put`
  // so the server rewrites the file for the next hello.
  function settings_put(id: Id, value: unknown): void;
}
