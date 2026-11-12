// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The step system `isaiah_count` of Isaiah Cole's cattle drive, kept at
// `/_files/script/isaiah_count.js`: takes the intent `count`, its value the
// player's words, and counts the herd in at the stockyard gate. The tally man
// writes each herd of `head` and `bed` into `tally`, its head and the clock's
// tick. It says the tally, framed by the `bed` ground and the `losses`, the
// days on the trail, the clock's ticks in days, and the rider's wages of
// `wage`, earned a day at a time, and logs the beat `delivered`.
//
// Args: `ecs`, of the contract of `ecs_step`. Reads `head`, `bed`, `losses`,
// `clock` and `wage`. Writes `tally`.

// The step's methods and the drive's lib.
const ecs = args.ecs;
const lib = ecs.lib;

// The intent to count the herd in, taken, or none and no work this step.
const intent = ecs.take("count");
if (intent === null) {
  return;
}

ecs.run([
  {
    sql:
      "INSERT INTO tally (entity, head, tick) SELECT head.entity," +
      " head.count, (SELECT clock.tick FROM clock) FROM head" +
      " JOIN bed ON bed.entity = head.entity ORDER BY head.entity",
    params: [],
  },
]);

const herd = lib.row_one(
  ecs.rows(
    "SELECT tally.head AS counted, tally.tick AS tick, bed.head AS bedded," +
      " losses.tolled AS tolled, losses.lost AS lost FROM tally" +
      " JOIN bed ON bed.entity = tally.entity" +
      " JOIN losses ON losses.entity = tally.entity ORDER BY tally.entity",
    [],
  ),
  "the herd's tally",
);
const clock = lib.row_one(
  ecs.rows("SELECT tick_seconds FROM clock", []),
  "the clock",
);
const wage = lib.row_one(
  ecs.rows("SELECT cents_a_day, earned FROM wage WHERE entity = ?", [
    intent.entity,
  ]),
  "the rider's wage",
);
const days = (herd.tick * clock.tick_seconds) / lib.SECONDS_A_DAY;

ecs.say(
  "At the stockyard gate the tally man counts" +
    ` ${lib.whole_text(herd.counted)} head: ${lib.whole_text(herd.bedded)}` +
    ` from the bed ground, ${lib.whole_text(herd.tolled)} paid at the ford` +
    ` and ${lib.whole_text(herd.lost)} lost on the trail.` +
    ` ${lib.days_text(days)} on the trail at` +
    ` ${lib.money_text(wage.cents_a_day)} a day:` +
    ` ${lib.money_text(wage.earned)} in wages, and a bath.`,
);
ecs.log("count", intent.value, "delivered");
