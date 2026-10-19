import jslb

# `db.create`: a forwarded operation. Reply empty.
def db_create(line: jslb.Object, *, db: str) -> jslb.Object: ...

# `db.drop`: a forwarded operation. Reply empty.
def db_drop(line: jslb.Object, *, db: str) -> jslb.Object: ...

# `db.snapshot`: reply with `sha256` and `seq`, and the file as one blob.
def db_snapshot(line: jslb.Object, *, db: str) -> jslb.Object: ...
