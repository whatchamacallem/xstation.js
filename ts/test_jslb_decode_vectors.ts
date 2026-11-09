// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The vectors of build/vectors, which the test page carries as test_vectors,
// each read with the limits its sidecar names, whole, by single bytes and split
// at every offset, a streamed blob's digest the one its sidecar holds, on the
// helpers of test_jslb_decode. A block of its own, disabled for its 7.1 s.

namespace test_jslb_decode_vectors {
  // The end of the name of a vector's file.
  const constants = Object.freeze({
    vector_suffix: ".jslb",
  });

  // Reads each vector of `test_vectors`, whole, by bytes and split.
  export class TestVectors extends test_jslb_decode.RefusalCase {
    // Each success vector, and the bytes it encodes to, decode to its sidecar.
    test_vectors_success(): void {
      const names = test_jslb_decode.vector_names(false);
      this.assertTrue(names.length > 0, "no success vectors in test_vectors");
      for (const name of names) {
        const data = test_jslb_decode.file_bytes(
          name + constants.vector_suffix,
        );
        const sidecar = test_jslb_decode.sidecar_read(name);
        const messages = JSON.stringify(sidecar.messages);
        const cache = test_jslb_decode.cache_make();
        const decoded = test_jslb_decode.pieces_decode(
          test_jslb_decode.sidecar_decoder(sidecar, cache),
          [data],
        );
        const encoded = test_jslb_decode.bytes_join(
          decoded.map((line) => test_jslb_decode.line_bytes(line, cache)),
        );
        const same = test_jslb_decode.bytes_equal(encoded, data);
        this.assertEqual(same, sidecar.canonical, name);
        for (const source of same ? [data] : [data, encoded]) {
          for (const pieces of test_jslb_decode.feeds_make(source)) {
            const feed_cache = test_jslb_decode.cache_make();
            const decoder = test_jslb_decode.sidecar_decoder(
              sidecar,
              feed_cache,
            );
            const found = test_jslb_decode.pieces_decode(decoder, pieces);
            const plain = found.map((line) =>
              test_jslb_decode.line_plain(line, feed_cache),
            );
            this.assertEqual(JSON.stringify(plain), messages, name);
            const renders = found.map((line) => jslb.line_render(line));
            this.assertEqual(renders, sidecar.render, name);
            const forms = found.map((line) => jslb.line_json(line));
            this.assertEqual(forms, sidecar.json, name);
          }
        }
      }
    }

    // Each error vector gives its lines, then its fault, however it is fed.
    test_vectors_error(): void {
      const names = test_jslb_decode.vector_names(true);
      this.assertTrue(names.length > 0, "no error vectors in test_vectors");
      for (const name of names) {
        const data = test_jslb_decode.file_bytes(
          name + constants.vector_suffix,
        );
        const sidecar = test_jslb_decode.sidecar_read(name);
        const expected = test_jslb_decode.errors_expected(sidecar.limits);
        this.assertEqual(Object.keys(expected).sort(), names);
        const [slug, message] = expected[name];
        this.assertEqual(sidecar.error, slug, name);
        const messages = JSON.stringify(sidecar.messages);
        for (const pieces of test_jslb_decode.feeds_make(data)) {
          const cache = test_jslb_decode.cache_make();
          const decoder = test_jslb_decode.sidecar_decoder(sidecar, cache);
          const found: jslb.Line[] = [];
          this.raised_assert(
            jslb.WireError,
            message,
            () => {
              for (const piece of pieces) {
                found.push(...decoder.bytes_feed(piece));
              }
              decoder.bytes_feed(new Uint8Array(0));
            },
            name,
          );
          const plain = found.map((line) =>
            test_jslb_decode.line_plain(line, cache),
          );
          this.assertEqual(JSON.stringify(plain), messages, name);
          const renders = found.map((line) => jslb.line_render(line));
          this.assertEqual(renders, sidecar.render, name);
          const forms = found.map((line) => jslb.line_json(line));
          this.assertEqual(forms, sidecar.json, name);
        }
      }
    }
  }
}
Object.freeze(test_jslb_decode_vectors);
