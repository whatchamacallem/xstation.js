import jslb

# `settings.put`: rewrites settings.json in the root, debug mode only.
def settings_put(
    line: jslb.Object, *, settings: dict[str, object]
) -> jslb.Object: ...

# `source.put`: one blob, written as `main_loop/<name>` in the root, debug.
def source_put(line: jslb.Object, *, name: str) -> jslb.Object: ...

# `system.restart`: execs Python itself to serve `main_loop`, debug only.
def system_restart(line: jslb.Object, *, main_loop: str) -> None: ...
