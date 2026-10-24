// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Tests of the dispatcher: registration, dispatch by type and version, the
// rules for replies, sleeps and failures, the reply and error lines it
// builds, the cascades it writes and the ids it counts from 102. The lines
// the tests send and expect and the texts of the throws are those of the
// gold record, test_settings.json, each fresh type set on the copy.

namespace test_dispatch {
  // The prefixes of the types and ports the tests make, which are their own.
  const constants = Object.freeze({
    type_prefix: "dispatch_test.",
    port_prefix: "dispatch_test_port_",
  });

  // How many types the tests have made, so that each one is new.
  let types_made = 0;

  // How many ports the tests have made, so that each one is new.
  let ports_made = 0;

  // A handler and the lines it has been called with.
  interface HandlerRecord {
    seen: lines.Line[];
    fn: dispatch.Handler;
  }

  // A type that no other test registers.
  function type_fresh(): string {
    types_made += 1;
    return `${constants.type_prefix}${types_made}`;
  }

  // A port name that no other test counts ids for.
  function port_fresh(): string {
    ports_made += 1;
    return `${constants.port_prefix}${ports_made}`;
  }

  // A copy of a value of this module's gold, which the harness keeps frozen.
  function gold_value(name: string): unknown {
    return structuredClone(
      harness.gold_get(`typescript.test_dispatch.${name}`),
    );
  }

  // A text of this module's gold, a run time `{n}` left for the test to fill.
  function gold_text(name: string): string {
    return harness.gold_get(
      `typescript.test_dispatch.texts.${name}`,
    ) as string;
  }

  // A copy of a line of this module's gold, a run time part set on the copy.
  function gold_line(name: string): lines.Line {
    return gold_value(`lines.${name}`) as lines.Line;
  }

  // A copy of a gold line in short names, the fresh type set as `t`.
  function line_short(name: string, type: string): lines.Line {
    const line = gold_line(name);
    Object.assign(line[0], { t: type });
    return line;
  }

  // A copy of a gold line in full names, the fresh type set as `type`.
  function line_full(name: string, type: string): lines.Line {
    const line = gold_line(name);
    Object.assign(line[0], { type });
    return line;
  }

  // Makes a handler that records its lines and always returns the result.
  function record_make(
    result: dispatch.Reply | dispatch.Sleep | dispatch.Failure,
  ): HandlerRecord {
    const seen: lines.Line[] = [];
    return {
      seen,
      fn: (line) => {
        seen.push(line);
        return result;
      },
    };
  }

  // The error the function throws, and an error of its own when it doesn't.
  function thrown_get(fn: () => unknown): Error {
    try {
      fn();
    } catch (error) {
      if (error instanceof Error) {
        return error;
      }
      throw error;
    }
    throw new Error("Nothing was thrown.");
  }

  // The registration of handlers.
  export class TestHandlerRegistration extends unittest.TestCase {
    // A second registration of a pair throws and the first one stays.
    test_twice_throws(): void {
      const type = type_fresh();
      const first = record_make(undefined);
      const second = record_make(undefined);
      dispatch.handler_register(type, 0, first.fn);
      const error = thrown_get(() =>
        dispatch.handler_register(type, 0, second.fn),
      );
      this.assertEqual(
        error.message,
        gold_text("dispatch_handler_twice").replaceAll("{0}", type),
      );
      dispatch.line_dispatch(line_short("notification", type));
      this.assertEqual(first.seen.length, 1);
      this.assertEqual(second.seen.length, 0);
    }

    // The same type at another version, and another type, register.
    test_pairs_differ(): void {
      const type = type_fresh();
      const other = type_fresh();
      const records = [
        record_make(undefined),
        record_make(undefined),
        record_make(undefined),
      ];
      dispatch.handler_register(type, 0, records[0].fn);
      dispatch.handler_register(type, 1, records[1].fn);
      dispatch.handler_register(other, 0, records[2].fn);
      dispatch.line_dispatch(line_short("notification", type));
      dispatch.line_dispatch(line_short("versioned", type));
      dispatch.line_dispatch(line_short("notification", other));
      for (const record of records) {
        this.assertEqual(record.seen.length, 1);
      }
    }
  }

  // The call of the handler a line names and the rules for its result.
  export class TestLineDispatch extends unittest.TestCase {
    // Only the handler of the line's type and version is called.
    test_handler_called(): void {
      const type = type_fresh();
      const other = type_fresh();
      const first = record_make(undefined);
      const versioned = record_make(undefined);
      const elsewhere = record_make(undefined);
      dispatch.handler_register(type, 0, first.fn);
      dispatch.handler_register(type, 1, versioned.fn);
      dispatch.handler_register(other, 0, elsewhere.fn);
      const line = line_short("versioned_text", type);
      this.assertEqual(dispatch.line_dispatch(line), undefined);
      this.assertEqual(versioned.seen.length, 1);
      this.assertTrue(versioned.seen[0] === line);
      this.assertEqual(first.seen.length, 0);
      this.assertEqual(elsewhere.seen.length, 0);
    }

    // A line with no version reaches the handler of version 0.
    test_version_default(): void {
      const type = type_fresh();
      const zero = record_make(undefined);
      dispatch.handler_register(type, 0, zero.fn);
      dispatch.line_dispatch(line_short("notification", type));
      dispatch.line_dispatch(line_short("notification", type));
      this.assertEqual(zero.seen.length, 2);
    }

    // The handler gets the line itself, with its blobs and payload in place.
    test_line_whole(): void {
      const type = type_fresh();
      const record = record_make(undefined);
      dispatch.handler_register(type, 0, record.fn);
      const data = new Uint8Array([1, 2, 3]);
      const line = line_short("blob_line", type);
      Object.assign(line[1] as lines.BlobHeader, { d: data });
      const blob = gold_line("blob_line")[1] as lines.BlobHeader;
      blob.d = data;
      dispatch.line_dispatch(line);
      this.assertTrue(record.seen[0] === line);
      this.assertEqual(line.n, 1);
      this.assertEqual(line[1], blob);
    }

    // A type or a version that nothing registered throws.
    test_pair_unknown(): void {
      const type = type_fresh();
      const other = type_fresh();
      dispatch.handler_register(type, 0, record_make(undefined).fn);
      const type_error = thrown_get(() =>
        dispatch.line_dispatch(line_short("notification", other)),
      );
      this.assertEqual(
        type_error.message,
        gold_text("dispatch_handler_unknown_type").replaceAll("{0}", other),
      );
      const version_error = thrown_get(() =>
        dispatch.line_dispatch(line_short("versioned", type)),
      );
      this.assertEqual(
        version_error.message,
        gold_text("dispatch_handler_unknown_version").replaceAll("{0}", type),
      );
    }

    // An error from a handler propagates unchanged.
    test_handler_throws(): void {
      const type = type_fresh();
      const failure = new Error("missing");
      dispatch.handler_register(type, 0, () => {
        throw failure;
      });
      const line = line_short("request_7", type);
      const error = thrown_get(() => dispatch.line_dispatch(line));
      this.assertTrue(error === failure);
    }

    // A request gets the reply its handler returned, with `r` set to its `i`.
    test_request_reply(): void {
      const type = type_fresh();
      const request = line_short("request_7", type);
      const reply = dispatch.reply_make(request, { n: 1 });
      dispatch.handler_register(type, 0, record_make(reply).fn);
      this.assertTrue(dispatch.line_dispatch(request) === reply);
      this.assertEqual(reply[0], { t: type, r: 7 });
    }

    // A full name request is answered in full names.
    test_full_request(): void {
      const type = type_fresh();
      const request = line_full("request_full_9", type);
      const reply = dispatch.reply_make(request, { n: 1 });
      dispatch.handler_register(type, 0, record_make(reply).fn);
      this.assertTrue(dispatch.line_dispatch(request) === reply);
      this.assertEqual(reply[0], { type, reply: 9 });
    }

    // A reply without `r` gets it, spelled in the name form of its header.
    test_reply_unset(): void {
      const short_type = type_fresh();
      const full_type = type_fresh();
      const short_reply = line_short("notification", short_type);
      const full_reply = line_full("notification", full_type);
      dispatch.handler_register(short_type, 0, record_make(short_reply).fn);
      dispatch.handler_register(full_type, 0, record_make(full_reply).fn);
      dispatch.line_dispatch(line_short("request_7", short_type));
      dispatch.line_dispatch(line_short("request_8", full_type));
      this.assertEqual(short_reply[0], { t: short_type, r: 7 });
      this.assertEqual(full_reply[0], { type: full_type, reply: 8 });
    }

    // A reply that names another request is changed to name this one.
    test_reply_overwritten(): void {
      const type = type_fresh();
      const reply = dispatch.reply_make(line_short("request_3", type), {});
      dispatch.handler_register(type, 0, record_make(reply).fn);
      dispatch.line_dispatch(line_short("request_7", type));
      this.assertEqual(reply[0], { t: type, r: 7 });
    }

    // A request whose handler returns nothing throws.
    test_request_none(): void {
      const type = type_fresh();
      dispatch.handler_register(type, 0, record_make(undefined).fn);
      const error = thrown_get(() =>
        dispatch.line_dispatch(line_short("request_7", type)),
      );
      this.assertEqual(
        error.message,
        gold_text("dispatch_request_unanswered").replaceAll("{0}", type),
      );
    }

    // A notification whose handler returns nothing returns nothing.
    test_notification_none(): void {
      const type = type_fresh();
      dispatch.handler_register(type, 0, record_make(undefined).fn);
      const line = line_short("notification_text", type);
      this.assertEqual(dispatch.line_dispatch(line), undefined);
    }

    // A notification whose handler returns a reply to no request throws.
    test_notification_reply(): void {
      const type = type_fresh();
      const notification = line_short("notification", type);
      const reply = dispatch.reply_make(notification, {});
      dispatch.handler_register(type, 0, record_make(reply).fn);
      const error = thrown_get(() => dispatch.line_dispatch(notification));
      this.assertEqual(
        error.message,
        gold_text("dispatch_notification_replied").replaceAll("{0}", type),
      );
    }

    // A wake line has no id and may return the reply to an earlier request.
    test_wake_reply(): void {
      const wake_type = type_fresh();
      const request_type = type_fresh();
      const request = line_short("request_5", request_type);
      const reply = dispatch.reply_make(request, { turn: 7 });
      dispatch.handler_register(wake_type, 0, record_make(reply).fn);
      const line = line_short("wake", wake_type);
      line.state = request;
      this.assertTrue(dispatch.line_dispatch(line) === reply);
      this.assertEqual(reply[0], { t: request_type, r: 5 });
    }

    // A reply with no header throws, for a request and for a notification.
    test_reply_headerless(): void {
      const type = type_fresh();
      const headerless = { n: 1 } as unknown as lines.Line;
      dispatch.handler_register(type, 0, record_make(headerless).fn);
      for (const name of ["request_7", "notification"]) {
        const error = thrown_get(() =>
          dispatch.line_dispatch(line_short(name, type)),
        );
        this.assertEqual(
          error.message,
          gold_text("dispatch_reply_headerless").replaceAll("{0}", type),
        );
      }
    }
  }

  // The sleep a handler returns.
  export class TestTaskSleep extends unittest.TestCase {
    // The sleep holds the state, the ids and the type it was given.
    test_sleep_fields(): void {
      const state = { step: 2 };
      const then_type = type_fresh();
      const sleep = dispatch.task_sleep(state, [3, 4], then_type);
      this.assertTrue(sleep.state === state);
      this.assertEqual(sleep, { state, wait_ids: [3, 4], then_type });
    }

    // A sleep comes back unchanged, from a request and from a notification.
    test_sleep_returned(): void {
      const type = type_fresh();
      const then_type = type_fresh();
      const sleep = dispatch.task_sleep({ step: 1 }, [1, 2], then_type);
      dispatch.handler_register(type, 0, record_make(sleep).fn);
      this.assertTrue(
        dispatch.line_dispatch(line_short("request_7", type)) === sleep,
      );
      this.assertTrue(
        dispatch.line_dispatch(line_short("notification", type)) === sleep,
      );
      this.assertEqual(sleep, {
        state: { step: 1 },
        wait_ids: [1, 2],
        then_type,
      });
    }
  }

  // The failure a handler returns: a reply, then the queue fails.
  export class TestFailure extends unittest.TestCase {
    // The failure holds the reply and the error it was given.
    test_failure_fields(): void {
      const reply = line_short("notification", type_fresh());
      const error = new Error("boom");
      const failure = dispatch.failure_make(reply, error);
      this.assertTrue(failure.reply === reply);
      this.assertTrue(failure.error === error);
      this.assertEqual(Object.keys(failure).sort(), ["error", "reply"]);
    }

    // The reply of a request's failure gets `r`, the failure comes back.
    test_request_failure(): void {
      const type = type_fresh();
      const reply = line_short("notification_n", type);
      const failure = dispatch.failure_make(reply, new Error("boom"));
      dispatch.handler_register(type, 0, record_make(failure).fn);
      const result = dispatch.line_dispatch(line_short("request_7", type));
      this.assertTrue(result === failure);
      this.assertEqual(reply[0], { t: type, r: 7 });
    }

    // The failure of a wake whose reply answers a request comes back as is.
    test_wake_failure(): void {
      const wake_type = type_fresh();
      const request_type = type_fresh();
      const request = line_short("request_5", request_type);
      const reply = dispatch.reply_make(request, { turn: 7 });
      const failure = dispatch.failure_make(reply, new Error("boom"));
      dispatch.handler_register(wake_type, 0, record_make(failure).fn);
      const line = line_short("wake", wake_type);
      line.state = request;
      this.assertTrue(dispatch.line_dispatch(line) === failure);
      this.assertEqual(reply[0], { t: request_type, r: 5 });
    }

    // A failure whose reply answers no request, of a line with no id, throws.
    test_notification_failure(): void {
      const type = type_fresh();
      const reply = line_short("notification", type);
      const failure = dispatch.failure_make(reply, new Error("boom"));
      dispatch.handler_register(type, 0, record_make(failure).fn);
      const error = thrown_get(() =>
        dispatch.line_dispatch(line_short("notification", type)),
      );
      this.assertEqual(
        error.message,
        gold_text("dispatch_notification_replied").replaceAll("{0}", type),
      );
    }
  }

  // The reply line a handler builds.
  export class TestReplyMake extends unittest.TestCase {
    // A short name reply has `t` and `r` and nothing else of the request.
    test_short_names(): void {
      const type = type_fresh();
      const request = line_short("request_keyed", type);
      const reply = dispatch.reply_make(request, { found: true, size: 3 });
      this.assertEqual(reply[0], { t: type, r: 7 });
      this.assertFalse("1" in reply);
      this.assertEqual(reply, line_short("reply_found", type));
    }

    // A full name reply has `type` and `reply` and nothing else.
    test_full_names(): void {
      const type = type_fresh();
      const request = line_full("request_keyed_full", type);
      const reply = dispatch.reply_make(request, { found: true, size: 3 });
      this.assertEqual(reply[0], { type, reply: 7 });
      this.assertFalse("1" in reply);
      this.assertEqual(reply, line_full("reply_found_full", type));
    }

    // A reply to a notification has no `r`.
    test_id_absent(): void {
      const type = type_fresh();
      const notification = line_short("notification", type);
      const reply = dispatch.reply_make(notification, { n: 1 });
      this.assertEqual(reply[0], { t: type });
    }

    // Blobs are numbered from 1 and counted, apart from the payload.
    test_blobs_numbered(): void {
      const request = line_short("request_3", type_fresh());
      const first = gold_value("lines.blob_three") as lines.BlobHeader;
      first.d = new Uint8Array([1, 2, 3]);
      const second = gold_value("lines.blob_two") as lines.BlobHeader;
      second.d = new Uint8Array([4, 5]);
      const reply = dispatch.reply_make(request, { seq: 4 }, [first, second]);
      this.assertEqual(reply[0].b, 2);
      this.assertEqual(reply[1], first);
      this.assertEqual(reply[2], second);
      this.assertFalse("3" in reply);
      this.assertEqual(Object.keys(reply), ["0", "1", "2", "seq"]);
      this.assertEqual(reply.seq, 4);
    }
  }

  // The error line.
  export class TestErrorMake extends unittest.TestCase {
    // The error line of a request has `r`, the message and the stack.
    test_request_error(): void {
      const error = new Error("boom");
      const request = line_short("request_5", type_fresh());
      const line = dispatch.error_make(request, error);
      this.assertEqual(line[0], { t: "error", r: 5 });
      this.assertEqual(Object.keys(line), ["0", "message", "stack"]);
      this.assertEqual(line.message, "boom");
      this.assertEqual(line.stack, error.stack);
    }

    // The error line of a full name request uses full names.
    test_full_error(): void {
      const request = line_full("request_full_5", type_fresh());
      const line = dispatch.error_make(request, new Error("boom"));
      this.assertEqual(line[0], { type: "error", reply: 5 });
    }

    // The error line of a notification has no `r`.
    test_notification_error(): void {
      const notification = line_short("notification", type_fresh());
      const line = dispatch.error_make(notification, new Error("boom"));
      this.assertEqual(line[0], { t: "error" });
      this.assertEqual(line.message, "boom");
    }

    // The error line of no line has no `r`, in the form the settings pick.
    test_no_line(): void {
      const line = dispatch.error_make(undefined, new Error("boom"));
      if (harness.setting_get("debug") === true) {
        this.assertEqual(line[0], { type: "error" });
      } else {
        this.assertEqual(line[0], { t: "error" });
      }
    }

    // An error with no stack cannot be sent, so it throws.
    test_stack_missing(): void {
      const error = new Error("boom");
      Object.defineProperty(error, "stack", { value: undefined });
      const thrown = thrown_get(() => dispatch.error_make(undefined, error));
      const message = gold_text("dispatch_stack_missing_line");
      this.assertEqual(thrown.message, message);
    }

    // The error line carries the cascade under `cause`, the first innermost.
    test_cascade(): void {
      const first = new Error("first");
      const error = new Error("second", { cause: first });
      const request = line_short("request_5", type_fresh());
      const line = dispatch.error_make(request, error);
      this.assertEqual(Object.keys(line), ["0", "message", "stack", "cause"]);
      this.assertEqual(line, {
        ...gold_line("error_request_5"),
        message: "second",
        stack: error.stack,
        cause: { message: "first", stack: first.stack },
      });
    }

    // A thrown value that is no `Error` is written as its text, no stack.
    test_value_thrown(): void {
      const line = dispatch.error_make(undefined, "boom");
      this.assertEqual(line, gold_line("error_value"));
    }
  }

  // The cascade of an error as nested `cause` entries.
  export class TestCauseMake extends unittest.TestCase {
    // An `Error` with two nested causes gives three entries, nested in order.
    test_nested_errors(): void {
      const first = new Error("first");
      const second = new Error("second", { cause: first });
      const third = new Error("third", { cause: second });
      this.assertEqual(dispatch.cause_make(third), {
        message: "third",
        stack: third.stack,
        cause: {
          message: "second",
          stack: second.stack,
          cause: { message: "first", stack: first.stack },
        },
      });
    }

    // A `cause` that is no `Error` is written as its text with no stack.
    test_cause_value(): void {
      const error = new Error("outer", { cause: 7 });
      this.assertEqual(dispatch.cause_make(error), {
        message: "outer",
        stack: error.stack,
        cause: { message: "7", stack: "" },
      });
    }

    // A thrown value that is no `Error` is written as its text with no stack.
    test_value_thrown(): void {
      this.assertEqual(dispatch.cause_make(undefined), {
        message: "undefined",
        stack: "",
      });
    }

    // A nested `Error` with no stack cannot be sent, so it throws.
    test_stack_missing(): void {
      const inner = new Error("inner");
      Object.defineProperty(inner, "stack", { value: undefined });
      const error = new Error("outer", { cause: inner });
      const thrown = thrown_get(() => dispatch.cause_make(error));
      const message = gold_text("dispatch_stack_missing_nested");
      this.assertEqual(thrown.message, message);
    }
  }

  // The kinds of the header fields the dispatcher reads.
  export class TestHeaderKinds extends unittest.TestCase {
    // A type that is not text throws in each call that reads it.
    test_type_invalid(): void {
      const line = { 0: { t: 5 } } as unknown as lines.Line;
      const message = gold_text("dispatch_type_invalid");
      const dispatched = thrown_get(() => dispatch.line_dispatch(line));
      const replied = thrown_get(() => dispatch.reply_make(line, {}));
      this.assertEqual(dispatched.message, message);
      this.assertEqual(replied.message, message);
    }

    // An id that is not a number throws, before the handler is called.
    test_id_invalid(): void {
      const type = type_fresh();
      const record = record_make(undefined);
      dispatch.handler_register(type, 0, record.fn);
      const line = { 0: { t: type, i: "7" } } as unknown as lines.Line;
      const message = gold_text("dispatch_id_invalid").replaceAll("{0}", type);
      const dispatched = thrown_get(() => dispatch.line_dispatch(line));
      const replied = thrown_get(() => dispatch.reply_make(line, {}));
      const failed = thrown_get(() =>
        dispatch.error_make(line, new Error("boom")),
      );
      this.assertEqual(dispatched.message, message);
      this.assertEqual(replied.message, message);
      this.assertEqual(failed.message, message);
      this.assertEqual(record.seen.length, 0);
    }
  }

  // The ids of the ports.
  export class TestIdNext extends unittest.TestCase {
    // The ids of a port count up from 102, as 101 is the first line's.
    test_ids_count(): void {
      const port = port_fresh();
      const counted = [
        dispatch.id_next(port),
        dispatch.id_next(port),
        dispatch.id_next(port),
      ];
      this.assertEqual(counted, [102, 103, 104]);
    }

    // Each port counts on its own, each from 102.
    test_ports_separate(): void {
      const wire = port_fresh();
      const page = port_fresh();
      this.assertEqual(dispatch.id_next(wire), 102);
      this.assertEqual(dispatch.id_next(page), 102);
      this.assertEqual(dispatch.id_next(wire), 103);
      this.assertEqual(dispatch.id_next(page), 103);
    }
  }
}

Object.freeze(test_dispatch);
