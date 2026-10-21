// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Tests of the verbose module.

namespace test_verbose {
  // A ring that reads the given value as the ring size setting.
  function ring_make(size: unknown): verbose.LineRing {
    return new verbose.LineRing(() => size);
  }

  // Logs each text, one after another.
  function texts_log(ring: verbose.LineRing, ...texts: string[]): void {
    for (const text of texts) {
      ring.log(text);
    }
  }

  // The texts of the lines as one string separated by commas.
  function texts_join(list: lines.VerboseLine[]): string {
    return list.map((line) => line.text).join(",");
  }

  // The size of the ring and the setting it comes from.
  export class TestRingSize extends unittest.TestCase {
    // Lines come back oldest first.
    test_order_oldest(): void {
      const ring = ring_make(10);
      texts_log(ring, "a", "b", "c");
      this.assertEqual(texts_join(ring.history_get(3)), "a,b,c");
    }

    // The ring holds the newest lines up to its size and no more.
    test_size_limit(): void {
      const ring = ring_make(3);
      texts_log(ring, "a", "b", "c", "d", "e");
      const list = ring.history_get(10);
      this.assertEqual(list.length, 3);
      this.assertEqual(texts_join(list), "c,d,e");
    }

    // A ring of size 0 keeps nothing but the sink still gets the lines.
    test_size_zero(): void {
      const ring = ring_make(0);
      const seen: lines.VerboseLine[] = [];
      ring.sink_set((line) => {
        seen.push(line);
      });
      texts_log(ring, "a", "b");
      this.assertEqual(ring.history_get(10).length, 0);
      this.assertEqual(texts_join(seen), "a,b");
    }

    // The size is read at the first line, so one before the settings throws.
    test_size_first(): void {
      let reads = 0;
      const ring = new verbose.LineRing(() => {
        reads += 1;
        throw new Error("The settings are not set.");
      });
      const seen: lines.VerboseLine[] = [];
      ring.sink_set((line) => {
        seen.push(line);
      });
      this.assertRaises(Error, () => ring.log("a"));
      this.assertEqual(reads, 1);
      this.assertEqual(ring.history_get(10).length, 0);
      this.assertEqual(seen.length, 0);
    }

    // A size that is not a whole number from 0 up throws and writes nothing.
    test_size_invalid(): void {
      const bad = [-1, 1.5, NaN, Infinity, "3", null, undefined];
      for (const value of bad) {
        const ring = ring_make(value);
        this.assertRaises(Error, () => ring.log("x"));
        this.assertEqual(ring.history_get(10).length, 0);
      }
      let size: unknown = 2;
      const seen: lines.VerboseLine[] = [];
      const ring = new verbose.LineRing(() => size);
      ring.sink_set((line) => {
        seen.push(line);
      });
      ring.log("a");
      size = -1;
      this.assertRaises(Error, () => ring.log("b"));
      this.assertEqual(texts_join(ring.history_get(10)), "a");
      this.assertEqual(texts_join(seen), "a");
    }

    // The size is read again for each line, so a change shows at once.
    test_size_live(): void {
      let size = 3;
      const ring = new verbose.LineRing(() => size);
      texts_log(ring, "a", "b", "c", "d");
      this.assertEqual(texts_join(ring.history_get(10)), "b,c,d");
      size = 1;
      ring.log("e");
      this.assertEqual(texts_join(ring.history_get(10)), "e");
      size = 2;
      ring.log("f");
      this.assertEqual(texts_join(ring.history_get(10)), "e,f");
    }

    // A line has the fields at and text only and cannot be changed.
    test_line_fields(): void {
      const ring = ring_make(10);
      const before = utility.time_now();
      ring.log("progress");
      const after = utility.time_now();
      const line = ring.history_get(1)[0];
      this.assertEqual(Object.keys(line).join(","), "at,text");
      this.assertEqual(line.text, "progress");
      this.assertTrue(before <= line.at && line.at <= after);
      this.assertTrue(Object.isFrozen(line));
      this.assertRaises(TypeError, () => {
        line.text = "changed";
      });
      this.assertEqual(ring.history_get(1)[0].text, "progress");
    }
  }

  // The last lines of the ring.
  export class TestHistoryGet extends unittest.TestCase {
    // A count gives that many of the newest lines, or all there are.
    test_count_values(): void {
      const ring = ring_make(10);
      texts_log(ring, "a", "b", "c", "d");
      this.assertEqual(ring.history_get(0).length, 0);
      this.assertEqual(texts_join(ring.history_get(1)), "d");
      this.assertEqual(texts_join(ring.history_get(2)), "c,d");
      this.assertEqual(texts_join(ring.history_get(4)), "a,b,c,d");
      this.assertEqual(texts_join(ring.history_get(5)), "a,b,c,d");
    }

    // A ring with no line gives no line.
    test_ring_empty(): void {
      const ring = ring_make(10);
      this.assertEqual(ring.history_get(0).length, 0);
      this.assertEqual(ring.history_get(3).length, 0);
    }

    // A count that is not a whole number from 0 up throws.
    test_count_invalid(): void {
      const ring = ring_make(10);
      texts_log(ring, "a", "b");
      for (const count of [-1, 1.5, NaN, Infinity]) {
        this.assertRaises(Error, () => ring.history_get(count));
      }
      this.assertEqual(texts_join(ring.history_get(2)), "a,b");
    }

    // Changing the returned list leaves the ring as it was.
    test_list_copy(): void {
      const ring = ring_make(10);
      texts_log(ring, "a", "b", "c");
      const list = ring.history_get(3);
      list.pop();
      list.reverse();
      this.assertEqual(texts_join(ring.history_get(3)), "a,b,c");
    }
  }

  // The one sink of a ring.
  export class TestSinkRules extends unittest.TestCase {
    // The sink gets every line once, in order, the same line the ring keeps.
    test_each_once(): void {
      const ring = ring_make(10);
      const seen: lines.VerboseLine[] = [];
      ring.sink_set((line) => {
        seen.push(line);
      });
      texts_log(ring, "a", "b", "c");
      this.assertEqual(texts_join(seen), "a,b,c");
      const kept = ring.history_get(10);
      this.assertEqual(texts_join(kept), "a,b,c");
      for (let index = 0; index < seen.length; index += 1) {
        this.assertTrue(seen[index] === kept[index]);
      }
    }

    // A sink gets the lines written after it is set and none before.
    test_sink_late(): void {
      const ring = ring_make(10);
      const seen: lines.VerboseLine[] = [];
      ring.log("a");
      ring.sink_set((line) => {
        seen.push(line);
      });
      ring.log("b");
      this.assertEqual(texts_join(seen), "b");
      this.assertEqual(texts_join(ring.history_get(10)), "a,b");
    }

    // A second sink throws and the first one stays.
    test_sink_twice(): void {
      const ring = ring_make(10);
      const seen: lines.VerboseLine[] = [];
      ring.sink_set((line) => {
        seen.push(line);
      });
      this.assertRaises(Error, () => ring.sink_set(() => {}));
      ring.log("a");
      this.assertEqual(texts_join(seen), "a");
    }

    // A sink that throws fails the call, after the ring took the line.
    test_sink_throws(): void {
      const ring = ring_make(10);
      let calls = 0;
      ring.sink_set(() => {
        calls += 1;
        throw new Error("The sink failed.");
      });
      this.assertRaises(Error, () => ring.log("a"));
      this.assertRaises(Error, () => ring.log("b"));
      this.assertEqual(calls, 2);
      this.assertEqual(texts_join(ring.history_get(10)), "a,b");
    }
  }

  // The module functions, on whatever state the thread has.
  export class TestLiveVerbose extends unittest.TestCase {
    // A count that is not a whole number from 0 up throws whatever the state.
    test_count_invalid(): void {
      this.assertRaises(Error, () => verbose.history_get(-1));
    }
  }
}

Object.freeze(test_verbose);
