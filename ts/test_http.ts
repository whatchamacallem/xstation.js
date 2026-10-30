// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Tests of the HTTP port that need no network. No test here posts a request
// that passes the checks, so no test starts a `fetch`. The request lines,
// the expected replies and every thrown or carried text are entries of the
// gold record, test_settings.json; a text that holds a platform's message
// keeps a placeholder that the test fills.

namespace test_http {
  // The values the tests share.
  const constants = Object.freeze({
    url: "https://api.x.ai/v1/chat/completions",
    authorization: "Bearer test-key",
  });

  // A payload of fields by name.
  type LinePayload = { [key: string]: unknown };

  // A copy of a value of this module's gold, which the harness keeps frozen.
  function gold_value(name: string): unknown {
    return structuredClone(harness.gold_get(`typescript.test_http.${name}`));
  }

  // A text of this module's gold, a run time `{n}` left for the test to fill.
  function gold_text(name: string): string {
    return harness.gold_get(`typescript.test_http.texts.${name}`) as string;
  }

  // A copy of a line of this module's gold, a run time part set on the copy.
  function gold_line(name: string): lines.Line {
    return gold_value(`lines.${name}`) as lines.Line;
  }

  // A copy of the gold request line named, with the payload fields given set.
  function request_make(name: string, extra: LinePayload): lines.Line {
    return Object.assign(gold_line(name), extra);
  }

  // The exchange of a request line, the gold's numbered 7 in short names.
  function exchange_make(
    extra: LinePayload,
    name = "request",
  ): http.HttpExchange {
    return new http.HttpExchange(request_make(name, extra));
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

  // The error `JSON.parse` throws for the text, which must throw.
  function parse_thrown(text: string): Error {
    try {
      JSON.parse(text);
    } catch (error) {
      return error as Error;
    }
    throw new Error(`The text ${text} was parsed.`);
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
      const sent = exchange_make({
        json: { model: "grok-4", n: 1 },
      }).arguments_make();
      this.assertEqual(sent.url, constants.url);
      this.assertEqual(sent.init.method, "POST");
      this.assertEqual(sent.init.body, '{"model":"grok-4","n":1}');
    }

    // A `body` field is sent as it is, white space and all.
    test_text_body(): void {
      const body = '  { "a": 1 }\n';
      const sent = exchange_make({ body }).arguments_make();
      this.assertEqual(sent.init.body, body);
    }

    // When both fields are present the `json` field is the body.
    test_json_wins(): void {
      const sent = exchange_make({
        json: { a: 1 },
        body: "text",
      }).arguments_make();
      this.assertEqual(sent.init.body, '{"a":1}');
    }

    // A `json` field of `null` is present, so the body is the text `null`.
    test_json_null(): void {
      const sent = exchange_make({ json: null }).arguments_make();
      this.assertEqual(sent.init.body, "null");
    }

    // Text outside ASCII is written as it is and not as an escape.
    test_json_unicode(): void {
      const letter = String.fromCodePoint(0xe9);
      const sent = exchange_make({ json: { text: letter } }).arguments_make();
      this.assertEqual(sent.init.body, '{"text":"' + letter + '"}');
    }

    // A request with neither field has no body at all.
    test_body_absent(): void {
      const sent = exchange_make({ method: "GET" }).arguments_make();
      this.assertEqual(sent.init.method, "GET");
      this.assertFalse(Object.hasOwn(sent.init, "body"));
    }

    // The headers go on as given, names in the case they came in.
    test_headers_kept(): void {
      const headers = {
        Authorization: constants.authorization,
        "X-Mixed": "a",
      };
      const sent = exchange_make({ headers }).arguments_make();
      this.assertEqual(sent.init.headers, headers);
    }

    // A `json` field that JSON cannot carry throws and sends nothing.
    test_json_refused(): void {
      const exchange = exchange_make({ json: undefined });
      const message = message_thrown(this, () => exchange.arguments_make());
      this.assertEqual(message, gold_text("utility_value_refused"));
    }

    // NaN and the infinities, which no decoder lets in, are sent as null.
    test_json_unchecked(): void {
      for (const json of [NaN, Infinity]) {
        const exchange = exchange_make({ json });
        this.assertEqual(exchange.arguments_make().init.body, "null");
      }
    }
  }

  // The checks that refuse a line before anything is sent.
  export class TestRequestChecks extends unittest.TestCase {
    // The smallest request is accepted.
    test_fields_least(): void {
      const exchange = exchange_make({ method: "GET", headers: {} });
      this.assertEqual(exchange.arguments_make().init.headers, {});
    }

    // A line of another type is refused.
    test_type_other(): void {
      const line = request_make("request_kv_get", {});
      this.assertEqual(
        message_thrown(this, () => new http.HttpExchange(line)),
        gold_text("http_type_invalid"),
      );
    }

    // A request with no id is refused, as nothing could answer it.
    test_id_missing(): void {
      this.assertEqual(
        message_thrown(this, () => exchange_make({}, "request_unnumbered")),
        gold_text("http_id_missing"),
      );
    }

    // A request that carries a blob is refused.
    test_blobs_refused(): void {
      const line = request_make("request_blob", {});
      (line[1] as lines.BlobHeader).d = new Uint8Array(1);
      this.assertEqual(
        message_thrown(this, () => new http.HttpExchange(line)),
        gold_text("http_blobs_refused"),
      );
    }

    // A method other than GET or POST, in any form, is refused.
    test_method_invalid(): void {
      for (const method of [undefined, null, "PUT", "get", "", 5]) {
        this.assertEqual(
          message_thrown(this, () => exchange_make({ method })),
          gold_text("http_field_invalid_method"),
        );
      }
    }

    // A url that is not text is refused.
    test_url_invalid(): void {
      for (const url of [undefined, null, 5, {}, ["https://a.test/"]]) {
        this.assertEqual(
          message_thrown(this, () => exchange_make({ url })),
          gold_text("http_field_invalid_url"),
        );
      }
    }

    // Headers that are not an object of text values are refused.
    test_headers_invalid(): void {
      const bad = [undefined, null, [], "a", 5, { a: 1 }, { a: null }];
      for (const headers of bad) {
        this.assertEqual(
          message_thrown(this, () => exchange_make({ headers })),
          gold_text("http_field_invalid_headers"),
        );
      }
    }

    // A `body` that is not text is refused, even beside a `json` field.
    test_body_invalid(): void {
      const refused = gold_text("http_field_invalid_body");
      for (const body of [undefined, null, 5, {}]) {
        this.assertEqual(
          message_thrown(this, () => exchange_make({ body })),
          refused,
        );
        this.assertEqual(
          message_thrown(this, () => exchange_make({ body, json: 1 })),
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
      const reply = exchange_make({}).answer_reply(answer);
      this.assertEqual(reply, gold_line("answer_json"));
      this.assertEqual(Object.keys(reply).join(","), "0,status,headers,json");
    }

    // The media type is read without its parameters and in any case.
    test_json_parameters(): void {
      const types = ["application/json; charset=utf-8", "Application/JSON "];
      for (const type of types) {
        const answer = answer_make(200, type, "[1]");
        const reply = exchange_make({}).answer_reply(answer);
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
        const reply = exchange_make({}).answer_reply(answer);
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
      const reply = exchange_make({}).answer_reply(
        answer_make(204, undefined, ""),
      );
      this.assertEqual(reply, gold_line("answer_empty"));
    }

    // Statuses 200 to 299 are replies and every other status is an error.
    test_status_range(): void {
      const exchange = exchange_make({});
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
        this.assertEqual(reply[0].t, type);
      }
    }

    // A failed status is an `error` line naming the url, status and body.
    test_status_error(): void {
      const answer = answer_make(404, "text/plain", "no such model");
      const reply = exchange_make({}).answer_reply(answer);
      this.assertEqual(reply[0], gold_value("lines.header_error"));
      this.assertEqual(Object.keys(reply).join(","), "0,message,stack");
      this.assertEqual(message_get(reply), gold_text("http_status_failed"));
      this.assertEqual(typeof reply.stack, "string");
      this.assertTrue(String(reply.stack).length > 0);
    }

    // A body that is not JSON under a JSON content type is an `error` line.
    test_json_malformed(): void {
      for (const text of ["", "{", '{"a":', "nope"]) {
        const answer = answer_make(200, "application/json", text);
        const reply = exchange_make({}).answer_reply(answer);
        const parsed = String(parse_thrown(text));
        this.assertEqual(reply[0], gold_value("lines.header_error"));
        this.assertEqual(
          message_get(reply),
          gold_text("http_json_invalid_malformed").replaceAll("{0}", parsed),
        );
      }
    }

    // A JSON body holding a number that overflows a double is refused too.
    test_json_overflow(): void {
      const text = '{"a":1e400}';
      const answer = answer_make(200, "application/json", text);
      const reply = exchange_make({}).answer_reply(answer);
      this.assertEqual(reply[0], gold_value("lines.header_error"));
      this.assertEqual(
        message_get(reply),
        gold_text("http_json_invalid_overflow"),
      );
    }

    // The reply carries the id of its own request, and no id of its own.
    test_reply_number(): void {
      const requests: [number, string][] = [
        [1, "request_id_1"],
        [2, "request_id_2"],
        [41, "request_id_41"],
      ];
      for (const [id, name] of requests) {
        const exchange = exchange_make({}, name);
        const reply = exchange.answer_reply(answer_make(200, undefined, ""));
        this.assertEqual(reply[0].r, id);
        this.assertFalse(Object.hasOwn(reply[0], "i"));
      }
    }

    // A request in full names is answered in full names, error lines too.
    test_full_names(): void {
      const exchange = exchange_make({}, "request_full");
      const reply = exchange.answer_reply(answer_make(200, undefined, ""));
      this.assertEqual(reply[0], gold_value("lines.header_full"));
      const failed = exchange.answer_reply(answer_make(500, undefined, ""));
      this.assertEqual(failed[0], gold_value("lines.header_error_full"));
    }
  }

  // The error line made from the timer.
  export class TestFailureReply extends unittest.TestCase {
    // The timeout is an `error` line naming the url and the seconds.
    test_timeout_text(): void {
      const exchange = exchange_make({});
      const reply = exchange.timeout_reply(5);
      this.assertEqual(reply[0], gold_value("lines.header_error"));
      this.assertEqual(Object.keys(reply).join(","), "0,message,stack");
      this.assertEqual(
        message_get(reply),
        gold_text("http_timeout_expired_whole"),
      );
      this.assertTrue(String(reply.stack).length > 0);
    }

    // Fractions of a second are named as they are.
    test_timeout_fraction(): void {
      const exchange = exchange_make({});
      this.assertEqual(
        message_get(exchange.timeout_reply(0.5)),
        gold_text("http_timeout_expired_fraction"),
      );
    }

    // The timeout's error line follows the name form of the request.
    test_error_full(): void {
      const exchange = exchange_make({}, "request_full");
      const expected = gold_value("lines.header_error_full");
      this.assertEqual(exchange.timeout_reply(5)[0], expected);
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

    // Timeouts that are 0, negative or too long for a timer throw.
    test_timeout_invalid(): void {
      const timeouts: [number, string][] = [
        [0, "http_timeout_invalid_zero"],
        [-1, "http_timeout_invalid_negative"],
        [2147484, "http_timeout_invalid_long"],
      ];
      for (const [seconds, name] of timeouts) {
        this.assertEqual(
          message_thrown(this, () => new http.HttpPort(seconds)),
          gold_text(name),
        );
      }
    }

    // A second receiver throws.
    test_receiver_twice(): void {
      const port = new http.HttpPort(1);
      port.line_receive(() => {});
      this.assertEqual(
        message_thrown(this, () => port.line_receive(() => {})),
        gold_text("http_receiver_twice"),
      );
    }

    // A request posted before a receiver is set throws.
    test_post_unreceived(): void {
      const port = new http.HttpPort(1);
      const line = request_make("request", {});
      this.assertEqual(
        message_thrown(this, () => port.line_post(line, [])),
        gold_text("http_receiver_missing"),
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
        [request_make("request_kv_get", {}), gold_text("http_type_invalid")],
        [request_make("request_unnumbered", {}), gold_text("http_id_missing")],
        [
          request_make("request", { url: 5 }),
          gold_text("http_field_invalid_url"),
        ],
        [
          request_make("request", { json: undefined }),
          gold_text("utility_value_refused"),
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
