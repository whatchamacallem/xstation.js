// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The tick system `dawa_move`, kept at /_files/script/dawa_move.js: each tick
// every climb counts down a tick, and the world's day moves on by the tick's
// minutes. A climb that ends puts its climber at the camp it climbs to,
// raises the high mark the climber holds, and ends its climb and its `busy`.
// For the climber whose head the sim follows, the holder of `ams`, a climb
// that ends higher says the arrival with the air there, then a night over
// the doctors' sleep rule without bottled oxygen, which adds a grade to the
// headache. A climb down says nothing of the air.
//
// Args: `ecs`. Reads `climb`, `at`, `camp`, `ams`, `oxygen` and the clock;
// writes `climb`, `day`, `at`, `high`, `ams` and `busy`.

// The step's view of the world, with its lib.
const ecs = args.ecs;
const lib = ecs.lib;

// The climbers whose climbs end this tick, once the countdown has run.
const ENDING = "SELECT entity FROM climb WHERE ticks_left = 0";

// Moves every climb on a tick, ending those that reach their camps.
function climbs_move() {
  const units = lib.units;
  const minutes = lib.tick_minutes(ecs);
  const floor = lib.oxygen_read(ecs).altitude_m;
  const arriving = ecs.rows(
    "SELECT climb.entity AS entity, here.altitude_m AS from_m," +
      " there.place AS place, there.altitude_m AS to_m FROM climb" +
      " JOIN ams ON ams.entity = climb.entity" +
      " JOIN at ON at.entity = climb.entity" +
      " JOIN camp AS here ON here.entity = at.camp" +
      " JOIN camp AS there ON there.entity = climb.to_camp" +
      " WHERE climb.ticks_left = 1 ORDER BY climb.entity",
    [],
  );
  const said = [];
  const statements = [
    { sql: "UPDATE climb SET ticks_left = ticks_left - 1", params: [] },
    {
      sql: "UPDATE day SET minute = (minute + ?) % ?",
      params: [minutes, units.hours_per_day * units.minutes_per_hour],
    },
  ];
  for (const climber of arriving) {
    if (climber.to_m <= climber.from_m) {
      continue;
    }
    said.push(lib.air_text(lib.sentence_start(climber.place), climber.to_m));
    const bottled = climber.to_m >= floor;
    const night = lib.night_text(climber.from_m, climber.to_m, bottled);
    if (night !== null) {
      said.push(night);
      statements.push({
        sql: "UPDATE ams SET grade = grade + 1 WHERE entity = ?",
        params: [climber.entity],
      });
    }
  }
  statements.push(
    {
      sql:
        "UPDATE high SET m = MAX(m, (SELECT camp.altitude_m FROM climb" +
        " JOIN camp ON camp.entity = climb.to_camp" +
        ` WHERE climb.entity = high.entity)) WHERE entity IN (${ENDING})`,
      params: [],
    },
    {
      sql:
        "UPDATE at SET camp = (SELECT to_camp FROM climb" +
        ` WHERE climb.entity = at.entity) WHERE entity IN (${ENDING})`,
      params: [],
    },
    { sql: `DELETE FROM busy WHERE entity IN (${ENDING})`, params: [] },
    { sql: "DELETE FROM climb WHERE ticks_left = 0", params: [] },
  );
  ecs.run(statements);
  if (said.length > 0) {
    ecs.say(said.join(" "));
  }
}

climbs_move();
