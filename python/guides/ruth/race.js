// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The step system `ruth_race`, kept at /_files/script/ruth_race.js: takes the
// player's intent `race`, its value the throttle, `full throttle` or `cruise`,
// and starts the race down the county road, into the wind, at the book's
// leveling off height. The aircraft races at the throttle's airspeed less the
// wind over the road, its throttle kept for the log, and every vehicle at its
// top speed; each racer starts busy, so the step ticks until ruth_drive has
// brought both to the course's end and ruth_finish says the result and logs
// the beat. It says the race's start, ending in a comma, as the finish goes on.
//
// Args: `ecs`. Reads `airframe`, `altitude`, `wind` and `vehicle`; writes
// `altitude`, `racer`, `throttle` and `busy`.

// The step's view of the world, and the lib.
const ecs = args.ecs;
const lib = ecs.lib;

// The throttles by the choice's text: the words and the book figure flown.
const THROTTLES = Object.freeze({
  "full throttle": { name: "Full throttle", figure: "max_mph" },
  cruise: { name: "Cruise", figure: "cruise_mph" },
});

// The player's intent to race, or null when none waits this step.
const intent = ecs.take("race");
if (intent === null) {
  return;
}
const throttle = lib.choice_get(THROTTLES, intent.value);
const aircraft = lib.aircraft_read(ecs);
const wind = lib.wind_read(ecs);
const mph = aircraft[throttle.figure];
const ground = mph - wind.mph;
ecs.run([
  {
    sql: "UPDATE altitude SET ft = ? WHERE entity = ?",
    params: [aircraft.level_off_ft, aircraft.entity],
  },
  {
    sql:
      "INSERT INTO racer (entity, ground_mph, feet, ticks)" +
      " VALUES (?, ?, 0, 0)",
    params: [aircraft.entity, ground],
  },
  {
    sql:
      "INSERT INTO racer (entity, ground_mph, feet, ticks)" +
      " SELECT entity, top_mph, 0, 0 FROM vehicle ORDER BY entity",
    params: [],
  },
  {
    sql: "INSERT INTO throttle (entity, setting) VALUES (?, ?)",
    params: [aircraft.entity, intent.value],
  },
  {
    sql: "INSERT INTO busy (entity) SELECT entity FROM racer ORDER BY entity",
    params: [],
  },
]);
ecs.say(
  `${throttle.name}: ${mph} mph into a ${wind.mph} mph wind is ${ground}` +
    ` over the road,`,
);
