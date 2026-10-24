// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The UI thread's media cache and the port that fills it. The port decodes
// the image of each `media.store` line, downloads and decodes the image of
// each `media.fetch` line, and answers with a reply line. The cache keeps the
// decoded images within a byte budget, the newest kept. Its promises and its
// timer only turn an event of the platform into a line.

namespace media {
  // The line types, header key, bytes of a pixel and timer limits.
  const constants = Object.freeze({
    store_type: "media.store",
    fetch_type: "media.fetch",
    error_type: "error",
    full_key: "type",
    pixel_bytes: 4,
    second_ms: 1000,
    timer_max_ms: 2 ** 31 - 1,
  });

  // A decoded image and the bytes it was counted as when it was kept.
  interface CacheEntry {
    image: ImageBitmap;
    bytes: number;
  }

  // The bytes a decoded image counts as: its width times height times 4.
  function image_bytes(image: ImageBitmap): number {
    return image.width * image.height * constants.pixel_bytes;
  }

  // Decoded images by key within a byte budget, the newest always kept.
  export class ImageCache {
    private readonly budget_bytes: number;
    private readonly entries = new Map<lines.KvRef, CacheEntry>();
    private total = 0;

    // Takes the budget in bytes, which must be above 0.
    constructor(budget_bytes: number) {
      if (budget_bytes <= 0) {
        throw new Error(i18n("media.budget_invalid", budget_bytes));
      }
      this.budget_bytes = budget_bytes;
    }

    // Keeps the image as the newest, then evicts the oldest to fit the budget.
    image_put(k: lines.KvRef, image: ImageBitmap): void {
      this.entry_drop(k);
      const bytes = image_bytes(image);
      this.entries.set(k, { image, bytes });
      this.total += bytes;
      for (const key of this.entries.keys()) {
        if (key === k || this.total <= this.budget_bytes) {
          break;
        }
        this.entry_drop(key);
      }
    }

    // The decoded image, or undefined once evicted.
    image_get(k: lines.KvRef): ImageBitmap | undefined {
      return this.entries.get(k)?.image;
    }

    // The bytes of every image kept.
    total_bytes(): number {
      return this.total;
    }

    // The keys kept, the oldest first.
    keys_list(): lines.KvRef[] {
      return [...this.entries.keys()];
    }

    // Removes the entry of the key, if there is one, and closes its image.
    private entry_drop(k: lines.KvRef): void {
      const entry = this.entries.get(k);
      if (entry === undefined) {
        return;
      }
      this.entries.delete(k);
      this.total -= entry.bytes;
      entry.image.close();
    }
  }

  // Whether the value is the type of a line the media port answers.
  function type_known(value: unknown): value is string {
    return value === constants.store_type || value === constants.fetch_type;
  }

  // The error for a request field that is missing or not valid.
  function field_error(name: string): Error {
    return new Error(i18n("media.field_invalid", name));
  }

  // The bytes of blob 1 of a `media.store` line, which must be in memory.
  function blob_bytes(line: lines.Line): Uint8Array {
    const data = jslb.field_get(line[1] as lines.BlobHeader, "data");
    if (!(data instanceof Uint8Array)) {
      throw new Error(i18n("media.blob_bytes", constants.store_type));
    }
    return data;
  }

  // The steps from one request line to its reply lines.
  export class MediaExchange {
    // The key the image is kept under.
    readonly key: lines.KvRef;
    // The bytes of a `media.store` line, or the url of a `media.fetch` line.
    readonly source: Uint8Array | string;
    private readonly type: string;
    private readonly id: number;
    private readonly full: boolean;

    // Takes a `media.store` or `media.fetch` line with an id and valid fields.
    constructor(line: lines.Line) {
      const header = line[0];
      const type = jslb.field_get(header, "type");
      if (!type_known(type)) {
        throw new Error(
          i18n(
            "media.type_invalid",
            type,
            constants.store_type,
            constants.fetch_type,
          ),
        );
      }
      const id = jslb.field_get(header, "id");
      if (typeof id !== "number") {
        throw new Error(i18n("media.id_missing", type));
      }
      const wanted = type === constants.store_type ? 1 : 0;
      const blobs = jslb.headers_of(line).length - 1;
      if (blobs !== wanted) {
        throw new Error(i18n("media.blobs_invalid", type, blobs, wanted));
      }
      const payload = jslb.payload_of(line);
      const key = payload.k;
      if (typeof key !== "string" || key.length === 0) {
        throw field_error("k");
      }
      if (type === constants.store_type) {
        this.source = blob_bytes(line);
      } else {
        const url = payload.url;
        if (typeof url !== "string" || url.length === 0) {
          throw field_error("url");
        }
        this.source = url;
      }
      this.type = type;
      this.id = id;
      this.full = Object.hasOwn(header, constants.full_key);
      this.key = key;
    }

    // The reply for a kept image, with the bytes as blob 1 for a download.
    image_reply(bytes: Uint8Array): lines.Line {
      const blobs =
        this.type === constants.fetch_type ? [jslb.blob_make(bytes)] : [];
      return this.reply_make(this.type, blobs, {
        k: this.key,
        size: bytes.length,
        sha256: utility.sha256_hex(bytes),
      });
    }

    // The error reply to bytes that did not decode.
    decode_reply(cause: unknown): lines.Line {
      return this.error_reply(
        utility.error_wrap(
          i18n("media.decode_failed", this.key, String(cause)),
          cause,
        ),
      );
    }

    // The error reply to a download that failed.
    download_reply(url: string, cause: unknown): lines.Line {
      return this.error_reply(
        utility.error_wrap(
          i18n("media.download_failed", url, this.key, String(cause)),
          cause,
        ),
      );
    }

    // The error reply to a download that outlived its timer.
    timeout_reply(url: string, timeout_seconds: number): lines.Line {
      return this.error_reply(
        new Error(
          i18n("media.download_expired", url, this.key, timeout_seconds),
        ),
      );
    }

    // The line that answers the request, with its id as `r`.
    private reply_make(
      type: string,
      blobs: lines.BlobHeader[],
      payload: { [key: string]: unknown },
    ): lines.Line {
      const header = jslb.header_make(type, {
        reply: this.id,
        full: this.full,
      });
      return jslb.line_make(header, blobs, payload);
    }

    // The `error` line of the request: the message and stack of an error.
    private error_reply(error: Error): lines.Line {
      return this.reply_make(constants.error_type, [], {
        message: error.message,
        stack: error.stack,
      });
    }
  }

  // Downloads the url to its end: a status outside 200 to 299 throws.
  function bytes_download(
    url: string,
    signal: AbortSignal,
  ): Promise<Uint8Array> {
    return fetch(url, { signal })
      .then((response: Response) => {
        if (!response.ok) {
          throw new Error(i18n("media.status_failed", url, response.status));
        }
        return response.arrayBuffer();
      })
      .then((buffer: ArrayBuffer) => new Uint8Array(buffer));
  }

  // The port that answers `media.store` and `media.fetch` lines.
  export class MediaPort implements queue.Port {
    private readonly cache: ImageCache;
    private readonly timeout_seconds: number;
    private receiver: ((line: lines.Line) => void) | undefined;

    // Takes the cache budget in bytes and the seconds a download may last.
    constructor(budget_bytes: number, timeout_seconds: number) {
      if (
        timeout_seconds <= 0 ||
        timeout_seconds * constants.second_ms > constants.timer_max_ms
      ) {
        throw new Error(i18n("media.timeout_invalid", timeout_seconds));
      }
      this.cache = new ImageCache(budget_bytes);
      this.timeout_seconds = timeout_seconds;
    }

    // Starts the decode or the download of a line, which is answered later.
    line_post(line: lines.Line, _transfer: ArrayBuffer[]): void {
      const receiver = this.receiver;
      if (receiver === undefined) {
        throw new Error(i18n("media.receiver_missing"));
      }
      const exchange = new MediaExchange(line);
      const source = exchange.source;
      if (typeof source === "string") {
        this.fetch_start(exchange, source, receiver);
      } else {
        this.image_keep(exchange, source).then((reply: lines.Line) =>
          receiver(reply),
        );
      }
    }

    // Sets the one receiver of the reply lines.
    line_receive(fn: (line: lines.Line) => void): void {
      if (this.receiver !== undefined) {
        throw new Error(i18n("media.receiver_twice"));
      }
      this.receiver = fn;
    }

    // The decoded image, or undefined once evicted.
    image_get(k: lines.KvRef): ImageBitmap | undefined {
      return this.cache.image_get(k);
    }

    // Downloads the url under a timer, then keeps the image it holds.
    private fetch_start(
      exchange: MediaExchange,
      url: string,
      receiver: (line: lines.Line) => void,
    ): void {
      const controller = new AbortController();
      const timer = setTimeout(
        () => controller.abort(),
        this.timeout_seconds * constants.second_ms,
      );
      bytes_download(url, controller.signal)
        .then(
          (bytes: Uint8Array) => {
            clearTimeout(timer);
            return this.image_keep(exchange, bytes);
          },
          (cause: unknown) => {
            clearTimeout(timer);
            return controller.signal.aborted
              ? exchange.timeout_reply(url, this.timeout_seconds)
              : exchange.download_reply(url, cause);
          },
        )
        .then((reply: lines.Line) => receiver(reply));
    }

    // Decodes the bytes and keeps the image, or answers with an error line.
    private image_keep(
      exchange: MediaExchange,
      bytes: Uint8Array,
    ): Promise<lines.Line> {
      return createImageBitmap(new Blob([bytes.slice()])).then(
        (image: ImageBitmap) => {
          this.cache.image_put(exchange.key, image);
          return exchange.image_reply(bytes);
        },
        (cause: unknown) => exchange.decode_reply(cause),
      );
    }
  }
}

Object.freeze(media);
