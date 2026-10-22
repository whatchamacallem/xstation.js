// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Tests of the HTTP port that need no network. No test here posts a request
// that passes the checks, so no test starts a `fetch`.

namespace test_http {
  // The values the tests share.
  const constants = Object.freeze({
    url: "https://api.x.ai/v1/chat/completions",
    id: 7,
    authorization: "Bearer test-key",
  });

  // A payload of fields by name.
  type LinePayload = { [key: string]: unknown };

  // The header options of a line: its id and whether it has full names.
  type HeaderOptions = { id?: number; full?: boolean };

  // A line of the type with the payload and the header options given.
  function line_build(
    type: string,
    payload: LinePayload,
    options: HeaderOptions,
  ): lines.Line {
    return jslb.line_make(jslb.header_make(type, options), [], payload);
  }

  // The headers a chat request carries.
  function headers_make(): { [name: string]: string } {
    return {
      authorization: constants.authorization,
      "content-type": "application/json",
    };
  }

  // The payload of a chat request, with the extra fields added or replaced.
  function payload_make(extra: LinePayload): LinePayload {
    return {
      method: "POST",
      url: constants.url,
      headers: headers_make(),
      ...extra,
    };
  }

  // The exchange of a request line, numbered 7 and in short names by default.
  function exchange_make(
    payload: LinePayload,
    options: HeaderOptions = { id: constants.id },
  ): http.HttpExchange {
    return new http.HttpExchange(line_build("http.request", payload, options));
  }

  // A finished response with the content type, or none, and the body text.
  function answer_make(
    status: number,
    content_type: string | undefined,
    text: string,
  ): http.HttpAnswer {
    const headers: { [name: string]: string } = {};
    if (content_type !== undefined) {
      headers["content-type"] = content_type;
    }
    return { status, headers, text };
  }

  // The message of an error line, which the tests read as text.
  function message_get(reply: lines.Line): string {
    const message = reply.message;
    if (typeof message !== "string") {
      throw new Error("The error line has no message text.");
    }
    return message;
  }

  // The message of the error the function throws, failing the test if none.
  function message_thrown(test: unittest.TestCase, fn: () => void): string {
    try {
      fn();
    } catch (error) {
      if (error instanceof Error) {
        return error.message;
      }
      throw error;
    }
    return test.fail("Nothing was thrown.");
  }

  // The translation of a request line into the arguments of a fetch.
  export class TestRequestTranslate extends unittest.TestCase {
    // A `json` field is serialized as the body, with no white space.
    test_json_body(): void {
      const sent = exchange_make(
        payload_make({ json: { model: "grok-4", n: 1 } }),
      ).arguments_make();
      this.assertEqual(sent.url, constants.url);
      this.assertEqual(sent.init.method, "POST");
      this.assertEqual(sent.init.body, '{"model":"grok-4","n":1}');
    }

    // A `body` field is sent as it is, white space and all.
    test_text_body(): void {
      const body = '  { "a": 1 }\n';
      const sent = exchange_make(payload_make({ body })).arguments_make();
      this.assertEqual(sent.init.body, body);
    }

    // When both fields are present the `json` field is the body.
    test_json_wins(): void {
      const sent = exchange_make(
        payload_make({ json: { a: 1 }, body: "text" }),
      ).arguments_make();
      this.assertEqual(sent.init.body, '{"a":1}');
    }

    // A `json` field of `null` is present, so the body is the text `null`.
    test_json_null(): void {
      const sent = exchange_make(
        payload_make({ json: null }),
      ).arguments_make();
      this.assertEqual(sent.init.body, "null");
    }

    // Text outside ASCII is written as it is and not as an escape.
    test_json_unicode(): void {
      const letter = String.fromCodePoint(0xe9);
      const sent = exchange_make(
        payload_make({ json: { text: letter } }),
      ).arguments_make();
      this.assertEqual(sent.init.body, '{"text":"' + letter + '"}');
    }

    // A request with neither field has no body at all.
    test_body_absent(): void {
      const payload = payload_make({ method: "GET" });
      const sent = exchange_make(payload).arguments_make();
      this.assertEqual(sent.init.method, "GET");
      this.assertFalse(Object.hasOwn(sent.init, "body"));
    }

    // The headers go on as given, names in the case they came in.
    test_headers_kept(): void {
      const headers = {
        Authorization: constants.authorization,
        "X-Mixed": "a",
      };
      const sent = exchange_make(payload_make({ headers })).arguments_make();
      this.assertEqual(sent.init.headers, headers);
    }

    // A `json` field that JSON cannot carry throws and sends nothing.
    test_json_refused(): void {
      const expected = new Map<unknown, string>([
        [NaN, i18n("utility.number_refused", NaN)],
        [Infinity, i18n("utility.number_refused", Infinity)],
        [undefined, i18n("utility.value_refused")],
      ]);
      for (const [json, text] of expected) {
        const exchange = exchange_make(payload_make({ json }));
        const message = message_thrown(this, () => exchange.arguments_make());
        this.assertEqual(message, text);
      }
    }
  }

  // The checks that refuse a line before anything is sent.
  export class TestRequestChecks extends unittest.TestCase {
    // The smallest request is accepted.
    test_fields_least(): void {
      const exchange = exchange_make({
        method: "GET",
        url: constants.url,
        headers: {},
      });
      this.assertEqual(exchange.arguments_make().init.headers, {});
    }

    // A line of another type is refused.
    test_type_other(): void {
      const line = line_build("kv.get", payload_make({}), {
        id: constants.id,
      });
      this.assertEqual(
        message_thrown(this, () => new http.HttpExchange(line)),
        i18n("http.type_invalid", "kv.get", "http.request"),
      );
    }

    // A request with no id is refused, as nothing could answer it.
    test_id_missing(): void {
      this.assertEqual(
        message_thrown(this, () => exchange_make(payload_make({}), {})),
        i18n("http.id_missing", "http.request"),
      );
    }

    // A request that carries a blob is refused.
    test_blobs_refused(): void {
      const header = jslb.header_make("http.request", { id: constants.id });
      const blob = jslb.blob_make(new Uint8Array(1));
      const line = jslb.line_make(header, [blob], payload_make({}));
      this.assertEqual(
        message_thrown(this, () => new http.HttpExchange(line)),
        i18n("http.blobs_refused", "http.request"),
      );
    }

    // A method other than GET or POST, in any form, is refused.
    test_method_invalid(): void {
      for (const method of [undefined, null, "PUT", "get", "", 5]) {
        this.assertEqual(
          message_thrown(this, () => exchange_make(payload_make({ method }))),
          i18n("http.field_invalid", "method"),
        );
      }
    }

    // A url that is not text is refused.
    test_url_invalid(): void {
      for (const url of [undefined, null, 5, {}, ["https://a.test/"]]) {
        this.assertEqual(
          message_thrown(this, () => exchange_make(payload_make({ url }))),
          i18n("http.field_invalid", "url"),
        );
      }
    }

    // Headers that are not an object of text values are refused.
    test_headers_invalid(): void {
      const bad = [undefined, null, [], "a", 5, { a: 1 }, { a: null }];
      for (const headers of bad) {
        this.assertEqual(
          message_thrown(this, () => exchange_make(payload_make({ headers }))),
          i18n("http.field_invalid", "headers"),
        );
      }
    }

    // A `body` that is not text is refused, even beside a `json` field.
    test_body_invalid(): void {
      const refused = i18n("http.field_invalid", "body");
      for (const body of [undefined, null, 5, {}]) {
        this.assertEqual(
          message_thrown(this, () => exchange_make(payload_make({ body }))),
          refused,
        );
        this.assertEqual(
          message_thrown(this, () =>
            exchange_make(payload_make({ body, json: 1 })),
          ),
          refused,
        );
      }
    }
  }

  // The reply line made from a finished response.
  export class TestAnswerReply extends unittest.TestCase {
    // A JSON response is a reply with `r` set and the parsed `json`.
    test_json_answer(): void {
      const answer = answer_make(
        200,
        "application/json",
        '{"id":"c1","n":[1,2]}',
      );
      const reply = exchange_make(payload_make({})).answer_reply(answer);
      this.assertEqual(reply, {
        0: { t: "http.request", r: constants.id },
        status: 200,
        headers: { "content-type": "application/json" },
        json: { id: "c1", n: [1, 2] },
      });
      this.assertEqual(Object.keys(reply).join(","), "0,status,headers,json");
    }

    // The media type is read without its parameters and in any case.
    test_json_parameters(): void {
      const types = ["application/json; charset=utf-8", "Application/JSON "];
      for (const type of types) {
        const answer = answer_make(200, type, "[1]");
        const reply = exchange_make(payload_make({})).answer_reply(answer);
        this.assertEqual(reply.json, [1]);
        this.assertFalse(Object.hasOwn(reply, "text"));
      }
    }

    // Any other body is `text`, even one that would parse as JSON.
    test_text_answer(): void {
      const types = [
        "text/plain; charset=utf-8",
        "text/html",
        "application/problem+json",
        "application/jsonx",
        undefined,
      ];
      for (const type of types) {
        const answer = answer_make(200, type, '{"a":1}');
        const reply = exchange_make(payload_make({})).answer_reply(answer);
        this.assertEqual(reply.text, '{"a":1}');
        this.assertFalse(Object.hasOwn(reply, "json"));
        this.assertEqual(
          Object.keys(reply).join(","),
          "0,status,headers,text",
        );
      }
    }

    // A success with no body and no headers is an empty `text`.
    test_empty_answer(): void {
      const reply = exchange_make(payload_make({})).answer_reply(
        answer_make(204, undefined, ""),
      );
      this.assertEqual(reply, {
        0: { t: "http.request", r: constants.id },
        status: 204,
        headers: {},
        text: "",
      });
    }

    // Statuses 200 to 299 are replies and every other status is an error.
    test_status_range(): void {
      const exchange = exchange_make(payload_make({}));
      const expected = new Map<number, string>([
        [199, "error"],
        [200, "http.request"],
        [201, "http.request"],
        [299, "http.request"],
        [300, "error"],
        [404, "error"],
        [500, "error"],
      ]);
      for (const [status, type] of expected) {
        const answer = answer_make(status, "text/plain", "");
        const reply = exchange.answer_reply(answer);
        this.assertEqual(jslb.field_get(reply[0], "type"), type);
      }
    }

    // A failed status is an `error` line naming the url, status and body.
    test_status_error(): void {
      const answer = answer_make(404, "text/plain", "no such model");
      const reply = exchange_make(payload_make({})).answer_reply(answer);
      this.assertEqual(reply[0], { t: "error", r: constants.id });
      this.assertEqual(Object.keys(reply).join(","), "0,message,stack");
      this.assertEqual(
        message_get(reply),
        i18n("http.status_failed", constants.url, 404, "no such model"),
      );
      this.assertEqual(typeof reply.stack, "string");
      this.assertTrue(String(reply.stack).length > 0);
    }

    // A body that is not JSON under a JSON content type is an `error` line.
    test_json_malformed(): void {
      for (const text of ["", "{", '{"a":', "nope"]) {
        const answer = answer_make(200, "application/json", text);
        const reply = exchange_make(payload_make({})).answer_reply(answer);
        const parsed = message_thrown(this, () => JSON.parse(text));
        const cause = String(new SyntaxError(parsed));
        this.assertEqual(reply[0], { t: "error", r: constants.id });
        this.assertEqual(
          message_get(reply),
          i18n("http.json_invalid", constants.url, cause),
        );
      }
    }

    // The reply carries the id of its own request, and no id of its own.
    test_reply_number(): void {
      for (const id of [1, 2, 41]) {
        const exchange = exchange_make(payload_make({}), { id });
        const reply = exchange.answer_reply(answer_make(200, undefined, ""));
        this.assertEqual(jslb.field_get(reply[0], "reply"), id);
        this.assertFalse(Object.hasOwn(reply[0], "i"));
      }
    }

    // A request in full names is answered in full names, error lines too.
    test_full_names(): void {
      const exchange = exchange_make(payload_make({}), {
        id: constants.id,
        full: true,
      });
      const reply = exchange.answer_reply(answer_make(200, undefined, ""));
      this.assertEqual(reply[0], {
        type: "http.request",
        reply: constants.id,
      });
      const failed = exchange.answer_reply(answer_make(500, undefined, ""));
      this.assertEqual(failed[0], { type: "error", reply: constants.id });
    }
  }

  // The error lines made from a rejected fetch and from the timer.
  export class TestFailureReply extends unittest.TestCase {
    // A rejected fetch is an `error` line naming the url and the cause.
    test_failure_text(): void {
      const exchange = exchange_make(payload_make({}));
      const cause = new TypeError("Failed to fetch");
      const reply = exchange.failure_reply(cause);
      this.assertEqual(reply[0], { t: "error", r: constants.id });
      this.assertEqual(Object.keys(reply).join(","), "0,message,stack");
      this.assertEqual(
        message_get(reply),
        i18n("http.fetch_failed", constants.url, String(cause)),
      );
      this.assertTrue(String(reply.stack).length > 0);
    }

    // A cause that is no error is named by its text.
    test_failure_other(): void {
      const exchange = exchange_make(payload_make({}));
      for (const cause of ["boom", 5, undefined, null]) {
        const reply = exchange.failure_reply(cause);
        this.assertEqual(
          message_get(reply),
          i18n("http.fetch_failed", constants.url, String(cause)),
        );
      }
    }

    // The timeout is an `error` line naming the url and the seconds.
    test_timeout_text(): void {
      const exchange = exchange_make(payload_make({}));
      const reply = exchange.timeout_reply(5);
      this.assertEqual(reply[0], { t: "error", r: constants.id });
      this.assertEqual(Object.keys(reply).join(","), "0,message,stack");
      this.assertEqual(
        message_get(reply),
        i18n("http.timeout_expired", constants.url, 5),
      );
      this.assertTrue(String(reply.stack).length > 0);
    }

    // Fractions of a second are named as they are.
    test_timeout_fraction(): void {
      const exchange = exchange_make(payload_make({}));
      this.assertEqual(
        message_get(exchange.timeout_reply(0.5)),
        i18n("http.timeout_expired", constants.url, 0.5),
      );
    }

    // The timeout message differs from the message of a failed fetch.
    test_timeout_distinct(): void {
      const exchange = exchange_make(payload_make({}));
      const timeout = message_get(exchange.timeout_reply(5));
      const failure = message_get(exchange.failure_reply(new Error("x")));
      this.assertFalse(timeout === failure);
    }

    // Both error lines follow the name form of the request.
    test_error_full(): void {
      const exchange = exchange_make(payload_make({}), {
        id: constants.id,
        full: true,
      });
      const expected = { type: "error", reply: constants.id };
      this.assertEqual(exchange.timeout_reply(5)[0], expected);
      this.assertEqual(exchange.failure_reply("x")[0], expected);
    }
  }

  // The checks of the port that run before any fetch starts.
  export class TestPortChecks extends unittest.TestCase {
    // Timeouts above 0 that a timer can hold are accepted.
    test_timeout_valid(): void {
      for (const seconds of [0.5, 1, 120, 2147483]) {
        this.assertTrue(new http.HttpPort(seconds) instanceof http.HttpPort);
      }
    }

    // Timeouts that are 0, negative, not finite or too long for a timer throw.
    test_timeout_invalid(): void {
      for (const seconds of [0, -1, NaN, Infinity, 2147484]) {
        this.assertEqual(
          message_thrown(this, () => new http.HttpPort(seconds)),
          i18n("http.timeout_invalid", seconds),
        );
      }
    }

    // A second receiver throws.
    test_receiver_twice(): void {
      const port = new http.HttpPort(1);
      port.line_receive(() => {});
      this.assertEqual(
        message_thrown(this, () => port.line_receive(() => {})),
        i18n("http.receiver_twice"),
      );
    }

    // A request posted before a receiver is set throws.
    test_post_unreceived(): void {
      const port = new http.HttpPort(1);
      const line = line_build("http.request", payload_make({}), {
        id: constants.id,
      });
      this.assertEqual(
        message_thrown(this, () => port.line_post(line, [])),
        i18n("http.receiver_missing"),
      );
    }

    // A line that fails a check throws from the post and nothing is received.
    test_post_refused(): void {
      const port = new http.HttpPort(1);
      let received = 0;
      port.line_receive(() => {
        received += 1;
      });
      const refused: [lines.Line, string][] = [
        [
          line_build("kv.get", payload_make({}), { id: constants.id }),
          i18n("http.type_invalid", "kv.get", "http.request"),
        ],
        [
          line_build("http.request", payload_make({}), {}),
          i18n("http.id_missing", "http.request"),
        ],
        [
          line_build("http.request", payload_make({ url: 5 }), {
            id: constants.id,
          }),
          i18n("http.field_invalid", "url"),
        ],
        [
          line_build("http.request", payload_make({ json: NaN }), {
            id: constants.id,
          }),
          i18n("utility.number_refused", NaN),
        ],
      ];
      for (const [line, text] of refused) {
        this.assertEqual(
          message_thrown(this, () => port.line_post(line, [])),
          text,
        );
      }
      this.assertEqual(received, 0);
    }
  }
}

Object.freeze(test_http);
