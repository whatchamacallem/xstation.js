// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The spawn of Ruth Calloway's sim, kept at /_files/script/ruth_spawn.js and
// run once by the build turn, after ecs_init and the guide's schema: makes in
// the world database every entity, every component row and the clock, in one
// sql_run, from the figures of the Curtiss `JN-4D`'s 1918 specifications,
// Ruth's technique and fares, and the guide's world, each constant with its
// source, and keeps its say in `output` at step 0. It runs the lib the
// schedule names once, as ecs_step runs it, for the formats of its say. The
// entities, in the order of their ids: world, jenny, ruth, player, the
// partner, fair, motorcar, wind, and the fields north and south. A figure
// that is no whole number is kept as an integer of a stated scale, its column
// ending in `_x100` or `_x10`.
//
// Args: `world`, the world database, and `partner`, the player's name.
// Returns `say`, the Jenny's figures, and `outcome` ready.

// The store of the AI worker the script works through.
const store = engine.store;

// The start and the end of the key of a script's text.
const SCRIPT_PREFIX = "/_files/script/";
const SCRIPT_SUFFIX = ".js";

// The kind of the system of the schedule that is the lib.
const LIB_KIND = "lib";

// Reads a script's bytes as text, refusing any that are not `UTF-8`.
const decoder = new TextDecoder("utf-8", { fatal: true });

// Game rule: a tick of the sim is 20 seconds, so each racer moves whole feet.
const TICK_SECONDS = 20;
// Game rule: the most ticks one step runs, ten minutes of the sim.
const TICKS_MAX = 30;

// 1918 specifications: gross weight loaded, two of 165 pounds and full fuel.
const GROSS_LB = 1920;
// 1918 specifications: total supporting surface, hundredths of a square foot.
const WING_SQFT_X100 = 35256;
// 1918 specifications: the `OX-5` rated at 1400 rpm, horsepower.
const HP = 90;
// 1918 specifications: speed, maximum, horizontal flight, mph.
const MAX_MPH = 75;
// 1918 specifications: speed, minimum, horizontal flight, the stall at 1 g.
const MIN_MPH = 45;
// 1918 specifications: climb in 10 minutes, feet.
const CLIMB_FT = 2000;
// 1918 specifications: the minutes of that climb.
const CLIMB_MIN = 10;
// 1918 specifications: fuel tank capacity, gallons.
const TANK_GAL = 21;
// 1918 specifications: fuel consumption, gallons an hour.
const BURN_GAL_HR = 9;
// 1918 operating instructions: final leveling off about fifty feet up.
const LEVEL_OFF_FT = 50;
// P. M. Bowers, Curtiss Aircraft 1907 to 1947 (1979), p. 156: cruise, mph.
const CRUISE_MPH = 60;
// B. van der Zalm (2018), aircraftinvestigation.info: lift to drag, hundredths.
const GLIDE_RATIO_X100 = 1066;
// Ruth's technique: the pull at the bottom of the loop, in g.
const LOOP_PULL_G = 4;
// Ruth's technique: light over the top of the loop, in tenths of a g.
const LOOP_TOP_G_X10 = 5;
// Ruth's count for a roll, seconds.
const ROLL_SECONDS = 4;
// The guide's world: where Ruth teaches, feet.
const STUNT_FT = 2000;
// The introduction, "Five dollars buys ten minutes": a ride, cents.
const RIDE_CENTS = 500;
// The introduction: the minutes a ride buys.
const RIDE_MIN = 10;
// U.S. DOE Vehicle Technologies Office, Fact 915 (2016): 1929 pump price.
const GAS_CENTS_GAL = 21;
// The guide's world: the cigar box holds nothing at the start, cents.
const PURSE_START_CENTS = 0;
// The guide's world: the evening show's flying, minutes.
const SHOW_MIN = 40;
// The guide's world: the wing walk's height, where the engine quits, feet.
const SHOW_FT = 1000;
// The guide's world: the fair's race purse, cents.
const PRIZE_CENTS = 2500;
// The guide's world: the county road race, 5 miles of 5280 feet.
const RACE_FT = 26400;
// The Henry Ford: the Model T's top speed of about 45 mph.
const MOTORCAR_MPH = 45;
// The guide's world: the day's wind, mph.
const WIND_MPH = 15;
// The guide's world: the quarter the day's wind blows from.
const WIND_QUARTER = "north";
// The guide's world: the north hayfield's distance, tenths of a mile.
const NORTH_MILES_X10 = 15;
// The guide's world: the south pasture's distance, tenths of a mile.
const SOUTH_MILES_X10 = 30;

// The entities, in the order of their ids.
const ENTITIES = Object.freeze([
  "world",
  "jenny",
  "ruth",
  "player",
  "fair",
  "motorcar",
  "wind",
  "north",
  "south",
]);

// The world database and the partner's name, which the args must hold.
if (typeof args.world !== "string" || args.world === "") {
  throw new Error(
    `ruth_spawn takes world as the name of a database, not` +
      ` ${JSON.stringify(args.world)}.`,
  );
}
if (typeof args.partner !== "string" || args.partner === "") {
  throw new Error(
    `ruth_spawn takes partner as the player's name, not` +
      ` ${JSON.stringify(args.partner)}.`,
  );
}
const world = args.world;

// The statement that gives the named entity its row of a component.
function component_row(table, columns, values, entity) {
  const marks = values.map(() => "?").join(", ");
  return {
    sql:
      `INSERT INTO ${table} (entity, ${columns.join(", ")})` +
      ` SELECT id, ${marks} FROM entity WHERE name = ?`,
    params: [...values, entity],
  };
}

// The entities and their component rows, in the order they are made.
const statements = [
  {
    sql:
      "INSERT INTO entity (name) VALUES " +
      ENTITIES.map(() => "(?)").join(", "),
    params: [...ENTITIES],
  },
  component_row(
    "clock",
    ["step", "tick", "tick_seconds", "ticks_max"],
    [0, 0, TICK_SECONDS, TICKS_MAX],
    "world",
  ),
  component_row(
    "airframe",
    [
      "gross_lb",
      "wing_sqft_x100",
      "hp",
      "max_mph",
      "min_mph",
      "climb_ft",
      "climb_min",
      "tank_gal",
      "burn_gal_hr",
      "level_off_ft",
      "cruise_mph",
      "glide_ratio_x100",
    ],
    [
      GROSS_LB,
      WING_SQFT_X100,
      HP,
      MAX_MPH,
      MIN_MPH,
      CLIMB_FT,
      CLIMB_MIN,
      TANK_GAL,
      BURN_GAL_HR,
      LEVEL_OFF_FT,
      CRUISE_MPH,
      GLIDE_RATIO_X100,
    ],
    "jenny",
  ),
  component_row("altitude", ["ft"], [0], "jenny"),
  component_row(
    "technique",
    ["loop_pull_g", "loop_top_g_x10", "roll_seconds", "stunt_ft"],
    [LOOP_PULL_G, LOOP_TOP_G_X10, ROLL_SECONDS, STUNT_FT],
    "ruth",
  ),
  component_row(
    "fares",
    ["ride_cents", "ride_min", "gas_cents_gal"],
    [RIDE_CENTS, RIDE_MIN, GAS_CENTS_GAL],
    "ruth",
  ),
  component_row("purse", ["cents"], [PURSE_START_CENTS], "ruth"),
  component_row("name", ["text"], [args.partner], "player"),
  component_row("exits", ["count"], [0], "player"),
  component_row("show", ["minutes", "ft"], [SHOW_MIN, SHOW_FT], "fair"),
  component_row("prize", ["cents"], [PRIZE_CENTS], "fair"),
  component_row("course", ["feet"], [RACE_FT], "fair"),
  component_row("vehicle", ["top_mph"], [MOTORCAR_MPH], "motorcar"),
  component_row(
    "wind",
    ["mph", "quarter"],
    [WIND_MPH, WIND_QUARTER],
    "wind",
  ),
  component_row(
    "field",
    ["miles_x10", "name"],
    [NORTH_MILES_X10, "north hayfield"],
    "north",
  ),
  component_row(
    "field",
    ["miles_x10", "name"],
    [SOUTH_MILES_X10, "south pasture"],
    "south",
  ),
];

// The lib the schedule names, compiled and run once as `ecs_step` runs it.
function lib_run() {
  const [result] = store.sql_run(world, [
    { sql: "SELECT name FROM system WHERE kind = ?", params: [LIB_KIND] },
  ]);
  if (result.rows.length !== 1) {
    throw new Error(
      `ruth_spawn needs one system of kind lib in ${world}, not` +
        ` ${JSON.stringify(result.rows)}.`,
    );
  }
  const ref = SCRIPT_PREFIX + result.rows[0][0] + SCRIPT_SUFFIX;
  const { data } = store.kv_get(ref);
  // A script over `overflow_bytes` comes back as a handle of the cache.
  if (!(data instanceof Uint8Array)) {
    throw new Error(
      `ruth_spawn reads ${ref}, the lib, as a handle of the cache and not` +
        " as its bytes, as it is over overflow_bytes.",
    );
  }
  const body = new Function("engine", "args", decoder.decode(data));
  return body(engine, {});
}

// Makes the summer's world and says the Jenny's figures from the book.
function summer_spawn() {
  const lib = lib_run();
  const say =
    `The Jenny: a Curtiss JN-4D with a ${lib.whole_text(HP)} horsepower` +
    ` OX-5, ${WING_SQFT_X100 / 100} square feet of wing, and` +
    ` ${lib.whole_text(GROSS_LB)} pounds aboard with the two of us and` +
    ` ${lib.whole_text(TANK_GAL)} gallons of gasoline. She stalls at` +
    ` ${lib.whole_text(MIN_MPH)} mph, cruises at` +
    ` ${lib.whole_text(CRUISE_MPH)} and tops out at` +
    ` ${lib.whole_text(MAX_MPH)}.`;
  store.sql_run(world, [
    ...statements,
    {
      sql:
        "INSERT INTO output (step, tick, system, text) VALUES (?, ?, ?, ?)",
      params: [0, 0, "ruth_spawn", say],
    },
  ]);
  return { say, outcome: "ready" };
}

return store.transaction_run(summer_spawn);
