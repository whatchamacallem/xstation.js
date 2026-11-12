// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The step system `ruth_field`, kept at /_files/script/ruth_field.js: takes
// the player's intent `field`, its value the heading of a field, the name of
// its entity, `north` or `south`, and glides for it with the engine dead at
// the cruise: the aircraft's height times the glide ratio in still air, over
// the ground times (V - W) / V into the wind or (V + W) / V with it, in whole
// feet. Outcome short or reached by the field's distance; on the grass
// already, set down by an exit, it says so, outcome reached, as no glide is
// left to fly. Logged as the beat field.
//
// Args: `ecs`. Reads `field`, `airframe`, `altitude` and `wind`; writes
// nothing but its say and beat.

// The step's view of the world, and the lib.
const ecs = args.ecs;
const lib = ecs.lib;

// The player's intent to glide for a field, or null when none waits.
const intent = ecs.take("field");
if (intent === null) {
  return;
}
const choice = intent.value;
const field = lib.sole_row(
  lib.fields_read(ecs).filter((place) => place.heading === choice),
  `the field ${JSON.stringify(choice)}`,
);
const aircraft = lib.aircraft_read(ecs);
const wind = lib.wind_read(ecs);
// The ways a heading meets the wind: into it, or with it from behind.
const ways = {
  [wind.quarter]: { word: "into", sign: -1 },
  [lib.choice_get(lib.OPPOSITE, wind.quarter)]: { word: "with", sign: 1 },
};
const way = lib.choice_get(ways, choice);
const height = aircraft.ft;
if (height === 0) {
  ecs.say(
    `She's on the grass already, where Ruth set her down, so there's no` +
      ` glide left to fly for the ${field.called}.`,
  );
  ecs.log("field", intent.value, "reached");
  return;
}
const cruise = aircraft.cruise_mph;
const ground = cruise + way.sign * wind.mph;
const reach = Math.round((height * aircraft.glide_ratio * ground) / cruise);
const margin = reach - Math.round(field.miles * lib.FEET_PER_MILE);
const opening =
  `Gliding ${choice} ${way.word} the wind at ${ground} mph over the ground,` +
  ` ${height} feet carries you ${reach} feet,` +
  ` ${lib.tenths_text(reach / lib.FEET_PER_MILE)} miles, and the` +
  ` ${field.called} is ${lib.tenths_text(field.miles)} miles off:`;
if (margin < 0) {
  ecs.say(`${opening} ${lib.count_text(-margin, "foot", "feet")} short.`);
  ecs.log("field", intent.value, "short");
  return;
}
ecs.say(`${opening} ${lib.count_text(margin, "foot", "feet")} to spare.`);
ecs.log("field", intent.value, "reached");
