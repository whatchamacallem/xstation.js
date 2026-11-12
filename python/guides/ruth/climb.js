// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The step system `ruth_climb`, kept at /_files/script/ruth_climb.js: takes
// the player's intent `climb` and climbs the aircraft at the book's rate from
// its height to where its pilot teaches, saying the minutes, the rate and the
// gasoline. It logs the beat climb, choice the intent's value, outcome made.
//
// Args: `ecs`. Reads `airframe`, `altitude` and `technique`; writes
// `altitude`.

// The step's view of the world, and the lib.
const ecs = args.ecs;
const lib = ecs.lib;

// The player's intent to climb, or null when none waits this step.
const intent = ecs.take("climb");
if (intent === null) {
  return;
}
const aircraft = lib.aircraft_read(ecs);
const pilot = lib.pilot_read(ecs);
const cost = lib.climb_cost(aircraft, aircraft.ft, pilot.stunt_ft);
ecs.run([
  {
    sql: "UPDATE altitude SET ft = ? WHERE entity = ?",
    params: [pilot.stunt_ft, aircraft.entity],
  },
]);
ecs.say(
  `Up to ${pilot.stunt_ft} feet in ${lib.whole_text(cost.minutes)} minutes,` +
    ` the book's ${lib.whole_text(cost.rate)} feet a minute, on` +
    ` ${lib.tenths_text(cost.gallons)} gallons of gasoline.`,
);
ecs.log("climb", intent.value, "made");
