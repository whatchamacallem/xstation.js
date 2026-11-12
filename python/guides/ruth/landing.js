// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The step system `ruth_landing`, kept at /_files/script/ruth_landing.js:
// takes the player's intent `landing`, its value `into the wind` or `with the
// wind`, and touches the aircraft down at the book's stall through the air,
// the stall less the wind over the hay into it or plus the wind with it.
// Outcome landed when that is under the stall, else landed long; on the grass
// already, set down by an exit, it says so, outcome landed. Either way the
// engine out is over, its `engine_out` removed, and the beat is landing.
//
// Args: `ecs`. Reads `airframe`, `altitude` and `wind`; writes `altitude` and
// `engine_out`.

// The step's view of the world, and the lib.
const ecs = args.ecs;
const lib = ecs.lib;

// The ways to land by the choice's text: the words and the wind's sign.
const LANDINGS = Object.freeze({
  "into the wind": { name: "Into the wind", sign: -1 },
  "with the wind": { name: "With the wind", sign: 1 },
});

// The player's intent to land, or null when none waits this step.
const intent = ecs.take("landing");
if (intent === null) {
  return;
}
const landing = lib.choice_get(LANDINGS, intent.value);
const aircraft = lib.aircraft_read(ecs);
const wind = lib.wind_read(ecs);
const ground = aircraft.min_mph + landing.sign * wind.mph;
const height = aircraft.ft;
ecs.run([
  {
    sql: "UPDATE altitude SET ft = 0 WHERE entity = ?",
    params: [aircraft.entity],
  },
  {
    sql: "DELETE FROM engine_out WHERE entity = ?",
    params: [aircraft.entity],
  },
]);
if (height === 0) {
  ecs.say(
    "She's on the grass already, stopped where Ruth set her down: nothing" +
      " left to bring in.",
  );
  ecs.log("landing", intent.value, "landed");
  return;
}
const opening =
  `${landing.name} she touches down at ${aircraft.min_mph} mph through the` +
  ` air and ${ground} over the hay, and rolls`;
if (ground < aircraft.min_mph) {
  ecs.say(`${opening} to a stop. Down safe.`);
  ecs.log("landing", intent.value, "landed");
  return;
}
ecs.say(`${opening} long, past the fence posts. Down, and lucky.`);
ecs.log("landing", intent.value, "landed long");
