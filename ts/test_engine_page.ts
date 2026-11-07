// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The line cases of the UI thread's program, `engine.page_run`, on the
// elements of the engine page, made here as the page's integration block makes
// them, under the ids the program finds. The program builds every part from
// the document and registers the UI handlers on a real queue whose lane to the
// AI worker is the test's end: a render paints black, shows its subtitle and
// opens the box, a typed number becomes `ai.say` on that lane and the turn's
// end shows its subtitle and opens the box again, the focus in it each time,
// a permit request shows its buttons and a click answers it, and ctrl 0 shows
// the console, which takes the focus from the box, then hides it, which gives
// an open box the focus back, and the box holds what `line_max` bounds. The
// cases also send lines of types of the topology's own, whose handlers read
// the DOM back and act as the player does, through DOM events.
// The program's handlers register once on a thread, so its refusal of a page
// without its elements is taken first, before they exist, on a queue of its
// own, and a case reads it.

namespace test_engine_page {
  // The threads, the types of the topology's own and the page's elements.
  const constants = Object.freeze({
    thread: "ui" as const,
    owner: "ai" as const,
    probe_prefix: "engine_probe.",
    refusal_type: "engine_probe.refusal",
    band_type: "engine_probe.band",
    box_type: "engine_probe.box",
    image_type: "engine_probe.image",
    permit_type: "engine_probe.permit",
    submit_type: "engine_probe.submit",
    choose_type: "engine_probe.choose",
    key_type: "engine_probe.key",
    handler_version: 0,
    synchronous_setting: "queue_synchronous",
    // The ids the program finds.
    image_id: "image",
    subtitle_id: "subtitle",
    input_id: "input",
    permit_id: "permit",
    debug_id: "debug",
    overlays_id: "overlays",
  });

  // The elements the cases read and act on.
  interface PageElements {
    canvas: HTMLCanvasElement;
    subtitle: HTMLElement;
    form: HTMLFormElement;
    input: HTMLInputElement;
    permit: HTMLElement;
  }

  // Makes the page's elements in its order, the input closed until a render.
  function elements_make(): PageElements {
    const canvas = document.createElement("canvas");
    canvas.id = constants.image_id;
    const debug = document.createElement("div");
    debug.id = constants.debug_id;
    const overlays = document.createElement("div");
    overlays.id = constants.overlays_id;
    debug.append(overlays);
    const band = document.createElement("div");
    const subtitle = document.createElement("p");
    subtitle.id = constants.subtitle_id;
    const form = document.createElement("form");
    const input = document.createElement("input");
    input.id = constants.input_id;
    input.disabled = true;
    form.append(input);
    const permit = document.createElement("div");
    permit.id = constants.permit_id;
    band.append(subtitle, form, permit);
    document.body.append(canvas, debug, band);
    return { canvas, subtitle, form, input, permit };
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
  function probes_register(elements: PageElements, refusal: string): void {
    const { canvas, subtitle, form, input, permit } = elements;
    probe_add(constants.refusal_type, (line) =>
      dispatch.reply_make(line, { message: refusal }),
    );
    probe_add(constants.band_type, (line) =>
      dispatch.reply_make(line, {
        subtitle: subtitle.textContent,
        input_disabled: input.disabled,
        // A person's keys reach the box when it is open and holds the focus.
        input_focused: !input.disabled && document.activeElement === input,
      }),
    );
    // The most the box takes, which cuts a paste too long for one line.
    probe_add(constants.box_type, (line) =>
      dispatch.reply_make(line, { max_length: input.maxLength }),
    );
    // With the image hidden, what shows above the band is the page's colour.
    probe_add(constants.image_type, (line) =>
      dispatch.reply_make(line, {
        hidden: canvas.hidden,
        background: getComputedStyle(document.body).backgroundColor,
      }),
    );
    probe_add(constants.permit_type, (line) =>
      dispatch.reply_make(line, {
        texts: texts_of(permit, "p"),
        buttons: texts_of(permit, "button"),
      }),
    );
    // The player's number, typed into the input and submitted.
    probe_add(constants.submit_type, (line) => {
      input.value = jslb.payload_of(line).text as string;
      form.dispatchEvent(
        new SubmitEvent("submit", { bubbles: true, cancelable: true }),
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
    // The player's control key, held with ctrl.
    probe_add(constants.key_type, (line) => {
      document.body.dispatchEvent(
        new KeyboardEvent("keydown", {
          key: jslb.payload_of(line).key as string,
          ctrlKey: true,
          bubbles: true,
          cancelable: true,
        }),
      );
      return undefined;
    });
  }

  // What the program throws on a page without its elements, on its own queue.
  function refusal_read(): string {
    const owners = page.owners_make();
    const tasks = new queue.TaskQueue(constants.thread, owners, true);
    try {
      engine.page_run(tasks);
    } catch (error) {
      if (error instanceof Error) {
        return error.message;
      }
      throw error;
    }
    throw new Error("engine.page_run ran on a page without its elements");
  }

  // The program on a real queue, the test's end its lane to the AI worker.
  export function topology_build(): queue.ThreadPort {
    const refusal = refusal_read();
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
    engine.page_run(tasks);
    probes_register(elements, refusal);
    return new queue.ThreadPort(lane.port1);
  }
}
Object.freeze(test_engine_page);
