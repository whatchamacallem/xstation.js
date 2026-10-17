declare namespace settings {
  // The shape of settings.json, injected by `hello` unmodified.
  interface Settings {
    version: number;
    port_windows: number;
    port_wsl: number;
    line_max: number;
    blob_max: number;
    overflow_bytes: number;
    chunk_bytes: number;
    srv_buf_size: number;
    log_ring: number;
    media_db_bytes: number;
    files_browser_bytes: number;
    provider: {
      scripted: boolean;
      base_url: string;
      chat_model: string;
      image_model: string;
      timeout_seconds: number;
    };
    mcp_protocol_version: string;
    console_enabled: boolean;
    console_columns: number;
    console_rows: number;
    log_forward: boolean;
    long_task_ms: number;
  }

  // Stores the settings the hello carried, once per thread. A second
  // call throws.
  function settings_set(value: Settings): void;

  // Throws before `settings_set`.
  function settings_get(): Settings;
}
