// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The step system `isaiah_river` of Isaiah Cole's cattle drive, kept at
// `/_files/script/isaiah_river.js`: takes the intent `river`, its value the
// player's choice at the Cimarron, `wait` or `swim`. The herd, the entity of
// `losses`, stands at the `place` of a river, the entity of `water`, which
// runs high when the herd comes to it. Waiting holds the herd on the bank:
// it gains `wait` and is `busy`, and the tick system `isaiah_hold` counts the
// days until the water drops and swims it over. Swimming now drowns one head
// in each `water.per_drowned` of the herd, lost. It says the choice, and logs
// the beat `crossed` or `swum`.
//
// Args: `ecs`, of the contract of `ecs_step`. Reads `losses`, `head`,
// `place` and `water`. Writes `wait` and `busy`, or `head` and
// `losses.lost`.

// The step's methods and the drive's lib.
const ecs = args.ecs;
const lib = ecs.lib;

// The intent to cross the river, taken, or none and no work this step.
const intent = ecs.take("river");
if (intent === null) {
  return;
}
const choice = lib.choice_read(intent.value, ["wait", "swim"]);

// The herd and the river at its mile, found by the mile they share.
const ford = lib.row_one(
  ecs.rows(
    "SELECT losses.entity AS herd, head.count AS count," +
      " water.high AS high, water.per_drowned AS per_drowned FROM losses" +
      " JOIN head ON head.entity = losses.entity" +
      " JOIN place AS bank ON bank.entity = losses.entity" +
      " JOIN place AS shore ON shore.mile = bank.mile" +
      " JOIN water ON water.entity = shore.entity ORDER BY losses.entity",
    [],
  ),
  "the herd at a river",
);
// The drive comes to the river once, while its water runs high.
if (ford.high === 0) {
  throw new Error(
    "Isaiah's drive crosses the river once, in high water, and its water" +
      " is down already.",
  );
}

if (choice === "wait") {
  ecs.run([
    { sql: "INSERT INTO wait (entity, days) VALUES (?, 0)", params: [ford.herd] },
    { sql: "INSERT INTO busy (entity) VALUES (?)", params: [ford.herd] },
  ]);
  ecs.say("You hold the herd a day on the south bank of the Cimarron");
  ecs.log("river", choice, "crossed");
} else {
  const drowned = Math.floor(ford.count / ford.per_drowned);
  ecs.run([
    {
      sql: "UPDATE head SET count = count - ? WHERE entity = ?",
      params: [drowned, ford.herd],
    },
    {
      sql: "UPDATE losses SET lost = lost + ? WHERE entity = ?",
      params: [drowned, ford.herd],
    },
  ]);
  const herd = lib.row_one(
    ecs.rows("SELECT count FROM head WHERE entity = ?", [ford.herd]),
    "the herd's head",
  );
  ecs.say(
    `You swim them now in high water: ${lib.whole_text(ford.count)} go in,` +
      ` ${lib.whole_text(drowned)} drown and ${lib.whole_text(herd.count)}` +
      " come out on the north bank.",
  );
  ecs.log("river", choice, "swum");
}
