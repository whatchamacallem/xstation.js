// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The line cases of the engine's worker, group C, on the headless page of the
// block's own ttyd: `engine.worker_run` in a worker brought up by
// `boot.engine_worker`, on the real wire to the stock server and real tty 0 to
// dash, the scripted AI walking the seed's table. The main thread plays the UI
// thread: each line of the UI lane goes to the test's end, and a request also
// to a real queue in synchronous mode. Its `render` and `media.store` run the
// real page handlers and media port on real elements, so the seed's image goes
// from the server's database to the canvas. A permit takes the gold's choice
// of its number, and `console.show` opens tty 0 as the shown view does.
//
// The wire is read on the UI lane, each `overlay.line` one line of tty 1 as
// the `WireTap` rendered it. A rendering that holds every part of a mark of
// the gold's `wire` sends the test's end the mark's line, so a case pins the
// order of the wire's lines among the UI's. The `mcp` lines of the wire are
// the server client's handshake, as the seed's table calls browser tools only.

namespace test_integrate_engine {
  // The gold, the threads, the settings, the line types and handlers' version.
  const constants = Object.freeze({
    gold_id: "typescript.test_integrate_engine",
    thread: "ui" as const,
    worker_thread: "ai" as const,
    media_owner: "media" as const,
    media_setting: "media_db_bytes",
    timeout_setting: "provider.timeout_seconds",
    ring_setting: "verbose_ring",
    render_type: "render",
    store_type: "media.store",
    media_wake: "ui.media_reply",
    permit_type: "permit.ask",
    show_type: "console.show",
    shown_type: "ui.console_shown",
    open_type: "console.open",
    input_type: "console.input",
    output_type: "console.output",
    overlay_type: "overlay.line",
    notice_type: "settings.set",
    painted_type: "test_integrate_engine.first_painted",
    handler_version: 0,
    // The bytes of a pixel `getImageData` gives: red, green, blue and alpha.
    pixel_bytes: 4,
  });

  // A mark of the gold: the line it sends, the parts a rendering must hold.
  interface WireMark {
    line: string;
    parts: string[];
  }

  // The scripted UI's near port and the canvas its real handlers paint.
  interface ScriptedUi {
    near: queue.LocalPort;
    canvas: HTMLCanvasElement;
  }

  // A copy of a value of this block's gold, which the harness keeps frozen.
  function gold_value(name: string): unknown {
    return structuredClone(harness.gold_get(`${constants.gold_id}.${name}`));
  }

  // The type of a line.
  function type_of(line: lines.Line): unknown {
    return jslb.field_get(line[0], "type");
  }

  // A line of the type with its blobs and payload, in the form settings pick.
  function line_typed(
    type: string,
    blobs: lines.BlobHeader[],
    payload: { [key: string]: unknown } = {},
  ): lines.Line {
    const header = jslb.header_make(type, { full: settings.names_full() });
    return jslb.line_make(header, blobs, payload);
  }

  // Tty 0's first message, the token of its open and the gold's size.
  function first_message(reply: lines.Line): lines.Line {
    const text = utility.json_text({
      AuthToken: jslb.payload_of(reply).token,
      columns: gold_value("columns"),
      rows: gold_value("rows"),
    });
    const blob = jslb.blob_make(utility.utf8_encode(text));
    return line_typed(constants.input_type, [blob]);
  }

  // The line of what the canvas shows: its size and its pixels' colours.
  function painted_line(canvas: HTMLCanvasElement): lines.Line {
    const { hidden, width, height } = canvas;
    const context = canvas.getContext("2d") as CanvasRenderingContext2D;
    const { data } = context.getImageData(0, 0, width, height);
    const colours = new Set<string>();
    for (let at = 0; at < data.length; at += constants.pixel_bytes) {
      colours.add(data.subarray(at, at + constants.pixel_bytes).join(" "));
    }
    const painted = { hidden, width, height, colours: [...colours] };
    return line_typed(constants.painted_type, [], painted);
  }

  // The page's parts on real elements, the canvas hidden until a render.
  function parts_make(tasks: queue.TaskQueue): page.PageParts {
    const canvas = document.createElement("canvas");
    canvas.hidden = true;
    const debug = document.createElement("div");
    const overlays = document.createElement("div");
    const subtitle = document.createElement("p");
    const input = document.createElement("input");
    input.disabled = true;
    const permit = document.createElement("div");
    document.body.append(canvas, debug, overlays, subtitle, input, permit);
    const images = new media.MediaPort(
      harness.setting_get(constants.media_setting) as number,
      harness.setting_get(constants.timeout_setting) as number,
    );
    tasks.port_add(constants.media_owner, images);
    return {
      tasks,
      canvas,
      subtitle,
      input,
      permit,
      images,
      view: new console_view.ConsoleView(debug, tasks),
      overlays: new overlay.Overlay(
        overlays,
        harness.setting_get(constants.ring_setting) as number,
      ),
      debug: switches.debug_on(),
    };
  }

  // Registers the page's handlers of `render` and `media.store`, no others.
  function image_register(parts: page.PageParts): void {
    const real: string[] = [
      constants.render_type,
      constants.store_type,
      constants.media_wake,
    ];
    page.handlers_register(parts, (type, version, fn) => {
      if (real.includes(type)) {
        dispatch.handler_register(type, version, fn);
      }
    });
  }

  // The scripted UI, a real queue in synchronous mode, and its near port.
  function far_make(): ScriptedUi {
    const owners: queue.OwnerTable = {
      [constants.render_type]: constants.thread,
      [constants.store_type]: constants.thread,
      [constants.permit_type]: constants.thread,
      [constants.show_type]: constants.thread,
    };
    const far = new queue.TaskQueue(constants.thread, owners, true);
    const version = constants.handler_version;
    const parts = parts_make(far);
    image_register(parts);
    // Answers an ask with the gold's choice of its number, which it keeps.
    dispatch.handler_register(constants.permit_type, version, (line) => {
      const permit = jslb.payload_of(line).permit as number;
      const choices = gold_value("permit_choices") as string[];
      const choice = choices[permit - 1];
      return dispatch.reply_make(line, { permit, choice });
    });
    // Opens tty 0 as the shown view does, and sleeps until it is open.
    dispatch.handler_register(constants.show_type, version, (line) => {
      const open = line_typed(constants.open_type, []);
      const id = far.task_submit(open, constants.worker_thread);
      return dispatch.task_sleep(line, [id], constants.shown_type);
    });
    // Sends tty 0 its first message, then answers the show.
    dispatch.handler_register(constants.shown_type, version, (line) => {
      const [reply] = line.replies as lines.Line[];
      far.line_notify(first_message(reply), constants.worker_thread);
      return dispatch.reply_make(line.state as lines.Line, {});
    });
    const near = new queue.LocalPort();
    far.port_add(constants.worker_thread, new queue.LocalPort(near));
    return { near, canvas: parts.canvas };
  }

  // Joins the test's end and the scripted UI to the worker's UI lane.
  function lanes_join(
    end: queue.ThreadPort,
    ui: queue.ThreadPort,
    far: ScriptedUi,
  ): void {
    const { near, canvas } = far;
    const marks = gold_value("wire") as WireMark[];
    const kind = gold_value("output_kind") as string;
    const reached = gold_value("reached") as string;
    // Tty 0's output until the command's own shows in it, then nothing.
    let output: string | undefined = "";
    // Whether the test's end has been told what the first render painted.
    let painted = false;
    // Sends the test's end the line of the mark a line of the wire fits.
    const wire_take = (line: lines.Line): void => {
      const text = jslb.payload_of(line).text as string;
      const mark = marks.find(({ parts }) =>
        parts.every((part) => text.includes(part)),
      );
      if (mark !== undefined) {
        end.line_post(gold_value(`lines.${mark.line}`) as lines.Line, []);
      }
    };
    // Tells the test's end once the command's output has come from dash.
    const output_take = (line: lines.Line): void => {
      const blob = line[1] as lines.BlobHeader;
      const data = jslb.field_get(blob, "data") as Uint8Array;
      if (output === undefined || String.fromCharCode(data[0]) !== kind) {
        return;
      }
      for (const byte of data.subarray(1)) {
        output += String.fromCharCode(byte);
      }
      if (output.includes(reached)) {
        output = undefined;
        end.line_post(gold_value("lines.dash_reached") as lines.Line, []);
      }
    };
    // A line of the case goes to the worker as the UI thread's.
    end.line_receive((line) => {
      ui.line_post(line, []);
    });
    // Once the first render's reply has gone, the canvas is read back.
    near.line_receive((line) => {
      ui.line_post(line, []);
      if (!painted && type_of(line) === constants.render_type) {
        painted = true;
        end.line_post(painted_line(canvas), []);
      }
    });
    // `settings.set`, `console.output` and an open's reply are not compared.
    ui.line_receive((line) => {
      const type = type_of(line);
      if (type === constants.overlay_type) {
        wire_take(line);
      } else if (type === constants.output_type) {
        output_take(line);
      } else if (type === constants.open_type) {
        near.line_post(line, []);
      } else if (type !== constants.notice_type) {
        end.line_post(line, []);
        if (jslb.field_get(line[0], "id") !== undefined) {
          near.line_post(line, []);
        }
      }
    });
  }

  // The scripted UI on an engine worker's UI lane, and the test's end.
  export function engine_build(ui: MessagePort): queue.ThreadPort {
    const lane = new MessageChannel();
    lanes_join(
      new queue.ThreadPort(lane.port2),
      new queue.ThreadPort(ui),
      far_make(),
    );
    return new queue.ThreadPort(lane.port1);
  }
}

Object.freeze(test_integrate_engine);
