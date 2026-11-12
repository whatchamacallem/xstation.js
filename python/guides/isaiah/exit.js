// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The step system `isaiah_exit` of Isaiah Cole's cattle drive, kept at
// `/_files/script/isaiah_exit.js`: takes the intent `exit`, its value the
// player's words, and rides the player back to the fire while Isaiah keeps
// the herd, the promised exit. The rider's `exits.count` goes up by one. It
// says the head of the herd, the entity of `head` and `calm`, that stay
// down, and logs the beat `at the fire`.
//
// Args: `ecs`, of the contract of `ecs_step`. Reads `head` and `calm`.
// Writes the rider's `exits.count`.

// The step's methods and the drive's lib.
const ecs = args.ecs;
const lib = ecs.lib;

// The intent to leave for the fire, taken, or none and no work this step.
const intent = ecs.take("exit");
if (intent === null) {
  return;
}

const herd = lib.row_one(
  ecs.rows(
    "SELECT head.count AS count FROM head" +
      " JOIN calm ON calm.entity = head.entity ORDER BY head.entity",
    [],
  ),
  "the herd's head",
);
ecs.run([
  {
    sql: "UPDATE exits SET count = count + 1 WHERE entity = ?",
    params: [intent.entity],
  },
]);
ecs.say(
  "You ride back to the fire and the coffee. Isaiah keeps the circle" +
    ` alone, singing, and the ${lib.whole_text(herd.count)} head stay down.`,
);
ecs.log("exit", intent.value, "at the fire");
