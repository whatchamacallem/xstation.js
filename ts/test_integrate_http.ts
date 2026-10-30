// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The line cases of the HTTP port: `http.request` lines through a real
// `http.HttpPort` to the driver's HTTP server on 127.0.0.1, which answers each
// path with the status, headers, body and delay of this block's gold under
// `server`, and the reply or `error` line the port sends back for each. The
// failures are real: a status outside 200 to 299, a JSON body that does not
// decode, a fetch to a port nothing listens on, and a request that outlives
// the port's timer of `timeout_seconds`. The test's end is a real
// `queue.ThreadPort` over a MessageChannel, and the port at the other end
// hands each line to the HTTP port and each of its answers back, by two
// receivers that are this file's own functions. No `queue.TaskQueue` stands
// between them: a queue passes on no request that has an id, which only a
// handler's submit sends, and an `error` line that reaches a queue stops it,
// so no failure would come back as a line.

namespace test_integrate_http {
  // The gold of this block.
  const constants = Object.freeze({
    timeout_id: "typescript.test_integrate_http.timeout_seconds",
  });

  // The HTTP port behind a real port pair, and the test's end of the pair.
  export function topology_build(): queue.ThreadPort {
    const seconds = harness.gold_get(constants.timeout_id) as number;
    const port = new http.HttpPort(seconds);
    const channel = new MessageChannel();
    const far = new queue.ThreadPort(channel.port2);
    far.line_receive((line) => port.line_post(line, []));
    port.line_receive((line) => far.line_post(line, []));
    return new queue.ThreadPort(channel.port1);
  }
}

Object.freeze(test_integrate_http);
