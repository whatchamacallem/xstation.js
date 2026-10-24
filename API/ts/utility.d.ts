// The single door routines the modules above share, every one synchronous.
// `SHA-256` is implemented here once, as `HashStream`, which `sha256_hex` and
// the store's cache use, not by crypto.subtle. `json_text` checks no number:
// the JSLB decoders are the one door for bad numbers, so NaN and the
// infinities reach it only from the program's own arithmetic, and the JSLB
// encoder refuses them before any line carries them.
//
// `cause_append` keeps both faults when a fault is met while one is handled:
// the first goes under the innermost `cause` of the second. A thrown value
// that is not an Error, at either place, becomes an Error whose message is
// its text, so nothing of either fault is lost.

declare namespace utility {
  // An Error with `cause` set.
  function error_wrap(message: string, cause: unknown): Error;

  // A throw as an expression.
  function fail_now(message: string): never;

  // Puts `first` under the innermost `cause` of `error` and returns it.
  function cause_append(error: unknown, first: unknown): Error;

  // A `SHA-256` fed in pieces of any size, as a streamed blob arrives.
  class HashStream {
    // Feeds bytes, keeping none of the caller's view after the call.
    bytes_add(data: Uint8Array): void;
    // The digest of the bytes fed so far.
    digest_hex(): lines.Sha256;
  }

  // The digest of the bytes, by `HashStream`.
  function sha256_hex(data: Uint8Array): lines.Sha256;

  // Strict: throws on a lone surrogate.
  function utf8_encode(text: string): Uint8Array;

  // Strict: throws on an invalid sequence.
  function utf8_decode(data: Uint8Array): string;

  // Strict base64: throws on any other text.
  function base64_decode(text: string): Uint8Array;

  // JSON text with no whitespace outside strings. Throws on no text.
  function json_text(value: unknown): string;

  // Milliseconds since the epoch.
  function time_now(): number;
}
