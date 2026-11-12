// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The step system `ruth_exit`, kept at /_files/script/ruth_exit.js: takes the
// player's intent `exit`, Ruth's promise to set her down like a feather. It
// counts the exit on the player's `exits`; on the grass it says so, outcome
// grounded; aloft it glides with the throttle closed at the cruise, a foot
// down for every glide ratio's feet on, sets the aircraft on the grass and
// keeps the height left in its `resume`, outcome landed. It logs the beat
// exit, choice the intent's value.
//
// Args: `ecs`. Reads `airframe`, `altitude` and `exits`; writes `altitude`,
// `resume` and `exits`.

// The step's view of the world, and the lib.
const ecs = args.ecs;
const lib = ecs.lib;

// The player's intent to come down, or null when none waits this step.
const intent = ecs.take("exit");
if (intent === null) {
  return;
}
const aircraft = lib.aircraft_read(ecs);
const height = aircraft.ft;
// The exit is counted on the entity whose intent it was.
const counted = {
  sql: "UPDATE exits SET count = count + 1 WHERE entity = ?",
  params: [intent.entity],
};
if (height === 0) {
  ecs.run([counted]);
  ecs.say("We're on the grass already.");
  ecs.log("exit", intent.value, "grounded");
  return;
}
const speed = lib.speed_feet(aircraft.cruise_mph);
const distance = height * aircraft.glide_ratio;
const sink = speed / aircraft.glide_ratio;
const seconds = Math.round(distance / speed);
ecs.run([
  counted,
  {
    sql: "UPDATE altitude SET ft = 0 WHERE entity = ?",
    params: [aircraft.entity],
  },
  {
    sql:
      "INSERT INTO resume (entity, ft) VALUES (?, ?)" +
      " ON CONFLICT (entity) DO UPDATE SET ft = excluded.ft",
    params: [aircraft.entity, height],
  },
]);
ecs.say(
  `Throttle closed at ${height} feet. Gliding at ${aircraft.cruise_mph} mph,` +
    ` ${aircraft.glide_ratio} feet on for every foot down, she sinks` +
    ` ${lib.tenths_text(sink)} feet a second and settles onto the grass` +
    ` ${lib.whole_text(distance)} feet on, in ${lib.clock_text(seconds)},` +
    ` like a feather.`,
);
ecs.log("exit", intent.value, "landed");
