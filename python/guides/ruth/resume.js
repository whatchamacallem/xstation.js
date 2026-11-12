// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The step system `ruth_resume`, kept at /_files/script/ruth_resume.js: takes
// the player's intent `resume` after an exit. With the aircraft's
// `engine_out` she stays on the grass, no climb left, outcome grounded; with
// no `resume` kept it waits, outcome made; otherwise it climbs the aircraft
// at the book's rate back to the height the exit left and removes its
// `resume`, outcome made, a climb under a minute said in words. It logs the
// beat resume, choice the intent's value.
//
// Args: `ecs`. Reads `airframe`, `altitude`, `engine_out` and `resume`;
// writes `altitude` and `resume`.

// The step's view of the world, and the lib.
const ecs = args.ecs;
const lib = ecs.lib;

// The player's intent to go back up, or null when none waits this step.
const intent = ecs.take("resume");
if (intent === null) {
  return;
}
const aircraft = lib.aircraft_read(ecs);
if (lib.engine_dead(ecs, aircraft)) {
  ecs.say("The OX-5 is still dead, so she stays on the grass where she is.");
  ecs.log("resume", intent.value, "grounded");
  return;
}
const kept = ecs.rows("SELECT ft AS ft FROM resume WHERE entity = ?", [
  aircraft.entity,
]);
if (kept.length === 0) {
  ecs.say("Ready when you are.");
  ecs.log("resume", intent.value, "made");
  return;
}
const height = kept[0].ft;
const cost = lib.climb_cost(aircraft, aircraft.ft, height);
ecs.run([
  {
    sql: "UPDATE altitude SET ft = ? WHERE entity = ?",
    params: [height, aircraft.entity],
  },
  {
    sql: "DELETE FROM resume WHERE entity = ?",
    params: [aircraft.entity],
  },
]);
// A climb of under one minute, said in words, as its figures round to none.
if (cost.minutes < 1) {
  ecs.say(
    `Back up to ${height} feet in under a minute, on a splash of gasoline.`,
  );
} else {
  ecs.say(
    `Back up to ${height} feet in ${lib.whole_text(cost.minutes)} minutes,` +
      ` on ${lib.tenths_text(cost.gallons)} gallons more.`,
  );
}
ecs.log("resume", intent.value, "made");
