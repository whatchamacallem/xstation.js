// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The AI's scripts: a script is the text of the KV row
// `/_files/script/<name>.js`, run inside the calling task by
// `new Function("engine", "args", text)`. `engine` is a frozen object of
// `store`, `verbose.log` and `i18n`, where `store` is a frozen object of the
// store's routine methods bound to the store: the operations of the tools,
// `turn_compact` and `transaction_run`, and not `db_open`, `db_close`,
// `kv_check`, `db_snapshot`, `db_restore`, `sink` or `handlers_register`,
// which would expose the store beyond routine queries. A run returns the
// value, or the exception with its stack, and the verbose lines the run
// wrote. With `trace`, as `script_debug` runs it, each call of `store` is
// traced first.

namespace script {
  // The row of a script and the names of the store's routine methods.
  const constants = Object.freeze({
    script_prefix: "/_files/script/",
    script_suffix: ".js",
    store_methods: Object.freeze([
      "sql_run",
      "db_list",
      "db_create",
      "db_drop",
      "kv_get",
      "kv_put",
      "kv_delete",
      "kv_list",
      "doc_get",
      "doc_put",
      "doc_head",
      "turn_append",
      "turn_list",
      "turn_compact",
      "transaction_run",
    ] as const),
  });

  // What a run returned: the value or the exception, and the lines it wrote.
  export interface ScriptResult {
    value?: unknown;
    error?: string;
    stack?: string;
    lines: lines.VerboseLine[];
  }

  // The store's routine methods a script may call, bound to the store.
  export type ScriptStore = Pick<
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

  // The frozen object a script gets as `engine`: the store, the log, `i18n`.
  export interface Engine {
    store: ScriptStore;
    log(text: string): void;
    i18n(name: string, ...args: unknown[]): string;
  }

  // A method of the store, called with any arguments.
  type MethodCall = (...values: unknown[]) => unknown;

  // The text of a KV value, read from the cache when it is held there.
  function value_text(store: substrate.Store, ref: string): string {
    const value = store.kv_get(ref);
    const cache = store.sink() as substrate.CacheFiles;
    const data =
      typeof value.data === "string"
        ? cache.cache_read(value.data, 0, value.size)
        : value.data;
    return utility.utf8_decode(data);
  }

  // A JSON replacer that shows bytes by their count.
  function bytes_counted(_key: string, value: unknown): unknown {
    return value instanceof Uint8Array ? { bytes: value.length } : value;
  }

  // The JSON text of the arguments of a traced call.
  function arguments_text(values: unknown[]): string {
    return JSON.stringify(values, bytes_counted);
  }

  // The text of what a script threw, with the stack when it is an `Error`.
  function thrown_fields(thrown: unknown): { error: string; stack?: string } {
    if (thrown instanceof Error) {
      return { error: String(thrown), stack: thrown.stack };
    }
    return { error: String(thrown) };
  }

  // The frozen object of the store's routine methods, each bound to it.
  function store_routine(store: substrate.Store): ScriptStore {
    const routine: { [name: string]: MethodCall } = {};
    for (const name of constants.store_methods) {
      const method = Reflect.get(store, name) as MethodCall;
      routine[name] = method.bind(store);
    }
    return Object.freeze(routine) as unknown as ScriptStore;
  }

  // The same methods, each writing its trace line before it runs.
  function store_traced(
    store: ScriptStore,
    line_write: (text: string) => void,
  ): ScriptStore {
    const traced: { [name: string]: MethodCall } = {};
    for (const name of constants.store_methods) {
      const method = Reflect.get(store, name) as MethodCall;
      traced[name] = (...values: unknown[]): unknown => {
        line_write(i18n("script.trace_call", name, arguments_text(values)));
        return method(...values);
      };
    }
    return Object.freeze(traced) as unknown as ScriptStore;
  }

  // Runs the script of the name on the arguments, traced when asked.
  export function script_run(
    store: substrate.Store,
    name: string,
    args: unknown,
    trace: boolean,
  ): ScriptResult {
    const ref = constants.script_prefix + name + constants.script_suffix;
    const text = value_text(store, ref);
    const kept: lines.VerboseLine[] = [];
    // Logs on the thread and keeps every line for the result.
    const line_write = (line_text: string): void => {
      verbose.log(line_text);
      kept.push({ at: utility.time_now(), text: line_text });
    };
    const routine = store_routine(store);
    const door = trace ? store_traced(routine, line_write) : routine;
    const engine: Engine = Object.freeze({
      store: door,
      log: line_write,
      i18n,
    });
    try {
      const body = new Function("engine", "args", text);
      const value: unknown = body(engine, args);
      // A value JSON cannot carry is the run's exception, not the tool's.
      utility.json_text({ value });
      return { value, lines: kept };
    } catch (thrown) {
      return { ...thrown_fields(thrown), lines: kept };
    }
  }
}

Object.freeze(script);
