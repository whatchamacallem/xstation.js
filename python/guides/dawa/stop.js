// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The tick system `dawa_stop`, kept at /_files/script/dawa_stop.js: once a
// climber other than the followed one, the holder of `ams`, breathes from a
// bottle that is empty and climbs no more, he is down, and the push stops
// where the rope stands, the camp below the top. It reckons the oxygen from
// what the ticks measured: the hour of the world's day, the litres left in
// the followed climber's bottle, the minutes of the `leg` up to the top,
// back and down to the camp below, the spare the guide carries and what a
// sick climber needs to get down. The top and the rescue cannot both
// happen, or the table is broken and it throws. The climber stops breathing
// his empty bottle and holds `down`.
//
// Args: `ecs`. Reads `breathe`, `bottle`, `climb`, `ams`, `day`, `at`,
// `camp`, `leg`, `oxygen` and `limits`; writes `breathe` and `down`. Says
// the hour, the climber down and the oxygen reckoned.

// The step's view of the world, with its lib.
const ecs = args.ecs;
const lib = ecs.lib;

// Stops the push where a climber's bottle ran dry, and reckons the oxygen left.
function push_stop() {
  const dry = ecs.rows(
    "SELECT breathe.entity AS entity FROM breathe JOIN bottle" +
      " ON bottle.entity = breathe.bottle WHERE bottle.left_l = 0" +
      " AND breathe.entity NOT IN (SELECT entity FROM climb)" +
      " AND breathe.entity NOT IN (SELECT entity FROM ams)" +
      " ORDER BY breathe.entity",
    [],
  );
  if (dry.length === 0) {
    return;
  }
  if (dry.length > 1) {
    throw new Error(
      `dawa_stop: ${dry.length} climbers ran dry, where the push stops for` +
        " one.",
    );
  }
  const fallen = dry[0].entity;
  const you = lib.row_read(
    ecs,
    "SELECT ams.entity AS entity, breathe.lpm AS lpm," +
      " bottle.left_l AS left_l FROM ams" +
      " JOIN breathe ON breathe.entity = ams.entity" +
      " JOIN bottle ON bottle.entity = breathe.bottle",
    [],
  );
  const ends = lib.route_ends(ecs);
  const here = lib.climber_camp(ecs, you.entity);
  if (here.ord !== ends.top - 1) {
    throw new Error(
      `dawa_stop: the rope stands at ${here.name}, not at the camp below the` +
        " top.",
    );
  }
  const top = lib.route_camp(ecs, ends.top);
  const legs = lib.row_read(
    ecs,
    "SELECT here.down_minutes AS down, top.up_minutes AS up," +
      " top.down_minutes AS back FROM leg AS here, leg AS top" +
      " WHERE here.entity = ? AND top.entity = ?",
    [here.entity, top.entity],
  );
  const spare = lib.row_read(
    ecs,
    "SELECT bottle.left_l AS left_l FROM bottle" +
      " JOIN limits ON limits.entity = bottle.holder",
    [],
  );
  const sick_lpm = lib.oxygen_read(ecs).sick_lpm;
  const day = lib.row_read(ecs, "SELECT minute FROM day", []);
  const round = legs.up + legs.back + legs.down;
  const needed = round * you.lpm;
  const borrowed = needed - you.left_l;
  const left = spare.left_l - borrowed;
  const teo = legs.down * sick_lpm;
  const lasts = you.left_l / you.lpm;
  if (borrowed <= 0 || left >= teo || !Number.isInteger(lasts)) {
    throw new Error(
      `dawa_stop: the spare leaves ${left} litres after the top and Teo` +
        ` needs ${teo}, so there is no stake.`,
    );
  }
  ecs.run([
    { sql: "DELETE FROM breathe WHERE entity = ?", params: [fallen] },
    { sql: "INSERT INTO down (entity) VALUES (?)", params: [fallen] },
  ]);
  ecs.say(
    `It is ${lib.clock_text(day.minute)}, the top is ` +
      `${top.altitude_m - here.altitude_m} m above, and Teo is down, his ` +
      `bottle empty. Your bottle holds ${you.left_l} litres, ` +
      `${lib.duration_text(lasts)} at ${you.lpm} litres a minute. The top ` +
      `and back down to the Col takes ${lib.duration_text(round)} and ` +
      `${needed} litres, ${borrowed} of them from Dawa's spare, which leaves ` +
      `it ${left}, and Teo needs ${teo} at ${sick_lpm} litres a minute to ` +
      "get down. Not both.",
  );
}

push_stop();
