// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Tests of a scene with an image, in a fresh worker of its own, since a realm
// takes one registration of the chain, on the bench of test_engine.ts. The
// scene names the seed's value over `overflow_bytes`, so that the image is a
// cache file of the browser's store. The far end of `ui` answers `render`
// alone, so that a `media.store` waits for this file's answer as it waits for
// a real decode, and a test sees that no render comes before that answer. The
// first render goes that way, and so does the `render` tool in the block's one
// turn.

namespace test_engine_image {
  // The gold of this block.
  const constants = Object.freeze({
    gold_id: "typescript.test_engine_image",
  });

  // What the UI lane got at each step of the block's one run.
  interface ImageRun {
    // The lines of the chain, up to the wait on the first `media.store`.
    first_held: lines.Line[];
    // The lines the answer to that `media.store` brought.
    first_shown: lines.Line[];
    // The lines of the player's turn, up to the wait on the tool's.
    turn_held: lines.Line[];
    // The lines the answer to the tool's `media.store` brought.
    turn_shown: lines.Line[];
  }

  // The run of the block, made at the first test that needs it.
  let run_kept: ImageRun | undefined = undefined;

  // A copy of a value of this module's gold, which the harness keeps frozen.
  function gold_value(name: string): unknown {
    return structuredClone(harness.gold_get(`${constants.gold_id}.${name}`));
  }

  // A copy of a line of this module's gold.
  function gold_line(name: string): lines.Line {
    return gold_value(`lines.${name}`) as lines.Line;
  }

  // A `media.store` line of the gold, holding the image's bytes in memory.
  function store_line(name: string): lines.Line {
    const line = gold_line(name);
    const data = test_engine.large_bytes();
    line[1] = { size: data.length, d: data };
    return line;
  }

  // Answers a `media.store` as the UI thread does once it has decoded.
  function store_answer(ui: test_engine.LaneEnd, line: lines.Line): void {
    const data = test_engine.large_bytes();
    const { k } = jslb.payload_of(line);
    const sha256 = utility.sha256_hex(data);
    const size = data.length;
    ui.port.line_post(dispatch.reply_make(line, { k, size, sha256 }), []);
  }

  // Runs the first render, then the player's turn, each answered in its turn.
  function run_make(): ImageRun {
    const { ui, chain_ui } = test_engine.bench_build(
      gold_value("scene") as lines.Document,
      gold_value("script"),
    );
    store_answer(ui, chain_ui[0]);
    const first_shown = ui.came.slice(chain_ui.length);
    const before = ui.came.length;
    ui.port.line_post(gold_line("say_one"), []);
    const turn_held = ui.came.slice(before);
    store_answer(ui, turn_held[0]);
    const turn_shown = ui.came.slice(before + turn_held.length);
    return { first_held: chain_ui, first_shown, turn_held, turn_shown };
  }

  // The run of the block, made at its first use.
  function run_get(): ImageRun {
    if (run_kept === undefined) {
      run_kept = run_make();
    }
    return run_kept;
  }

  // The image reaches the UI before each render that names it.
  export class TestImageRender extends unittest.TestCase {
    // The chain sends the bytes of the cache file, and no render follows yet.
    test_first_held(): void {
      this.assertEqual(run_get().first_held, [store_line("first_store")]);
    }

    // The answer to `media.store` brings the first render, naming the image.
    test_first_shown(): void {
      this.assertEqual(run_get().first_shown, [gold_line("first_render")]);
    }

    // The tool sends the bytes of the cache file, and no render follows yet.
    test_tool_held(): void {
      this.assertEqual(run_get().turn_held, [store_line("tool_store")]);
    }

    // The answer to `media.store` brings the tool's render, then the turn ends.
    test_tool_shown(): void {
      this.assertEqual(run_get().turn_shown, [
        gold_line("tool_render"),
        gold_line("turn_answer"),
      ]);
    }
  }
}

Object.freeze(test_engine_image);
