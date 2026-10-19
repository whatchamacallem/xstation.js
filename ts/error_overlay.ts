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
    reload_button: "<button onclick=\"location.reload()\">Reload</button>",
    resource_failure: "Failed to load ",
    stop_twice: "The stop function was registered twice",
  });

  // What stopping the app means, set once by the page.
  let stop_function: (() => void) | null = null;

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

  // Names the element that failed to load and the address it asked for.
  function resource_message(element: Element): string {
    const address =
      element.getAttribute("src") ?? element.getAttribute("href");
    return `${constants.resource_failure}${element.localName} ${address}`;
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
    if (stop_function !== null) {
      throw new Error(constants.stop_twice);
    }
    stop_function = fn;
  }

  // Replaces the screen with the fault, stops the app and offers Reload.
  export function overlay_show(message: string, stack: string): void {
    const pre = `<pre>${text_escape(message)}\n${text_escape(stack)}</pre>`;
    document.write(pre + constants.reload_button);
    document.close();
    if (stop_function !== null) {
      stop_function();
    }
  }
}
Object.freeze(error_overlay);
