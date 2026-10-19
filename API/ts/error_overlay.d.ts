declare namespace error_overlay {
  // The first script in the page; it depends on nothing. Installs the
  // handlers: `error` and `unhandledrejection` on the window, resource
  // load failures in the capture phase. In the worker, the same two
  // events post `fault` to the UI instead.
  function overlay_install(): void;

  // Registers what stopping the app means: closing the wire and
  // terminating the worker. Called once by page.ts.
  function stop_register(fn: () => void): void;

  // Replaces the screen by document.write with a <pre> holding the
  // message and the call stack, runs the stop function, and offers
  // Reload, which is location.reload().
  function overlay_show(message: string, stack: string): void;
}
