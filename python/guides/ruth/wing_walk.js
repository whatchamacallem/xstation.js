// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The step system `ruth_wing_walk`, kept at /_files/script/ruth_wing_walk.js:
// takes the player's intent `wing_walk`, its value who walks, Ruth or the
// player's `name`, and flies the wing walk at the cruise and the show's
// height; then the engine quits over open country, the aircraft's
// `engine_out` until ruth_landing, and it says the height, the wind and each
// field's distance, in the order of their entities. Outcome walked, logged as
// the beat wing_walk.
//
// Args: `ecs`. Reads `name`, `airframe`, `altitude`, `show`, `wind` and
// `field`; writes `altitude` and `engine_out`.

// The step's view of the world, and the lib.
const ecs = args.ecs;
const lib = ecs.lib;

// The player's intent for the wing walk, or null when none waits this step.
const intent = ecs.take("wing_walk");
if (intent === null) {
  return;
}
const partner = lib.sole_row(
  ecs.rows("SELECT text AS text FROM name WHERE entity = ?", [intent.entity]),
  "the player's name",
).text;
// The walks by who walks: Ruth, or the partner by name.
const walks = {
  Ruth: "Ruth walks the top wing while you hold her straight and level",
  [partner]: "You walk the top wing while Ruth holds her straight and level",
};
const opening = lib.choice_get(walks, intent.value);
const aircraft = lib.aircraft_read(ecs);
const wind = lib.wind_read(ecs);
const show = lib.sole_row(ecs.rows("SELECT ft AS ft FROM show", []), "show");
const places = lib
  .fields_read(ecs)
  .map(
    (field, index) =>
      `the ${field.called} ${lib.tenths_text(field.miles)}` +
      (index === 0 ? " miles off" : ""),
  );
ecs.run([
  {
    sql: "UPDATE altitude SET ft = ? WHERE entity = ?",
    params: [show.ft, aircraft.entity],
  },
  {
    sql: "INSERT INTO engine_out (entity) VALUES (?)",
    params: [aircraft.entity],
  },
]);
ecs.say(
  `${opening} at ${aircraft.cruise_mph} mph and ${show.ft} feet. Then, over` +
    ` open country, the OX-5 coughs and quits: ${show.ft} feet up, the wind` +
    ` ${wind.mph} mph from the ${wind.quarter}, ${lib.list_text(places)}.`,
);
ecs.log("wing_walk", intent.value, "walked");
