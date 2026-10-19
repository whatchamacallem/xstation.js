import jslb

# `doc.put`: a forwarded operation. Reply with `ref` and `seq`.
def doc_put(
    line: jslb.Object, *, db: str, id: str, body: dict[str, object], since: int
) -> jslb.Object: ...

# `doc.head`: reply with `ref`.
def doc_head(line: jslb.Object, *, db: str, id: str) -> jslb.Object: ...
