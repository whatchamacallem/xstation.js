declare namespace media {
  // The UI thread's media cache: decoded images by key within a byte
  // budget, the newest kept. Nothing here touches SQLite.
  class MediaDb {
    constructor(budget_bytes: number);
    // Downloads the URL, decodes it, keeps it under `key`.
    media_fetch(url: string, key: string): Promise<lines.MediaReply>;
    // Keeps bytes the AI worker sent.
    media_store(key: string, data: Uint8Array): Promise<lines.MediaReply>;
    // The decoded image, or undefined once evicted.
    media_get(key: string): ImageBitmap | undefined;
    // The encoded bytes, for backup; throws when evicted.
    media_bytes(key: string): Uint8Array;
    // Evicts oldest first until under budget; returns the keys evicted.
    media_evict(): string[];
    bytes_held(): number;
  }
}
