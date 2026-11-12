// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The step system `ruth_roll`, kept at /_files/script/ruth_roll.js: takes the
// player's intent `roll`, its value the degrees of nose up, and rolls at the
// book's top speed, weightless for the pilot's count: the height changes by
// V sin(nose) T less g T squared over 2, in whole feet. Outcome sank, with the
// nose that keeps the height, or made, logged as the beat roll.
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
ecs.run([
  {
    sql: "UPDATE altitude SET ft = ft + ? WHERE entity = ?",
    params: [moved, aircraft.entity],
  },
]);
const opening =
  `Nose ${nose} degrees up at ${aircraft.max_mph} mph and ${count}` +
  ` seconds round: she comes out`;
if (change < 0) {
  ecs.say(
    `${opening} ${-moved} feet low. A roll at ${aircraft.max_mph} wants` +
      ` ${lib.whole_text(wanted)} degrees of nose to keep her height.`,
  );
  ecs.log("roll", intent.value, "sank");
  return;
}
ecs.say(`${opening} ${moved} feet high. A roll.`);
ecs.log("roll", intent.value, "made");
