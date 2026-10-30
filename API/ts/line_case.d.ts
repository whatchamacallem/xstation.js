// The line cases of a block, the infrastructure for testing a module that
// serves JSLB lines through a port. The block's suite exports one function
// that builds the module's real topology in the realm: a real
// `queue.TaskQueue` with the module's handlers registered through the
// module's own register function, and the module's ports. It returns the
// test's end of the lane the cases speak, a real `queue.ThreadPort` over a
// MessageChannel whose other end the queue owns.
//
// The gold of a block's id lists its cases in order under `cases`, each
// naming lines of the gold under `lines`. A block's id is
// `typescript.<block>`. A blob header of a gold line holds its bytes in `d`
// as base64. `block_run` opens the block with
// `tap_producer.TAPTestRunner.block_start`, then for each case sends its
// lines through the test's end, collects every line that comes back, and
// adds one point when as many lines came as the case expects, or when its
// seconds are up. A case that expects none waits its seconds. The point is
// `ok` when the lines that came equal the expected lines in order: the header
// and the payload by value, each blob header but `d` by value, and each
// blob's bytes by their size and `utility.sha256_hex`. Otherwise it is `not
// ok` with one diagnostic line naming the first difference, a line still
// missing or a line not expected. With the runner's failfast the first
// failed point ends the cases. Then `block_end` closes the block. A line that
// comes once the last point is in throws. A case never answers a request the
// module makes.

declare namespace line_case {
  // One case of the gold: the names of the lines sent and expected, a wait.
  interface Case {
    name: string;
    send: string[];
    expect: string[];
    seconds: number;
  }

  // What a block of line cases exports: builds the topology, the test's end.
  type TopologyBuild = () => queue.ThreadPort;

  // Runs the cases of gold `id` as block `name`, then `done` with the verdict.
  function block_run(
    runner: tap_producer.TAPTestRunner,
    name: string,
    id: string,
    build: TopologyBuild,
    done: (passed: boolean) => void,
  ): void;
}
