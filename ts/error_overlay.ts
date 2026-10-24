// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The first script of the page; it depends on nothing, so its texts are plain
// English and every line it builds has full names. It installs the handlers
// of `error` and `unhandledrejection` on both threads, and of resource load
// failures in the capture phase on the main thread.
//
// On the main thread an uncaught fault replaces the screen with its message
// and stack, the first fault only, then runs the stop function with the
// thrown value: the page posts it to the AI worker as a `fault` line, and the
// worker sends it to the server as an `error` line and waits for the server
// to end the wire. A resource that failed to load is such a fault, its thrown
// value an Error of the text that names it.
//
// In the AI worker an uncaught fault runs the report function with the
// thrown value and a `done` callback: the worker sends the `error` line to
// the server, which logs it and ends the wire by its exit, and then calls
// `done`, which posts the `fault` line to the page. With no report function
// yet registered the `fault` line is posted at once. A fault met while the
// report waits, as the expiry of the wire's drain timer, posts its `fault`
// line at once, the first fault's cascade under its innermost `cause`; any
// later fault is not reported. A `fault` line holds the cascade of the
// thrown value, each Error's `cause` nested, written by this module itself.
namespace error_overlay {
  // The texts of this module, plain English as it depends on no other module.
  const constants = Object.freeze({
    reload_button: '<button onclick="location.reload()">Reload</button>',
    resource_failure: "Failed to load ",
    address_names: Object.freeze(["src", "href"]),
    address_missing: "Neither src nor href names what failed to load in ",
    stop_twice: "The stop function was registered twice",
    report_twice: "The report function was registered twice",
    fault_type: "fault",
    worker_thread: "ai",
  });

  // One failure of a cascade and, under `cause`, the failure before it.
  interface Cascade {
    message: string;
    stack: string;
    cause?: Cascade;
  }

  // Where the faults of a thread stand: none yet, one reporting, reported.
  type FaultPhase = "idle" | "reporting" | "ended";

  // One fault screen per thread: it takes the first fault and ignores others.
  export class FaultScreen {
    // What stopping means on the main thread, set once by the page.
    #stop_function: ((thrown: unknown) => void) | null = null;

    // What reporting means in the AI worker, set once by the worker.
    #report_function:
      | ((thrown: unknown, done: () => void) => void)
      | null = null;

    // Whether a fault was shown, after which later ones are not.
    #fault_shown = false;

    // Where the faults this screen took stand.
    #phase: FaultPhase = "idle";

    // The cascade of the fault the report function is reporting.
    #first: Cascade | null = null;

    // Registers what stopping means on the main thread, once.
    stop_register(fn: (thrown: unknown) => void): void {
      if (this.#stop_function !== null) {
        throw new Error(constants.stop_twice);
      }
      this.#stop_function = fn;
    }

    // Registers what reporting means in the AI worker, once.
    report_register(fn: (thrown: unknown, done: () => void) => void): void {
      if (this.#report_function !== null) {
        throw new Error(constants.report_twice);
      }
      this.#report_function = fn;
    }

    // Writes the first fault on the screen with a Reload, and only that.
    overlay_show(message: string, stack: string): void {
      if (this.#fault_shown) {
        return;
      }
      this.#fault_shown = true;
      const pre = `<pre>${text_escape(message)}\n${text_escape(stack)}</pre>`;
      document.write(pre + constants.reload_button);
      document.close();
    }

    // The thread's uncaught fault, `post` null on the main thread.
    fault_take(thrown: unknown, post: ((line: object) => void) | null): void {
      if (post === null) {
        this.#main_take(thrown);
        return;
      }
      this.#worker_take(thrown, post);
    }

    // A resource of the main thread that failed to load, taken as its fault.
    resource_take(element: Element): void {
      this.fault_take(new Error(resource_message(element)), null);
    }

    // The first fault of the main thread: the screen, then the stop function.
    #main_take(thrown: unknown): void {
      if (this.#phase !== "idle") {
        return;
      }
      this.#phase = "ended";
      const cascade = cascade_make(thrown);
      this.overlay_show(cascade.message, cascade.stack);
      if (this.#stop_function !== null) {
        this.#stop_function(thrown);
      }
    }

    // A fault of the worker: reported first, at once while one is reported.
    #worker_take(thrown: unknown, post: (line: object) => void): void {
      if (this.#phase === "ended") {
        return;
      }
      if (this.#phase === "reporting") {
        this.#phase = "ended";
        const cascade = cascade_make(thrown);
        cascade_innermost(cascade).cause = this.#first as Cascade;
        post(fault_line(cascade));
        return;
      }
      const report = this.#report_function;
      if (report === null) {
        this.#phase = "ended";
        post(fault_line(cascade_make(thrown)));
        return;
      }
      this.#phase = "reporting";
      this.#first = cascade_make(thrown);
      try {
        report(thrown, () => {
          if (this.#phase === "reporting") {
            this.#phase = "ended";
            post(fault_line(this.#first as Cascade));
          }
        });
      } catch (error) {
        // Thrown inside the error event, it would reach no handler but here.
        this.#worker_take(error, post);
      }
    }
  }

  // The fault screen of this thread.
  const screen_page = new FaultScreen();

  // Tells whether this code runs in a worker, which has no document.
  function worker_inside(): boolean {
    return typeof document === "undefined";
  }

  // Escapes text so that markup shows it as it is.
  function text_escape(text: string): string {
    return text
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;");
  }

  // The cascade of a thrown value, a value that is no Error its text alone.
  function cascade_make(thrown: unknown): Cascade {
    if (!(thrown instanceof Error)) {
      return { message: String(thrown), stack: "" };
    }
    const cascade: Cascade = {
      message: thrown.message,
      stack: thrown.stack ?? "",
    };
    if (thrown.cause !== undefined) {
      cascade.cause = cascade_make(thrown.cause);
    }
    return cascade;
  }

  // The innermost failure of a cascade, the one with no `cause`.
  function cascade_innermost(cascade: Cascade): Cascade {
    let node = cascade;
    while (node.cause !== undefined) {
      node = node.cause;
    }
    return node;
  }

  // The `fault` line of the worker, in full names, holding the cascade.
  function fault_line(cascade: Cascade): object {
    return {
      0: { type: constants.fault_type },
      thread: constants.worker_thread,
      ...cascade,
    };
  }

  // Names the element that failed to load and the one address it has.
  function resource_message(element: Element): string {
    for (const name of constants.address_names) {
      const address = element.getAttribute(name);
      if (address !== null) {
        const failure = constants.resource_failure;
        return `${failure}${element.localName} ${name}="${address}"`;
      }
    }
    throw new Error(`${constants.address_missing}${element.localName}`);
  }

  // What posts a fault line to the page: from the worker only.
  function post_of(): ((line: object) => void) | null {
    if (worker_inside()) {
      return (line) => self.postMessage(line);
    }
    return null;
  }

  // Takes an uncaught error that reached the global scope.
  function error_event(event: ErrorEvent): void {
    // The worker cancels it so the page's `onerror` gets only the posted line.
    if (worker_inside()) {
      event.preventDefault();
    }
    const thrown =
      event.error instanceof Error ? event.error : new Error(event.message);
    screen_page.fault_take(thrown, post_of());
  }

  // Takes a promise rejection that nothing handled.
  function rejection_event(event: PromiseRejectionEvent): void {
    screen_page.fault_take(event.reason, post_of());
  }

  // Takes a resource that failed to load, which only the capture phase sees.
  function resource_event(event: Event): void {
    const target = event.target;
    // Errors of the window itself are taken by `error_event`.
    if (!(target instanceof Element)) {
      return;
    }
    screen_page.resource_take(target);
  }

  // Installs the handlers for faults on the main thread or in the worker.
  export function overlay_install(): void {
    self.addEventListener("error", error_event);
    self.addEventListener("unhandledrejection", rejection_event);
    if (!worker_inside()) {
      self.addEventListener("error", resource_event, true);
    }
  }

  // Registers what stopping means on the main thread, once.
  export function stop_register(fn: (thrown: unknown) => void): void {
    screen_page.stop_register(fn);
  }

  // Registers what reporting means in the AI worker, once.
  export function report_register(
    fn: (thrown: unknown, done: () => void) => void,
  ): void {
    screen_page.report_register(fn);
  }

  // Replaces the screen with the fault, the first one only, with a Reload.
  export function overlay_show(message: string, stack: string): void {
    screen_page.overlay_show(message, stack);
  }

  // The handlers stand from the first module of the bundle, before any other.
  overlay_install();
}
Object.freeze(error_overlay);
