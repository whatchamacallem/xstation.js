// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The line cases of the console view on the page, every part real, on a queue
// of the UI thread whose lane to the AI worker is the test's end. The frame is
// sized from the cells of a terminal the topology measures first, so that the
// rows a show fits are the gold's `rows` whatever the font. Lines of types of
// the topology's own read the DOM back and act as the player does. Output
// reaches the rows after the call that feeds it, so a case that feeds output
// waits its seconds for the terminal to draw. The last cases check the echo of
// a typed line: around `console.busy`, on the bottom row, between a program's
// saved cursor, ESC 7, and its restore, ESC 8, and at a program's pending
// wrap, whose erase leaves the wrap pending. A probe reads a row's runs of
// text with their colour classes, the runs of one colour joined.
namespace test_integrate_console_view {
  // The threads, the types of the topology's own and the page's elements.
  const constants = Object.freeze({
    thread: "ui" as const,
    owner: "ai" as const,
    probe_prefix: "console_probe.",
    rows_type: "console_probe.rows",
    spans_type: "console_probe.spans",
    shown_type: "console_probe.shown",
    key_type: "console_probe.key",
    text_type: "console_probe.type",
    close_type: "console_probe.close",
    handler_version: 0,
    gold_id: "typescript.test_integrate_console_view",
    synchronous_setting: "queue_synchronous",
    // The ids the page's DOM port finds.
    image_id: "image",
    input_id: "input",
    permit_id: "permit",
    // The class prefixes of the colours of xterm.js's rows.
    colour_prefixes: ["xterm-fg-", "xterm-bg-"],
    // The elements xterm.js makes: the rows' holder, its rows, its input.
    screen_selector: ".xterm-screen",
    rows_selector: ".xterm-rows",
    input_selector: ".xterm-helper-textarea",
    // The height of the band under the console, its writer's choice.
    band_height: 50,
    // The lines each overlay keeps, its writer's choice.
    ring_lines: 3,
    // The media cache's budget and a download's seconds, their writer's.
    media_budget: 1000000,
    media_seconds: 10,
  });

  // The parts the topology's own handlers read and act on.
  interface ProbeParts {
    console_area: HTMLElement;
    input: HTMLInputElement;
    view: console_view.ConsoleView;
  }

  // A value of this block's gold.
  function gold_value(name: string): unknown {
    return harness.gold_get(`${constants.gold_id}.${name}`);
  }

  // The element xterm.js names inside the console, which must be there.
  function part_find(area: HTMLElement, selector: string): HTMLElement {
    const part = area.querySelector<HTMLElement>(selector);
    if (part === null) {
      throw new Error(`The console has no element ${selector}.`);
    }
    return part;
  }

  // The height in pixels of the rows of a terminal made and measured here.
  function rows_height(rows: number): number {
    const scratch = document.createElement("div");
    document.body.append(scratch);
    new Terminal({ cols: 1, rows, disableStdin: true }).open(scratch);
    const screen = part_find(scratch, constants.screen_selector);
    const height = screen.getBoundingClientRect().height;
    scratch.remove();
    return height;
  }

  // Puts in the page a frame whose console fits the gold's rows, and a band.
  function frame_make(): HTMLElement {
    const rows = gold_value("rows") as number;
    const height = rows_height(rows);
    // Half a row more than the rows need, so that the fit keeps them all.
    const space = height + height / rows / 2;
    const frame = document.createElement("div");
    Object.assign(frame.style, {
      position: "fixed",
      top: "0px",
      left: "0px",
      right: "0px",
      height: `${space + constants.band_height}px`,
      display: "flex",
      flexDirection: "column",
      justifyContent: "space-between",
    });
    const console_area = document.createElement("div");
    Object.assign(console_area.style, {
      minHeight: "0px",
      overflowX: "hidden",
      overflowY: "auto",
    });
    const band = document.createElement("div");
    Object.assign(band.style, {
      flexShrink: "0",
      height: `${constants.band_height}px`,
    });
    frame.append(console_area, band);
    document.body.append(frame);
    return console_area;
  }

  // The page's elements the DOM port and the handlers find, in a container.
  function elements_make(): HTMLElement {
    const container = document.createElement("div");
    const canvas = document.createElement("canvas");
    canvas.id = constants.image_id;
    const subtitle = document.createElement("p");
    const form = document.createElement("form");
    const input = document.createElement("input");
    input.id = constants.input_id;
    form.append(input);
    const permit = document.createElement("div");
    permit.id = constants.permit_id;
    const overlays = document.createElement("div");
    container.append(canvas, subtitle, form, permit, overlays);
    document.body.append(container);
    return container;
  }

  // The text of each row of the console, its end trimmed, the last empty out.
  function rows_read(area: HTMLElement): string[] {
    const rows = part_find(area, constants.rows_selector);
    const texts = Array.from(rows.children, (row) =>
      (row.textContent as string).trimEnd(),
    );
    while (texts.length > 0 && texts[texts.length - 1] === "") {
      texts.pop();
    }
    return texts;
  }

  // The colour classes of a node of a row, none for text outside a span.
  function colour_read(node: Node): string {
    if (!(node instanceof Element)) {
      return "";
    }
    return Array.from(node.classList)
      .filter((name) =>
        constants.colour_prefixes.some((prefix) => name.startsWith(prefix)),
      )
      .join(" ");
  }

  // The runs of text and colour of each row given, its end's blanks out.
  function spans_read(area: HTMLElement, indexes: number[]): string[][][] {
    const rows = part_find(area, constants.rows_selector);
    return indexes.map((index) => {
      const runs: string[][] = [];
      for (const node of Array.from(rows.children[index].childNodes)) {
        const colour = colour_read(node);
        const text = node.textContent as string;
        const previous = runs[runs.length - 1];
        if (previous !== undefined && previous[1] === colour) {
          previous[0] += text;
        } else {
          runs.push([text, colour]);
        }
      }
      while (runs.length > 0 && runs[runs.length - 1][0].trimEnd() === "") {
        runs.pop();
      }
      if (runs.length > 0) {
        const last = runs[runs.length - 1];
        last[0] = last[0].trimEnd();
      }
      return runs;
    });
  }

  // Registers the handlers of the topology's own types.
  function probes_register(parts: ProbeParts): void {
    const version = constants.handler_version;
    dispatch.handler_register(constants.rows_type, version, (line) =>
      dispatch.reply_make(line, { rows: rows_read(parts.console_area) }),
    );
    dispatch.handler_register(constants.spans_type, version, (line) => {
      const indexes = jslb.payload_of(line).rows as number[];
      const spans = spans_read(parts.console_area, indexes);
      return dispatch.reply_make(line, { spans });
    });
    dispatch.handler_register(constants.shown_type, version, (line) => {
      const child = parts.console_area.firstElementChild as HTMLElement;
      return dispatch.reply_make(line, { shown: !child.hidden });
    });
    // Control with a digit, pressed in the page as the player presses it.
    dispatch.handler_register(constants.key_type, version, (line) => {
      const digit = jslb.payload_of(line).digit as number;
      parts.input.dispatchEvent(
        new KeyboardEvent("keydown", {
          key: String(digit),
          ctrlKey: true,
          bubbles: true,
          cancelable: true,
        }),
      );
      return undefined;
    });
    // Text typed into the console's terminal, as an input method gives it.
    dispatch.handler_register(constants.text_type, version, (line) => {
      const text = jslb.payload_of(line).text as string;
      const input = part_find(parts.console_area, constants.input_selector);
      input.dispatchEvent(
        new InputEvent("input", { data: text, inputType: "insertText" }),
      );
      return undefined;
    });
    // The close of tty 0, whose wake the page's handler takes.
    dispatch.handler_register(constants.close_type, version, () =>
      parts.view.close_request(),
    );
  }

  // The page's handlers on a real queue and real parts, the test's lane end.
  export function topology_build(): queue.ThreadPort {
    const console_area = frame_make();
    const container = elements_make();
    const element_find = (id: string): HTMLElement =>
      container.querySelector(`#${id}`) as HTMLElement;
    const synchronous = harness.setting_get(
      constants.synchronous_setting,
    ) as boolean;
    const owners: queue.OwnerTable = {
      ...page.owners_make(),
      [constants.probe_prefix]: constants.thread,
    };
    const tasks = new queue.TaskQueue(constants.thread, owners, synchronous);
    const lane = new MessageChannel();
    tasks.port_add(constants.owner, new queue.ThreadPort(lane.port2));
    const images = new media.MediaPort(
      constants.media_budget,
      constants.media_seconds,
    );
    tasks.port_add("media", images);
    tasks.port_add("dom", new page.DomPort(container));
    const view = new console_view.ConsoleView(console_area, tasks);
    const input = element_find(constants.input_id) as HTMLInputElement;
    page.handlers_register(
      {
        tasks,
        canvas: element_find(constants.image_id) as HTMLCanvasElement,
        subtitle: container.querySelector("p") as HTMLElement,
        input,
        permit: element_find(constants.permit_id),
        images,
        view,
        overlays: new overlay.Overlay(
          container.lastElementChild as HTMLElement,
          constants.ring_lines,
        ),
        debug: switches.debug_on(),
      },
      dispatch.handler_register,
    );
    probes_register({ console_area, input, view });
    return new queue.ThreadPort(lane.port1);
  }
}
Object.freeze(test_integrate_console_view);
