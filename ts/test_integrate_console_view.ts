// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The line cases of the console view on the page: `console.show`,
// `console.output` and `console.exit`, which the page's handlers serve on a
// real queue of the UI thread, its lane to the AI worker the test's end. The
// view is the real one, on the real xterm.js terminal, in a frame sized from
// the cells of a terminal the topology measures first, so that the rows a
// show fits are the gold's `rows` whatever the font. The page's other parts
// are real too: the DOM port on the page's elements, the media port and the
// overlays. The cases also send lines of types of the topology's own, whose
// handlers read the DOM back, the console's rows and whether it is shown,
// and act as the player does, a key with control, typed text, and the close
// that only a handler asks for. Output reaches the rows after the call that
// feeds it, so a case that feeds output waits its seconds for the terminal
// to draw.
namespace test_integrate_console_view {
  // The threads, the types of the topology's own and the page's elements.
  const constants = Object.freeze({
    thread: "ui" as const,
    owner: "ai" as const,
    probe_prefix: "console_probe.",
    rows_type: "console_probe.rows",
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

  // Registers the handlers of the topology's own types.
  function probes_register(parts: ProbeParts): void {
    const version = constants.handler_version;
    dispatch.handler_register(constants.rows_type, version, (line) =>
      dispatch.reply_make(line, { rows: rows_read(parts.console_area) }),
    );
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
        debug: harness.setting_get("debug") as boolean,
      },
      dispatch.handler_register,
    );
    probes_register({ console_area, input, view });
    return new queue.ThreadPort(lane.port1);
  }
}
Object.freeze(test_integrate_console_view);
