// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The line cases of the media port on the page: `media.store` lines whose
// bytes a real `media.MediaPort` decodes, and `media.fetch` lines it downloads
// from the driver's HTTP server on 127.0.0.1, which answers each path with
// the status, headers, body and delay of this block's gold under `server`
// and serves this page too, so every fetch is of its own origin. Each case
// expects the reply or `error` line the port sends back. The failures are
// real: bytes that do not decode as an image, a status outside 200 to 299, a
// fetch to a port nothing listens on, and a download that outlives the
// port's timer of `timeout_seconds`. The test's end is a real
// `queue.ThreadPort` over a MessageChannel, and the port at the other end
// hands each line to the media port and each of its answers back, by two
// receivers that are this file's own functions. No `queue.TaskQueue` stands
// between them, as in `test_integrate_http`: an `error` line that reaches a
// queue stops it, so no failure would come back as a line.

namespace test_integrate_media {
  // The gold of this block.
  const constants = Object.freeze({
    budget_id: "typescript.test_integrate_media.budget_bytes",
    timeout_id: "typescript.test_integrate_media.timeout_seconds",
  });

  // The media port behind a real port pair, and the test's end of the pair.
  export function topology_build(): queue.ThreadPort {
    const budget = harness.gold_get(constants.budget_id) as number;
    const seconds = harness.gold_get(constants.timeout_id) as number;
    const port = new media.MediaPort(budget, seconds);
    const channel = new MessageChannel();
    const far = new queue.ThreadPort(channel.port2);
    far.line_receive((line) => port.line_post(line, []));
    port.line_receive((line) => far.line_post(line, []));
    return new queue.ThreadPort(channel.port1);
  }
}

Object.freeze(test_integrate_media);
