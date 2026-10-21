// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The AI's scripts, the database administrator: a script is the text of the
// KV row `/_files/script/<name>.js`, run inside the calling task as the body
// of a `new Function` taking `engine`, the frozen object of the store, the
// verbose log and `i18n`, and `args`. A run returns the value, or the
// exception with its stack, and every verbose line it wrote. A traced run,
// as `script_debug` asks for, traces each call the script makes through the
// store first.

namespace script {
  // The row of a script: the prefix and the suffix around its name.
  const constants = Object.freeze({
    script_prefix: "/_files/script/",
    script_suffix: ".js",
  });

  // What a run returned: the value or the exception, and the lines it wrote.
  export interface ScriptResult {
    value?: unknown;
    error?: string;
    stack?: string;
    lines: lines.VerboseLine[];
  }

  // The frozen object a script gets as `engine`: the store, the log, `i18n`.
  export interface Engine {
    store: substrate.Store;
    log(text: string): void;
    i18n(name: string, ...args: unknown[]): string;
  }

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

  // The store seen through a proxy that traces each method call first.
  function store_traced(
    store: substrate.Store,
    line_write: (text: string) => void,
  ): substrate.Store {
    return new Proxy(store, {
      // A method of the store, wrapped to write its trace line first.
      get(target: substrate.Store, property: string | symbol): unknown {
        const member: unknown = Reflect.get(target, property);
        if (typeof member !== "function") {
          return member;
        }
        return (...values: unknown[]): unknown => {
          const call = String(property);
          const shown = arguments_text(values);
          line_write(i18n("script.trace_call", call, shown));
          return Reflect.apply(member, target, values);
        };
      },
    });
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
    const door = trace ? store_traced(store, line_write) : store;
    const engine: Engine = Object.freeze({
      store: door,
      log: line_write,
      i18n,
    });
    try {
      const body = new Function("engine", "args", text);
      const value: unknown = body(engine, args);
      return { value, lines: kept };
    } catch (thrown) {
      return { ...thrown_fields(thrown), lines: kept };
    }
  }
}

Object.freeze(script);
