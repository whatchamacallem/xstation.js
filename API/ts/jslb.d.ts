// JSON Lines with Blobs. The decoders of both languages are the single door
// for bad numbers: no other layer checks a number. At read, a decoder refuses
// an integer token, digits without a fraction or an exponent, beyond 2^53
// either way, with `jslb.integer_refused`, and a number token whose double
// overflows to an infinity, such as `1e400`, with `jslb.number_overflow`.
// Both raise `WireError`, so the port that fed the decoder closes. A number
// token with a fraction or an exponent within the doubles is read as the
// double it names. `json_decode` applies the same rules to a JSON text read
// from anywhere but a line. The encoders keep their own refusal of NaN and
// the infinities, `jslb.number_refused`, inside the same layer.
//
// A fault met while a fault is being handled, as a `sink_close` that throws
// while the decoder shuts a stream after a fault, is thrown with the first
// fault under its innermost `cause`, so one error holds both.

declare namespace jslb {
  type Line = lines.Line;
  type LineHeader = lines.LineHeader;
  type BlobHeader = lines.BlobHeader;

  // A framing, header or number fault. The port that fed the decoder closes.
  class WireError extends Error {}

  // Where a blob over `overflow_bytes` streams as it arrives, hashed by it.
  interface BlobSink {
    sink_open(header: BlobHeader): string;
    sink_append(handle: string, data: Uint8Array): void;
    sink_close(handle: string): lines.Sha256;
  }

  // Builds the header 0. `full` selects full names, as `names_full()` says.
  function header_make(
    type: string,
    options?: {
      version?: number;
      id?: number;
      reply?: number;
      key?: string;
      full?: boolean;
    },
  ): LineHeader;

  // Builds a blob header with `d` the bytes and `s` their length.
  function blob_make(
    data: Uint8Array,
    key?: string,
    fields?: { [field: string]: unknown },
  ): BlobHeader;

  // Builds a line from its header, blob headers and payload, setting `b`.
  function line_make(
    header: LineHeader,
    blobs: BlobHeader[],
    payload: { [key: string]: unknown },
  ): Line;

  // Resolves a short or full field name on a header and its default.
  function field_get(header: LineHeader | BlobHeader, name: string): unknown;

  // The headers of an object, 0 on, found by probing the integer keys.
  function headers_of(object: { [key: string]: unknown }): unknown[];

  // The payload: the keys that aren't integer keys.
  function payload_of(line: Line): { [key: string]: unknown };

  // The JSON bytes ending in CR, then each blob's `d` as it is.
  function line_encode(line: Line): (Uint8Array | string)[];

  // The JSON text followed by one `<blob "n"=K>` tag per blob.
  function line_render(line: Line): string;

  // Parses a JSON text by the decoder's number rules. Throws `WireError`.
  function json_decode(text: string): unknown;

  // WireError: a line over `line_max`, or blobs over `blob_max` in all.
  class LineDecoder {
    constructor(
      line_max: number,
      blob_max: number,
      overflow_bytes: number,
      sink: BlobSink,
    );
    // Returns the complete lines the bytes finish. Throws at the first fault.
    bytes_feed(data: Uint8Array): Line[];
    // Whether no line or blob is partly read.
    idle(): boolean;
  }
}
