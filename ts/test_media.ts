// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Tests of the media cache and port that need no image decoder and no
// network. No test here posts a request that passes the checks, so no test
// starts a decode or a `fetch`. The request lines, the expected replies and
// every thrown or carried text are entries of the gold record,
// test_settings.json; the image's bytes and their SHA-256 are one entry of
// the digest vector test_digests.json.

namespace test_media {
  // The vector files of the test page, each base64.
  declare const test_vectors: { readonly [name: string]: string };

  // The values the tests share.
  const constants = Object.freeze({
    key: "/_files/gatehouse/arrival.png",
    url: "https://images.example.test/arrival.png",
    // The cache budget in bytes, a size its writer chose.
    budget: 1000,
    digests_name: "test_digests.json",
  });

  // One entry of the digest vector: an input and its `SHA-256`, both in hex.
  type DigestRecord = { data: string; sha256: string };

  // The digest vector: test module to entry name to its record.
  type DigestVector = { [module: string]: { [name: string]: DigestRecord } };

  // The digest vector of every test module, read once.
  let digests: DigestVector | null = null;

  // A copy of a value of this module's gold, which the harness keeps frozen.
  function gold_value(name: string): unknown {
    return structuredClone(harness.gold_get(`typescript.test_media.${name}`));
  }

  // A text of this module's gold, a run time `{n}` left for the test to fill.
  function gold_text(name: string): string {
    return harness.gold_get(`typescript.test_media.texts.${name}`) as string;
  }

  // A copy of a line of this module's gold, a run time part set on the copy.
  function gold_line(name: string): lines.Line {
    return gold_value(`lines.${name}`) as lines.Line;
  }

  // The digest vector of every test module, parsed at the first call.
  function digests_get(): DigestVector {
    if (digests === null) {
      if (!Object.hasOwn(test_vectors, constants.digests_name)) {
        throw new Error(`test_vectors has no file ${constants.digests_name}`);
      }
      const file = Uint8Array.from(
        atob(test_vectors[constants.digests_name]),
        (c) => c.charCodeAt(0),
      );
      const text = new TextDecoder("utf-8", { fatal: true }).decode(file);
      digests = JSON.parse(text) as DigestVector;
    }
    return digests;
  }

  // The input and digest of an entry of this module's digest vector.
  function digest_entry(name: string): { data: Uint8Array; sha256: string } {
    const vectors = digests_get();
    if (!Object.hasOwn(vectors, "test_media")) {
      throw new Error("the digest vector has no module test_media");
    }
    if (!Object.hasOwn(vectors.test_media, name)) {
      throw new Error(`the digest vector of test_media has no entry ${name}`);
    }
    const entry = vectors.test_media[name];
    if (!/^(?:[0-9a-f]{2})*$/.test(entry.data)) {
      throw new Error(`the digest input ${name} is not lowercase hex`);
    }
    const data = new Uint8Array(entry.data.length / 2);
    for (let index = 0; index < data.length; index += 1) {
      const pair = entry.data.slice(2 * index, 2 * index + 2);
      data[index] = Number.parseInt(pair, 16);
    }
    return { data, sha256: entry.sha256 };
  }

  // The bytes of the image the tests send, the input of the gold's digest.
  function bytes_make(): Uint8Array {
    return digest_entry("abc").data;
  }

  // A copy of the gold line named, each blob header given the image's bytes.
  function line_bytes(name: string): lines.Line {
    const line = gold_line(name);
    for (let number = 1; Object.hasOwn(line, String(number)); number += 1) {
      (line[String(number)] as lines.BlobHeader).d = bytes_make();
    }
    return line;
  }

  // A copy of the gold line named, its blobs given bytes, the fields set.
  function line_fields(
    name: string,
    fields: { [key: string]: unknown },
  ): lines.Line {
    return Object.assign(line_bytes(name), fields);
  }

  // The exchange of a copy of the gold request line named.
  function exchange_make(name: string): media.MediaExchange {
    return new media.MediaExchange(line_bytes(name));
  }

  // The message of the error the function throws, failing the test if none.
  function message_thrown(test: unittest.TestCase, fn: () => unknown): string {
    try {
      fn();
    } catch (error) {
      return (error as Error).message;
    }
    return test.fail("Nothing was thrown.");
  }

  // The message a new exchange of the line throws, failing the test if none.
  function refusal_text(test: unittest.TestCase, line: lines.Line): string {
    return message_thrown(test, () => new media.MediaExchange(line));
  }

  // The checks of the budget the cache takes.
  export class TestCacheBudget extends unittest.TestCase {
    // Budgets above 0 are accepted, whole bytes or not.
    test_budget_valid(): void {
      for (const budget of [0.5, 1, 268435456]) {
        this.assertEqual(new media.ImageCache(budget).total_bytes(), 0);
      }
    }

    // Budgets that are 0 or negative throw.
    test_budget_invalid(): void {
      const budgets: [number, string][] = [
        [0, "media_budget_invalid_zero"],
        [-1, "media_budget_invalid_negative"],
      ];
      for (const [budget, name] of budgets) {
        const message = message_thrown(
          this,
          () => new media.ImageCache(budget),
        );
        this.assertEqual(message, gold_text(name));
      }
    }
  }

  // The checks that refuse a line before anything is decoded or sent.
  export class TestRequestChecks extends unittest.TestCase {
    // The smallest store request is accepted and keeps its bytes.
    test_store_least(): void {
      const exchange = exchange_make("store");
      this.assertEqual(exchange.key, constants.key);
      this.assertEqual(exchange.source, bytes_make());
    }

    // The smallest fetch request is accepted and keeps its url.
    test_fetch_least(): void {
      const exchange = exchange_make("fetch");
      this.assertEqual(exchange.key, constants.key);
      this.assertEqual(exchange.source, constants.url);
    }

    // A line of another type is refused.
    test_type_other(): void {
      const line = gold_line("kv_get");
      const expected = gold_text("media_type_invalid");
      this.assertEqual(refusal_text(this, line), expected);
    }

    // A request with no id is refused, as nothing could answer it.
    test_id_missing(): void {
      const store = refusal_text(this, line_bytes("store_unnumbered"));
      const fetched = refusal_text(this, gold_line("fetch_unnumbered"));
      this.assertEqual(store, gold_text("media_id_missing_store"));
      this.assertEqual(fetched, gold_text("media_id_missing_fetch"));
    }

    // A store needs exactly one blob and a fetch needs none.
    test_blobs_count(): void {
      const cases: [lines.Line, string][] = [
        [gold_line("store_unblobbed"), gold_text("media_blobs_invalid_none")],
        [line_bytes("store_two"), gold_text("media_blobs_invalid_two")],
        [line_bytes("fetch_blob"), gold_text("media_blobs_invalid_fetch")],
      ];
      for (const [line, expected] of cases) {
        this.assertEqual(refusal_text(this, line), expected);
      }
    }

    // A store whose blob is a cache handle and not bytes is refused.
    test_blob_handle(): void {
      const line = gold_line("store");
      (line[1] as lines.BlobHeader).d = "cache/handle";
      const expected = gold_text("media_blob_bytes");
      this.assertEqual(refusal_text(this, line), expected);
    }

    // A key that is missing, empty or not text is refused in both types.
    test_key_invalid(): void {
      const refused: lines.Line[] = [
        line_bytes("store_keyless"),
        gold_line("fetch_keyless"),
      ];
      for (const k of [undefined, null, "", 5, ["a"]]) {
        refused.push(line_fields("store_keyless", { k }));
        refused.push(line_fields("fetch_keyless", { k }));
      }
      const expected = gold_text("media_field_invalid_k");
      for (const line of refused) {
        this.assertEqual(refusal_text(this, line), expected);
      }
    }

    // A url that is missing, empty or not text is refused.
    test_url_invalid(): void {
      const refused: lines.Line[] = [gold_line("fetch_urlless")];
      for (const url of [undefined, null, "", 5, {}]) {
        refused.push(line_fields("fetch_urlless", { url }));
      }
      const expected = gold_text("media_field_invalid_url");
      for (const line of refused) {
        this.assertEqual(refusal_text(this, line), expected);
      }
    }
  }

  // The reply lines made for an image that was kept.
  export class TestReplyLines extends unittest.TestCase {
    // A store is answered with its key, size and hash and no blob.
    test_store_reply(): void {
      const entry = digest_entry("abc");
      const reply = exchange_make("store").image_reply(entry.data);
      const expected = gold_line("reply_store");
      expected.sha256 = entry.sha256;
      this.assertEqual(reply, expected);
      this.assertEqual(Object.keys(reply).join(","), "0,k,size,sha256");
    }

    // A fetch is answered with the same payload and the bytes as blob 1.
    test_fetch_reply(): void {
      const entry = digest_entry("abc");
      const reply = exchange_make("fetch").image_reply(entry.data);
      const expected = gold_line("reply_fetch");
      (expected[1] as lines.BlobHeader).d = entry.data;
      expected.sha256 = entry.sha256;
      this.assertEqual(reply, expected);
      this.assertEqual(Object.keys(reply).join(","), "0,1,k,size,sha256");
    }

    // The reply carries the id of its own request and no id of its own.
    test_reply_number(): void {
      const requests: [number, string, string][] = [
        [1, "store_id_1", "fetch_id_1"],
        [2, "store_id_2", "fetch_id_2"],
        [41, "store_id_41", "fetch_id_41"],
      ];
      for (const [id, store_name, fetch_name] of requests) {
        const store = exchange_make(store_name).image_reply(bytes_make());
        const fetched = exchange_make(fetch_name).image_reply(bytes_make());
        for (const reply of [store, fetched]) {
          this.assertEqual(reply[0].r, id);
          this.assertFalse(Object.hasOwn(reply[0], "i"));
        }
      }
    }

    // A request in full names is answered in full names.
    test_full_names(): void {
      const store = exchange_make("store_full").image_reply(bytes_make());
      this.assertEqual(store[0], gold_value("lines.header_store_full"));
      const fetched = exchange_make("fetch_full").image_reply(bytes_make());
      this.assertEqual(fetched[0], gold_value("lines.header_fetch_full"));
    }

    // The size and hash are those of the bytes in a view, not of its buffer.
    test_view_bytes(): void {
      const entry = digest_entry("abc");
      const buffer = new Uint8Array(entry.data.length + 2);
      buffer.set(entry.data, 1);
      const view = buffer.subarray(1, 1 + entry.data.length);
      const reply = exchange_make("store").image_reply(view);
      this.assertEqual(reply.size, entry.data.length);
      this.assertEqual(reply.sha256, entry.sha256);
    }
  }

  // The error line made for a download that outlived its timer.
  export class TestFailureLines extends unittest.TestCase {
    // The timeout gives an error line naming the url, key and seconds.
    test_timeout_text(): void {
      const reply = exchange_make("fetch").timeout_reply(constants.url, 5);
      const expected = gold_text("media_download_expired_whole");
      this.assertEqual(reply[0], gold_value("lines.header_error"));
      this.assertEqual(Object.keys(reply).join(","), "0,message,stack");
      this.assertEqual(reply.message, expected);
      this.assertEqual(typeof reply.stack, "string");
    }

    // Fractions of a second are named as they are.
    test_timeout_fraction(): void {
      const reply = exchange_make("fetch").timeout_reply(constants.url, 0.5);
      const expected = gold_text("media_download_expired_fraction");
      this.assertEqual(reply.message, expected);
    }

    // The timeout's error line follows the name form of the request.
    test_error_full(): void {
      const exchange = exchange_make("fetch_full");
      const expected = gold_value("lines.header_error_full");
      this.assertEqual(exchange.timeout_reply(constants.url, 5)[0], expected);
    }
  }

  // The checks of the port that run before any decode or fetch starts.
  export class TestPortChecks extends unittest.TestCase {
    // Timeouts above 0 that a timer can hold are accepted.
    test_timeout_valid(): void {
      for (const seconds of [0.5, 1, 120, 2147483]) {
        const port = new media.MediaPort(constants.budget, seconds);
        this.assertEqual(port.image_get(constants.key), undefined);
      }
    }

    // Timeouts that are 0, negative or too long for a timer throw.
    test_timeout_invalid(): void {
      const timeouts: [number, string][] = [
        [0, "media_timeout_invalid_zero"],
        [-1, "media_timeout_invalid_negative"],
        [2147484, "media_timeout_invalid_long"],
      ];
      for (const [seconds, name] of timeouts) {
        const message = message_thrown(
          this,
          () => new media.MediaPort(constants.budget, seconds),
        );
        this.assertEqual(message, gold_text(name));
      }
    }

    // A budget that is 0 or negative throws from the port too.
    test_budget_invalid(): void {
      const budgets: [number, string][] = [
        [0, "media_budget_invalid_zero"],
        [-1, "media_budget_invalid_negative"],
      ];
      for (const [budget, name] of budgets) {
        const message = message_thrown(
          this,
          () => new media.MediaPort(budget, 1),
        );
        this.assertEqual(message, gold_text(name));
      }
    }

    // A second receiver throws.
    test_receiver_twice(): void {
      const port = new media.MediaPort(constants.budget, 1);
      port.line_receive(() => {});
      const message = message_thrown(this, () => port.line_receive(() => {}));
      this.assertEqual(message, gold_text("media_receiver_twice"));
    }

    // A request posted before a receiver is set throws.
    test_post_unreceived(): void {
      const port = new media.MediaPort(constants.budget, 1);
      const line = line_bytes("store");
      const message = message_thrown(this, () => port.line_post(line, []));
      this.assertEqual(message, gold_text("media_receiver_missing"));
    }

    // A line that fails a check throws from the post and nothing is received.
    test_post_refused(): void {
      const port = new media.MediaPort(constants.budget, 1);
      let received = 0;
      port.line_receive(() => {
        received += 1;
      });
      const cases: [lines.Line, string][] = [
        [gold_line("kv_get_key"), gold_text("media_type_invalid")],
        [line_bytes("store_unnumbered"), gold_text("media_id_missing_store")],
        [gold_line("fetch_unnumbered"), gold_text("media_id_missing_fetch")],
        [gold_line("store_unblobbed"), gold_text("media_blobs_invalid_none")],
        [
          line_fields("fetch_urlless", { url: 5 }),
          gold_text("media_field_invalid_url"),
        ],
      ];
      for (const [line, expected] of cases) {
        const message = message_thrown(this, () => port.line_post(line, []));
        this.assertEqual(message, expected);
      }
      this.assertEqual(received, 0);
    }

    // A port that has kept nothing has no image under any key.
    test_image_absent(): void {
      const port = new media.MediaPort(constants.budget, 1);
      this.assertEqual(port.image_get(constants.key), undefined);
    }
  }
}

Object.freeze(test_media);
