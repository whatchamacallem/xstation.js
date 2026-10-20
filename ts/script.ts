// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The AI's scripts, the database administrator: a script is the text of the
// KV row `/_files/script/<name>.js`, run inside the calling task as the body
// of a `new Function` taking `engine`, the frozen object of the store, the
// verbose log and `i18n`, and `args`. A run returns the value, or the
// exception with its stack, and the verbose lines it wrote at its level. At
// level 2 each call the script makes through the store is traced first.

namespace script {
  // The row of a script, the highest run level and the level of a trace.
  const constants = Object.freeze({
    script_prefix: "/_files/script/",
    script_suffix: ".js",
    level_max: 2,
    trace_level: 2,
  });

  // What a run returned: the value or the exception, and the lines it kept.
  export interface ScriptResult {
    value?: unknown;
    error?: string;
    stack?: string;
    lines: lines.VerboseLine[];
  }

  // The frozen object a script gets as `engine`: the store, the log, `i18n`.
  export interface Engine {
    store: substrate.Store;
    log(level: number, text: string): void;
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
    line_write: (level: number, text: string) => void,
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
          line_write(
            constants.trace_level,
            i18n("script.trace_call", call, shown),
          );
          return Reflect.apply(member, target, values);
        };
      },
    });
  }

  // Runs the script of the name on the arguments at the verbose level given.
  export function script_run(
    store: substrate.Store,
    name: string,
    args: unknown,
    level: number,
  ): ScriptResult {
    if (!Number.isInteger(level) || level < 0 || level > constants.level_max) {
      throw new Error(
        i18n("script.level_invalid", level, constants.level_max),
      );
    }
    const ref = constants.script_prefix + name + constants.script_suffix;
    const text = value_text(store, ref);
    const kept: lines.VerboseLine[] = [];
    // Logs on the thread, and keeps the line when the run's level allows.
    const line_write = (line_level: number, line_text: string): void => {
      verbose.log(line_level, line_text);
      if (line_level <= level) {
        kept.push({
          at: utility.time_now(),
          level: line_level,
          text: line_text,
        });
      }
    };
    const door =
      level < constants.trace_level ? store : store_traced(store, line_write);
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
