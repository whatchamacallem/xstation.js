// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The first script of the page. It catches uncaught faults, replaces the
// screen with their text, stops the app and offers Reload. In the worker it
// posts a fault line instead. It depends on no other module.
namespace error_overlay {
  // The texts of this module, plain English as it depends on no other module.
  const constants = Object.freeze({
    reload_button: '<button onclick="location.reload()">Reload</button>',
    resource_failure: "Failed to load ",
    address_names: Object.freeze(["src", "href"]),
    address_missing: "Neither src nor href names what failed to load in ",
    stop_twice: "The stop function was registered twice",
  });

  // One fault screen: it shows the first fault and ignores later ones.
  export class FaultScreen {
    // What stopping the app means, set once by the page.
    #stop_function: (() => void) | null = null;

    // Whether a fault was shown, after which later faults are ignored.
    #fault_shown = false;

    // Registers what stopping the app means, once.
    stop_register(fn: () => void): void {
      if (this.#stop_function !== null) {
        throw new Error(constants.stop_twice);
      }
      this.#stop_function = fn;
    }

    // Shows the first fault only, stops the app and offers Reload.
    overlay_show(message: string, stack: string): void {
      if (this.#fault_shown) {
        return;
      }
      this.#fault_shown = true;
      const pre = `<pre>${text_escape(message)}\n${text_escape(stack)}</pre>`;
      document.write(pre + constants.reload_button);
      document.close();
      if (this.#stop_function !== null) {
        this.#stop_function();
      }
    }
  }

  // The fault screen of this page.
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

  // The message of anything that was thrown.
  function thrown_message(value: unknown): string {
    return value instanceof Error ? value.message : String(value);
  }

  // The call stack of anything that was thrown, empty when it has none.
  function thrown_stack(value: unknown): string {
    return value instanceof Error ? (value.stack ?? "") : "";
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

  // Shows a fault on the main thread, or posts it to the page from the worker.
  function fault_report(message: string, stack: string): void {
    if (worker_inside()) {
      self.postMessage({ 0: { t: "fault" }, thread: "ai", message, stack });
      return;
    }
    overlay_show(message, stack);
  }

  // Reports an uncaught error that reached the global scope.
  function error_event(event: ErrorEvent): void {
    fault_report(event.message, thrown_stack(event.error));
  }

  // Reports a promise rejection that nothing handled.
  function rejection_event(event: PromiseRejectionEvent): void {
    fault_report(thrown_message(event.reason), thrown_stack(event.reason));
  }

  // Reports a resource that failed to load, which only the capture phase sees.
  function resource_event(event: Event): void {
    const target = event.target;
    // Errors of the window itself are reported by `error_event`.
    if (!(target instanceof Element)) {
      return;
    }
    overlay_show(resource_message(target), "");
  }

  // Installs the handlers for faults on the main thread or in the worker.
  export function overlay_install(): void {
    self.addEventListener("error", error_event);
    self.addEventListener("unhandledrejection", rejection_event);
    if (!worker_inside()) {
      self.addEventListener("error", resource_event, true);
    }
  }

  // Registers what stopping the app means, once.
  export function stop_register(fn: () => void): void {
    screen_page.stop_register(fn);
  }

  // Replaces the screen with the first fault, stops the app and offers Reload.
  export function overlay_show(message: string, stack: string): void {
    screen_page.overlay_show(message, stack);
  }
}
Object.freeze(error_overlay);
