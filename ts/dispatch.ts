// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The dispatcher: handlers registered by line type and version, the call of
// the one a line names, and the sleeps, failures, replies and error lines it
// builds. A handler is synchronous: it returns the reply line, nothing for a
// notification, a sleep, or a failure, which is a reply its request gets
// before the queue fails with the failure's error, so an answer is never
// lost to the fault after it. The reply of a failure is checked as a reply
// is: for a request it gets the request's `i` as its `r`, and for a line
// with no `i`, as a wake, it must already answer a request by its `r`.
//
// `error_make` writes a cascade as nested `cause` entries, by `cause_make`:
// the error's own `message` and `stack`, then under `cause` its `cause`, and
// so on, the first failure innermost. A thrown value or a `cause` that is
// not an Error is written as its text with an empty stack. An `error` line
// that answers a line takes that line's name form, and one that answers none
// takes the form `settings.names_full()` picks, full names before the
// settings exist. `id_next` counts each port's ids from 102, as 101 is the
// first line's.

namespace dispatch {
  // The error line type, the header names that tell the name forms apart and
  // the fixed id of the first line, `tap.start`, after which each port counts.
  const constants = Object.freeze({
    error_type: "error",
    full_marker: "type",
    reply_full: "reply",
    reply_short: "r",
    first_id: 101,
  });

  // A reply line, or nothing for a notification.
  export type Reply = lines.Line | undefined;

  // A sleep: the handler's state, the ids it waits for and the wake type.
  export interface Sleep {
    state: unknown;
    wait_ids: number[];
    then_type: string;
  }

  // A reply the queue posts before it fails with `error`.
  export interface Failure {
    reply: lines.Line;
    error: Error;
  }

  // A handler gets the line and returns a reply, a sleep, a failure or none.
  export type Handler = (line: lines.Line) => Reply | Sleep | Failure;

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

  // Says whether an object is a failure: its own reply and error, no key 0.
  function failure_is(value: object): value is Failure {
    return (
      Object.hasOwn(value, "reply") &&
      Object.hasOwn(value, "error") &&
      !Object.hasOwn(value, "0")
    );
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

  // Checks a reply a handler returned and sets its `r` to the line's `i`.
  function reply_check(
    type: string,
    version: unknown,
    id: number | undefined,
    reply: { [key: string]: unknown },
  ): void {
    if (!line_is(reply)) {
      throw new Error(i18n("dispatch.reply_headerless", type, version));
    }
    if (id === undefined) {
      if (typeof jslb.field_get(reply[0], "reply") !== "number") {
        throw new Error(i18n("dispatch.notification_replied", type, version));
      }
      return;
    }
    Object.assign(reply[0], { [reply_name(reply[0])]: id });
  }

  // Makes the sleep a handler returns to the task manager.
  export function task_sleep(
    state: unknown,
    wait_ids: number[],
    then_type: string,
  ): Sleep {
    return { state, wait_ids, then_type };
  }

  // Makes the failure a handler returns: the reply posted, then the error.
  export function failure_make(reply: lines.Line, error: Error): Failure {
    return { reply, error };
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
  export function line_dispatch(line: lines.Line): Reply | Sleep | Failure {
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
    if (failure_is(result)) {
      try {
        reply_check(type, version, id, result.reply);
      } catch (error) {
        throw utility.cause_append(error, result.error);
      }
      return result;
    }
    reply_check(type, version, id, result);
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

  // The one `error` line for a throw, its cascade under `cause`, `r` when `i`.
  export function error_make(
    line: lines.Line | undefined,
    error: unknown,
  ): lines.Line {
    const header = jslb.header_make(constants.error_type, {
      reply: line === undefined ? undefined : id_get(line),
      full: line === undefined ? settings.names_full() : header_full(line[0]),
    });
    return jslb.line_make(header, [], { ...cause_make(error) });
  }

  // The cascade of an error as the payload `error_make` writes.
  export function cause_make(error: unknown): lines.ErrorCause {
    if (!(error instanceof Error)) {
      return { message: String(error), stack: "" };
    }
    const entry: lines.ErrorCause = {
      message: error.message,
      stack: stack_get(error),
    };
    if (error.cause !== undefined) {
      entry.cause = cause_make(error.cause);
    }
    return entry;
  }

  // The next `i` for the port, from 102: 101 is the first line's.
  export function id_next(port: string): number {
    const id = (ids.get(port) ?? constants.first_id) + 1;
    ids.set(port, id);
    return id;
  }
}

Object.freeze(dispatch);
