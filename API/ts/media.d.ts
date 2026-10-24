// The UI thread's media cache: decoded images by Key-Value-Ref within a byte
// budget, the newest kept. Nothing here touches SQLite. One of the four
// modules allowed platform callbacks: the image decode and the download are
// events it turns into reply lines. The port answers `media.fetch` with the
// bytes as blob 1 once downloaded and decoded, and `media.store` once
// decoded, and either with `error` on a failure or a timeout.

declare namespace media {
  class MediaPort implements queue.Port {
    constructor(budget_bytes: number, timeout_seconds: number);
    line_post(line: lines.Line, transfer: ArrayBuffer[]): void;
    line_receive(fn: (line: lines.Line) => void): void;
    // The decoded image, or undefined once evicted.
    image_get(k: lines.KvRef): ImageBitmap | undefined;
  }
}
