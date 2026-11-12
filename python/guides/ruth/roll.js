// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The step system `ruth_roll`, kept at /_files/script/ruth_roll.js: takes the
// player's intent `roll`, its value the degrees of nose up, and rolls at the
// book's top speed, weightless for the pilot's count: the height changes by
// V sin(nose) T less g T squared over 2, in whole feet. A roll that would
// bring her out under the book's leveling off is not flown: Ruth climbs her
// back to where she teaches at the book's rate, outcome low. Otherwise the
// outcome is sank, with the nose that keeps the height, or made, each logged
// as the beat roll.
//
// Args: `ecs`. Reads `airframe`, `altitude` and `technique`; writes
// `altitude`.

// The step's view of the world, and the lib.
const ecs = args.ecs;
const lib = ecs.lib;

// The player's intent to roll, or null when none waits this step.
const intent = ecs.take("roll");
if (intent === null) {
  return;
}
const nose = lib.whole_value(intent.value);
const aircraft = lib.aircraft_read(ecs);
const pilot = lib.pilot_read(ecs);
const count = pilot.roll_seconds;
const speed = lib.speed_feet(aircraft.max_mph);
const fall = (lib.G * count * count) / 2;
const rise = speed * Math.sin(nose * lib.RADIANS_PER_DEGREE) * count;
const change = rise - fall;
const moved = Math.round(change);
const wanted =
  Math.asin((lib.G * count) / (2 * speed)) / lib.RADIANS_PER_DEGREE;
if (change < 0 && aircraft.ft + moved < aircraft.level_off_ft) {
  const cost = lib.climb_cost(aircraft, aircraft.ft, pilot.stunt_ft);
  ecs.run([
    {
      sql: "UPDATE altitude SET ft = ? WHERE entity = ?",
      params: [pilot.stunt_ft, aircraft.entity],
    },
  ]);
  ecs.say(
    `At ${aircraft.ft} feet, nose ${lib.count_text(nose, "degree", "degrees")} up at ${aircraft.max_mph}` +
      ` mph and ${count} seconds round would bring her out ${lib.count_text(-moved, "foot", "feet")}` +
      ` low, under the ${aircraft.level_off_ft} feet the book gives for` +
      ` leveling off. Ruth takes the stick and climbs her back up to` +
      ` ${pilot.stunt_ft} feet in ${lib.whole_text(cost.minutes)} minutes,` +
      ` on ${lib.tenths_text(cost.gallons)} gallons of gasoline.`,
  );
  ecs.log("roll", intent.value, "low");
  return;
}
ecs.run([
  {
    sql: "UPDATE altitude SET ft = ft + ? WHERE entity = ?",
    params: [moved, aircraft.entity],
  },
]);
const opening =
  `Nose ${lib.count_text(nose, "degree", "degrees")} up at ${aircraft.max_mph} mph and ${count}` +
  ` seconds round: she comes out`;
if (change < 0) {
  ecs.say(
    `${opening} ${lib.count_text(-moved, "foot", "feet")} low. A roll at ${aircraft.max_mph} wants` +
      ` ${lib.whole_text(wanted)} degrees of nose to keep her height.`,
  );
  ecs.log("roll", intent.value, "sank");
  return;
}
ecs.say(`${opening} ${lib.count_text(moved, "foot", "feet")} high. A roll.`);
ecs.log("roll", intent.value, "made");
