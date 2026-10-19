declare namespace jslb {
  type Line = lines.Line;
  type LineHeader = lines.LineHeader;
  type BlobHeader = lines.BlobHeader;

  // A framing or header fault. The port that fed the decoder closes.
  class WireError extends Error {}

  // Where a blob over `overflow_bytes` streams as it arrives: the AI
  // worker's substrate cache. The handler finds the handle in `d`.
  interface BlobSink {
    sink_open(header: BlobHeader): string;
    sink_append(handle: string, data: Uint8Array): void;
    sink_close(handle: string): lines.Sha256;
  }

  // Builds the header "0". `full` selects full names, the debug form.
  // A field at its default is left out.
  function header_make(
    type: string,
    options?: {
      version?: number;
      id?: number;
      reply?: number;
      key?: string;
      full?: boolean;
    }
  ): LineHeader;

  // Builds a blob header with `d` set and `s` measured; other fields are
  // the handler's.
  function blob_make(
    data: Uint8Array | string,
    key?: string,
    fields?: { [field: string]: unknown }
  ): BlobHeader;

  // Builds a line from its header, blob headers and payload, numbering
  // the blob headers "1" on and setting `b`.
  function line_make(
    header: LineHeader,
    blobs: BlobHeader[],
    payload: { [key: string]: unknown }
  ): Line;

  // Resolves a short or full field name on a header and its default.
  function field_get(header: LineHeader | BlobHeader, name: string): unknown;

  // The headers of an object, "0" on, found by probing the integer keys.
  function headers_of(object: { [key: string]: unknown }): unknown[];

  // The payload: the keys that aren't decimal integer strings.
  function payload_of(line: Line): { [key: string]: unknown };

  // The JSON bytes ending in CR, then each blob's `d` as it is, for the
  // port to send in order. Copies no blob bytes.
  function line_encode(line: Line): (Uint8Array | string)[];

  // The JSON text followed by one `<blob "n"=K>` tag per blob.
  function line_render(line: Line): string;

  class LineDecoder {
    constructor(
      line_max: number,
      blob_max: number,
      overflow_bytes: number,
      sink: BlobSink
    );
    // Returns the complete lines the bytes finish, zero or more. Throws
    // WireError at the first fault; the decoder is then unusable.
    bytes_feed(data: Uint8Array): Line[];
  }
}
