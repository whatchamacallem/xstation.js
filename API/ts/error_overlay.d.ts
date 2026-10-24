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

declare namespace error_overlay {
  function overlay_install(): void;

  // Registers what stopping means on the main thread, once.
  function stop_register(fn: (thrown: unknown) => void): void;

  // Registers what reporting means in the AI worker, once.
  function report_register(
    fn: (thrown: unknown, done: () => void) => void,
  ): void;

  // Replaces the screen with the fault, the first one only, with a Reload.
  function overlay_show(message: string, stack: string): void;
}
