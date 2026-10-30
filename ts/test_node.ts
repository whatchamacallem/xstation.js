// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The Node realm of one block of group A, the last file of the Node bundle,
// which starts it when the bundle loads:
//
//     node node.js BLOCK [--failfast]
//
// It speaks JSLB with the driver on the lane `realm`, its stdin and stdout.
// The first line must be `tap.start` with `i` 101, carrying the settings
// and the test settings, decoded by `jslb.LineDecoder` over an empty
// `substrate.CacheFiles`, as the bring up of the page decodes its first
// line. It sets this realm's settings and the harness's values, answers
// with an Empty reply, and runs the block named BLOCK of the table below as
// the one block of a TAP stream, each line sent as a `tap.line` push the
// moment it is made. A block is a unittest module, run through
// `TAPTestRunner.module_run`, a block of line cases, whose suite's topology
// `line_case.block_run` runs on the gold `typescript.BLOCK`, or a block that
// writes its own points as they arrive, as `test_line_case` does, and may
// send lines of its own to the driver, as `test_tap_pair` sends `tap.pair`.
// With `--failfast` the first failure ends the stream with a bail out. The
// realm exits 0 after `run_end`. Any other first line, a second line, or
// any throw exits 1 with the cascade on stderr, which is Node's own report
// of a throw no handler caught. Node writes to a pipe synchronously on
// Linux, so a hard exit loses no line. The queues' MessageChannels keep
// Node's loop alive, so the realm ends by exiting. `process` is declared
// here with the members this file uses, as no package declares it.

namespace test_node {
  // The members of Node's `process` that this file uses.
  declare const process: {
    readonly argv: readonly string[];
    readonly stdin: {
      on(event: "data", fn: (data: Uint8Array) => void): void;
      on(event: "end", fn: () => void): void;
    };
    readonly stdout: { write(data: Uint8Array): boolean };
    exit(code: number): never;
  };

  // The lane's line types and numbers, the arguments and the first decoder.
  const constants = Object.freeze({
    first_type: "tap.start",
    first_id: 101,
    line_type: "tap.line",
    language: "typescript" as const,
    gold_prefix: "typescript.",
    // The arguments after `node` and the bundle's path.
    argument_index: 2,
    failfast_flag: "--failfast",
    exit_ended: 0,
    // The longest first line: 10 MiB, as the wire reads the page's first.
    first_line_max: 10485760,
    // The blob bytes of the first line: none, as it has none.
    first_blob_max: 0,
    first_overflow_bytes: 0,
  });

  // What a block's run calls once its stream is written: its verdict.
  type BlockDone = (passed: boolean) => void;

  // What a block's run calls to send a line of its own to the driver.
  type LineSend = (line: lines.Line) => void;

  // A block: a unittest module, a block of line cases, or its own writer.
  type Block =
    | { readonly module: () => { [name: string]: unknown } }
    | { readonly topology: line_case.TopologyBuild }
    | {
        readonly run: (
          runner: tap_producer.TAPTestRunner,
          name: string,
          done: BlockDone,
          send: LineSend,
        ) => void;
      };

  // The blocks of group A by name.
  const blocks: { readonly [name: string]: Block } = Object.freeze({
    test_tap_producer: { module: () => test_tap_producer },
    test_unittest: { module: () => test_unittest },
    test_harness: { module: () => test_harness },
    test_ui_strings: { module: () => test_ui_strings },
    test_i18n: { module: () => test_i18n },
    test_utility: { module: () => test_utility },
    test_jslb: { module: () => test_jslb },
    test_settings: { module: () => test_settings },
    test_dispatch: { module: () => test_dispatch },
    test_http: { module: () => test_http },
    test_media: { module: () => test_media },
    test_provider: { module: () => test_provider },
    test_provider_key: { module: () => test_provider_key },
    test_provider_key_unset: { module: () => test_provider_key_unset },
    test_provider_script: { module: () => test_provider_script },
    test_verbose: { module: () => test_verbose },
    test_wire: { module: () => test_wire },
    test_queue: { module: () => test_queue },
    test_substrate: { module: () => test_substrate },
    test_mcp: { module: () => test_mcp },
    test_line_case: { run: test_line_case.block_run },
    test_wire_port: { module: () => test_wire_port },
    test_tap_pair: { run: test_tap_pair.block_run },
    test_integrate_http: { topology: test_integrate_http.topology_build },
    test_integrate_provider_script: {
      topology: test_integrate_provider_script.topology_build,
    },
    test_integrate_queue: { topology: test_integrate_queue.topology_build },
    test_integrate_mcp: { topology: test_integrate_mcp.topology_build },
    failing_block: { module: () => failing_block },
  });

  // The block's name and whether failfast is set, from the command line.
  interface RealmArguments {
    name: string;
    failfast: boolean;
  }

  // Reads the command line: a block of the table, then `--failfast` or not.
  function arguments_read(): RealmArguments {
    const given = process.argv.slice(constants.argument_index);
    const [name, ...rest] = given;
    const flagged = rest.length === 1 && rest[0] === constants.failfast_flag;
    if (name === undefined || (rest.length > 0 && !flagged)) {
      throw new Error(
        `test_node takes BLOCK [--failfast], not ${JSON.stringify(given)}`,
      );
    }
    if (!Object.hasOwn(blocks, name)) {
      throw new Error(`test_node has no block ${JSON.stringify(name)}`);
    }
    return { name, failfast: flagged };
  }

  // Writes a line to the driver, its JSON bytes the only piece it has.
  function line_write(line: lines.Line): void {
    for (const piece of jslb.line_encode(line)) {
      if (typeof piece === "string") {
        throw new Error("internal error");
      }
      process.stdout.write(piece);
    }
  }

  // Sends one line of the stream at once, as a `tap.line` push.
  function text_send(text: string): void {
    const header = jslb.header_make(constants.line_type, {
      full: settings.names_full(),
    });
    const payload = { language: constants.language, text };
    line_write(jslb.line_make(header, [], payload));
  }

  // Runs the block as the one block of the stream, then `done`.
  function block_launch(
    runner: tap_producer.TAPTestRunner,
    name: string,
    done: BlockDone,
  ): void {
    const block = blocks[name];
    if ("module" in block) {
      const loader = new unittest.TestLoader();
      done(
        runner.module_run(name, () =>
          loader.loadTestsFromModule(block.module()),
        ),
      );
    } else if ("topology" in block) {
      const id = `${constants.gold_prefix}${name}`;
      line_case.block_run(runner, name, id, block.topology, done);
    } else {
      block.run(runner, name, done, line_write);
    }
  }

  // Takes `tap.start`, sets the values, answers it, and runs the block.
  function first_take(first: lines.Line, start: RealmArguments): void {
    const header = first[0];
    if (
      jslb.field_get(header, "type") !== constants.first_type ||
      jslb.field_get(header, "id") !== constants.first_id
    ) {
      throw new Error(
        "the first line is not tap.start with i 101: " +
          jslb.line_render(first),
      );
    }
    const payload = jslb.payload_of(first) as unknown as lines.TapStart;
    const gold = payload.test_settings;
    if (gold === undefined) {
      throw new Error("tap.start carries no test_settings: not debug mode");
    }
    settings.settings_set(payload.settings);
    harness.values_set(payload.settings, gold);
    line_write(dispatch.reply_make(first, {}));
    const runner = new tap_producer.TAPTestRunner(start.failfast);
    runner.set_stream(text_send);
    block_launch(runner, start.name, () => {
      runner.run_end();
      process.exit(constants.exit_ended);
    });
  }

  // Reads the first line from stdin, and refuses any byte after it.
  function realm_start(): void {
    const start = arguments_read();
    const decoder = new jslb.LineDecoder(
      constants.first_line_max,
      constants.first_blob_max,
      constants.first_overflow_bytes,
      new substrate.CacheFiles([]),
    );
    let taken = false;
    process.stdin.on("data", (data) => {
      if (taken) {
        throw new Error("the driver sent bytes after tap.start");
      }
      const found = decoder.bytes_feed(data);
      if (found.length === 0) {
        return;
      }
      if (found.length > 1 || !decoder.idle()) {
        throw new Error("the driver sent bytes after tap.start");
      }
      taken = true;
      first_take(found[0], start);
    });
    process.stdin.on("end", () => {
      if (!taken) {
        throw new Error("stdin ended before tap.start");
      }
    });
  }

  realm_start();
}
Object.freeze(test_node);
