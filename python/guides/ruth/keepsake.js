// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The step system `ruth_keepsake`, kept at /_files/script/ruth_keepsake.js:
// takes the player's intent `keepsake` and prints the handbill, the player's
// `name` beside Ruth's, bragging of the feats `beat_log` shows made, with the
// price of a ride from the `fares`. It makes the item entity handbill and its
// `keepsake` row, says the handbill's text, outcome kept, logged as the beat
// keepsake.
//
// Args: `ecs`. Reads `name`, `fares` and `beat_log`; writes `entity` and
// `keepsake`.

// The step's view of the world, and the lib.
const ecs = args.ecs;
const lib = ecs.lib;

// What a handbill brags of: a beat and outcome of `beat_log`, then its words.
const FEATS = Object.freeze([
  ["loop", "made", "loops"],
  ["roll", "made", "rolls"],
  ["wing_walk", "walked", "the wing walk"],
  ["race", "won", "a motorcar beaten"],
]);

// The item the keepsake is, its entity's name and the kind of its row.
const ITEM = "handbill";

// The player's intent to keep the handbill, or null when none waits.
const intent = ecs.take("keepsake");
if (intent === null) {
  return;
}
const partner = lib.sole_row(
  ecs.rows("SELECT text AS text FROM name WHERE entity = ?", [intent.entity]),
  "the player's name",
).text;
const fares = lib.sole_row(
  ecs.rows(
    "SELECT ride_cents AS ride_cents, ride_min AS ride_min FROM fares",
    [],
  ),
  "fares",
);
const flown = new Set(
  ecs
    .rows("SELECT beat AS beat, outcome AS outcome FROM beat_log", [])
    .map((row) => row.beat + " " + row.outcome),
);
const words = FEATS.filter((feat) => flown.has(feat[0] + " " + feat[1])).map(
  (feat) => feat[2],
);
const list = words.length > 0 ? ": " + lib.list_text(words) : "";
const text =
  `RUTH CALLOWAY AND ${partner.toUpperCase()}, AERIAL ACROBATS${list}!` +
  ` Rides ${lib.money_text(fares.ride_cents)} for ${fares.ride_min} minutes.`;
ecs.run([
  { sql: "INSERT INTO entity (name) VALUES (?)", params: [ITEM] },
  {
    sql:
      "INSERT INTO keepsake (entity, kind, text)" +
      " SELECT id, ?, ? FROM entity WHERE name = ?",
    params: [ITEM, text, ITEM],
  },
]);
ecs.say(text);
ecs.log("keepsake", intent.value, "kept");
