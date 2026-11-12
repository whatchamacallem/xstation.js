// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The spawn of Dawa's climb, `dawa_spawn`, kept at
// /_files/script/dawa_spawn.js and run once by the build turn, after ecs_init
// made the core tables and the table's SQL made the components and the
// schedule of `system`. It runs the lib the schedule names once, as ecs_step
// runs it, the one script it runs, for its say: the air at Base Camp, where
// the rope of you, Dawa and Teo starts. Then it makes every entity and
// component row of the climb from the constants of the guide's world, each
// with the one line comment naming its source, the clock of the entity world
// and its say as one row of `output` at step 0, in one sql_run and so one
// push.
//
// Args: `world`, the world database. Returns `say`, the air at Base Camp, and
// `outcome`, `ready`.

// The store of the AI worker the script works through.
const store = engine.store;

// The start and the end of the key of a script's text.
const SCRIPT_PREFIX = "/_files/script/";
const SCRIPT_SUFFIX = ".js";

// The kind of the system of the schedule that is the lib.
const LIB_KIND = "lib";

// Reads a script's bytes as text, refusing any that are not `UTF-8`.
const decoder = new TextDecoder("utf-8", { fatal: true });

// The seconds a tick of the clock stands for: half an hour, the guide's world.
const TICK_SECONDS = 1800;

// The most ticks one step may run: a day of half hours, longer than any climb of the route, a game rule.
const TICKS_MAX = 48;

// The entities of the climb, in the order they are made.
const ENTITIES = Object.freeze([
  "world",
  "player",
  "dawa",
  "teo",
  "base_camp",
  "camp_1",
  "camp_2",
  "camp_3",
  "camp_4",
  "south_summit",
  "summit",
  "player_bottle",
  "teo_bottle",
  "spare",
  "forecast_1",
  "forecast_3",
]);

// The camps of the South Col route, their heights in metres as commonly given, and the way up to each.
const CAMPS = Object.freeze([
  Object.freeze({
    entity: "base_camp",
    name: "Base Camp",
    place: "Base Camp",
    m: 5364,
    way: "the Khumbu Glacier",
  }),
  Object.freeze({
    entity: "camp_1",
    name: "Camp 1",
    place: "Camp 1",
    m: 6065,
    way: "the Khumbu Icefall",
  }),
  Object.freeze({
    entity: "camp_2",
    name: "Camp 2",
    place: "Camp 2",
    m: 6400,
    way: "the Western Cwm",
  }),
  Object.freeze({
    entity: "camp_3",
    name: "Camp 3",
    place: "Camp 3",
    m: 7162,
    way: "the Lhotse Face",
  }),
  Object.freeze({
    entity: "camp_4",
    name: "Camp 4",
    place: "Camp 4 on the South Col",
    m: 7906,
    way: "the Geneva Spur",
  }),
  Object.freeze({
    entity: "south_summit",
    name: "South Summit",
    place: "the South Summit",
    m: 8749,
    way: "the Southeast Ridge",
  }),
]);

// The top in metres: 8848.86 m by the survey Nepal and China announced on 8 December 2020, rounded, up the summit ridge.
const SUMMIT = Object.freeze({
  entity: "summit",
  name: "Summit",
  place: "the top",
  m: 8849,
  way: "the summit ridge",
});

// The South Summit is five hours up from Camp 4, from 23:00 to 4:00, and 270 minutes down to it, the guide's world.
const SOUTH_SUMMIT_LEG = Object.freeze({ up: 300, down: 270 });

// The top is 90 minutes up from the South Summit and 60 back down to it, the guide's world.
const SUMMIT_LEG = Object.freeze({ up: 90, down: 60 });

// The summit push leaves Camp 4 at 23:00, the guide's world.
const DEPARTURE_HOUR = 23;

// Dawa's rope takes 6 hours through the icefall, and the sun loosens its ice at 9:00, the guide's world.
const ICEFALL = Object.freeze({ hours: 6, sun_hour: 9 });

// The camp where the rope waits for its weather window, the guide's world.
const STAGING_CAMP = "camp_2";

// The camp from which the rope breathes bottled oxygen, the guide's world.
const OXYGEN_CAMP = "camp_3";

// The litres a minute of a climber on bottled oxygen and of a sick one, the guide's world.
const FLOW = Object.freeze({ climb_lpm: 2, sick_lpm: 4 });

// Dawa's limits, a new climber's load in kg and the wind on the summit in km/h, his rules in the guide's world.
const LIMITS = Object.freeze({ load_kg: 12, wind_kmh: 40 });

// Dawa's record of never leaving anyone behind, kept until it is broken.
const RECORD = "kept";

// The expedition's gear for the high camps in kg, the guide's world.
const KIT = Object.freeze({ tent_kg: 4, stove_kg: 2, food_kg: 3 });

// A bottle's litres and its weight in kg, the guide's world.
const BOTTLE = Object.freeze({ litres: 1200, kg: 3 });

// The bottles of the climb and who carries each: yours, the spare you pack, and Teo's, the guide's world.
const BOTTLES = Object.freeze([
  Object.freeze({ entity: "player_bottle", holder: "player" }),
  Object.freeze({ entity: "teo_bottle", holder: "teo" }),
  Object.freeze({ entity: "spare", holder: "player" }),
]);

// Each climber breathes from his own bottle: you at a climber's flow, and Teo, whom the altitude takes on the push, at a sick one's, the guide's world.
const BREATHERS = Object.freeze([
  Object.freeze({ entity: "player", bottle: "player_bottle", sick: false }),
  Object.freeze({ entity: "teo", bottle: "teo_bottle", sick: true }),
]);

// The radio forecast of the wind on the summit in km/h by the days ahead, the guide's world.
const FORECASTS = Object.freeze([
  Object.freeze({ entity: "forecast_1", days: 1, kmh: 45 }),
  Object.freeze({ entity: "forecast_3", days: 3, kmh: 25 }),
]);

// The climbers of the rope, who start at the bottom of the route: you, Dawa and Teo.
const ROPE = Object.freeze(["player", "dawa", "teo"]);

// The world database, which the args must name.
if (typeof args.world !== "string" || args.world === "") {
  throw new Error(
    `dawa_spawn takes world as the name of a database, not` +
      ` ${JSON.stringify(args.world)}.`,
  );
}
const world = args.world;

// A field that holds the id of the entity of the name.
function entity_ref(name) {
  return Object.freeze({ entity: name });
}

// A statement that adds a component row to the entity of the name, each field a value or the id an `entity_ref` names.
function component_add(table, name, fields) {
  const columns = Object.keys(fields);
  const marks = columns.map((column) =>
    typeof fields[column] === "object"
      ? "(SELECT id FROM entity WHERE name = ?)"
      : "?",
  );
  const params = columns.map((column) =>
    typeof fields[column] === "object" ? fields[column].entity : fields[column],
  );
  return {
    sql:
      `INSERT INTO ${table} (entity, ${columns.join(", ")})` +
      ` SELECT id, ${marks.join(", ")} FROM entity WHERE name = ?`,
    params: [...params, name],
  };
}

// The statements of every entity and component row of the climb, in order.
function climb_statements() {
  const route = [...CAMPS, SUMMIT];
  const base = route[0];
  const statements = [
    {
      sql:
        "INSERT INTO entity (name) VALUES " +
        ENTITIES.map(() => "(?)").join(", "),
      params: [...ENTITIES],
    },
    component_add("clock", "world", {
      step: 0,
      tick: 0,
      tick_seconds: TICK_SECONDS,
      ticks_max: TICKS_MAX,
    }),
  ];
  route.forEach((camp, index) => {
    statements.push(
      component_add("camp", camp.entity, {
        name: camp.name,
        place: camp.place,
        altitude_m: camp.m,
        ord: index + 1,
        way: camp.way,
      }),
    );
  });
  statements.push(
    component_add("leg", "south_summit", {
      up_minutes: SOUTH_SUMMIT_LEG.up,
      down_minutes: SOUTH_SUMMIT_LEG.down,
    }),
    component_add("leg", SUMMIT.entity, {
      up_minutes: SUMMIT_LEG.up,
      down_minutes: SUMMIT_LEG.down,
    }),
    component_add("sun", "world", { loosen_hour: ICEFALL.sun_hour }),
    component_add("icefall", "world", { hours: ICEFALL.hours }),
    component_add("staging", "world", { camp: entity_ref(STAGING_CAMP) }),
    component_add("oxygen", "world", {
      camp: entity_ref(OXYGEN_CAMP),
      climb_lpm: FLOW.climb_lpm,
      sick_lpm: FLOW.sick_lpm,
    }),
    component_add("kit", "world", {
      tent_kg: KIT.tent_kg,
      stove_kg: KIT.stove_kg,
      food_kg: KIT.food_kg,
    }),
    component_add("departure", "world", { hour: DEPARTURE_HOUR }),
  );
  for (const climber of ROPE) {
    statements.push(
      component_add("at", climber, { camp: entity_ref(base.entity) }),
    );
  }
  statements.push(
    component_add("ams", "player", { grade: 0, hidden: 0 }),
    component_add("rest", "player", { days: 0 }),
    component_add("load", "player", { kg: 0 }),
    component_add("high", "player", { m: base.m }),
    component_add("exits", "player", { count: 0 }),
    component_add("limits", "dawa", {
      load_kg: LIMITS.load_kg,
      wind_kmh: LIMITS.wind_kmh,
    }),
    component_add("record", "dawa", { text: RECORD }),
  );
  for (const bottle of BOTTLES) {
    statements.push(
      component_add("bottle", bottle.entity, {
        full_l: BOTTLE.litres,
        left_l: BOTTLE.litres,
        kg: BOTTLE.kg,
        holder: entity_ref(bottle.holder),
      }),
    );
  }
  for (const breather of BREATHERS) {
    statements.push(
      component_add("breathe", breather.entity, {
        lpm: breather.sick ? FLOW.sick_lpm : FLOW.climb_lpm,
        bottle: entity_ref(breather.bottle),
      }),
    );
  }
  for (const forecast of FORECASTS) {
    statements.push(
      component_add("forecast", forecast.entity, {
        days_ahead: forecast.days,
        kmh: forecast.kmh,
      }),
    );
  }
  return statements;
}

// The text of a thrown value: its stack when it is an `Error`.
function thrown_text(thrown) {
  return thrown instanceof Error ? String(thrown.stack) : String(thrown);
}

// The lib the schedule names, compiled and run once as `ecs_step` runs it, its value a frozen object.
function lib_run() {
  const [result] = store.sql_run(world, [
    { sql: "SELECT name FROM system WHERE kind = ?", params: [LIB_KIND] },
  ]);
  if (result.rows.length !== 1) {
    throw new Error(
      `dawa_spawn needs one system of kind lib in ${world}, not` +
        ` ${JSON.stringify(result.rows)}.`,
    );
  }
  const name = result.rows[0][0];
  const ref = SCRIPT_PREFIX + name + SCRIPT_SUFFIX;
  const { data } = store.kv_get(ref);
  // A script over `overflow_bytes` comes back as a handle of the cache.
  if (!(data instanceof Uint8Array)) {
    throw new Error(
      `dawa_spawn reads ${ref}, the script of the lib ${name}, as a handle` +
        " of the cache and not as its bytes, as it is over overflow_bytes.",
    );
  }
  let body;
  try {
    body = new Function("engine", "args", decoder.decode(data));
  } catch (thrown) {
    throw new Error(
      `dawa_spawn cannot compile ${ref}, the script of the lib ${name}:` +
        ` ${thrown_text(thrown)}`,
      { cause: thrown },
    );
  }
  let value;
  try {
    value = body(engine, {});
  } catch (thrown) {
    throw new Error(
      `dawa_spawn ran the lib ${name} of ${world}, which threw` +
        ` ${thrown_text(thrown)}`,
      { cause: thrown },
    );
  }
  if (typeof value !== "object" || value === null) {
    throw new Error(
      `dawa_spawn ran the lib ${name} of ${world}, which returned` +
        ` ${value === null ? "null" : typeof value}, not a frozen object.`,
    );
  }
  if (!Object.isFrozen(value)) {
    throw new Error(
      `dawa_spawn ran the lib ${name} of ${world}, which returned an object` +
        " not frozen.",
    );
  }
  return value;
}

// Makes the climb and says the air at the camp where the rope starts.
function climb_spawn() {
  const lib = lib_run();
  const base = CAMPS[0];
  const say = lib.air_text(base.place, base.m);
  store.sql_run(world, [
    ...climb_statements(),
    {
      sql:
        "INSERT INTO output (step, tick, system, text) VALUES (?, ?, ?, ?)",
      params: [0, 0, "dawa_spawn", say],
    },
  ]);
  return { say, outcome: "ready" };
}

return store.transaction_run(climb_spawn);
