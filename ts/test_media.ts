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
    pixel_bytes: 4,
    digests_name: "test_digests.json",
  });

  // One entry of the digest vector: an input and its `SHA-256`, both in hex.
  type DigestRecord = { data: string; sha256: string };

  // The digest vector: test module to entry name to its record.
  type DigestVector = { [module: string]: { [name: string]: DigestRecord } };

  // The digest vector of every test module, read once.
  let digests: DigestVector | null = null;

  // An image that counts its closes and, once closed, reports no size.
  class ImageDouble {
    width: number;
    height: number;
    closes = 0;

    // Takes the size of the image in pixels.
    constructor(width: number, height: number) {
      this.width = width;
      this.height = height;
    }

    // Counts the close and drops the size.
    close(): void {
      this.closes += 1;
      this.width = 0;
      this.height = 0;
    }
  }

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

  // An image one pixel high that counts as the given number of bytes.
  function image_make(bytes: number): ImageDouble {
    return new ImageDouble(bytes / constants.pixel_bytes, 1);
  }

  // A cache with the budget of the tests.
  function cache_make(): media.ImageCache {
    return new media.ImageCache(constants.budget);
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

  // The order and accounting of the images a cache keeps.
  export class TestCacheEviction extends unittest.TestCase {
    // Each image counts as its width times height times 4 bytes.
    test_bytes_counted(): void {
      const cache = cache_make();
      cache.image_put("a", new ImageDouble(10, 10));
      cache.image_put("b", new ImageDouble(5, 10));
      this.assertEqual(cache.total_bytes(), 600);
      this.assertEqual(cache.keys_list(), ["a", "b"]);
    }

    // A total exactly at the budget is within it, so nothing is evicted.
    test_budget_exact(): void {
      const cache = cache_make();
      const first = image_make(400);
      const second = image_make(600);
      cache.image_put("a", first);
      cache.image_put("b", second);
      this.assertEqual(cache.total_bytes(), constants.budget);
      this.assertEqual(cache.keys_list(), ["a", "b"]);
      this.assertEqual(first.closes + second.closes, 0);
    }

    // The oldest goes first, closed, and the total drops by its counted bytes.
    test_oldest_evicted(): void {
      const cache = cache_make();
      const images = [image_make(400), image_make(400), image_make(400)];
      cache.image_put("a", images[0]);
      cache.image_put("b", images[1]);
      cache.image_put("c", images[2]);
      this.assertEqual(cache.keys_list(), ["b", "c"]);
      this.assertEqual(cache.total_bytes(), 800);
      this.assertEqual(cache.image_get("a"), undefined);
      this.assertTrue(cache.image_get("b") === images[1]);
      this.assertTrue(cache.image_get("c") === images[2]);
      this.assertEqual(
        images.map((image) => image.closes),
        [1, 0, 0],
      );
    }

    // Eviction stops as soon as the total fits, so the younger images stay.
    test_evict_least(): void {
      const cache = cache_make();
      const images = [
        image_make(400),
        image_make(200),
        image_make(200),
        image_make(600),
      ];
      images.forEach((image, index) => {
        cache.image_put("abcd"[index], image);
      });
      this.assertEqual(cache.keys_list(), ["b", "c", "d"]);
      this.assertEqual(cache.total_bytes(), 1000);
      this.assertEqual(
        images.map((image) => image.closes),
        [1, 0, 0, 0],
      );
    }

    // One large image evicts every older image, oldest first.
    test_evict_many(): void {
      const cache = cache_make();
      const images = [
        image_make(400),
        image_make(200),
        image_make(200),
        image_make(1000),
      ];
      images.forEach((image, index) => {
        cache.image_put("abcd"[index], image);
      });
      this.assertEqual(cache.keys_list(), ["d"]);
      this.assertEqual(cache.total_bytes(), 1000);
      this.assertEqual(
        images.map((image) => image.closes),
        [1, 1, 1, 0],
      );
    }

    // The newest image is kept alone though it is over the budget.
    test_newest_alone(): void {
      const cache = cache_make();
      const older = image_make(400);
      const larger = image_make(1600);
      cache.image_put("a", older);
      cache.image_put("b", larger);
      this.assertEqual(cache.keys_list(), ["b"]);
      this.assertEqual(cache.total_bytes(), 1600);
      this.assertTrue(cache.image_get("b") === larger);
      this.assertEqual([older.closes, larger.closes], [1, 0]);
    }

    // An image over the budget is kept in an empty cache.
    test_oversize_first(): void {
      const cache = cache_make();
      const larger = image_make(1600);
      cache.image_put("a", larger);
      this.assertEqual(cache.keys_list(), ["a"]);
      this.assertEqual(cache.total_bytes(), 1600);
      this.assertEqual(larger.closes, 0);
    }

    // The next image evicts an oversize one, as the oldest image goes first.
    test_oversize_evicted(): void {
      const cache = cache_make();
      const larger = image_make(1600);
      const next = image_make(400);
      cache.image_put("a", larger);
      cache.image_put("b", next);
      this.assertEqual(cache.keys_list(), ["b"]);
      this.assertEqual(cache.total_bytes(), 400);
      this.assertEqual([larger.closes, next.closes], [1, 0]);
    }

    // A key kept again closes the old image and makes the new one newest.
    test_key_replaced(): void {
      const cache = cache_make();
      const old = image_make(400);
      const other = image_make(200);
      const fresh = image_make(600);
      cache.image_put("a", old);
      cache.image_put("b", other);
      cache.image_put("a", fresh);
      this.assertEqual(cache.keys_list(), ["b", "a"]);
      this.assertEqual(cache.total_bytes(), 800);
      this.assertTrue(cache.image_get("a") === fresh);
      this.assertEqual([old.closes, other.closes, fresh.closes], [1, 0, 0]);
    }

    // A replacement can evict, and the old image is not counted twice.
    test_replace_evicts(): void {
      const cache = cache_make();
      const old = image_make(400);
      const other = image_make(400);
      const fresh = image_make(800);
      cache.image_put("a", old);
      cache.image_put("b", other);
      cache.image_put("a", fresh);
      this.assertEqual(cache.keys_list(), ["a"]);
      this.assertEqual(cache.total_bytes(), 800);
      this.assertEqual([old.closes, other.closes, fresh.closes], [1, 1, 0]);
    }

    // Looking an image up does not make it newer.
    test_lookup_order(): void {
      const cache = cache_make();
      cache.image_put("a", image_make(400));
      cache.image_put("b", image_make(400));
      this.assertFalse(cache.image_get("a") === undefined);
      cache.image_put("c", image_make(400));
      this.assertEqual(cache.keys_list(), ["b", "c"]);
    }

    // A key that was never kept has no image.
    test_get_missing(): void {
      const cache = cache_make();
      this.assertEqual(cache.image_get("a"), undefined);
      cache.image_put("b", image_make(400));
      this.assertEqual(cache.image_get("a"), undefined);
    }
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

  // The error lines made for bytes that fail to decode and for downloads.
  export class TestFailureLines extends unittest.TestCase {
    // Bytes that do not decode give an error line naming the key and cause.
    test_decode_text(): void {
      const cause = new Error("bad bytes");
      const reply = exchange_make("store").decode_reply(cause);
      const expected = gold_text("media_decode_failed_error");
      this.assertEqual(reply[0], gold_value("lines.header_error"));
      this.assertEqual(Object.keys(reply).join(","), "0,message,stack");
      this.assertEqual(reply.message, expected);
      this.assertEqual(typeof reply.stack, "string");
    }

    // A cause that is no error is named by its text.
    test_decode_other(): void {
      const exchange = exchange_make("store");
      const causes: [unknown, string][] = [
        ["boom", "media_decode_failed_text"],
        [5, "media_decode_failed_number"],
        [undefined, "media_decode_failed_undefined"],
        [null, "media_decode_failed_null"],
      ];
      for (const [cause, name] of causes) {
        const reply = exchange.decode_reply(cause);
        this.assertEqual(reply.message, gold_text(name));
      }
    }

    // A failed download gives an error line naming the url, key and cause.
    test_download_text(): void {
      const exchange = exchange_make("fetch");
      const cause = new TypeError("Failed to fetch");
      const reply = exchange.download_reply(constants.url, cause);
      const expected = gold_text("media_download_failed");
      this.assertEqual(reply[0], gold_value("lines.header_error"));
      this.assertEqual(Object.keys(reply).join(","), "0,message,stack");
      this.assertEqual(reply.message, expected);
      this.assertEqual(typeof reply.stack, "string");
    }

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

    // The three failures have three different messages.
    test_messages_distinct(): void {
      const exchange = exchange_make("fetch");
      const cause = new Error("x");
      const messages = [
        exchange.decode_reply(cause).message,
        exchange.download_reply(constants.url, cause).message,
        exchange.timeout_reply(constants.url, 5).message,
      ];
      this.assertEqual(new Set(messages).size, 3);
    }

    // The error lines follow the name form of the request.
    test_error_full(): void {
      const exchange = exchange_make("fetch_full");
      const expected = gold_value("lines.header_error_full");
      const cause = new Error("x");
      const download = exchange.download_reply(constants.url, cause);
      this.assertEqual(exchange.decode_reply(cause)[0], expected);
      this.assertEqual(download[0], expected);
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
