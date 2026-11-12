// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The step system `isaiah_exit` of Isaiah Cole's cattle drive, kept at
// `/_files/script/isaiah_exit.js`: takes the intent `exit`, its value the
// player's words, and rides the player back to the fire while Isaiah keeps
// the herd, the promised exit. The rider's `exits.count` goes up by one. It
// says where the herd, the entity of `head` and `calm`, stands, by the state
// the drive holds: counted in when it has a `tally`, at the trail's end when
// no `place` lies ahead of it, on the bank when a river of `water` shares its
// mile, gathered while bunches are `hidden`, running once the beat log holds
// a right reading and no stampede, else down on night guard. It logs the beat
// `at the fire`.
//
// Args: `ecs`, of the contract of `ecs_step`. Reads `head`, `calm`, `tally`,
// `place`, `water`, `hidden` and `beat_log`. Writes the rider's
// `exits.count`.

// The step's methods and the drive's lib.
const ecs = args.ecs;
const lib = ecs.lib;

// Where the rider goes, whatever the herd is doing.
const FIRE = "You ride back to the fire and the coffee.";

// The intent to leave for the fire, taken, or none and no work this step.
const intent = ecs.take("exit");
if (intent === null) {
  return;
}

// The herd's head, its tally, and whether it is at the trail's end or a river.
const herd = lib.row_one(
  ecs.rows(
    "SELECT head.count AS count, (SELECT tally.head FROM tally" +
      " WHERE tally.entity = head.entity) AS tallied, NOT EXISTS" +
      " (SELECT 1 FROM place AS ahead WHERE ahead.mile > place.mile)" +
      " AS ended, EXISTS (SELECT 1 FROM place AS shore JOIN water" +
      " ON water.entity = shore.entity WHERE shore.mile = place.mile)" +
      " AS forded FROM head JOIN calm ON calm.entity = head.entity" +
      " JOIN place ON place.entity = head.entity ORDER BY head.entity",
    [],
  ),
  "the herd's head",
);
// The head of the bunches still out after the stampede.
const out = ecs
  .rows(
    "SELECT head.count AS count FROM head" +
      " JOIN hidden ON hidden.entity = head.entity ORDER BY head.entity",
    [],
  )
  .reduce((sum, bunch) => sum + bunch.count, 0);
// Whether the storm has come: a right reading logged and no stampede yet.
const storm = lib.row_one(
  ecs.rows(
    "SELECT EXISTS (SELECT 1 FROM beat_log WHERE beat = ? AND outcome = ?)" +
      " AND NOT EXISTS (SELECT 1 FROM beat_log WHERE beat = ?) AS running",
    ["read", "right", "stampede"],
  ),
  "the storm",
).running;

const head = lib.whole_text(herd.count);
let kept;
if (herd.tallied !== null) {
  kept =
    `The ${lib.whole_text(herd.tallied)} head stand counted in the` +
    " stockyard pens, and Isaiah waits by the gate.";
} else if (herd.ended === 1) {
  kept = `Isaiah holds the ${head} head on the grass by the stockyard gate.`;
} else if (herd.forded === 1) {
  kept = `Isaiah holds the ${head} head on the bank of the Cimarron.`;
} else if (out > 0) {
  kept =
    `Isaiah holds the ${head} head together, and` +
    ` ${lib.whole_text(out)} are still out.`;
} else if (storm === 1) {
  kept =
    `Isaiah rides for the leaders alone, and the ${head} head run on` +
    " through the storm.";
} else {
  kept =
    "Isaiah keeps the circle alone, singing, and the" +
    ` ${head} head stay down. His song carries in from the dark, slow and` +
    " easy.";
}
ecs.run([
  {
    sql: "UPDATE exits SET count = count + 1 WHERE entity = ?",
    params: [intent.entity],
  },
]);
ecs.say(`${FIRE} ${kept}`);
ecs.log("exit", intent.value, "at the fire");
