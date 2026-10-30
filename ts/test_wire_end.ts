// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Tests of the wire port's end on an open socket, group C: `wire_end` and
// `wire_close`, and a fault in a socket message, which leaves the socket
// open. A socket double stands in the port's private socket and the
// port's private message event is called, as no realm without ttyd opens
// a socket, so this module runs only on the ttyd page. The lines the tests
// send and expect and the texts of the faults are the gold of
// test_settings.json; the bytes the server sends are a line's JSON text, its
// CR, then its blobs.

namespace test_wire_end {
  // An address, ttyd's output kind, the text of the sink double.
  const constants = Object.freeze({
    base_url: "http://127.0.0.1:7681/",
    output_kind: 0x30,
    unused_sink: "No blob of these tests streams to a sink.",
  });

  // A blob sink these tests never reach, as their blobs stay in memory.
  class UnusedSink implements jslb.BlobSink {
    // Fails, as no blob streams.
    sink_open(): string {
      throw new Error(constants.unused_sink);
    }

    // Fails, as no blob streams.
    sink_append(): void {
      throw new Error(constants.unused_sink);
    }

    // Fails, as no blob streams.
    sink_close(): lines.Sha256 {
      throw new Error(constants.unused_sink);
    }
  }

  // A socket that records what is sent and closed, open until told otherwise.
  class SocketDouble {
    readyState: number = WebSocket.OPEN;
    bufferedAmount = 0;
    readonly sent: Uint8Array[] = [];
    readonly closes: number[] = [];

    // Keeps a copy of the frame.
    send(data: ArrayBuffer): void {
      this.sent.push(new Uint8Array(data.slice(0)));
    }

    // Keeps the code, the close event being the test's to deliver.
    close(code: number): void {
      this.closes.push(code);
    }
  }

  // A copy of a value of this module's gold, which the harness keeps frozen.
  function gold_value(name: string): unknown {
    return structuredClone(
      harness.gold_get(`typescript.test_wire_end.${name}`),
    );
  }

  // A text of this module's gold, a run time `{n}` left for the test to fill.
  function gold_text(name: string): string {
    return harness.gold_get(
      `typescript.test_wire_end.texts.${name}`,
    ) as string;
  }

  // A copy of a line of this module's gold, a run time part set on the copy.
  function gold_line(name: string): lines.Line {
    return gold_value(`lines.${name}`) as lines.Line;
  }

  // A `settings_get` of the settings, with the test's own value for some ids.
  function reader_make(
    values: { [id: string]: number } = {},
  ): (id: string) => unknown {
    return (id: string) =>
      Object.hasOwn(values, id) ? values[id] : harness.setting_get(id);
  }

  // A wire port that is never opened, sized by the settings and the values.
  function port_make(values: { [id: string]: number } = {}): wire.WirePort {
    return new wire.WirePort(
      constants.base_url,
      new UnusedSink(),
      reader_make(values),
    );
  }

  // Puts a socket double where the port's opened socket would be.
  function socket_attach(port: wire.WirePort): SocketDouble {
    const socket = new SocketDouble();
    port["socket"] = socket as unknown as WebSocket;
    return socket;
  }

  // Delivers a message of ttyd's as the socket's message event does.
  function message_deliver(port: wire.WirePort, message: Uint8Array): void {
    const data = message.slice().buffer;
    port["message_event"](new MessageEvent("message", { data }));
  }

  // The parts joined into one array of bytes.
  function bytes_join(parts: Uint8Array[]): Uint8Array {
    let total = 0;
    for (const part of parts) {
      total += part.length;
    }
    const joined = new Uint8Array(total);
    let offset = 0;
    for (const part of parts) {
      joined.set(part, offset);
      offset += part.length;
    }
    return joined;
  }

  // The JSON text the encoder writes for a line, each blob's `d` left out.
  function line_text(line: lines.Line): string {
    const sent: { [key: string]: unknown } = { ...line };
    for (let number = 1; Object.hasOwn(line, String(number)); number += 1) {
      const blob = { ...(line[String(number)] as lines.BlobHeader) };
      delete blob.d;
      sent[String(number)] = blob;
    }
    return JSON.stringify(sent);
  }

  // The JSON bytes of a line, its CR included.
  function json_bytes(line: lines.Line): Uint8Array {
    return new TextEncoder().encode(line_text(line) + "\r");
  }

  // The encoded bytes of a line whose blobs are in memory.
  function line_bytes(line: lines.Line): Uint8Array {
    const parts = [json_bytes(line)];
    for (let number = 1; Object.hasOwn(line, String(number)); number += 1) {
      const data = (line[String(number)] as lines.BlobHeader).d;
      if (!(data instanceof Uint8Array)) {
        throw new Error(`The line holds the cache handle ${String(data)}.`);
      }
      parts.push(data);
    }
    return bytes_join(parts);
  }

  // A message of ttyd's: the kind byte, then the body.
  function message_make(kind: number, body: Uint8Array): Uint8Array {
    return bytes_join([Uint8Array.of(kind), body]);
  }

  // A message of ttyd's of the kind with a text body.
  function message_text(kind: number, text: string): Uint8Array {
    return message_make(kind, new TextEncoder().encode(text));
  }

  // An output message of ttyd's holding the text.
  function output_text(text: string): Uint8Array {
    return message_text(constants.output_kind, text);
  }

  // An output message of ttyd's holding the encoded lines.
  function output_lines(...list: lines.Line[]): Uint8Array {
    const body = bytes_join(list.map((line) => line_bytes(line)));
    return message_make(constants.output_kind, body);
  }

  // The bodies of the frames joined, which is what reaches the server.
  function bodies_join(list: Uint8Array[]): Uint8Array {
    return bytes_join(list.map((frame) => frame.subarray(1)));
  }

  // The message of the error the function throws, failing the test if none.
  function message_thrown(test: unittest.TestCase, fn: () => void): string {
    try {
      fn();
    } catch (error) {
      if (error instanceof Error) {
        return error.message;
      }
      throw error;
    }
    return test.fail("Nothing was thrown.");
  }

  // The end of the wire after a fault, which waits for the server's close.
  export class TestWireEnd extends unittest.TestCase {
    // The line goes, then `fn` runs once at the close, which raises nothing.
    test_end_waits(): void {
      const port = port_make();
      const socket = socket_attach(port);
      const closes: unknown[] = [];
      let ends = 0;
      port.first_receive(() => {});
      port.close_receive((code, had_error) => {
        closes.push([code, had_error]);
      });
      port.message_take(output_lines(gold_line("first")));
      const report = gold_line("report");
      port.wire_end(report, () => {
        ends += 1;
      });
      // Read before the close, which stops the wait's timer at once.
      const sent = bodies_join(socket.sent);
      const ends_before = ends;
      port.close_take(1000);
      port.close_take(1000);
      this.assertEqual(sent, line_bytes(report));
      this.assertEqual(ends_before, 0);
      this.assertEqual(ends, 1);
      this.assertEqual(closes, []);
      this.assertEqual(socket.closes, []);
    }

    // On a socket already closed `fn` runs at once and nothing is sent.
    test_end_closed(): void {
      const port = port_make();
      const socket = socket_attach(port);
      let ends = 0;
      port.first_receive(() => {});
      port.message_take(output_lines(gold_line("first")));
      socket.readyState = WebSocket.CLOSED;
      port.wire_end(gold_line("report"), () => {
        ends += 1;
      });
      this.assertEqual(ends, 1);
      this.assertEqual(socket.sent, []);
      const closed = port_make();
      const shut = socket_attach(closed);
      let closed_ends = 0;
      closed.wire_close();
      closed.wire_end(gold_line("report"), () => {
        closed_ends += 1;
      });
      this.assertEqual(closed_ends, 1);
      this.assertEqual(shut.closes, [1000]);
      this.assertEqual(shut.sent, []);
    }

    // A fault in a message leaves the socket open and takes no later one.
    test_fault_open(): void {
      const port = port_make();
      const socket = socket_attach(port);
      const received: lines.Line[] = [];
      port.first_receive(() => {});
      port.line_receive((line) => {
        received.push(line);
      });
      message_deliver(port, output_lines(gold_line("first")));
      const message = message_thrown(this, () =>
        message_deliver(port, output_text("{}\r")),
      );
      message_deliver(port, output_lines(gold_line("notice_mcp")));
      const notice = gold_line("notice_tap_line");
      port.line_post(notice, []);
      this.assertEqual(message, gold_text("jslb_no_header_zero"));
      this.assertEqual(received.length, 0);
      this.assertEqual(socket.closes, []);
      this.assertEqual(bodies_join(socket.sent), line_bytes(notice));
    }
  }
}

Object.freeze(test_wire_end);
