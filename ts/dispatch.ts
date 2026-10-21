// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The dispatcher: handlers registered by line type and version, the call of
// the one a line names, and the sleeps, replies and error lines it builds.

namespace dispatch {
  // The error line type and the header names that tell the name forms apart.
  const constants = Object.freeze({
    error_type: "error",
    full_marker: "type",
    reply_full: "reply",
    reply_short: "r",
  });

  // The reply of a handler: a line from `reply_make`, or nothing.
  export type Reply = { [key: string]: unknown } | undefined;

  // A sleep: the handler's state, the ids it waits for and the wake type.
  export interface Sleep {
    state: unknown;
    wait_ids: number[];
    then_type: string;
  }

  // A handler gets the line and returns a reply, a sleep or nothing.
  export type Handler = (line: lines.Line) => Reply | Sleep;

  // The handlers by type, then by version.
  const handlers = new Map<string, Map<unknown, Handler>>();

  // The last id given to each port.
  const ids = new Map<string, number>();

  // Says whether a header uses full names, which spell the type as `type`.
  function header_full(header: lines.LineHeader): boolean {
    return constants.full_marker in header;
  }

  // The name of the reply field in the name form of a header.
  function reply_name(header: lines.LineHeader): string {
    return header_full(header) ? constants.reply_full : constants.reply_short;
  }

  // The type of a line, which must be text.
  function type_get(line: lines.Line): string {
    const type = jslb.field_get(line[0], "type");
    if (typeof type === "string") {
      return type;
    }
    return utility.fail_now(i18n("dispatch.type_invalid", type));
  }

  // The id of a line, which is undefined for a notification.
  function id_get(line: lines.Line): number | undefined {
    const id = jslb.field_get(line[0], "id");
    if (id === undefined || typeof id === "number") {
      return id;
    }
    return utility.fail_now(
      i18n("dispatch.id_invalid", jslb.field_get(line[0], "type"), id),
    );
  }

  // Says whether an object is a sleep, which has all three of its fields.
  function sleep_is(value: object): value is Sleep {
    return "state" in value && "wait_ids" in value && "then_type" in value;
  }

  // Says whether an object is a line, which has its header at key 0.
  function line_is(value: { [key: string]: unknown }): value is lines.Line {
    const header = value[0];
    return typeof header === "object" && header !== null;
  }

  // The stack of an error, which must have one to be sent.
  function stack_get(error: Error): string {
    const stack = error.stack;
    if (stack === undefined) {
      throw utility.error_wrap(
        i18n("dispatch.stack_missing", error.message),
        error,
      );
    }
    return stack;
  }

  // Makes the sleep a handler returns to the task manager.
  export function task_sleep(
    state: unknown,
    wait_ids: number[],
    then_type: string,
  ): Sleep {
    return { state, wait_ids, then_type };
  }

  // Registers `fn` for one type and version. A second registration throws.
  export function handler_register(
    type: string,
    version: number,
    fn: Handler,
  ): void {
    let versions = handlers.get(type);
    if (versions === undefined) {
      versions = new Map<unknown, Handler>();
      handlers.set(type, versions);
    }
    if (versions.has(version)) {
      throw new Error(i18n("dispatch.handler_twice", type, version));
    }
    versions.set(version, fn);
  }

  // Calls the handler of the line's type and version and checks its result.
  export function line_dispatch(line: lines.Line): Reply | Sleep {
    const type = type_get(line);
    const version = jslb.field_get(line[0], "version");
    const fn = handlers.get(type)?.get(version);
    if (fn === undefined) {
      throw new Error(i18n("dispatch.handler_unknown", type, version));
    }
    const id = id_get(line);
    const result = fn(line);
    if (result === undefined) {
      if (id !== undefined) {
        throw new Error(
          i18n("dispatch.request_unanswered", type, version, id),
        );
      }
      return undefined;
    }
    if (sleep_is(result)) {
      return result;
    }
    if (!line_is(result)) {
      throw new Error(i18n("dispatch.reply_headerless", type, version));
    }
    if (id === undefined) {
      if (typeof jslb.field_get(result[0], "reply") !== "number") {
        throw new Error(i18n("dispatch.notification_replied", type, version));
      }
      return result;
    }
    Object.assign(result[0], { [reply_name(result[0])]: id });
    return result;
  }

  // Builds a reply to `line` with `r` set and the payload and blobs given.
  export function reply_make(
    line: lines.Line,
    payload: { [key: string]: unknown },
    blobs: lines.BlobHeader[] = [],
  ): lines.Line {
    const header = jslb.header_make(type_get(line), {
      reply: id_get(line),
      full: header_full(line[0]),
    });
    return jslb.line_make(header, blobs, payload);
  }

  // The one `error` line for a throw: `message`, `stack`, `r` when `i`.
  export function error_make(
    line: lines.Line | undefined,
    error: Error,
  ): lines.Line {
    const header = jslb.header_make(constants.error_type, {
      reply: line === undefined ? undefined : id_get(line),
      full: line !== undefined && header_full(line[0]),
    });
    return jslb.line_make(header, [], {
      message: error.message,
      stack: stack_get(error),
    });
  }

  // The next `i` for the port, from 1.
  export function id_next(port: string): number {
    const id = (ids.get(port) ?? 0) + 1;
    ids.set(port, id);
    return id;
  }
}

Object.freeze(dispatch);
