// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The line cases of the console view's open path, group C, on the UI side of
// the headless page that the block's own ttyd serves, through dash on tty 0,
// every part real. The UI queue's `ai` lane is linked to the `ui` lane of a
// second real queue of thread `ai` in the same realm, which holds
// `worker_ai.console_register` and a real `wire.ConsolePort`. The test's end
// is the UI queue's lane of thread `server`, which the UI thread's table gives
// no type, so the requests it sends of the types the UI owns run there and
// their replies come back on it. The rows are read from the first that starts
// with the gold's `prompt` on, so that what comes before dash's first prompt
// changes no expectation.
namespace test_console_open {
  // The threads, the lanes, the types of the topology's own, the elements.
  const constants = Object.freeze({
    ui_thread: "ui" as const,
    ai_thread: "ai" as const,
    ai_owner: "ai" as const,
    ui_owner: "ui" as const,
    console_owner: "console" as const,
    test_owner: "server" as const,
    exit_type: "console.exit",
    probe_prefix: "console_probe.",
    rows_type: "console_probe.rows",
    phase_type: "console_probe.phase",
    text_type: "console_probe.type",
    close_type: "console_probe.close",
    handler_version: 0,
    gold_id: "typescript.test_console_open",
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
    view: console_view.ConsoleView;
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
    const rows = harness.gold_get(`${constants.gold_id}.rows`) as number;
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

  // Each row's text, its end trimmed, the last empty out, from the prompt on.
  function rows_read(area: HTMLElement): string[] {
    const rows = part_find(area, constants.rows_selector);
    const texts = Array.from(rows.children, (row) =>
      (row.textContent as string).trimEnd(),
    );
    while (texts.length > 0 && texts[texts.length - 1] === "") {
      texts.pop();
    }
    // What a sandbox or dash writes before dash's first prompt is left out.
    const prompt = harness.gold_get(`${constants.gold_id}.prompt`) as string;
    const first = texts.findIndex((text) => `${text} `.startsWith(prompt));
    return first < 0 ? texts : texts.slice(first);
  }

  // Registers the handlers of the topology's own types.
  function probes_register(parts: ProbeParts): void {
    const version = constants.handler_version;
    dispatch.handler_register(constants.rows_type, version, (line) =>
      dispatch.reply_make(line, { rows: rows_read(parts.console_area) }),
    );
    dispatch.handler_register(constants.phase_type, version, (line) =>
      dispatch.reply_make(line, { wanted: parts.view.open_wanted() }),
    );
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

  // The AI side: a real queue with the relays and tty 0's real port.
  function relay_build(far: queue.LocalPort): void {
    const tasks = new queue.TaskQueue(
      constants.ai_thread,
      worker_ai.owners_make(),
      true,
    );
    tasks.port_add(constants.ui_owner, new queue.LocalPort(far));
    const port = new wire.ConsolePort(location.href);
    // The end of tty 0, pushed to the UI as `worker_ai.console_attach` does.
    port.close_receive((code) => {
      const header = jslb.header_make(constants.exit_type, {
        full: settings.names_full(),
      });
      tasks.line_notify(jslb.line_make(header, [], { code }));
    });
    tasks.port_add(constants.console_owner, port);
    worker_ai.console_register(tasks, dispatch.handler_register, () => {
      port.console_close();
    });
  }

  // The page's handlers and the AI side's relays, the test's lane end.
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
      [constants.probe_prefix]: constants.ui_thread,
    };
    const tasks = new queue.TaskQueue(
      constants.ui_thread,
      owners,
      synchronous,
    );
    const near = new queue.LocalPort();
    tasks.port_add(constants.ai_owner, near);
    relay_build(near);
    const lane = new MessageChannel();
    tasks.port_add(constants.test_owner, new queue.ThreadPort(lane.port2));
    const images = new media.MediaPort(
      constants.media_budget,
      constants.media_seconds,
    );
    tasks.port_add("media", images);
    tasks.port_add("dom", new page.DomPort(container));
    const view = new console_view.ConsoleView(console_area, tasks);
    page.handlers_register(
      {
        tasks,
        canvas: element_find(constants.image_id) as HTMLCanvasElement,
        subtitle: container.querySelector("p") as HTMLElement,
        input: element_find(constants.input_id) as HTMLInputElement,
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
    probes_register({ console_area, view });
    return new queue.ThreadPort(lane.port1);
  }
}
Object.freeze(test_console_open);
