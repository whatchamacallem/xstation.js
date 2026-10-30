// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The line cases of the UI thread's handlers on the page: the lines of the AI
// worker that `page.handlers_register` serves, a render, a kept image, a
// permit, the player's turns, the overlays' keys and lines and a fetched
// image, each answered on a real queue of the UI thread whose lane to the AI
// worker is the test's end. Every part is real: the DOM port on the page's
// elements, which takes the player's text, clicks, keys and choices, the media
// port, which decodes the gold's image and downloads one from the driver's
// HTTP server, which serves this page too, the console view and the overlays.
// The cases also send lines of types of the topology's own, whose handlers
// read the DOM back, the band, the image's pixels, the permit area and the
// overlays, and act as the player does, through DOM events: text submitted, a
// click on a pixel of the image, a key with control and a permit button
// clicked. A line that another line's handling sends on is answered after the
// handling, so the case that reads what it changed comes after a wait.
namespace test_integrate_page {
  // The threads, the types of the topology's own and the page's elements.
  const constants = Object.freeze({
    thread: "ui" as const,
    owner: "ai" as const,
    probe_prefix: "page_probe.",
    band_type: "page_probe.band",
    image_type: "page_probe.image",
    permit_type: "page_probe.permit",
    overlays_type: "page_probe.overlays",
    key_type: "page_probe.key",
    submit_type: "page_probe.submit",
    click_type: "page_probe.click",
    choose_type: "page_probe.choose",
    handler_version: 0,
    synchronous_setting: "queue_synchronous",
    // The ids the page's DOM port finds.
    image_id: "image",
    input_id: "input",
    permit_id: "permit",
    // The pixel sizes of the console's frame and band, chosen by their writer.
    frame_width: 1000,
    frame_height: 400,
    band_height: 50,
    // The lines each overlay keeps, its writer's choice.
    ring_lines: 3,
    // The media cache's budget and a download's seconds, their writer's.
    media_budget: 1000000,
    media_seconds: 10,
  });

  // The page's elements the handlers and the DOM port work on.
  interface PageElements {
    container: HTMLElement;
    canvas: HTMLCanvasElement;
    subtitle: HTMLElement;
    form: HTMLFormElement;
    input: HTMLInputElement;
    permit: HTMLElement;
    overlays: HTMLElement;
  }

  // Puts in the page a frame of a fixed size: the console above a band.
  function frame_make(): HTMLElement {
    const frame = document.createElement("div");
    Object.assign(frame.style, {
      position: "fixed",
      top: "0px",
      left: "0px",
      width: `${constants.frame_width}px`,
      height: `${constants.frame_height}px`,
      display: "flex",
      flexDirection: "column",
      justifyContent: "space-between",
    });
    const console_area = document.createElement("div");
    Object.assign(console_area.style, { minHeight: "0px", overflow: "auto" });
    const band = document.createElement("div");
    Object.assign(band.style, {
      flexShrink: "0",
      height: `${constants.band_height}px`,
    });
    frame.append(console_area, band);
    document.body.append(frame);
    return console_area;
  }

  // Makes the page's elements in a container, the input closed until a render.
  function elements_make(): PageElements {
    const container = document.createElement("div");
    const canvas = document.createElement("canvas");
    canvas.id = constants.image_id;
    const subtitle = document.createElement("p");
    const form = document.createElement("form");
    const input = document.createElement("input");
    input.id = constants.input_id;
    input.disabled = true;
    form.append(input);
    const permit = document.createElement("div");
    permit.id = constants.permit_id;
    const overlays = document.createElement("div");
    container.append(canvas, subtitle, form, permit, overlays);
    document.body.append(container);
    return { container, canvas, subtitle, form, input, permit, overlays };
  }

  // The digest of the pixels of the image as the canvas holds them.
  function pixels_digest(canvas: HTMLCanvasElement): string {
    const context = canvas.getContext("2d") as CanvasRenderingContext2D;
    const pixels = context.getImageData(0, 0, canvas.width, canvas.height);
    return utility.sha256_hex(new Uint8Array(pixels.data.buffer));
  }

  // The texts of the elements a selector finds in an element, in order.
  function texts_of(element: HTMLElement, selector: string): string[] {
    return Array.from(
      element.querySelectorAll(selector),
      (found) => found.textContent as string,
    );
  }

  // Registers a handler of one of the topology's own types.
  function probe_add(type: string, fn: dispatch.Handler): void {
    dispatch.handler_register(type, constants.handler_version, fn);
  }

  // Registers the handlers that read the DOM back and act as the player.
  function probes_register(elements: PageElements): void {
    const { canvas, subtitle, form, input, permit, overlays } = elements;
    probe_add(constants.band_type, (line) =>
      dispatch.reply_make(line, {
        subtitle: subtitle.textContent,
        input_disabled: input.disabled,
      }),
    );
    probe_add(constants.image_type, (line) =>
      dispatch.reply_make(line, {
        hidden: canvas.hidden,
        width: canvas.width,
        height: canvas.height,
        pixels: pixels_digest(canvas),
      }),
    );
    probe_add(constants.permit_type, (line) =>
      dispatch.reply_make(line, {
        texts: texts_of(permit, "p"),
        buttons: texts_of(permit, "button"),
      }),
    );
    probe_add(constants.overlays_type, (line) => {
      const pres = Array.from(overlays.querySelectorAll("pre"));
      const shown = pres.map((pre) => ({
        text: pre.textContent,
        hidden: pre.hidden,
      }));
      return dispatch.reply_make(line, { overlays: shown });
    });
    // Control with a digit, pressed in the page as the player presses it.
    probe_add(constants.key_type, (line) => {
      const digit = jslb.payload_of(line).digit as number;
      input.dispatchEvent(
        new KeyboardEvent("keydown", {
          key: String(digit),
          ctrlKey: true,
          bubbles: true,
          cancelable: true,
        }),
      );
      return undefined;
    });
    // The player's text, typed into the input and submitted.
    probe_add(constants.submit_type, (line) => {
      input.value = jslb.payload_of(line).text as string;
      form.dispatchEvent(
        new SubmitEvent("submit", { bubbles: true, cancelable: true }),
      );
      return undefined;
    });
    // A click on the middle of a pixel of the image, where the page shows it.
    probe_add(constants.click_type, (line) => {
      const { x, y } = jslb.payload_of(line) as { x: number; y: number };
      const box = canvas.getBoundingClientRect();
      const scale = Math.min(
        box.width / canvas.width,
        box.height / canvas.height,
      );
      const left = (box.width - canvas.width * scale) / 2;
      const top = (box.height - canvas.height * scale) / 2;
      canvas.dispatchEvent(
        new MouseEvent("click", {
          clientX: box.left + left + (x + 0.5) * scale,
          clientY: box.top + top + (y + 0.5) * scale,
          bubbles: true,
        }),
      );
      return undefined;
    });
    // A click on a button of the permit area, by its place among them.
    probe_add(constants.choose_type, (line) => {
      const index = jslb.payload_of(line).button as number;
      const buttons = permit.querySelectorAll("button");
      (buttons[index] as HTMLButtonElement).click();
      return undefined;
    });
  }

  // The page's handlers on a real queue and real parts, the test's lane end.
  export function topology_build(): queue.ThreadPort {
    const console_area = frame_make();
    const elements = elements_make();
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
    tasks.port_add("dom", new page.DomPort(elements.container));
    page.handlers_register(
      {
        tasks,
        canvas: elements.canvas,
        subtitle: elements.subtitle,
        input: elements.input,
        permit: elements.permit,
        images,
        view: new console_view.ConsoleView(console_area, tasks),
        overlays: new overlay.Overlay(elements.overlays, constants.ring_lines),
        debug: harness.setting_get("debug") as boolean,
      },
      dispatch.handler_register,
    );
    probes_register(elements);
    return new queue.ThreadPort(lane.port1);
  }
}
Object.freeze(test_integrate_page);
