// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Tests of the wire port with no socket, on a real cache with no file:
// what it does with ttyd's messages before and after the first line, the
// first line's sizes and the settings that size the port after it, and the
// close of the wire and the fault it is without an error line. The lines
// the tests send and expect and the texts of the faults are the gold of
// test_settings.json; the bytes the server sends are a line's JSON text, its
// CR, then its blobs. The port reads the settings through the harness, a
// few replaced by the test's own values, or a reader that answers none.

namespace test_wire_port {
  // An address, ttyd's message kinds, the text of a reader that answers none.
  const constants = Object.freeze({
    base_url: "http://127.0.0.1:7681/",
    output_kind: 0x30,
    title_kind: 0x31,
    preferences_kind: 0x32,
    setting_unanswered: "No setting is answered before the settings exist.",
  });

  // A `settings_get` that answers no id, keeping each id it was asked.
  class SettingsUnset {
    readonly asked: string[] = [];

    // Keeps the id and throws, as no setting is answered.
    setting_get(id: string): unknown {
      this.asked.push(id);
      throw new Error(constants.setting_unanswered);
    }
  }

  // A copy of a value of this module's gold, which the harness keeps frozen.
  function gold_value(name: string): unknown {
    return structuredClone(
      harness.gold_get(`typescript.test_wire_port.${name}`),
    );
  }

  // A text of this module's gold, a run time `{n}` left for the test to fill.
  function gold_text(name: string): string {
    return harness.gold_get(
      `typescript.test_wire_port.texts.${name}`,
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
      new substrate.CacheFiles([]),
      reader_make(values),
    );
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

  // Bytes that count up from 0, wrapping at 251.
  function bytes_count(length: number): Uint8Array {
    const data = new Uint8Array(length);
    for (let index = 0; index < length; index += 1) {
      data[index] = index % 251;
    }
    return data;
  }

  // A blob header of a short named line, its size and its bytes.
  function blob_of(data: Uint8Array): lines.BlobHeader {
    return { s: data.length, d: data };
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

  // A `kv.put` request whose one blob is the header given.
  function put_make(blob: lines.BlobHeader): lines.Line {
    const line = gold_line("put");
    line[1] = blob;
    return line;
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

  // What the wire port does with ttyd's messages before and after the first.
  export class TestWireMessages extends unittest.TestCase {
    // Title and preferences are kept and never decoded, then the first line.
    test_first_line(): void {
      const port = port_make();
      const firsts: lines.Line[] = [];
      const received: lines.Line[] = [];
      port.first_receive((line) => {
        firsts.push(line);
      });
      port.line_receive((line) => {
        received.push(line);
      });
      // The carriage return would end a line the decoder refuses.
      port.message_take(message_text(constants.title_kind, "dash (xt)\r"));
      port.message_take(message_text(constants.preferences_kind, "{}"));
      this.assertEqual(port.title, "dash (xt)\r");
      this.assertEqual(port.preferences, {});
      port.message_take(output_lines(gold_line("first")));
      this.assertEqual(firsts, [gold_line("first")]);
      this.assertEqual(received.length, 0);
      port.message_take(output_lines(gold_line("notice_mcp")));
      this.assertEqual(firsts.length, 1);
      this.assertEqual(received, [gold_line("notice_mcp")]);
    }

    // Preferences are read by the decoders' rules for bad numbers.
    test_preferences_overflow(): void {
      const port = port_make();
      const text = '{"fontSize":1e400}';
      const message = message_thrown(this, () =>
        port.message_take(message_text(constants.preferences_kind, text)),
      );
      this.assertEqual(message, gold_text("jslb_number_overflow"));
    }

    // Nothing may follow the first line before its reply, whole or in part.
    test_first_trailing(): void {
      const port = port_make();
      const firsts: lines.Line[] = [];
      port.first_receive((line) => {
        firsts.push(line);
      });
      port.line_receive(() => {});
      const whole = output_lines(gold_line("first"), gold_line("notice_a"));
      this.assertEqual(
        message_thrown(this, () => port.message_take(whole)),
        gold_text("wire_start_trailing"),
      );
      this.assertEqual(firsts.length, 1);
      const other = port_make();
      other.first_receive(() => {});
      const bytes = bytes_join([
        line_bytes(gold_line("first")),
        line_bytes(gold_line("notice_a")).subarray(0, 4),
      ]);
      const part = message_make(constants.output_kind, bytes);
      this.assertEqual(
        message_thrown(this, () => other.message_take(part)),
        gold_text("wire_start_trailing"),
      );
    }

    // A first line split over two output messages arrives once it is whole.
    test_first_split(): void {
      const port = port_make();
      const firsts: lines.Line[] = [];
      port.first_receive((line) => {
        firsts.push(line);
      });
      const bytes = line_bytes(gold_line("first"));
      const half = Math.floor(bytes.length / 2);
      const kind = constants.output_kind;
      port.message_take(message_make(kind, bytes.subarray(0, half)));
      this.assertEqual(firsts.length, 0);
      port.message_take(message_make(kind, bytes.subarray(half)));
      this.assertEqual(firsts.length, 1);
    }

    // A line other than `tap.start` or error before `tap.start` is a fault.
    test_start_missing(): void {
      const port = port_make();
      port.first_receive(() => {});
      port.line_receive(() => {});
      const message = message_thrown(this, () =>
        port.message_take(output_lines(gold_line("notice_mcp"))),
      );
      this.assertEqual(message, gold_text("wire_start_missing"));
    }

    // A second `tap.start`, which a restart of the server sends, is a fault.
    test_start_twice(): void {
      const port = port_make();
      port.first_receive(() => {});
      port.line_receive(() => {});
      port.message_take(output_lines(gold_line("first")));
      const message = message_thrown(this, () =>
        port.message_take(output_lines(gold_line("first"))),
      );
      this.assertEqual(message, gold_text("wire_start_twice"));
    }

    // Nothing is posted before `tap.start`.
    test_post_early(): void {
      const port = port_make();
      const message = message_thrown(this, () =>
        port.line_post(gold_line("notice_verbose_put"), []),
      );
      this.assertEqual(message, gold_text("wire_post_early"));
    }

    // A port opens once: its first line receiver, which an open sets, is set.
    test_open_twice(): void {
      const port = port_make();
      port.first_receive(() => {});
      this.assertEqual(
        message_thrown(this, () => port.wire_open(() => {})),
        gold_text("wire_open_twice"),
      );
    }

    // An empty message, or one of a kind ttyd never sends, is a fault.
    test_kind_unknown(): void {
      const port = port_make();
      this.assertEqual(
        message_thrown(this, () => port.message_take(new Uint8Array(0))),
        gold_text("wire_message_empty"),
      );
      this.assertEqual(
        message_thrown(this, () => port.message_take(message_text(0x33, ""))),
        gold_text("wire_kind_unknown_digit"),
      );
      this.assertEqual(
        message_thrown(this, () => port.message_take(message_text(0x7b, "}"))),
        gold_text("wire_kind_unknown_brace"),
      );
    }

    // Output bytes the decoder refuses throw its fault.
    test_decoder_fault(): void {
      const port = port_make();
      port.first_receive(() => {});
      const message = message_thrown(this, () =>
        port.message_take(output_text("{}\r")),
      );
      this.assertEqual(message, gold_text("jslb_no_header_zero"));
    }

    // The lines before a fault reach their receiver, then the fault throws.
    test_fault_held(): void {
      const port = port_make();
      const received: lines.Line[] = [];
      port.first_receive(() => {});
      port.line_receive((line) => {
        received.push(line);
      });
      port.message_take(output_lines(gold_line("first")));
      const bytes = bytes_join([
        line_bytes(gold_line("notice_mcp")),
        new TextEncoder().encode("{}\r"),
      ]);
      const output = message_make(constants.output_kind, bytes);
      const message = message_thrown(this, () => port.message_take(output));
      this.assertEqual(received, [gold_line("notice_mcp")]);
      this.assertEqual(message, gold_text("jslb_no_header_zero"));
    }

    // A line with no receiver set is a fault.
    test_receiver_missing(): void {
      const port = port_make();
      const message = message_thrown(this, () =>
        port.message_take(output_lines(gold_line("first"))),
      );
      this.assertEqual(message, gold_text("wire_receiver_missing_start"));
    }

    // Each receiver is set once.
    test_receiver_twice(): void {
      const port = port_make();
      port.first_receive(() => {});
      port.line_receive(() => {});
      port.close_receive(() => {});
      this.assertEqual(
        message_thrown(this, () => port.first_receive(() => {})),
        gold_text("wire_receiver_twice_first"),
      );
      this.assertEqual(
        message_thrown(this, () => port.line_receive(() => {})),
        gold_text("wire_receiver_twice_line"),
      );
      this.assertEqual(
        message_thrown(this, () => port.close_receive(() => {})),
        gold_text("wire_receiver_twice_close"),
      );
    }

    // Only a page served over http or https has ttyd's sockets.
    test_scheme_unknown(): void {
      const cases: [string, string][] = [
        ["ftp://127.0.0.1/", "ftp"],
        ["file:///tmp/", "file"],
      ];
      for (const [base_url, name] of cases) {
        const read = reader_make();
        const sink = new substrate.CacheFiles([]);
        const expected = gold_text(`wire_scheme_unknown_${name}`);
        this.assertEqual(
          message_thrown(this, () => new wire.WirePort(base_url, sink, read)),
          expected,
        );
        this.assertEqual(
          message_thrown(this, () => new wire.ConsolePort(base_url)),
          expected,
        );
      }
    }
  }

  // The first line's sizes, then the settings that size the port after it.
  export class TestSettingsPhase extends unittest.TestCase {
    // The first line is read with the first phase sizes, which allow no blob.
    test_first_blob(): void {
      const port = port_make();
      port.first_receive(() => {});
      const first = gold_line("first_blob");
      first[1] = blob_of(Uint8Array.of(7));
      const message = message_thrown(this, () =>
        port.message_take(output_lines(first)),
      );
      this.assertEqual(message, gold_text("jslb_blobs_over"));
    }

    // The settings size the decoder only once the first line has come.
    test_settings_sized(): void {
      const port = port_make({ line_max: 64 });
      const firsts: lines.Line[] = [];
      port.first_receive((line) => {
        firsts.push(line);
      });
      port.line_receive(() => {});
      const text = "x".repeat(100);
      const first = gold_line("first");
      first.settings = { root: text };
      port.message_take(output_lines(first));
      this.assertEqual(firsts.length, 1);
      const long = gold_line("notice_mcp");
      long.text = text;
      const message = message_thrown(this, () =>
        port.message_take(output_lines(long)),
      );
      this.assertEqual(message, gold_text("jslb_line_over_max"));
    }

    // The first line asks for no setting, and the first post after it does.
    test_settings_unset(): void {
      const unset = new SettingsUnset();
      const port = new wire.WirePort(
        constants.base_url,
        new substrate.CacheFiles([]),
        (id) => unset.setting_get(id),
      );
      const firsts: lines.Line[] = [];
      port.first_receive((line) => {
        firsts.push(line);
      });
      port.message_take(output_lines(gold_line("first")));
      this.assertEqual(firsts.length, 1);
      this.assertEqual(unset.asked, []);
      const message = message_thrown(this, () =>
        port.line_post(gold_line("first_reply"), []),
      );
      this.assertEqual(message, constants.setting_unanswered);
      this.assertEqual(unset.asked.length, 1);
    }

    // Blobs over `blob_max` are refused before they are queued.
    test_blobs_over(): void {
      const port = port_make({ blob_max: 64 });
      port.first_receive(() => {});
      port.message_take(output_lines(gold_line("first")));
      const line = put_make(blob_of(bytes_count(100)));
      const message = message_thrown(this, () => port.line_post(line, []));
      this.assertEqual(message, gold_text("wire_blobs_over_posted"));
    }

    // A line over `line_max` is refused before it is queued.
    test_line_over(): void {
      const port = port_make({ line_max: 64 });
      port.first_receive(() => {});
      port.message_take(output_lines(gold_line("first")));
      const line = gold_line("notice_mcp");
      line.text = "x".repeat(100);
      const size = line_bytes(line).length;
      const message = message_thrown(this, () => port.line_post(line, []));
      this.assertEqual(
        message,
        gold_text("wire_line_over_posted").replaceAll("{1}", String(size)),
      );
    }

    // A line within the limits is queued, and sending it needs the socket.
    test_socket_missing(): void {
      const port = port_make();
      port.first_receive(() => {});
      port.message_take(output_lines(gold_line("first")));
      const message = message_thrown(this, () =>
        port.line_post(gold_line("first_reply"), []),
      );
      this.assertEqual(message, gold_text("wire_socket_missing_wire"));
    }
  }

  // The close of the wire and the fault it is without an error line.
  export class TestCloseFault extends unittest.TestCase {
    // A close with no error line is the fault, after its receiver hears it.
    test_close_silent(): void {
      const port = port_make();
      const closes: unknown[] = [];
      port.first_receive(() => {});
      port.close_receive((code, had_error) => {
        closes.push([code, had_error]);
      });
      port.message_take(output_lines(gold_line("first")));
      const message = message_thrown(this, () => port.close_take(1006));
      this.assertEqual(message, gold_text("wire_close_silent_abnormal"));
      this.assertEqual(closes, [[1006, false]]);
    }

    // An error line before the close leaves the fault to that line.
    test_close_error(): void {
      const port = port_make();
      const closes: unknown[] = [];
      const received: lines.Line[] = [];
      port.first_receive(() => {});
      port.line_receive((line) => {
        received.push(line);
      });
      port.close_receive((code, had_error) => {
        closes.push([code, had_error]);
      });
      port.message_take(output_lines(gold_line("first")));
      port.message_take(output_lines(gold_line("error_reply")));
      port.close_take(1006);
      this.assertEqual(closes, [[1006, true]]);
      this.assertEqual(received, [gold_line("error_reply")]);
    }

    // An error line in place of the first, a refused lock, throws its message.
    test_error_first(): void {
      const port = port_make();
      const closes: unknown[] = [];
      const firsts: lines.Line[] = [];
      port.first_receive((line) => {
        firsts.push(line);
      });
      port.close_receive((code, had_error) => {
        closes.push([code, had_error]);
      });
      const message = message_thrown(this, () =>
        port.message_take(output_lines(gold_line("refusal"))),
      );
      this.assertEqual(message, gold_text("wire_error_first"));
      port.close_take(1006);
      this.assertEqual(firsts.length, 0);
      this.assertEqual(closes, [[1006, true]]);
    }

    // An error line before the first is not passed on, though one is awaited.
    test_error_unpassed(): void {
      const port = port_make();
      const received: lines.Line[] = [];
      port.first_receive(() => {});
      port.line_receive((line) => {
        received.push(line);
      });
      const message = message_thrown(this, () =>
        port.message_take(output_lines(gold_line("refusal"))),
      );
      this.assertEqual(message, gold_text("wire_error_first"));
      this.assertEqual(received.length, 0);
    }

    // A close with no receiver set is still the fault, naming its code.
    test_close_unheard(): void {
      const port = port_make();
      const message = message_thrown(this, () => port.close_take(1000));
      this.assertEqual(message, gold_text("wire_close_silent_normal"));
    }

    // A close in the middle of a message is a fault of its own.
    test_close_partial(): void {
      const port = port_make();
      const closes: unknown[] = [];
      port.first_receive(() => {});
      port.close_receive((code, had_error) => {
        closes.push([code, had_error]);
      });
      const bytes = line_bytes(gold_line("first")).subarray(0, 8);
      port.message_take(message_make(constants.output_kind, bytes));
      const message = message_thrown(this, () => port.close_take(1006));
      this.assertEqual(message, gold_text("wire_close_partial"));
      this.assertEqual(closes, [[1006, false]]);
    }
  }
}

Object.freeze(test_wire_port);
