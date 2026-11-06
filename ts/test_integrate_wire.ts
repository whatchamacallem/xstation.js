// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The line cases of the console port over the whole console connection, a
// block of group C on the headless page that the block's own ttyd serves,
// through `bootstrap.py`'s console role and dash on ttyd's pty.
//
// A heredoc of binary bytes is typed one line per `console.input` push. Its
// payload is every byte that dash and the pty's line discipline carry, each
// control byte the line discipline acts on after its literal next, 0x16, and
// UTF-8 sequences that are not valid, so a connection that is not binary
// changes the bytes and fails the case.
//
// The far end's receivers are this file's own functions, as in
// `test_integrate_http`, since a queue passes on no request that has an id,
// such as `console.open`, which only a handler's submit sends. The bytes
// between the two `printf` markers go on as one `console.output` line, so
// neither the terminal's echo of the typed lines nor what comes before the
// first prompt is compared.

namespace test_integrate_wire {
  // The gold of this block and the line types.
  const constants = Object.freeze({
    start_id: "typescript.test_integrate_wire.marker_start",
    end_id: "typescript.test_integrate_wire.marker_end",
    kind_id: "typescript.test_integrate_wire.output_kind",
    output_type: "console.output",
    close_type: "console.close",
    exit_type: "console.exit",
  });

  // The bytes of the two arrays, one after the other.
  function bytes_join(first: Uint8Array, second: Uint8Array): Uint8Array {
    const joined = new Uint8Array(first.length + second.length);
    joined.set(first);
    joined.set(second, first.length);
    return joined;
  }

  // The offset of `needle` in `bytes` from `from` on, or `-1` when absent.
  function bytes_find(
    bytes: Uint8Array,
    needle: Uint8Array,
    from: number,
  ): number {
    const last = bytes.length - needle.length;
    for (let at = from; at <= last; at += 1) {
      let index = 0;
      while (index < needle.length && bytes[at + index] === needle[index]) {
        index += 1;
      }
      if (index === needle.length) {
        return at;
      }
    }
    return -1;
  }

  // A line of the type, its blobs and payload, in the settings' form.
  function line_typed(
    type: string,
    blobs: lines.BlobHeader[],
    payload: { [key: string]: unknown },
  ): lines.Line {
    const header = jslb.header_make(type, { full: settings.names_full() });
    return jslb.line_make(header, blobs, payload);
  }

  // The output of tty 0 joined, and the bytes between the markers passed on.
  class OutputJoin {
    readonly #start: Uint8Array;
    readonly #end: Uint8Array;
    readonly #pass: (line: lines.Line) => void;
    // The kind of ttyd's output messages, the gold's.
    readonly #kind = harness.gold_get(constants.kind_id) as string;
    // The output since the last end marker, or since the start.
    #joined = new Uint8Array(0);

    // Takes the two markers and what the bytes between them are passed to.
    constructor(start: string, end: string, pass: (line: lines.Line) => void) {
      this.#start = utility.utf8_encode(start);
      this.#end = utility.utf8_encode(end);
      this.#pass = pass;
    }

    // Joins the body of an output message, then passes on a whole run.
    output_take(line: lines.Line): void {
      const message = jslb.field_get(line[1] as lines.BlobHeader, "data");
      if (!(message instanceof Uint8Array)) {
        throw new Error("internal error");
      }
      if (String.fromCharCode(message[0]) !== this.#kind) {
        return;
      }
      this.#joined = bytes_join(this.#joined, message.subarray(1));
      const begin = bytes_find(this.#joined, this.#start, 0);
      if (begin < 0) {
        return;
      }
      const from = begin + this.#start.length;
      const end = bytes_find(this.#joined, this.#end, from);
      if (end < 0) {
        return;
      }
      const between = this.#joined.slice(from, end);
      this.#joined = this.#joined.slice(end + this.#end.length);
      this.#pass(
        line_typed(constants.output_type, [jslb.blob_make(between)], {}),
      );
    }
  }

  // The console port behind a real port pair, and the test's end of the pair.
  export function topology_build(): queue.ThreadPort {
    const port = new wire.ConsolePort(location.href);
    const channel = new MessageChannel();
    const far = new queue.ThreadPort(channel.port2);
    const join = new OutputJoin(
      harness.gold_get(constants.start_id) as string,
      harness.gold_get(constants.end_id) as string,
      (line) => far.line_post(line, []),
    );
    far.line_receive((line) => {
      if (jslb.field_get(line[0], "type") === constants.close_type) {
        port.console_close();
      } else {
        port.line_post(line, []);
      }
    });
    port.line_receive((line) => {
      if (jslb.field_get(line[0], "type") === constants.output_type) {
        join.output_take(line);
      } else {
        far.line_post(line, []);
      }
    });
    port.close_receive((code) => {
      far.line_post(line_typed(constants.exit_type, [], { code }), []);
    });
    return new queue.ThreadPort(channel.port1);
  }
}

Object.freeze(test_integrate_wire);
