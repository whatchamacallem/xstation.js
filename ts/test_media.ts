// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Tests of the media cache and port that need no image decoder and no
// network. No test here posts a request that passes the checks, so no test
// starts a decode or a `fetch`.

namespace test_media {
  // The values the tests share.
  const constants = Object.freeze({
    key: "/_files/gatehouse/arrival.png",
    url: "https://images.example.test/arrival.png",
    id: 7,
    budget: 1000,
    pixel_bytes: 4,
    abc_hash:
      "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
  });

  // A payload of fields by name.
  type PayloadFields = { [key: string]: unknown };

  // The header options of a line: its id and whether it has full names.
  type HeaderOptions = { id?: number; full?: boolean };

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

  // An image one pixel high that counts as the given number of bytes.
  function image_make(bytes: number): ImageDouble {
    return new ImageDouble(bytes / constants.pixel_bytes, 1);
  }

  // A cache with the budget of the tests.
  function cache_make(): media.ImageCache {
    return new media.ImageCache(constants.budget);
  }

  // The bytes of the image the tests send: the text abc.
  function bytes_make(): Uint8Array {
    return new Uint8Array([0x61, 0x62, 0x63]);
  }

  // A line of the type with the payload, header options and blobs given.
  function line_build(
    type: string,
    payload: PayloadFields,
    options: HeaderOptions,
    blobs: lines.BlobHeader[] = [],
  ): lines.Line {
    return jslb.line_make(jslb.header_make(type, options), blobs, payload);
  }

  // A `media.store` line of the key with one blob holding the bytes.
  function store_line(options: HeaderOptions): lines.Line {
    const blob = jslb.blob_make(bytes_make());
    return line_build("media.store", { k: constants.key }, options, [blob]);
  }

  // A `media.fetch` line of the url and key.
  function fetch_line(options: HeaderOptions): lines.Line {
    const payload = { url: constants.url, k: constants.key };
    return line_build("media.fetch", payload, options);
  }

  // The exchange of a `media.store` line, by default numbered 7, short names.
  function store_exchange(
    options: HeaderOptions = { id: constants.id },
  ): media.MediaExchange {
    return new media.MediaExchange(store_line(options));
  }

  // The exchange of a `media.fetch` line, by default numbered 7, short names.
  function fetch_exchange(
    options: HeaderOptions = { id: constants.id },
  ): media.MediaExchange {
    return new media.MediaExchange(fetch_line(options));
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

    // Budgets that are 0, negative or not finite throw.
    test_budget_invalid(): void {
      for (const budget of [0, -1, NaN, Infinity, -Infinity]) {
        const message = message_thrown(
          this,
          () => new media.ImageCache(budget),
        );
        this.assertEqual(message, i18n("media.budget_invalid", budget));
      }
    }
  }

  // The checks that refuse a line before anything is decoded or sent.
  export class TestRequestChecks extends unittest.TestCase {
    // The smallest store request is accepted and keeps its bytes.
    test_store_least(): void {
      const exchange = store_exchange();
      this.assertEqual(exchange.key, constants.key);
      this.assertEqual(exchange.source, bytes_make());
    }

    // The smallest fetch request is accepted and keeps its url.
    test_fetch_least(): void {
      const exchange = fetch_exchange();
      this.assertEqual(exchange.key, constants.key);
      this.assertEqual(exchange.source, constants.url);
    }

    // A line of another type is refused.
    test_type_other(): void {
      const payload = { url: constants.url, k: constants.key };
      const line = line_build("kv.get", payload, { id: constants.id });
      const expected = i18n(
        "media.type_invalid",
        "kv.get",
        "media.store",
        "media.fetch",
      );
      this.assertEqual(refusal_text(this, line), expected);
    }

    // A request with no id is refused, as nothing could answer it.
    test_id_missing(): void {
      const store = refusal_text(this, store_line({}));
      const fetched = refusal_text(this, fetch_line({}));
      this.assertEqual(store, i18n("media.id_missing", "media.store"));
      this.assertEqual(fetched, i18n("media.id_missing", "media.fetch"));
    }

    // A store needs exactly one blob and a fetch needs none.
    test_blobs_count(): void {
      const options = { id: constants.id };
      const blob = jslb.blob_make(bytes_make());
      const store_payload = { k: constants.key };
      const fetch_payload = { url: constants.url, k: constants.key };
      const cases: [lines.Line, string][] = [
        [
          line_build("media.store", store_payload, options),
          i18n("media.blobs_invalid", "media.store", 0, 1),
        ],
        [
          line_build("media.store", store_payload, options, [blob, blob]),
          i18n("media.blobs_invalid", "media.store", 2, 1),
        ],
        [
          line_build("media.fetch", fetch_payload, options, [blob]),
          i18n("media.blobs_invalid", "media.fetch", 1, 0),
        ],
      ];
      for (const [line, expected] of cases) {
        this.assertEqual(refusal_text(this, line), expected);
      }
    }

    // A store whose blob is a cache handle and not bytes is refused.
    test_blob_handle(): void {
      const blob: lines.BlobHeader = { s: 3, d: "cache/handle" };
      const line = line_build(
        "media.store",
        { k: constants.key },
        { id: constants.id },
        [blob],
      );
      const expected = i18n("media.blob_bytes", "media.store");
      this.assertEqual(refusal_text(this, line), expected);
    }

    // A key that is missing, empty or not text is refused in both types.
    test_key_invalid(): void {
      const blob = jslb.blob_make(bytes_make());
      const options = { id: constants.id };
      const refused: lines.Line[] = [
        line_build("media.store", {}, options, [blob]),
        line_build("media.fetch", { url: constants.url }, options),
      ];
      for (const k of [undefined, null, "", 5, ["a"]]) {
        refused.push(line_build("media.store", { k }, options, [blob]));
        refused.push(
          line_build("media.fetch", { url: constants.url, k }, options),
        );
      }
      const expected = i18n("media.field_invalid", "k");
      for (const line of refused) {
        this.assertEqual(refusal_text(this, line), expected);
      }
    }

    // A url that is missing, empty or not text is refused.
    test_url_invalid(): void {
      const options = { id: constants.id };
      const refused: lines.Line[] = [
        line_build("media.fetch", { k: constants.key }, options),
      ];
      for (const url of [undefined, null, "", 5, {}]) {
        const payload = { url, k: constants.key };
        refused.push(line_build("media.fetch", payload, options));
      }
      const expected = i18n("media.field_invalid", "url");
      for (const line of refused) {
        this.assertEqual(refusal_text(this, line), expected);
      }
    }
  }

  // The reply lines made for an image that was kept.
  export class TestReplyLines extends unittest.TestCase {
    // A store is answered with its key, size and hash and no blob.
    test_store_reply(): void {
      const reply = store_exchange().image_reply(bytes_make());
      this.assertEqual(reply[0], { t: "media.store", r: constants.id });
      this.assertEqual(Object.keys(reply).join(","), "0,k,size,sha256");
      this.assertEqual(reply.k, constants.key);
      this.assertEqual(reply.size, 3);
      this.assertEqual(reply.sha256, constants.abc_hash);
      this.assertEqual(jslb.headers_of(reply).length, 1);
    }

    // A fetch is answered with the same payload and the bytes as blob 1.
    test_fetch_reply(): void {
      const reply = fetch_exchange().image_reply(bytes_make());
      this.assertEqual(jslb.field_get(reply[0], "type"), "media.fetch");
      this.assertEqual(jslb.field_get(reply[0], "reply"), constants.id);
      this.assertEqual(jslb.field_get(reply[0], "blobs"), 1);
      this.assertEqual(Object.keys(reply).join(","), "0,1,k,size,sha256");
      this.assertEqual(reply.k, constants.key);
      this.assertEqual(reply.size, 3);
      this.assertEqual(reply.sha256, constants.abc_hash);
      const blob = reply[1] as lines.BlobHeader;
      this.assertEqual(jslb.field_get(blob, "size"), 3);
      this.assertEqual(jslb.field_get(blob, "data"), bytes_make());
    }

    // The reply carries the id of its own request and no id of its own.
    test_reply_number(): void {
      for (const id of [1, 2, 41]) {
        const store = store_exchange({ id }).image_reply(bytes_make());
        const fetched = fetch_exchange({ id }).image_reply(bytes_make());
        for (const reply of [store, fetched]) {
          this.assertEqual(jslb.field_get(reply[0], "reply"), id);
          this.assertFalse(Object.hasOwn(reply[0], "i"));
        }
      }
    }

    // A request in full names is answered in full names.
    test_full_names(): void {
      const options = { id: constants.id, full: true };
      const store = store_exchange(options).image_reply(bytes_make());
      this.assertEqual(store[0], { type: "media.store", reply: constants.id });
      const fetched = fetch_exchange(options).image_reply(bytes_make());
      this.assertEqual(jslb.field_get(fetched[0], "type"), "media.fetch");
      this.assertTrue(Object.hasOwn(fetched[0], "type"));
      this.assertFalse(Object.hasOwn(fetched[0], "t"));
      this.assertEqual(jslb.field_get(fetched[0], "reply"), constants.id);
    }

    // The size and hash are those of the bytes in a view, not of its buffer.
    test_view_bytes(): void {
      const buffer = new Uint8Array([0, 0x61, 0x62, 0x63, 0]);
      const reply = store_exchange().image_reply(buffer.subarray(1, 4));
      this.assertEqual(reply.size, 3);
      this.assertEqual(reply.sha256, constants.abc_hash);
    }
  }

  // The error lines made for bytes that fail to decode and for downloads.
  export class TestFailureLines extends unittest.TestCase {
    // Bytes that do not decode give an error line naming the key and cause.
    test_decode_text(): void {
      const cause = new Error("bad bytes");
      const reply = store_exchange().decode_reply(cause);
      const text = String(cause);
      const expected = i18n("media.decode_failed", constants.key, text);
      this.assertEqual(reply[0], { t: "error", r: constants.id });
      this.assertEqual(Object.keys(reply).join(","), "0,message,stack");
      this.assertEqual(reply.message, expected);
      this.assertEqual(typeof reply.stack, "string");
    }

    // A cause that is no error is named by its text.
    test_decode_other(): void {
      const exchange = store_exchange();
      for (const cause of ["boom", 5, undefined, null]) {
        const reply = exchange.decode_reply(cause);
        const text = String(cause);
        const expected = i18n("media.decode_failed", constants.key, text);
        this.assertEqual(reply.message, expected);
      }
    }

    // A failed download gives an error line naming the url, key and cause.
    test_download_text(): void {
      const exchange = fetch_exchange();
      const cause = new TypeError("Failed to fetch");
      const reply = exchange.download_reply(constants.url, cause);
      const expected = i18n(
        "media.download_failed",
        constants.url,
        constants.key,
        String(cause),
      );
      this.assertEqual(reply[0], { t: "error", r: constants.id });
      this.assertEqual(Object.keys(reply).join(","), "0,message,stack");
      this.assertEqual(reply.message, expected);
      this.assertEqual(typeof reply.stack, "string");
    }

    // The timeout gives an error line naming the url, key and seconds.
    test_timeout_text(): void {
      const reply = fetch_exchange().timeout_reply(constants.url, 5);
      const expected = i18n(
        "media.download_expired",
        constants.url,
        constants.key,
        5,
      );
      this.assertEqual(reply[0], { t: "error", r: constants.id });
      this.assertEqual(Object.keys(reply).join(","), "0,message,stack");
      this.assertEqual(reply.message, expected);
      this.assertEqual(typeof reply.stack, "string");
    }

    // Fractions of a second are named as they are.
    test_timeout_fraction(): void {
      const reply = fetch_exchange().timeout_reply(constants.url, 0.5);
      const expected = i18n(
        "media.download_expired",
        constants.url,
        constants.key,
        0.5,
      );
      this.assertEqual(reply.message, expected);
    }

    // The three failures have three different messages.
    test_messages_distinct(): void {
      const exchange = fetch_exchange();
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
      const exchange = fetch_exchange({ id: constants.id, full: true });
      const expected = { type: "error", reply: constants.id };
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

    // Timeouts that are 0, negative, not finite or too long for a timer throw.
    test_timeout_invalid(): void {
      for (const seconds of [0, -1, NaN, Infinity, 2147484]) {
        const message = message_thrown(
          this,
          () => new media.MediaPort(constants.budget, seconds),
        );
        this.assertEqual(message, i18n("media.timeout_invalid", seconds));
      }
    }

    // A budget that is 0, negative or not finite throws from the port too.
    test_budget_invalid(): void {
      for (const budget of [0, -1, NaN, Infinity]) {
        const message = message_thrown(
          this,
          () => new media.MediaPort(budget, 1),
        );
        this.assertEqual(message, i18n("media.budget_invalid", budget));
      }
    }

    // A second receiver throws.
    test_receiver_twice(): void {
      const port = new media.MediaPort(constants.budget, 1);
      port.line_receive(() => {});
      const message = message_thrown(this, () => port.line_receive(() => {}));
      this.assertEqual(message, i18n("media.receiver_twice"));
    }

    // A request posted before a receiver is set throws.
    test_post_unreceived(): void {
      const port = new media.MediaPort(constants.budget, 1);
      const line = store_line({ id: constants.id });
      const message = message_thrown(this, () => port.line_post(line, []));
      this.assertEqual(message, i18n("media.receiver_missing"));
    }

    // A line that fails a check throws from the post and nothing is received.
    test_post_refused(): void {
      const port = new media.MediaPort(constants.budget, 1);
      let received = 0;
      port.line_receive(() => {
        received += 1;
      });
      const options = { id: constants.id };
      const store_payload = { k: constants.key };
      const fetch_payload = { url: 5, k: constants.key };
      const cases: [lines.Line, string][] = [
        [
          line_build("kv.get", store_payload, options),
          i18n("media.type_invalid", "kv.get", "media.store", "media.fetch"),
        ],
        [store_line({}), i18n("media.id_missing", "media.store")],
        [fetch_line({}), i18n("media.id_missing", "media.fetch")],
        [
          line_build("media.store", store_payload, options),
          i18n("media.blobs_invalid", "media.store", 0, 1),
        ],
        [
          line_build("media.fetch", fetch_payload, options),
          i18n("media.field_invalid", "url"),
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
