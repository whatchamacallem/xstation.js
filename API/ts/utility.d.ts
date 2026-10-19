declare namespace utility {
  // Non essential error handling: an Error with `cause` set, and a throw
  // as an expression.
  function error_wrap(message: string, cause: unknown): Error;
  function fail_now(message: string): never;

  // The single door routines the modules below share. Every one is
  // synchronous: sha256 is implemented here, not by crypto.subtle.
  function sha256_hex(data: Uint8Array): lines.Sha256;
  function utf8_encode(text: string): Uint8Array;
  // Strict: throws on an invalid sequence.
  function utf8_decode(data: Uint8Array): string;
  function base64_decode(text: string): Uint8Array;
  // No whitespace outside strings; throws on NaN, infinities and ints
  // beyond 2^53.
  function json_text(value: unknown): string;
  // Milliseconds since the epoch.
  function time_now(): number;
}
