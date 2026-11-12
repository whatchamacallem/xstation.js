// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The step system `dawa_loads`, kept at /_files/script/dawa_loads.js: takes
// the intent `loads`, its value `everything` or `one bottle`, at the staging
// camp: the expedition's kit and either every bottle the player holds or the
// one the player breathes from. A load over Dawa's limit is refused, an
// outcome; a load within it is packed, the bottles left go to Dawa, and the
// rope climbs at once, its time stated by no band, two camps up, with the air
// at the higher and a night over the sleep rule at either, then is on oxygen
// for the push, which leaves at the hour of `departure`.
//
// Args: `ecs`. Reads `at`, `camp`, `staging`, `kit`, `limits`, `bottle`,
// `breathe`, `oxygen` and `departure`; writes `load`, `bottle`, `ams`, `at`
// and `high`. Says the load, and logs the beat `loads` with the value and
// `refused` or `carried`.

// The step's view of the world, with its lib.
const ecs = args.ecs;
const lib = ecs.lib;

// The values of the intent, what the player carries.
const EVERYTHING = "everything";
const ONE_BOTTLE = "one bottle";

// The count, weight and weight each of the bottles the player would carry.
function bottles_read(carry, player) {
  const breathed =
    carry === ONE_BOTTLE
      ? " AND entity IN (SELECT bottle FROM breathe WHERE entity = ?)"
      : "";
  const bottles = lib.row_read(
    ecs,
    "SELECT COUNT(*) AS count, SUM(kg) AS kg, MIN(kg) AS least," +
      " MAX(kg) AS most FROM bottle WHERE holder = ?" +
      breathed,
    carry === ONE_BOTTLE ? [player, player] : [player],
  );
  if (bottles.count === 0 || bottles.least !== bottles.most) {
    throw new Error(
      `dawa_loads: the bottles carried, ${JSON.stringify(bottles)}, are` +
        " none or of more than one weight.",
    );
  }
  return bottles;
}

// Packs the loads for the high camps, refused over Dawa's limit, else up to the camp the push leaves from.
function loads_pack(intent) {
  const carry = intent.value;
  if (carry !== EVERYTHING && carry !== ONE_BOTTLE) {
    throw new Error(
      `dawa_loads: the value ${JSON.stringify(carry)} is neither` +
        ` ${EVERYTHING} nor ${ONE_BOTTLE}.`,
    );
  }
  const player = intent.entity;
  const here = lib.climber_camp(ecs, player);
  const staging = lib.row_read(ecs, "SELECT camp FROM staging", []);
  if (here.entity !== staging.camp) {
    throw new Error(
      `dawa_loads: the rope is at ${here.name}, not at the staging camp.`,
    );
  }
  const kit = lib.row_read(
    ecs,
    "SELECT tent_kg, stove_kg, food_kg FROM kit",
    [],
  );
  const guide = lib.row_read(
    ecs,
    "SELECT entity, load_kg FROM limits",
    [],
  );
  const held = lib.row_read(
    ecs,
    "SELECT COUNT(*) AS count FROM bottle WHERE holder = ?",
    [player],
  );
  const bottles = bottles_read(carry, player);
  const kg = kit.tent_kg + kit.stove_kg + kit.food_kg + bottles.kg;
  const carried = lib.count_text(bottles.count, "bottle", "bottles");
  if (kg > guide.load_kg) {
    const what = carry === EVERYTHING ? "Everything" : "That";
    ecs.say(
      `${what} is the tent at ${kit.tent_kg} kg, the stove at ` +
        `${kit.stove_kg}, food at ${kit.food_kg} and ${carried} at ` +
        `${bottles.least} each: ${kg} kg, over the ${guide.load_kg} Dawa ` +
        "lets a new climber carry.",
    );
    ecs.log("loads", carry, "refused");
    return;
  }
  const high = lib.route_camp(ecs, here.ord + 1);
  const col = lib.route_camp(ecs, here.ord + 2);
  const oxygen = lib.oxygen_read(ecs);
  const departure = lib.row_read(ecs, "SELECT hour FROM departure", []);
  const handed = held.count - bottles.count;
  const statements = [
    {
      sql: "UPDATE load SET kg = ? WHERE entity = ?",
      params: [kg, player],
    },
  ];
  if (handed > 0) {
    statements.push({
      sql:
        "UPDATE bottle SET holder = ? WHERE holder = ? AND entity NOT IN" +
        " (SELECT bottle FROM breathe WHERE entity = ?)",
      params: [guide.entity, player, player],
    });
  }
  const said = [
    `The tent, the stove, food and ${carried}: ${kg} kg, within Dawa's ` +
      `${guide.load_kg}${handed > 0 ? ", and he carries the spare" : ""}.`,
    `Up ${high.way} to ${high.name} at ${high.altitude_m} m, then to ` +
      lib.air_text(col.place, col.altitude_m),
  ];
  let gained = 0;
  for (const [from, to] of [
    [here, high],
    [high, col],
  ]) {
    const bottled = to.altitude_m >= oxygen.altitude_m;
    const night = lib.night_text(from.altitude_m, to.altitude_m, bottled);
    if (night !== null) {
      gained += 1;
      said.push(night);
    }
    statements.push(...lib.rope_move(from.entity, to.entity));
  }
  if (gained > 0) {
    statements.push({
      sql: "UPDATE ams SET grade = grade + ? WHERE entity = ?",
      params: [gained, player],
    });
  }
  said.push(
    `On oxygen from ${oxygen.name} up; we leave at ` +
      `${lib.hour_text(departure.hour)} for the top.`,
  );
  ecs.run(statements);
  ecs.say(said.join(" "));
  ecs.log("loads", carry, "carried");
}

const intent = ecs.take("loads");
if (intent !== null) {
  loads_pack(intent);
}
