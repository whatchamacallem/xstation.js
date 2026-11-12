// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The step system `ruth_buzz`, kept at /_files/script/ruth_buzz.js: takes the
// player's intent `buzz`, its value the height in feet, and buzzes Main Street
// at the book's top speed, refusing a height under the book's leveling off
// and one above the height she flies, as a buzz goes down to the street.
// Outcome refused or made, logged as the beat buzz.
//
// Args: `ecs`. Reads `airframe` and `altitude`; writes `altitude`.

// The step's view of the world, and the lib.
const ecs = args.ecs;
const lib = ecs.lib;

// The player's intent to buzz the street, or null when none waits this step.
const intent = ecs.take("buzz");
if (intent === null) {
  return;
}
const feet = lib.whole_value(intent.value);
const aircraft = lib.aircraft_read(ecs);
if (feet < aircraft.level_off_ft) {
  ecs.say(
    `Under the ${aircraft.level_off_ft} feet the book gives for leveling` +
      ` off? I'm bold. I'm not stupid.`,
  );
  ecs.log("buzz", intent.value, "refused");
  return;
}
if (feet > aircraft.ft) {
  ecs.say(
    `Down to ${lib.count_text(feet, "foot", "feet")}, when we're flying at ${aircraft.ft}? That's a` +
      ` climb, not a buzz.`,
  );
  ecs.log("buzz", intent.value, "refused");
  return;
}
ecs.run([
  {
    sql: "UPDATE altitude SET ft = ? WHERE entity = ?",
    params: [feet, aircraft.entity],
  },
]);
ecs.say(
  `Down Main Street at ${feet} feet and ${aircraft.max_mph} mph,` +
    ` ${lib.whole_text(lib.speed_feet(aircraft.max_mph))} feet a second, and` +
    ` the handbills go over the side.`,
);
ecs.log("buzz", intent.value, "made");
