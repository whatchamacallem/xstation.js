// The UI thread's media cache: decoded images by Key-Value-Ref within a byte
// budget, the newest kept. Nothing here touches SQLite. One of the four
// modules allowed platform callbacks: the image decode and the download are
// events it turns into reply lines. The port answers `media.fetch` with the
// bytes as blob 1 once downloaded and decoded, and `media.store` once
// decoded, and either with `error` on a failure or a timeout.

declare namespace media {
  // Decoded images by key within a byte budget, the newest always kept.
  class ImageCache {
    constructor(budget_bytes: number);
    // Keeps the image as the newest, then evicts the oldest to fit the budget.
    image_put(k: lines.KvRef, image: ImageBitmap): void;
    // The decoded image, or undefined once evicted.
    image_get(k: lines.KvRef): ImageBitmap | undefined;
    // The bytes of every image kept.
    total_bytes(): number;
    // The keys kept, the oldest first.
    keys_list(): lines.KvRef[];
  }

  // The steps from one request line to its reply lines.
  class MediaExchange {
    constructor(line: lines.Line);
    // The key the image is kept under.
    readonly key: lines.KvRef;
    // The bytes of a `media.store` line, or the url of a `media.fetch` line.
    readonly source: Uint8Array | string;
    // The reply for a kept image, with the bytes as blob 1 for a download.
    image_reply(bytes: Uint8Array): lines.Line;
    // The error reply to bytes that did not decode.
    decode_reply(cause: unknown): lines.Line;
    // The error reply to a download that failed.
    download_reply(url: string, cause: unknown): lines.Line;
    // The error reply to a download that outlived its timer.
    timeout_reply(url: string, timeout_seconds: number): lines.Line;
  }

  class MediaPort implements queue.Port {
    constructor(budget_bytes: number, timeout_seconds: number);
    line_post(line: lines.Line, transfer: ArrayBuffer[]): void;
    line_receive(fn: (line: lines.Line) => void): void;
    // The decoded image, or undefined once evicted.
    image_get(k: lines.KvRef): ImageBitmap | undefined;
  }
}
