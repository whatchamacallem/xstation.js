// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The tick system `ruth_finish`, kept at /_files/script/ruth_finish.js: once
// every racer has reached the course's end and none is busy, says the course
// in miles, the aircraft's time and the vehicle's, each its ticks times the
// clock's seconds a tick, then the result: an aircraft home first wins the
// fair's prize into the purse, outcome won; one home last loses, outcome
// lost; both home at once is a dead heat, outcome tied; each logged as the
// beat race with the throttle as its choice. It then removes each `racer` and
// `throttle`. While a racer is busy, or with no race, it does nothing.
//
// Args: `ecs`. Reads `racer`, `busy`, `airframe`, `throttle`, `vehicle`,
// `course`, `prize`, `purse` and `clock`; writes `purse`, `racer` and
// `throttle`.

// The tick's view of the world, and the lib.
const ecs = args.ecs;
const lib = ecs.lib;

// The racers, and those of them still busy.
const racers = ecs.rows("SELECT entity AS entity FROM racer", []);
const racing = ecs.rows(
  "SELECT racer.entity AS entity FROM racer" +
    " JOIN busy ON busy.entity = racer.entity",
  [],
);
if (racers.length === 0 || racing.length > 0) {
  return;
}
const plane = lib.sole_row(
  ecs.rows(
    "SELECT racer.ticks AS ticks, throttle.setting AS setting FROM racer" +
      " JOIN airframe ON airframe.entity = racer.entity" +
      " JOIN throttle ON throttle.entity = racer.entity",
    [],
  ),
  "the racing aircraft",
);
const car = lib.sole_row(
  ecs.rows(
    "SELECT racer.ticks AS ticks, racer.ground_mph AS ground_mph FROM racer" +
      " JOIN vehicle ON vehicle.entity = racer.entity",
    [],
  ),
  "the racing vehicle",
);
const course = lib.sole_row(
  ecs.rows("SELECT feet AS feet FROM course", []),
  "course",
);
const prize = lib.sole_row(
  ecs.rows("SELECT cents AS cents FROM prize", []),
  "prize",
);
const purse = lib.sole_row(
  ecs.rows("SELECT entity AS entity, cents AS cents FROM purse", []),
  "purse",
);
const clock = lib.sole_row(
  ecs.rows("SELECT tick_seconds AS tick_seconds FROM clock", []),
  "clock",
);
const flown = plane.ticks * clock.tick_seconds;
const driven = car.ticks * clock.tick_seconds;
// The race's rows go once it is said.
const ended = [
  {
    sql: "DELETE FROM throttle WHERE entity IN (SELECT entity FROM racer)",
    params: [],
  },
  { sql: "DELETE FROM racer", params: [] },
];
ecs.say(
  `${lib.tenths_text(course.feet / lib.FEET_PER_MILE)} miles in` +
    ` ${lib.clock_text(flown)}. The motorcar at ${car.ground_mph} takes` +
    ` ${lib.clock_text(driven)}.`,
);
if (flown < driven) {
  ecs.run([
    {
      sql: "UPDATE purse SET cents = cents + ? WHERE entity = ?",
      params: [prize.cents, purse.entity],
    },
    ...ended,
  ]);
  ecs.say(
    `You win by ${lib.clock_text(driven - flown)} and the fair's` +
      ` ${lib.money_text(prize.cents)} purse:` +
      ` ${lib.money_text(purse.cents + prize.cents)} in the cigar box.`,
  );
  ecs.log("race", plane.setting, "won");
  return;
}
ecs.run(ended);
if (flown > driven) {
  ecs.say(
    `The motorcar wins by ${lib.clock_text(flown - driven)}, and the fair` +
      ` keeps its ${lib.money_text(prize.cents)} purse.`,
  );
  ecs.log("race", plane.setting, "lost");
  return;
}
ecs.say(
  `A dead heat, and the fair keeps its ${lib.money_text(prize.cents)} purse.`,
);
ecs.log("race", plane.setting, "tied");
