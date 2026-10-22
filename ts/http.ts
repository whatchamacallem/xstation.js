// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The port that turns an `http.request` line into one `fetch` and the end of
// that `fetch` into the reply line. Its promises and its timer only turn an
// event of the platform into a line.

namespace http {
  // The line types, header key, media type, status range and timer limits.
  const constants = Object.freeze({
    request_type: "http.request",
    reply_type: "http.request",
    error_type: "error",
    full_key: "type",
    content_key: "content-type",
    json_media: "application/json",
    parameter_mark: ";",
    status_min: 200,
    status_max: 299,
    second_ms: 1000,
    timer_max_ms: 2 ** 31 - 1,
  });

  // Header values by header name, as a request and a response carry them.
  type HeaderMap = lines.HttpRequest["headers"];

  // What one fetch needs: the url and its options.
  export interface FetchArguments {
    url: string;
    init: RequestInit;
  }

  // A response read to its end: status, header values and body text.
  export interface HttpAnswer {
    status: number;
    headers: HeaderMap;
    text: string;
  }

  // Whether the value is an object whose every value is text.
  function headers_valid(value: unknown): value is HeaderMap {
    return (
      typeof value === "object" &&
      value !== null &&
      !Array.isArray(value) &&
      Object.values(value).every((entry: unknown) => typeof entry === "string")
    );
  }

  // Throws the error for a request field that is missing or not valid.
  function field_invalid(name: string): never {
    return utility.fail_now(i18n("http.field_invalid", name));
  }

  // The request a line carries, with every field checked.
  function request_read(line: lines.Line): lines.HttpRequest {
    const payload = jslb.payload_of(line);
    const { method, url, headers } = payload;
    if (method !== "GET" && method !== "POST") {
      return field_invalid("method");
    }
    if (typeof url !== "string") {
      return field_invalid("url");
    }
    if (!headers_valid(headers)) {
      return field_invalid("headers");
    }
    const request: lines.HttpRequest = { method, url, headers };
    if (Object.hasOwn(payload, "json")) {
      request.json = payload.json;
    }
    if (Object.hasOwn(payload, "body")) {
      const body = payload.body;
      if (typeof body !== "string") {
        return field_invalid("body");
      }
      request.body = body;
    }
    return request;
  }

  // Whether the headers name a JSON body: the media type, in any case.
  function media_json(headers: HeaderMap): boolean {
    if (!Object.hasOwn(headers, constants.content_key)) {
      return false;
    }
    const media = headers[constants.content_key]
      .split(constants.parameter_mark)[0]
      .trim()
      .toLowerCase();
    return media === constants.json_media;
  }

  // Whether the status is a success: 200 to 299.
  function status_ok(status: number): boolean {
    return status >= constants.status_min && status <= constants.status_max;
  }

  // Reads a response to its end into its status, headers and body text.
  function answer_read(response: Response): Promise<HttpAnswer> {
    const headers: HeaderMap = {};
    response.headers.forEach((value: string, name: string) => {
      headers[name] = value;
    });
    return response
      .text()
      .then((text: string) => ({ status: response.status, headers, text }));
  }

  // The steps from one request line to its fetch and to its reply lines.
  export class HttpExchange {
    private readonly id: number;
    private readonly full: boolean;
    private readonly request: lines.HttpRequest;

    // Takes an `http.request` line that has an id, no blobs and valid fields.
    constructor(line: lines.Line) {
      const header = line[0];
      const type = jslb.field_get(header, "type");
      if (type !== constants.request_type) {
        throw new Error(
          i18n("http.type_invalid", type, constants.request_type),
        );
      }
      const id = jslb.field_get(header, "id");
      if (typeof id !== "number") {
        throw new Error(i18n("http.id_missing", constants.request_type));
      }
      if (jslb.headers_of(line).length > 1) {
        throw new Error(i18n("http.blobs_refused", constants.request_type));
      }
      this.id = id;
      this.full = Object.hasOwn(header, constants.full_key);
      this.request = request_read(line);
    }

    // The arguments of the one fetch: `json` as the body, else `body` as is.
    arguments_make(): FetchArguments {
      const { method, url, headers } = this.request;
      const init: RequestInit = { method, headers };
      if (Object.hasOwn(this.request, "json")) {
        init.body = utility.json_text(this.request.json);
      } else if (this.request.body !== undefined) {
        init.body = this.request.body;
      }
      return { url, init };
    }

    // The reply to a response: its lines, or an error for a failed status.
    answer_reply(answer: HttpAnswer): lines.Line {
      const url = this.request.url;
      if (!status_ok(answer.status)) {
        return this.error_reply(
          new Error(
            i18n("http.status_failed", url, answer.status, answer.text),
          ),
        );
      }
      const { status, headers } = answer;
      if (!media_json(headers)) {
        return this.reply_make({ status, headers, text: answer.text });
      }
      let json: unknown;
      try {
        json = JSON.parse(answer.text);
      } catch (cause) {
        return this.error_reply(
          utility.error_wrap(
            i18n("http.json_invalid", url, String(cause)),
            cause,
          ),
        );
      }
      return this.reply_make({ status, headers, json });
    }

    // The error reply to a fetch or a body read that rejected.
    failure_reply(cause: unknown): lines.Line {
      return this.error_reply(
        utility.error_wrap(
          i18n("http.fetch_failed", this.request.url, String(cause)),
          cause,
        ),
      );
    }

    // The error reply to a request that outlived its timer.
    timeout_reply(timeout_seconds: number): lines.Line {
      return this.error_reply(
        new Error(
          i18n("http.timeout_expired", this.request.url, timeout_seconds),
        ),
      );
    }

    // The line that answers the request, with its id as `r`.
    private reply_make(payload: { [key: string]: unknown }): lines.Line {
      const header = jslb.header_make(constants.reply_type, {
        reply: this.id,
        full: this.full,
      });
      return jslb.line_make(header, [], payload);
    }

    // The `error` line of the request: the message and stack of an error.
    private error_reply(error: Error): lines.Line {
      const stack = error.stack as string;
      const header = jslb.header_make(constants.error_type, {
        reply: this.id,
        full: this.full,
      });
      return jslb.line_make(header, [], { message: error.message, stack });
    }
  }

  // The port that answers `http.request` lines with one `fetch` each.
  export class HttpPort implements queue.Port {
    private readonly timeout_seconds: number;
    private receiver: ((line: lines.Line) => void) | undefined;

    // Takes the seconds a request may last, above 0 and within a timer.
    constructor(timeout_seconds: number) {
      if (
        !Number.isFinite(timeout_seconds) ||
        timeout_seconds <= 0 ||
        timeout_seconds * constants.second_ms > constants.timer_max_ms
      ) {
        throw new Error(i18n("http.timeout_invalid", timeout_seconds));
      }
      this.timeout_seconds = timeout_seconds;
    }

    // Starts the fetch of an `http.request` line, which is answered later.
    line_post(line: lines.Line, transfer: ArrayBuffer[]): void {
      const receiver = this.receiver;
      if (receiver === undefined) {
        throw new Error(i18n("http.receiver_missing"));
      }
      const exchange = new HttpExchange(line);
      const { url, init } = exchange.arguments_make();
      const controller = new AbortController();
      const timer = setTimeout(
        () => controller.abort(),
        this.timeout_seconds * constants.second_ms,
      );
      // Only the fetch and the body read fail into an `error` line.
      fetch(url, { ...init, signal: controller.signal })
        .then((response: Response) => answer_read(response))
        .then(
          (answer: HttpAnswer) => exchange.answer_reply(answer),
          (cause: unknown) =>
            controller.signal.aborted
              ? exchange.timeout_reply(this.timeout_seconds)
              : exchange.failure_reply(cause),
        )
        .then((reply: lines.Line) => {
          clearTimeout(timer);
          receiver(reply);
        });
    }

    // Sets the one receiver of the reply lines.
    line_receive(fn: (line: lines.Line) => void): void {
      if (this.receiver !== undefined) {
        throw new Error(i18n("http.receiver_twice"));
      }
      this.receiver = fn;
    }
  }
}

Object.freeze(http);
