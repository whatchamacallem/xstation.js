// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The step system `isaiah_resume` of Isaiah Cole's cattle drive, kept at
// `/_files/script/isaiah_resume.js`: takes the intent `resume`, its value the
// player's words, and rides the player out from the fire to the herd again.
// It says the head and the calm of the herd, the entity of `head` and
// `calm`, and logs the beat `riding`.
//
// Args: `ecs`, of the contract of `ecs_step`. Reads `head` and `calm`. Writes
// no component.

// The step's methods and the drive's lib.
const ecs = args.ecs;
const lib = ecs.lib;

// The intent to ride out again, taken, or none and no work this step.
const intent = ecs.take("resume");
if (intent === null) {
  return;
}

const herd = lib.row_one(
  ecs.rows(
    "SELECT head.count AS count, calm.level AS level, calm.most AS most" +
      " FROM head JOIN calm ON calm.entity = head.entity ORDER BY head.entity",
    [],
  ),
  "the herd's head and calm",
);
ecs.say(
  `You ride out again to the herd: ${lib.whole_text(herd.count)} head,` +
    ` calm ${lib.whole_text(herd.level)} of ${lib.whole_text(herd.most)}.`,
);
ecs.log("resume", intent.value, "riding");
