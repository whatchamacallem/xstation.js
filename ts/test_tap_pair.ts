// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The TypeScript half of the pair test of the TAP producer of TypeScript and
// the TAP consumer of Python: this block writes the streams, and the Python
// suite that starts its realm checks them. Each kind of outcome unittest has
// here, of a test, of its setUp and tearDown and of a module's load, runs
// with failfast and without, alone and as a block between passing blocks,
// which run until one fails, as the driver runs them, through
// `TAPTestRunner` into a list of lines. Each run goes to the driver as one
// `tap.pair` push: its name, its failfast, its lines, and for each block
// that ran the verdict of `module_run`, its `countTestCases` and the counts
// of a `unittest.TestResult` that ran the same tests anew, the oracle.
// Python's subtests and its class and module fixtures have no form here, and
// no fixture has two outcomes in one test, since the counts are per block. A
// load that fails is a module whose one member throws when the loader reads
// it, and its oracle is one test that runs that load, as Python's loader
// makes one failing test of a module that fails to import. The block writes
// one point per run once the run's push is sent, through `block_start` and
// `block_end` of the runner it is handed; the checks are the Python suite's.
// The fixtures are not exported, so that no loader collects them.

namespace test_tap_pair {
  // The texts of the fixtures, and the type of the line of each run.
  const constants = Object.freeze({
    error_text: "fixture error",
    reason_absent: "",
    reason_given: "fixture skip",
    pair_type: "tap.pair",
  });

  // A block of a run: its name, the load the runner takes, the oracle's load.
  interface FixtureBlock {
    readonly name: string;
    readonly load: () => unittest.TestSuite;
    readonly oracle: () => unittest.TestSuite;
  }

  // One run: the blocks of its stream, and whether failfast is set.
  interface FixtureRun {
    readonly blocks: readonly FixtureBlock[];
    readonly failfast: boolean;
  }

  // Passes.
  class PassFixture extends unittest.TestCase {
    // Passes an assertion.
    test_values_equal(): void {
      this.assertEqual(1, 1);
    }
  }

  // Skips one test without a reason and one with a reason.
  class SkipFixture extends unittest.TestCase {
    // Skips itself, giving no reason.
    test_reason_absent(): void {
      this.skipTest(constants.reason_absent);
    }

    // Skips itself with a reason.
    test_reason_given(): void {
      this.skipTest(constants.reason_given);
    }
  }

  // Fails an assertion.
  class AssertionFixture extends unittest.TestCase {
    // Fails `1 != 2`.
    test_values_differ(): void {
      this.assertEqual(1, 2);
    }
  }

  // Throws an error in its test.
  class ErrorFixture extends unittest.TestCase {
    // Throws an error that is not an assertion's.
    test_error_thrown(): void {
      throw new Error(constants.error_text);
    }
  }

  // Expects its assertion to fail, and it does.
  class ExpectedFixture extends unittest.TestCase {
    // Fails `1 != 2` as expected.
    test_values_differ(): void {
      this.assertEqual(1, 2);
    }

    // Marks the test as expected to fail.
    static {
      unittest.expectedFailure(this.prototype.test_values_differ);
    }
  }

  // Expects its assertion to fail, and it passes.
  class SurpriseFixture extends unittest.TestCase {
    // Passes though it is expected to fail.
    test_values_equal(): void {
      this.assertEqual(1, 1);
    }

    // Marks the test as expected to fail.
    static {
      unittest.expectedFailure(this.prototype.test_values_equal);
    }
  }

  // Throws in `setUp`.
  class SetupFixture extends unittest.TestCase {
    // Throws before the test.
    override setUp(): void {
      throw new Error(constants.error_text);
    }

    // Never runs.
    test_values_equal(): void {
      this.assertEqual(1, 1);
    }
  }

  // Throws in `tearDown` after a test that passed.
  class TeardownFixture extends unittest.TestCase {
    // Throws after the test.
    override tearDown(): void {
      throw new Error(constants.error_text);
    }

    // Passes an assertion.
    test_values_equal(): void {
      this.assertEqual(1, 1);
    }
  }

  // A module whose one member throws when the loader reads it.
  const module_broken = {
    // Throws, so that the module fails to load.
    get member(): never {
      throw new Error(constants.error_text);
    },
  };

  // Loads the module whose member throws, which throws.
  function module_load(): unittest.TestSuite {
    return new unittest.TestLoader().loadTestsFromModule(module_broken);
  }

  // Runs that load as its one test, as Python's loader runs a failed import.
  class LoadFixture extends unittest.TestCase {
    // Throws what the load throws.
    test_module_load(): void {
      module_load();
    }
  }

  // Holds no test, as a module with no tests does.
  class EmptyFixture extends unittest.TestCase {}

  // The block of a fixture class, whose tests both loads take in order.
  function class_block(fixture: typeof unittest.TestCase): FixtureBlock {
    const load = () =>
      new unittest.TestLoader().loadTestsFromModule({
        [fixture.name]: fixture,
      });
    return { name: fixture.name, load, oracle: load };
  }

  // The fixture blocks, in the order of the outcomes they hold.
  const fixtures: readonly FixtureBlock[] = [
    class_block(PassFixture),
    class_block(SkipFixture),
    class_block(AssertionFixture),
    class_block(ErrorFixture),
    class_block(ExpectedFixture),
    class_block(SurpriseFixture),
    class_block(SetupFixture),
    class_block(TeardownFixture),
    {
      name: LoadFixture.name,
      load: module_load,
      oracle: () =>
        new unittest.TestLoader().loadTestsFromModule({ LoadFixture }),
    },
    class_block(EmptyFixture),
  ];

  // Each fixture without failfast and with it, alone and between passes.
  function runs_list(): FixtureRun[] {
    const passing = class_block(PassFixture);
    const runs: FixtureRun[] = [];
    for (const fixture of fixtures) {
      for (const failfast of [false, true]) {
        runs.push({ blocks: [fixture], failfast });
        runs.push({ blocks: [passing, fixture, passing], failfast });
      }
    }
    return runs;
  }

  // The oracle of a block that ran: its tests run anew in unittest's result.
  function oracle_count(
    block: FixtureBlock,
    passed: boolean,
    failfast: boolean,
  ): lines.TapPairBlock {
    const suite = block.oracle();
    const result = new unittest.TestResult(failfast);
    suite.run(result);
    return {
      module: block.name,
      passed,
      cases: suite.countTestCases(),
      tests_run: result.testsRun,
      failures: result.failures.length,
      errors: result.errors.length,
      skipped: result.skipped.length,
      expected_failures: result.expectedFailures.length,
      unexpected_successes: result.unexpectedSuccesses.length,
    };
  }

  // Runs the blocks into a list until one fails, then the oracle of each.
  function pair_make(run: FixtureRun): lines.TapPair {
    const names = run.blocks.map((block) => block.name);
    const written: string[] = [];
    const runner = new tap_producer.TAPTestRunner(run.failfast);
    runner.set_stream((text) => written.push(text));
    const verdicts: boolean[] = [];
    for (const block of run.blocks) {
      verdicts.push(runner.module_run(block.name, block.load));
      if (!verdicts[verdicts.length - 1]) {
        break;
      }
    }
    runner.run_end();
    return {
      run: `blocks ${JSON.stringify(names)}, failfast ${run.failfast}`,
      failfast: run.failfast,
      lines: written,
      blocks: verdicts.map((passed, index) =>
        oracle_count(run.blocks[index], passed, run.failfast),
      ),
    };
  }

  // The `tap.pair` push that carries the run.
  function pair_line(pair: lines.TapPair): lines.Line {
    const header = jslb.header_make(constants.pair_type, {
      full: settings.names_full(),
    });
    return jslb.line_make(header, [], { ...pair });
  }

  // Runs this block as `name`: a push and a point per run, then `done`.
  export function block_run(
    runner: tap_producer.TAPTestRunner,
    name: string,
    done: (passed: boolean) => void,
    send: (line: lines.Line) => void,
  ): void {
    const runs = runs_list();
    const tracker = runner.block_start(name, runs.length);
    for (const run of runs) {
      const pair = pair_make(run);
      send(pair_line(pair));
      tracker.add_ok(name, pair.run);
    }
    done(runner.block_end(name));
  }
}
Object.freeze(test_tap_pair);
