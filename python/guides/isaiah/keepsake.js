// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The step system `isaiah_keepsake` of Isaiah Cole's cattle drive, kept at
// `/_files/script/isaiah_keepsake.js`: takes the intent `keepsake`, its value
// the player's words, and names the rider for the trail by the last word of
// the rider's `song.title`. The name's text tells the stampede's outcome in
// `beat_log`, the head the herd's `losses.found` tracked down and its
// `tally.head` brought in, and is kept as the `keepsake` of a new entity,
// `trail_name`. It says the name's text and logs the beat `named`.
//
// Args: `ecs`, of the contract of `ecs_step`. Reads `song`, `beat_log`,
// `tally` and `losses`. Writes `entity` and `keepsake`.

// The step's methods and the drive's lib.
const ecs = args.ecs;
const lib = ecs.lib;

// The entity of the keepsake and the kind of its row.
const ITEM_NAME = "trail_name";
const ITEM_KIND = "trail name";

// The intent to take a trail name, taken, or none and no work this step.
const intent = ecs.take("keepsake");
if (intent === null) {
  return;
}

const song = lib.row_one(
  ecs.rows("SELECT title FROM song WHERE entity = ?", [intent.entity]),
  "the rider's song",
);
const stampede = lib.row_one(
  ecs.rows(
    "SELECT outcome FROM beat_log WHERE beat = ? ORDER BY n DESC LIMIT 1",
    ["stampede"],
  ),
  "the stampede's beat",
);
const herd = lib.row_one(
  ecs.rows(
    "SELECT tally.head AS counted, losses.found AS found FROM tally" +
      " JOIN losses ON losses.entity = tally.entity ORDER BY tally.entity",
    [],
  ),
  "the herd's tally",
);

const name = song.title.split(" ").at(-1);
const deed = stampede.outcome === "circled" ? "turned" : "rode out";
const text =
  `Trail name: ${name}. Rode night guard with Isaiah Cole, ${deed} the` +
  ` stampede, tracked ${lib.whole_text(herd.found)} head and brought` +
  ` ${lib.whole_text(herd.counted)} to Dodge City.`;
ecs.run([
  { sql: "INSERT INTO entity (name) VALUES (?)", params: [ITEM_NAME] },
  {
    sql:
      "INSERT INTO keepsake (entity, kind, text) SELECT id, ?, ? FROM entity" +
      " WHERE name = ?",
    params: [ITEM_KIND, text, ITEM_NAME],
  },
]);
ecs.say(text);
ecs.log("keepsake", intent.value, "named");
