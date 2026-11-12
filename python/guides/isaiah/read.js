// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The step system `isaiah_read` of Isaiah Cole's cattle drive, kept at
// `/_files/script/isaiah_read.js`: takes the intent `read`, its value the
// player's judge of the herd's breathing, `settled` or `restless`. The herd,
// the entity of `calm` and `temper`, is settled at its `temper.settled` calm
// or more. It says the signs and the calm, and logs the beat `right` when the
// judge is the truth, else `wrong`.
//
// Args: `ecs`, of the contract of `ecs_step`. Reads `calm` and `temper`.
// Writes no component.

// The step's methods and the drive's lib.
const ecs = args.ecs;
const lib = ecs.lib;

// The intent to judge the herd, taken, or none and no work this step.
const intent = ecs.take("read");
if (intent === null) {
  return;
}
const judge = lib.choice_read(intent.value, ["settled", "restless"]);

const herd = lib.row_one(
  ecs.rows(
    "SELECT calm.level AS level, calm.most AS most, temper.settled AS least" +
      " FROM calm JOIN temper ON temper.entity = calm.entity" +
      " ORDER BY calm.entity",
    [],
  ),
  "the herd's calm",
);
const settled = herd.level >= herd.least;
const truth = settled ? "settled" : "restless";
const sign = settled
  ? "Long slow breaths and the cud going"
  : "Short breaths and heads coming up";
const calm =
  `calm ${lib.whole_text(herd.level)} of ${lib.whole_text(herd.most)}`;
if (judge === truth) {
  ecs.say(`${sign}: ${calm}, ${truth}, and you read it right.`);
  ecs.log("read", judge, "right");
} else {
  ecs.say(`${sign}: ${calm} is ${truth}, not ${judge}.`);
  ecs.log("read", judge, "wrong");
}
