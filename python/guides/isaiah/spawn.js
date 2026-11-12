// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The spawn of Isaiah Cole's cattle drive, the script `isaiah_spawn` kept at
// `/_files/script/isaiah_spawn.js`: beds the herd down at the start of the
// last hundred miles to Dodge City. In one transaction it runs the lib the
// schedule names once, as `ecs_step` runs it, for the formats of its say,
// then in one `sql_run` makes every entity of the drive in the world
// database, the world with its clock, the herd, the three bunches the
// stampede will scatter, the player, Isaiah, the Cimarron, the outfit at its
// ford and Dodge City, and each component row they start with, from the
// guide's constants below, and keeps its say in `output` at step 0. Every
// number the drive works with is a component value here, so the database
// holds the whole model. It runs once, after `ecs_init` made the core tables
// and the build turn made the components and the schedule.
//
// Args: `world`, the world database, `drive`. Returns `say`, the herd and the
// miles bedded down, and `outcome`, `ready`.

// The store of the AI worker the script works through.
const store = engine.store;

// The start and the end of the key of a script's text.
const SCRIPT_PREFIX = "/_files/script/";
const SCRIPT_SUFFIX = ".js";

// The kind of the system of the schedule that is the lib.
const LIB_KIND = "lib";

// Reads a script's bytes as text, refusing any that are not `UTF-8`.
const decoder = new TextDecoder("utf-8", { fatal: true });

// The head bound for Dodge City, from the introduction: two thousand head.
const HERD = 2000;

// The mile of the bed ground, where the last hundred miles start.
const BED_MILE = 0;

// The miles left to Dodge City, from the pitch: the last hundred miles.
const MILES = 100;

// The mile of the Cimarron and its ford, a game rule no band shows.
const RIVER_MILE = 60;

// The miles the herd walks in a day, by Isaiah's reckoning.
const MILES_A_DAY = 10;

// The herd's calm when it beds down, a game rule of 0 to 10.
const CALM_START = 5;

// The calm a song on night guard adds, a game rule.
const SONG_CALM = 3;

// The most calm a herd has, the top of the game rule's 0 to 10.
const CALM_MAX = 10;

// The least calm of a settled herd, a game rule.
const SETTLED_CALM = 7;

// The calm of a herd once its run is milled into a circle, a game rule.
const MILLED_CALM = 3;

// The forty head missing at sunrise, from the guide, bunched by a game rule.
const BUNCHES = Object.freeze([
  Object.freeze({
    name: "ridge",
    head: 12,
    cover: "cedars",
    opening: "Up on the ridge",
  }),
  Object.freeze({
    name: "creek",
    head: 25,
    cover: "willows",
    opening: "Along the creek",
  }),
  Object.freeze({
    name: "draw",
    head: 3,
    cover: "plum thicket",
    opening: "Down in the draw",
  }),
]);

// The looks before noon to find the scattered head, a game rule.
const LOOKS = 3;

// The head lost when a run reaches the breaks, a game rule.
const BREAKS_LOSS = 60;

// The days the Cimarron runs high, from the guide: wait a day for it to drop.
const HIGH_DAYS = 1;

// The head swum in high water for each one that drowns, a game rule.
const HIGH_WATER_PER = 100;

// The least toll in head the outfit at the ford takes, a game rule.
const TOLL_FLOOR = 20;

// A rider's wage in cents a day, a dollar a day by the guide's rule.
const WAGE_CENTS = 100;

// The seconds a tick of the clock stands for: a day on the trail.
const TICK_SECONDS = 86400;

// The most ticks one step runs: the whole hundred miles at the herd's pace.
const TICKS_MAX = MILES / MILES_A_DAY;

// The entities of the drive, in the order their ids are given.
const ENTITIES = Object.freeze([
  "world",
  "herd",
  ...BUNCHES.map((bunch) => bunch.name),
  "player",
  "isaiah",
  "cimarron",
  "outfit",
  "dodge",
]);

// The world database, which the args must name.
if (typeof args.world !== "string" || args.world === "") {
  throw new Error(
    `isaiah_spawn takes world as the name of a database, not` +
      ` ${JSON.stringify(args.world)}.`,
  );
}
const world = args.world;

// The INSERT of one component row of the entity named, its values by column.
function row_insert(table, values, name) {
  const columns = Object.keys(values);
  const marks = columns.map(() => "?").join(", ");
  return {
    sql:
      `INSERT INTO ${table} (entity, ${columns.join(", ")})` +
      ` SELECT id, ${marks} FROM entity WHERE name = ?`,
    params: [...Object.values(values), name],
  };
}

// The entities and their components, in the order they are made.
const statements = [
  {
    sql:
      "INSERT INTO entity (name) VALUES " +
      ENTITIES.map(() => "(?)").join(", "),
    params: [...ENTITIES],
  },
  row_insert(
    "clock",
    { step: 0, tick: 0, tick_seconds: TICK_SECONDS, ticks_max: TICKS_MAX },
    "world",
  ),
  row_insert("head", { count: HERD }, "herd"),
  row_insert("bed", { head: HERD }, "herd"),
  row_insert("calm", { level: CALM_START, most: CALM_MAX }, "herd"),
  row_insert(
    "temper",
    { song_calm: SONG_CALM, settled: SETTLED_CALM, milled: MILLED_CALM },
    "herd",
  ),
  row_insert("breaks", { loss: BREAKS_LOSS }, "herd"),
  row_insert("place", { mile: BED_MILE }, "herd"),
  row_insert("pace", { miles: MILES_A_DAY }, "herd"),
  row_insert("losses", { lost: 0, tolled: 0, found: 0 }, "herd"),
  ...BUNCHES.flatMap((bunch) => [
    row_insert("share", { head: bunch.head }, bunch.name),
    row_insert(
      "cover",
      { name: bunch.cover, opening: bunch.opening },
      bunch.name,
    ),
  ]),
  row_insert("looks", { used: 0, most: LOOKS }, "player"),
  row_insert("exits", { count: 0 }, "player"),
  row_insert("wage", { cents_a_day: WAGE_CENTS, earned: 0 }, "player"),
  row_insert("wage", { cents_a_day: WAGE_CENTS, earned: 0 }, "isaiah"),
  row_insert("place", { mile: RIVER_MILE }, "cimarron"),
  row_insert(
    "water",
    { high: HIGH_DAYS, per_drowned: HIGH_WATER_PER },
    "cimarron",
  ),
  row_insert("toll", { floor: TOLL_FLOOR }, "outfit"),
  row_insert("place", { mile: BED_MILE + MILES }, "dodge"),
];

// The text of a thrown value: its stack when it is an `Error`.
function thrown_text(thrown) {
  return thrown instanceof Error ? String(thrown.stack) : String(thrown);
}

// The function of the lib's script, read from its key and compiled once.
function lib_compile(name) {
  const ref = SCRIPT_PREFIX + name + SCRIPT_SUFFIX;
  const { data } = store.kv_get(ref);
  // A script over `overflow_bytes` comes back as a handle of the cache.
  if (!(data instanceof Uint8Array)) {
    throw new Error(
      `isaiah_spawn reads ${ref}, the script of the lib ${name}, as a handle` +
        " of the cache and not as its bytes, as it is over overflow_bytes.",
    );
  }
  try {
    return new Function("engine", "args", decoder.decode(data));
  } catch (thrown) {
    throw new Error(
      `isaiah_spawn cannot compile ${ref}, the script of the lib ${name}:` +
        ` ${thrown_text(thrown)}`,
      { cause: thrown },
    );
  }
}

// The lib the schedule names, compiled and run once as `ecs_step` runs it.
function lib_run() {
  const [result] = store.sql_run(world, [
    { sql: "SELECT name FROM system WHERE kind = ?", params: [LIB_KIND] },
  ]);
  if (result.rows.length !== 1) {
    throw new Error(
      `isaiah_spawn needs one system of kind lib in ${world}, not` +
        ` ${JSON.stringify(result.rows)}.`,
    );
  }
  const [[name]] = result.rows;
  const body = lib_compile(name);
  let value;
  try {
    value = body(engine, {});
  } catch (thrown) {
    throw new Error(
      `isaiah_spawn ran the lib ${name} of ${world}, which threw` +
        ` ${thrown_text(thrown)}`,
      { cause: thrown },
    );
  }
  if (typeof value !== "object" || value === null) {
    throw new Error(
      `isaiah_spawn ran the lib ${name} of ${world}, which returned` +
        ` ${value === null ? "null" : typeof value}, not a frozen object.`,
    );
  }
  if (!Object.isFrozen(value)) {
    throw new Error(
      `isaiah_spawn ran the lib ${name} of ${world}, which returned an` +
        " object not frozen.",
    );
  }
  return value;
}

// Beds the herd down and says the herd, the miles and the calm it starts with.
function drive_spawn() {
  const lib = lib_run();
  const say =
    `${lib.whole_text(HERD)} head bedded on the flat and` +
    ` ${lib.whole_text(MILES)} miles to Dodge City:` +
    ` ${lib.days_text(MILES / MILES_A_DAY)} at` +
    ` ${lib.whole_text(MILES_A_DAY)} miles a day. The herd's calm is` +
    ` ${lib.whole_text(CALM_START)} of ${lib.whole_text(CALM_MAX)}.`;
  store.sql_run(world, [
    ...statements,
    {
      sql:
        "INSERT INTO output (step, tick, system, text) VALUES (?, ?, ?, ?)",
      params: [0, 0, "isaiah_spawn", say],
    },
  ]);
  return { say, outcome: "ready" };
}

return store.transaction_run(drive_spawn);
