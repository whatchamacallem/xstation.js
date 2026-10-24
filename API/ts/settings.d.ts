// The settings of `settings.json`, which `tap.start` carries unmodified, set
// once per thread, read by id and, in debug mode, changed by id. The file
// also holds the constants of the PowerShell scripts, under `powershell`,
// which the browser receives and does not read.
//
// The limits, every one set so that the largest database moves as one blob:
// `blob_max` is the largest database, the one hard bound of a database's
// size. It bounds the blob bytes of one message in all, so a database file
// is the one blob of its `db.restore` line, and each cache file, which is a
// value over `overflow_bytes` or the blob of a `db.file` line, is at most
// `blob_max` too. It bounds the blob bytes a queue and the wire's frame queue
// hold in memory, a blob streamed to a cache file counting nothing.
// `line_max` bounds the JSON text of one line without its blobs, so one
// message is at most `line_max` plus `blob_max` bytes. It bounds a verbose
// entry: a `verbose.put` that holds one entry stays below it, and a wire
// line whose rendering would not fit is logged as its header and the sizes
// of its payload and blobs only. A blob over `overflow_bytes` streams to a
// cache file as it arrives. `chunk_bytes` is one input frame of the wire and
// one read of the server. `srv_buf_size` is ttyd's receive chunk, for the
// start script's ttyd and the tests' alike. The first line is read before
// the settings exist, under the fixed bound `first_line_max` of the wire,
// 10 MiB, which `settings.json` and `test_settings.json` together fit.
//
// `names_full()` is the one choice of the name form of the lines a thread
// builds: full names until the settings are set, then full names when
// `debug` is true and short names otherwise.

declare namespace settings {
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
    turn_compact_turns: number;
    provider: {
      scripted: boolean;
      timeout_seconds: number;
      variable: string;
    };
    powershell: {
      windows_port: number;
      linux_port: number;
      bind_address: string;
      bootstrap_script: string;
      engine_page: string;
      ttyd_build: string;
      ttyd_archive: string;
      ttyd_patches: string;
      terminal_type: string;
      linux_folder: string;
      distribution: string;
      task_name: string;
      firewall_rule: string;
      state_folder: string;
      certificate_file: string;
      key_file: string;
      certificate_days: number;
      runner_file: string;
      ttyd_log_file: string;
      poll_tries: number;
      poll_milliseconds: number;
      output_width: number;
      root_files: string[];
      runtime_modules: string[];
      build_tools: { [tool: string]: string };
      build_headers: { [header: string]: string };
    };
  }

  // An id is a key, nested keys joined by `.`, as `provider.timeout_seconds`.
  type Id = string;

  // Stores the settings `tap.start` carried, once per thread.
  function settings_set(value: Settings): void;

  // Throws before `settings_set` and on an unknown id.
  function settings_get(id: Id): unknown;

  // Debug mode only: changes the live value and sends `settings.put`.
  function settings_put(id: Id, value: unknown): void;

  // Registers the function that sends `settings.put` for this thread, once.
  function sender_register(sender: (payload: lines.SettingsPut) => void): void;

  // Whether this thread builds its lines in full names, as described above.
  function names_full(): boolean;
}
