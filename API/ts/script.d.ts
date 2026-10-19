declare namespace script {
  // What a run returned: the value or the exception with its stack, and
  // the verbose lines the run wrote at the level it ran at.
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
    log(level: number, text: string): void;
    i18n(name: string, ...args: unknown[]): string;
  }

  // Runs `/_files/script/<name>.js` with `new Function("engine", "args",
  // text)` inside the calling task at verbose level `level`; level 2 is
  // `script_debug`, which traces every substrate call.
  function script_run(
    store: substrate.Store,
    name: string,
    args: unknown,
    level: number
  ): ScriptResult;
}
