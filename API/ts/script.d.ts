declare namespace script {
  // What a run returned: the value or the exception with its stack, and
  // the verbose lines the run wrote.
  interface ScriptResult {
    value?: unknown;
    error?: string;
    stack?: string;
    lines: lines.VerboseLine[];
  }

  // The frozen object a script receives as `engine`: the store's
  // methods, `verbose.log` and `i18n`.
  interface Engine {
    store: substrate.Store;
    log(text: string): void;
    i18n(name: string, ...args: unknown[]): string;
  }

  // Runs `/_files/script/<name>.js` with `new Function("engine", "args",
  // text)` inside the calling task; with `trace`, as `script_debug` runs
  // it, each substrate call is traced first.
  function script_run(
    store: substrate.Store,
    name: string,
    args: unknown,
    trace: boolean
  ): ScriptResult;
}
