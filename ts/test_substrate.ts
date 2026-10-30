// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Tests of substrate.ts that need no store and no cache: refs split into
// their parts and bad refs refused, documents encoded and decoded with their
// refs in shared headers and malformed ones refused, and the module's
// surface. The texts it expects are its gold in `test_settings.json`, read
// through the harness.
namespace test_substrate {
  // The refs and texts the tests use.
  const constants = Object.freeze({
    // A ref of the hyperposition scene at its version 1.
    scene: "/metaverse/hyperposition/1",
    // Text beyond ASCII for keys and values, built from its code points.
    text_wide: String.fromCodePoint(0x4e2d, 0x6587, 0x1f600),
  });

  // A text of this module's gold, a run time `{n}` left for the test to fill.
  function gold_text(name: string): string {
    return harness.gold_get(
      `typescript.test_substrate.texts.${name}`,
    ) as string;
  }

  // A document in its normal form, with refs, shared refs and plain text.
  function fog_normal(): { [key: string]: unknown } {
    return {
      0: { t: "scene", v: 2 },
      subtitle: "Fog " + constants.text_wide,
      image: "/_files/fog.png",
      links: [
        "/metaverse/world",
        { to: "/_files/fog.png", note: "/not a ref" },
      ],
      local: "world",
      slash: "/",
      count: 3,
      ratio: 0.5,
      shown: true,
      none: null,
    };
  }

  // That document encoded, its refs moved into headers 1 and 2.
  function fog_encoded(): lines.Document {
    return {
      0: { t: "scene", v: 2 },
      1: "/_files/fog.png",
      2: "/metaverse/world",
      subtitle: "Fog " + constants.text_wide,
      image: { $ref: 1 },
      links: [{ $ref: 2 }, { to: { $ref: 1 }, note: "/not a ref" }],
      local: "world",
      slash: "/",
      count: 3,
      ratio: 0.5,
      shown: true,
      none: null,
    };
  }

  // A test case with the asserts of a refusal and its message.
  class RefusalCase extends unittest.TestCase {
    // Asserts the call throws a plain `Error` with exactly the message.
    raised_assert(message: string, fn: () => unknown, note?: string): void {
      try {
        fn();
      } catch (error) {
        if (error instanceof Error && error.constructor === Error) {
          this.assertEqual(error.message, message, note);
          return;
        }
        throw error;
      }
      const standard = "Error not raised";
      this.fail(note === undefined ? standard : `${standard} : ${note}`);
    }
  }

  // `Key-Value-Ref` and `Document-Ref` splitting, and bad refs.
  export class TestRefs extends RefusalCase {
    // Each form splits into its database, its key and its version.
    test_split_forms(): void {
      const cases: [string, substrate.RefParts][] = [
        [
          constants.scene,
          { db: "metaverse", key: "hyperposition/1", version: 1 },
        ],
        ["/metaverse/world", { db: "metaverse", key: "world" }],
        ["script/bootstrap.js", { key: "script/bootstrap.js" }],
        ["scene/arrival/12", { key: "scene/arrival/12", version: 12 }],
        ["/_files/a//b/", { db: "_files", key: "a//b/" }],
        ["maps/01", { key: "maps/01" }],
        ["7", { key: "7" }],
        [
          "/x/" + constants.text_wide + "/0",
          { db: "x", key: constants.text_wide + "/0", version: 0 },
        ],
        ["/x/line\nbreak", { db: "x", key: "line\nbreak" }],
      ];
      for (const [ref, parts] of cases) {
        this.assertEqual(substrate.ref_split(ref), parts, ref);
      }
    }

    // An empty ref, a missing key and a bad database name throw.
    test_refs_bad(): void {
      const refs: [string, string][] = [
        ["", "substrate_ref_bad_empty"],
        ["/", "substrate_ref_bad_slash"],
        ["//key", "substrate_ref_bad_db_empty"],
        ["/metaverse", "substrate_ref_bad_key_none"],
        ["/metaverse/", "substrate_ref_bad_key_empty"],
        ["/1db/key", "substrate_ref_bad_db_digit"],
        ["/d-b/key", "substrate_ref_bad_db_dash"],
        [
          "/caf" + String.fromCodePoint(0xe9) + "/key",
          "substrate_ref_bad_db_wide",
        ],
      ];
      for (const [ref, text] of refs) {
        this.raised_assert(gold_text(text), () => substrate.ref_split(ref));
      }
    }
  }

  // Documents: the round trip, reference strings, faults.
  export class TestDocuments extends RefusalCase {
    // Encoding moves refs into shared headers and decoding restores them.
    test_round_trip(): void {
      const encoded = substrate.doc_encode(fog_normal());
      this.assertEqual(encoded, fog_encoded());
      this.assertEqual(JSON.stringify(encoded), JSON.stringify(fog_encoded()));
      const decoded = substrate.doc_decode(encoded);
      this.assertEqual(decoded, fog_normal());
      this.assertEqual(JSON.stringify(decoded), JSON.stringify(fog_normal()));
    }

    // Documents that would not round trip, or are malformed, throw.
    test_documents_bad(): void {
      const normals: [{ [key: string]: unknown }, string][] = [
        [{ subtitle: "x" }, gold_text("substrate_header_missing")],
        [
          { 0: { t: "scene", v: 0 } },
          gold_text("substrate_header_bad_version"),
        ],
        [{ 0: { v: 2 } }, gold_text("substrate_header_bad_type")],
        [{ 0: { t: "scene", x: 1 } }, gold_text("substrate_header_bad_field")],
        [{ 0: "scene" }, gold_text("substrate_header_bad_text")],
        [
          { 0: { t: "scene" }, 1: "/a/b" },
          gold_text("substrate_header_normal"),
        ],
        [{ 0: { t: "scene" }, "07": "x" }, gold_text("substrate_key_digits")],
        [
          { 0: { t: "scene" }, x: { $ref: 1 } },
          gold_text("substrate_ref_shape"),
        ],
      ];
      for (const [normal, message] of normals) {
        this.raised_assert(message, () => substrate.doc_encode(normal));
      }
      const encodeds: [lines.Document, string][] = [
        [
          { 0: { t: "scene" }, 1: "/a/b", x: { $ref: 2 } },
          gold_text("substrate_ref_index_two"),
        ],
        [
          { 0: { t: "scene" }, 2: "/a/b", x: { $ref: 2 } },
          gold_text("substrate_header_gap"),
        ],
        [
          { 0: { t: "scene" }, 1: 5, x: { $ref: 1 } },
          gold_text("substrate_header_ref"),
        ],
        [
          { 0: { t: "scene" }, 1: "world", x: { $ref: 1 } },
          gold_text("substrate_header_ref"),
        ],
        [
          { 0: { t: "scene" }, 1: "/a/b", x: { $ref: true } },
          gold_text("substrate_ref_index_true"),
        ],
        [{ 0: { t: "scene" }, "07": "x" }, gold_text("substrate_key_digits")],
      ];
      for (const [encoded, message] of encodeds) {
        this.raised_assert(message, () => substrate.doc_decode(encoded));
      }
    }

    // A string whose key holds a space, as Python counts space, stays text.
    test_spaces_kept(): void {
      const lines_kept = [
        "/me/ waves and leaves",
        "/me/waves and\nleaves",
        "/me/a b",
      ];
      const python_spaces = [0x1c, 0x1f, 0x85].map(
        (point) => "/me/a" + String.fromCodePoint(point) + "b",
      );
      const marked = "/me/a" + String.fromCodePoint(0xfeff) + "b";
      const normal = {
        0: { t: "scene" },
        subtitle: "/me waves/ and leaves",
        lines: lines_kept,
        python: python_spaces,
        image: "/me/waves",
        marked,
      };
      const expected = {
        0: { t: "scene" },
        1: "/me/waves",
        2: marked,
        subtitle: "/me waves/ and leaves",
        lines: lines_kept,
        python: python_spaces,
        image: { $ref: 1 },
        marked: { $ref: 2 },
      };
      this.assertEqual(substrate.doc_encode(normal), expected);
      this.assertEqual(substrate.doc_decode(expected), normal);
      const kept = ["/me waves/ and leaves", ...lines_kept, ...python_spaces];
      for (const text of kept) {
        this.raised_assert(gold_text("substrate_header_ref"), () =>
          substrate.doc_decode({ 0: { t: "scene" }, 1: text }),
        );
      }
    }
  }

  // The shape of the module object and its classes.
  export class TestSurface extends unittest.TestCase {
    // The module is frozen and holds the names of its surface.
    test_frozen_names(): void {
      this.assertTrue(Object.isFrozen(substrate));
      this.assertEqual(Object.keys(substrate).sort(), [
        "CacheFiles",
        "Store",
        "doc_decode",
        "doc_encode",
        "ref_split",
      ]);
      this.assertEqual(
        Object.getOwnPropertyNames(substrate.Store.prototype).sort(),
        [
          "constructor",
          "db_close",
          "db_create",
          "db_drop",
          "db_list",
          "db_open",
          "db_restore",
          "db_snapshot",
          "doc_get",
          "doc_head",
          "doc_put",
          "handlers_register",
          "kv_check",
          "kv_delete",
          "kv_get",
          "kv_list",
          "kv_put",
          "sink",
          "sql_run",
          "transaction_run",
          "turn_append",
          "turn_compact",
          "turn_list",
        ],
      );
      this.assertEqual(
        Object.getOwnPropertyNames(substrate.CacheFiles.prototype).sort(),
        [
          "cache_read",
          "constructor",
          "sink_append",
          "sink_close",
          "sink_open",
          "slot_add",
          "slots_free",
        ],
      );
    }
  }
}
Object.freeze(test_substrate);
