// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Tests of the dispatcher: registration, dispatch by type and version, the
// rules for replies and sleeps, and the reply, error and id lines it builds.

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

  // Builds a line with no blobs from its type, header options and payload.
  function line_build(
    type: string,
    options: { version?: number; id?: number; key?: string; full?: boolean },
    payload: { [key: string]: unknown } = {},
  ): lines.Line {
    return jslb.line_make(jslb.header_make(type, options), [], payload);
  }

  // Makes a handler that records its lines and always returns the result.
  function record_make(
    result: dispatch.Reply | dispatch.Sleep,
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
      this.assertEqual(error.message, i18n("dispatch.handler_twice", type, 0));
      dispatch.line_dispatch(line_build(type, {}));
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
      dispatch.line_dispatch(line_build(type, {}));
      dispatch.line_dispatch(line_build(type, { version: 1 }));
      dispatch.line_dispatch(line_build(other, {}));
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
      const line = line_build(type, { version: 1 }, { text: "x" });
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
      dispatch.line_dispatch(line_build(type, {}));
      dispatch.line_dispatch(line_build(type, { version: 0 }));
      this.assertEqual(zero.seen.length, 2);
    }

    // The handler gets the line itself, with its blobs and payload in place.
    test_line_whole(): void {
      const type = type_fresh();
      const record = record_make(undefined);
      dispatch.handler_register(type, 0, record.fn);
      const blob = jslb.blob_make(new Uint8Array([1, 2, 3]));
      const header = jslb.header_make(type);
      const line = jslb.line_make(header, [blob], { n: 1 });
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
        dispatch.line_dispatch(line_build(other, {})),
      );
      this.assertEqual(
        type_error.message,
        i18n("dispatch.handler_unknown", other, 0),
      );
      const version_error = thrown_get(() =>
        dispatch.line_dispatch(line_build(type, { version: 1 })),
      );
      this.assertEqual(
        version_error.message,
        i18n("dispatch.handler_unknown", type, 1),
      );
    }

    // An error from a handler propagates unchanged.
    test_handler_throws(): void {
      const type = type_fresh();
      const failure = new Error("missing");
      dispatch.handler_register(type, 0, () => {
        throw failure;
      });
      const line = line_build(type, { id: 7 });
      const error = thrown_get(() => dispatch.line_dispatch(line));
      this.assertTrue(error === failure);
    }

    // A request gets the reply its handler returned, with `r` set to its `i`.
    test_request_reply(): void {
      const type = type_fresh();
      const request = line_build(type, { id: 7 });
      const reply = dispatch.reply_make(request, { n: 1 });
      dispatch.handler_register(type, 0, record_make(reply).fn);
      this.assertTrue(dispatch.line_dispatch(request) === reply);
      this.assertEqual(reply[0], { t: type, r: 7 });
    }

    // A full name request is answered in full names.
    test_full_request(): void {
      const type = type_fresh();
      const request = line_build(type, { id: 9, full: true });
      const reply = dispatch.reply_make(request, { n: 1 });
      dispatch.handler_register(type, 0, record_make(reply).fn);
      this.assertTrue(dispatch.line_dispatch(request) === reply);
      this.assertEqual(reply[0], { type, reply: 9 });
    }

    // A reply without `r` gets it, spelled in the name form of its header.
    test_reply_unset(): void {
      const short_type = type_fresh();
      const full_type = type_fresh();
      const short_reply = line_build(short_type, {});
      const full_reply = line_build(full_type, { full: true });
      dispatch.handler_register(short_type, 0, record_make(short_reply).fn);
      dispatch.handler_register(full_type, 0, record_make(full_reply).fn);
      dispatch.line_dispatch(line_build(short_type, { id: 7 }));
      dispatch.line_dispatch(line_build(full_type, { id: 8 }));
      this.assertEqual(short_reply[0], { t: short_type, r: 7 });
      this.assertEqual(full_reply[0], { type: full_type, reply: 8 });
    }

    // A reply that names another request is changed to name this one.
    test_reply_overwritten(): void {
      const type = type_fresh();
      const reply = dispatch.reply_make(line_build(type, { id: 3 }), {});
      dispatch.handler_register(type, 0, record_make(reply).fn);
      dispatch.line_dispatch(line_build(type, { id: 7 }));
      this.assertEqual(reply[0], { t: type, r: 7 });
    }

    // A request whose handler returns nothing throws.
    test_request_none(): void {
      const type = type_fresh();
      dispatch.handler_register(type, 0, record_make(undefined).fn);
      const error = thrown_get(() =>
        dispatch.line_dispatch(line_build(type, { id: 7 })),
      );
      this.assertEqual(
        error.message,
        i18n("dispatch.request_unanswered", type, 0, 7),
      );
    }

    // A notification whose handler returns nothing returns nothing.
    test_notification_none(): void {
      const type = type_fresh();
      dispatch.handler_register(type, 0, record_make(undefined).fn);
      const line = line_build(type, {}, { text: "x" });
      this.assertEqual(dispatch.line_dispatch(line), undefined);
    }

    // A notification whose handler returns a reply to no request throws.
    test_notification_reply(): void {
      const type = type_fresh();
      const notification = line_build(type, {});
      const reply = dispatch.reply_make(notification, {});
      dispatch.handler_register(type, 0, record_make(reply).fn);
      const error = thrown_get(() => dispatch.line_dispatch(notification));
      this.assertEqual(
        error.message,
        i18n("dispatch.notification_replied", type, 0),
      );
    }

    // A wake line has no id and may return the reply to an earlier request.
    test_wake_reply(): void {
      const wake_type = type_fresh();
      const request_type = type_fresh();
      const request = line_build(request_type, { id: 5 });
      const reply = dispatch.reply_make(request, { turn: 7 });
      dispatch.handler_register(wake_type, 0, record_make(reply).fn);
      const wake: lines.Wake = { state: request, replies: [] };
      const line = line_build(wake_type, {}, { ...wake });
      this.assertTrue(dispatch.line_dispatch(line) === reply);
      this.assertEqual(reply[0], { t: request_type, r: 5 });
    }

    // A reply with no header throws, for a request and for a notification.
    test_reply_headerless(): void {
      const type = type_fresh();
      dispatch.handler_register(type, 0, record_make({ n: 1 }).fn);
      for (const options of [{ id: 7 }, {}]) {
        const error = thrown_get(() =>
          dispatch.line_dispatch(line_build(type, options)),
        );
        this.assertEqual(
          error.message,
          i18n("dispatch.reply_headerless", type, 0),
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
        dispatch.line_dispatch(line_build(type, { id: 7 })) === sleep,
      );
      this.assertTrue(dispatch.line_dispatch(line_build(type, {})) === sleep);
      this.assertEqual(sleep, {
        state: { step: 1 },
        wait_ids: [1, 2],
        then_type,
      });
    }
  }

  // The reply line a handler builds.
  export class TestReplyMake extends unittest.TestCase {
    // A short name reply has `t` and `r` and nothing else of the request.
    test_short_names(): void {
      const type = type_fresh();
      const options = { version: 1, id: 7, key: "/a/b" };
      const request = line_build(type, options, { n: 1 });
      const reply = dispatch.reply_make(request, { found: true, size: 3 });
      this.assertEqual(reply[0], { t: type, r: 7 });
      this.assertFalse("1" in reply);
      this.assertEqual(jslb.payload_of(reply), { found: true, size: 3 });
    }

    // A full name reply has `type` and `reply` and nothing else.
    test_full_names(): void {
      const type = type_fresh();
      const options = { version: 1, id: 7, key: "/a/b", full: true };
      const request = line_build(type, options, { n: 1 });
      const reply = dispatch.reply_make(request, { found: true, size: 3 });
      this.assertEqual(reply[0], { type, reply: 7 });
      this.assertFalse("1" in reply);
      this.assertEqual(jslb.payload_of(reply), { found: true, size: 3 });
    }

    // A reply to a notification has no `r`.
    test_id_absent(): void {
      const type = type_fresh();
      const reply = dispatch.reply_make(line_build(type, {}), { n: 1 });
      this.assertEqual(reply[0], { t: type });
    }

    // Blobs are numbered from 1 and counted, apart from the payload.
    test_blobs_numbered(): void {
      const request = line_build(type_fresh(), { id: 3 });
      const first = jslb.blob_make(new Uint8Array([1, 2, 3]));
      const second = jslb.blob_make(new Uint8Array([4, 5]));
      const reply = dispatch.reply_make(request, { seq: 4 }, [first, second]);
      this.assertEqual(jslb.field_get(reply[0], "blobs"), 2);
      this.assertEqual(reply[1], first);
      this.assertEqual(reply[2], second);
      this.assertFalse("3" in reply);
      this.assertEqual(jslb.payload_of(reply), { seq: 4 });
    }
  }

  // The error line.
  export class TestErrorMake extends unittest.TestCase {
    // The error line of a request has `r`, the message and the stack.
    test_request_error(): void {
      const error = new Error("boom");
      const request = line_build(type_fresh(), { id: 5 });
      const line = dispatch.error_make(request, error);
      this.assertEqual(line[0], { t: "error", r: 5 });
      const payload = jslb.payload_of(line);
      this.assertEqual(Object.keys(payload), ["message", "stack"]);
      this.assertEqual(payload.message, "boom");
      this.assertEqual(payload.stack, error.stack);
    }

    // The error line of a full name request uses full names.
    test_full_error(): void {
      const request = line_build(type_fresh(), { id: 5, full: true });
      const line = dispatch.error_make(request, new Error("boom"));
      this.assertEqual(line[0], { type: "error", reply: 5 });
    }

    // The error line of a notification has no `r`.
    test_notification_error(): void {
      const notification = line_build(type_fresh(), {});
      const line = dispatch.error_make(notification, new Error("boom"));
      this.assertEqual(line[0], { t: "error" });
      this.assertEqual(jslb.payload_of(line).message, "boom");
    }

    // The error line of no line has no `r`, in short names.
    test_no_line(): void {
      const line = dispatch.error_make(undefined, new Error("boom"));
      this.assertEqual(line[0], { t: "error" });
    }

    // An error with no stack cannot be sent, so it throws.
    test_stack_missing(): void {
      const error = new Error("boom");
      Object.defineProperty(error, "stack", { value: undefined });
      const thrown = thrown_get(() => dispatch.error_make(undefined, error));
      this.assertEqual(thrown.message, i18n("dispatch.stack_missing", "boom"));
    }
  }

  // The kinds of the header fields the dispatcher reads.
  export class TestHeaderKinds extends unittest.TestCase {
    // A type that is not text throws in each call that reads it.
    test_type_invalid(): void {
      const line = { 0: { t: 5 } } as unknown as lines.Line;
      const message = i18n("dispatch.type_invalid", 5);
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
      const message = i18n("dispatch.id_invalid", type, "7");
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
    // The ids of a port count up from 1.
    test_ids_count(): void {
      const port = port_fresh();
      const counted = [
        dispatch.id_next(port),
        dispatch.id_next(port),
        dispatch.id_next(port),
      ];
      this.assertEqual(counted, [1, 2, 3]);
    }

    // Each port counts on its own.
    test_ports_separate(): void {
      const wire = port_fresh();
      const page = port_fresh();
      this.assertEqual(dispatch.id_next(wire), 1);
      this.assertEqual(dispatch.id_next(page), 1);
      this.assertEqual(dispatch.id_next(wire), 2);
      this.assertEqual(dispatch.id_next(page), 2);
    }
  }
}

Object.freeze(test_dispatch);
