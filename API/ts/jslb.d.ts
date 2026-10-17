declare namespace jslb {
  type Line = lines.Line;
  type LineHeader = lines.LineHeader;
  type BlobHeader = lines.BlobHeader;

  // A framing or header fault. The port that fed the decoder closes.
  class WireError extends Error {}

  // Where a blob over `overflow_bytes` streams as it arrives. The AI
  // worker's sink posts `cache.*` tasks to the WASM worker; the handler
  // closes the handle it finds in `d`.
  interface BlobSink {
    sink_open(header: BlobHeader): string;
    sink_append(handle: string, data: Uint8Array): void;
  }

  interface HeaderFields {
    version?: number;
    id?: number;
    reply?: number;
    key?: string;
    full?: boolean;
  }

  // Builds the line header "0". `full` selects the debug form. A field
  // at its default is left out.
  function header_make(type: string, fields?: HeaderFields): LineHeader;

  // Builds a blob header with `d` set and `s` measured.
  function blob_make(
    data: Uint8Array,
    key?: string,
    fields?: { [field: string]: unknown }
  ): BlobHeader;

  // Builds a line, numbering the blob headers "1" on and setting `b`.
  function line_make(
    header: LineHeader,
    blobs: BlobHeader[],
    payload: { [key: string]: unknown }
  ): Line;

  // Resolves a short or full field name on a header and its default.
  function field_get(header: LineHeader | BlobHeader, name: string): unknown;

  function blobs_of(line: Line): BlobHeader[];

  function payload_of(line: Line): { [key: string]: unknown };

  // The JSON bytes ending in CR, then each blob's `d` as it is. Copies
  // no blob bytes; the chunks are what the writer sends in order.
  function line_encode(line: Line): Uint8Array[];

  class LineDecoder {
    constructor(
      line_max: number,
      blob_max: number,
      overflow_bytes: number,
      sink: BlobSink
    );
    // The complete lines the bytes finish. Throws WireError at the first
    // fault; the decoder is then unusable.
    feed(data: Uint8Array): Line[];
  }
}
