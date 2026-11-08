// The AI's scripts: a script is the text of the KV row
// `/_files/script/<name>.js`, run inside the calling task by
// `new Function("engine", "args", text)`. `engine` is a frozen object of
// `store` and `i18n`, where `store` is a frozen object of the
// store's routine methods bound to the store: the operations of the tools,
// `turn_compact` and `transaction_run`, and not `db_open`, `db_close`,
// `kv_check`, `db_snapshot`, `db_restore`, `sink` or `handlers_register`,
// which would expose the store beyond routine queries. A run returns the
// value, or the exception with its stack. With `trace`, as `script_debug`
// runs it, each call of `store` is traced first, and the trace is one more
// field of the result, which is that tool's result and no record.

declare namespace script {
  // One traced call of `store`: milliseconds since the epoch and its text.
  interface TraceLine {
    at: number;
    text: string;
  }

  // What a run returned: the value or the exception, and a traced run's trace.
  interface ScriptResult {
    value?: unknown;
    error?: string;
    stack?: string;
    trace?: TraceLine[];
  }

  // The store's routine methods a script may call, bound to the store.
  type ScriptStore = Pick<
    substrate.Store,
    | "sql_run"
    | "db_list"
    | "db_create"
    | "db_drop"
    | "kv_get"
    | "kv_put"
    | "kv_delete"
    | "kv_list"
    | "doc_get"
    | "doc_put"
    | "doc_head"
    | "turn_append"
    | "turn_list"
    | "turn_compact"
    | "transaction_run"
  >;

  // The frozen object a script receives as `engine`.
  interface Engine {
    store: ScriptStore;
    i18n(name: string, ...args: unknown[]): string;
  }

  // Runs the script `name` with `args`, traced when `trace` is true.
  function script_run(
    store: substrate.Store,
    name: string,
    args: unknown,
    trace: boolean,
  ): ScriptResult;
}
