// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The core script `ecs_step`, kept at /_files/script/ecs_step.js: one step of
// a guide's entity-component-system sim in its world database, one decision
// of the player, in one transaction. It reads the clock and the schedule of
// `system`, compiles each system's script, runs the lib with `{}`, each step
// system once in `ord` with `{ecs}`, then, while `busy` holds a row, ticks:
// the tick plus 1 and each tick system in `ord`. An intent no step system
// took, an entity still busy after `ticks_max` ticks, a system that throws or
// returns a value, and a step that says nothing or logs other than one beat
// throw, naming what failed, and the transaction commits nothing.
//
// Args: `world`, the world database. Returns `say`, the step's outputs in
// order joined by single spaces, and `outcome`, that of its one beat. Each
// system gets `args.ecs`, frozen: `world`, `step`, `tick`, `system`, its own
// name, `lib`, the lib's value, `rows(sql, params)`, `run(statements)`,
// `id(name)`, `take(verb)`, `say(text)` and `log(beat, choice, outcome)`.

// The store of the AI worker the script works through.
const store = engine.store;

// The start and the end of the key of a script's text.
const SCRIPT_PREFIX = "/_files/script/";
const SCRIPT_SUFFIX = ".js";

// The entity whose component the clock is.
const WORLD_ENTITY = "world";

// The kinds of a system: the lib, a step system and a tick system.
const LIB_KIND = "lib";
const STEP_KIND = "step";
const TICK_KIND = "tick";

// Reads a script's bytes as text, refusing any that are not `UTF-8`.
const decoder = new TextDecoder("utf-8", { fatal: true });

// The world database, which the args must name.
if (typeof args.world !== "string" || args.world === "") {
  throw new Error(
    `ecs_step takes world as the name of a database, not` +
      ` ${JSON.stringify(args.world)}.`,
  );
}
const world = args.world;

// The text of a thrown value: its stack when it is an `Error`.
function thrown_text(thrown) {
  return thrown instanceof Error ? String(thrown.stack) : String(thrown);
}

// The rows of a statement on the world, each an object of its columns.
function rows_read(sql, params) {
  const [result] = store.sql_run(world, [{ sql, params }]);
  const { columns, rows } = result;
  if (new Set(columns).size !== columns.length) {
    throw new Error(
      `ecs_step reads ${JSON.stringify(sql)} in ${world}, whose columns` +
        ` ${JSON.stringify(columns)} hold one name twice.`,
    );
  }
  return rows.map((row) =>
    Object.fromEntries(columns.map((name, index) => [name, row[index]])),
  );
}

// The function of a system's script, read from its key and compiled once.
function script_compile(name) {
  const ref = SCRIPT_PREFIX + name + SCRIPT_SUFFIX;
  const { data } = store.kv_get(ref);
  // A script over `overflow_bytes` comes back as a handle of the cache.
  if (!(data instanceof Uint8Array)) {
    throw new Error(
      `ecs_step reads ${ref}, the script of the system ${name}, as a handle` +
        ` of the cache and not as its bytes, as it is over overflow_bytes.`,
    );
  }
  try {
    return new Function("engine", "args", decoder.decode(data));
  } catch (thrown) {
    throw new Error(
      `ecs_step cannot compile ${ref}, the script of the system ${name}:` +
        ` ${thrown_text(thrown)}`,
      { cause: thrown },
    );
  }
}

// The schedule: each row of `system` in `ord`, its script compiled.
function systems_read() {
  const rows = rows_read("SELECT name, kind FROM system ORDER BY ord", []);
  return rows.map((row) => ({
    name: row.name,
    kind: row.kind,
    body: script_compile(row.name),
  }));
}

// The one row of `clock`, which must be the component of the entity world.
function clock_read() {
  const rows = rows_read(
    "SELECT clock.entity AS entity, entity.name AS name, clock.step AS step," +
      " clock.tick AS tick, clock.ticks_max AS ticks_max FROM clock" +
      " JOIN entity ON entity.id = clock.entity ORDER BY clock.entity",
    [],
  );
  if (rows.length !== 1 || rows[0].name !== WORLD_ENTITY) {
    throw new Error(
      `ecs_step needs one row of clock in ${world}, the component of the` +
        ` entity ${WORLD_ENTITY}, not ${JSON.stringify(rows)}.`,
    );
  }
  return rows[0];
}

// Calls a system's function with its args, naming the system when it throws.
function system_call(system, given) {
  try {
    return system.body(engine, given);
  } catch (thrown) {
    throw new Error(
      `ecs_step ran the ${system.kind} system ${system.name} of ${world},` +
        ` which threw ${thrown_text(thrown)}`,
      { cause: thrown },
    );
  }
}

// The value of the one lib of the schedule, run with `{}`: a frozen object.
function lib_run(systems) {
  const libs = systems.filter((system) => system.kind === LIB_KIND);
  if (libs.length !== 1) {
    throw new Error(
      `ecs_step needs one system of kind lib in ${world}, not` +
        ` ${JSON.stringify(libs.map((system) => system.name))}.`,
    );
  }
  const [lib] = libs;
  const value = system_call(lib, {});
  if (typeof value !== "object" || value === null) {
    throw new Error(
      `ecs_step ran the lib ${lib.name} of ${world}, which returned` +
        ` ${value === null ? "null" : typeof value}, not a frozen object.`,
    );
  }
  if (!Object.isFrozen(value)) {
    throw new Error(
      `ecs_step ran the lib ${lib.name} of ${world}, which returned an` +
        ` object not frozen.`,
    );
  }
  return value;
}

// The frozen `ecs` of one run of a system: its time, its lib and its methods.
function view_make(name, step, tick, lib) {
  // The verb of the run's one call of `take`, null before that call.
  let taken = null;
  return Object.freeze({
    world,
    step,
    tick,
    system: name,
    lib,
    rows: (sql, params) => {
      if (typeof sql !== "string" || !Array.isArray(params)) {
        throw new Error(
          `the system ${name} reads rows of ${JSON.stringify(sql)} with` +
            ` ${JSON.stringify(params)}, not a text and an array.`,
        );
      }
      return rows_read(sql, params);
    },
    run: (statements) => store.sql_run(world, statements),
    id: (entity) => {
      const rows = rows_read("SELECT id FROM entity WHERE name = ?", [entity]);
      if (rows.length === 0) {
        throw new Error(
          `the system ${name} asks the id of the entity` +
            ` ${JSON.stringify(entity)}, which ${world} lacks.`,
        );
      }
      return rows[0].id;
    },
    take: (verb) => {
      if (typeof verb !== "string" || verb === "") {
        throw new Error(
          `the system ${name} takes the intent of ${JSON.stringify(verb)},` +
            ` which is no verb.`,
        );
      }
      if (taken !== null) {
        throw new Error(
          `the system ${name} takes the intents of ${taken} and ${verb} in` +
            ` one run, where a system takes one verb's intent at most.`,
        );
      }
      taken = verb;
      const rows = rows_read(
        "SELECT intent.entity AS entity, entity.name AS name," +
          " intent.value AS value FROM intent JOIN entity" +
          " ON entity.id = intent.entity WHERE intent.verb = ?" +
          " ORDER BY intent.entity",
        [verb],
      );
      if (rows.length === 0) {
        return null;
      }
      if (rows.length > 1) {
        throw new Error(
          `the system ${name} finds ${rows.length} intents of ${verb} in` +
            ` ${world}, of ${rows.map((row) => row.name).join(", ")},` +
            ` where it takes one.`,
        );
      }
      const [intent] = rows;
      store.sql_run(world, [
        { sql: "DELETE FROM intent WHERE entity = ?", params: [intent.entity] },
      ]);
      return intent;
    },
    say: (text) => {
      if (typeof text !== "string" || text === "") {
        throw new Error(
          `the system ${name} says ${JSON.stringify(text)}, where an output` +
            ` is a text that is not empty.`,
        );
      }
      store.sql_run(world, [
        {
          sql:
            "INSERT INTO output (step, tick, system, text)" +
            " VALUES (?, ?, ?, ?)",
          params: [step, tick, name, text],
        },
      ]);
    },
    log: (beat, choice, outcome) => {
      const fields = [beat, choice, outcome];
      if (!fields.every((field) => typeof field === "string")) {
        throw new Error(
          `the system ${name} logs ${JSON.stringify(fields)}, where a beat,` +
            ` a choice and an outcome are texts.`,
        );
      }
      store.sql_run(world, [
        {
          sql:
            "INSERT INTO beat_log (step, tick, beat, choice, outcome)" +
            " VALUES (?, ?, ?, ?, ?)",
          params: [step, tick, ...fields],
        },
      ]);
    },
  });
}

// Runs a step or tick system with its `ecs`, which returns nothing.
function system_run(system, step, tick, lib) {
  const ecs = view_make(system.name, step, tick, lib);
  if (system_call(system, { ecs }) !== undefined) {
    throw new Error(
      `ecs_step ran the ${system.kind} system ${system.name} of ${world},` +
        ` which returned a value where a system returns nothing.`,
    );
  }
}

// Throws at an intent left once the step systems ran, as none took it.
function intents_check(step) {
  const left = rows_read(
    "SELECT intent.verb AS verb, entity.name AS name FROM intent" +
      " JOIN entity ON entity.id = intent.entity ORDER BY intent.entity",
    [],
  );
  if (left.length > 0) {
    const named = left.map((row) => `${row.verb} of ${row.name}`);
    throw new Error(
      `ecs_step finds the intents ${named.join(", ")} left in ${world} after` +
        ` the step systems of step ${step}, as no system took them.`,
    );
  }
}

// The names of the entities `busy` holds, in their order.
function busy_read() {
  const rows = rows_read(
    "SELECT entity.name AS name FROM busy" +
      " JOIN entity ON entity.id = busy.entity ORDER BY busy.entity",
    [],
  );
  return rows.map((row) => row.name);
}

// The step's say, its outputs joined, and the outcome of its one beat.
function said_read(step) {
  const said = rows_read(
    "SELECT text FROM output WHERE step = ? ORDER BY n",
    [step],
  );
  const logged = rows_read(
    "SELECT outcome FROM beat_log WHERE step = ? ORDER BY n",
    [step],
  );
  if (said.length === 0) {
    throw new Error(
      `ecs_step's step ${step} of ${world} said nothing, where a step says` +
        ` one output or more.`,
    );
  }
  if (logged.length !== 1) {
    throw new Error(
      `ecs_step's step ${step} of ${world} logged ${logged.length} beats,` +
        ` where a step logs one.`,
    );
  }
  return {
    say: said.map((row) => row.text).join(" "),
    outcome: logged[0].outcome,
  };
}

// One step: the lib, the step systems, the ticks, the clock, then the say.
function step_run() {
  const clock = clock_read();
  const step = clock.step + 1;
  let tick = clock.tick;
  const systems = systems_read();
  const lib = lib_run(systems);
  for (const system of systems) {
    if (system.kind === STEP_KIND) {
      system_run(system, step, tick, lib);
    }
  }
  intents_check(step);
  let ticks = 0;
  for (let busy = busy_read(); busy.length > 0; busy = busy_read()) {
    if (ticks >= clock.ticks_max) {
      throw new Error(
        `ecs_step ran ${ticks} ticks, the clock's ticks_max, in step ${step}` +
          ` of ${world}, and ${busy.join(", ")} are still busy.`,
      );
    }
    tick += 1;
    ticks += 1;
    for (const system of systems) {
      if (system.kind === TICK_KIND) {
        system_run(system, step, tick, lib);
      }
    }
  }
  store.sql_run(world, [
    {
      sql: "UPDATE clock SET step = ?, tick = ? WHERE entity = ?",
      params: [step, tick, clock.entity],
    },
  ]);
  return said_read(step);
}

return store.transaction_run(step_run);
