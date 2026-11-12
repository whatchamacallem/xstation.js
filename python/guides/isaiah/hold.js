// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The tick system `isaiah_hold` of Isaiah Cole's cattle drive, kept at
// `/_files/script/isaiah_hold.js`: holds each entity of `wait` on the bank of
// the river at its `place`, the entity of `water`, a day each tick. The wait
// counts the day in `wait.days`, and the river's high water falls by a day in
// `water.high`. A waiter whose river is down swims it over with none lost:
// it says so with the days spent waiting, and its `wait` and `busy` rows go.
//
// Args: `ecs`, of the contract of `ecs_step`. Reads `wait`, `head`, `place`
// and `water`. Writes `wait`, `water.high` and `busy`.

// The step's methods and the drive's lib.
const ecs = args.ecs;
const lib = ecs.lib;

// The waiters on a bank, their days, head and the high water at their mile.
const waiting = ecs.rows(
  "SELECT wait.entity AS entity, wait.days AS days, head.count AS count," +
    " water.high AS high FROM wait JOIN head ON head.entity = wait.entity" +
    " JOIN place AS bank ON bank.entity = wait.entity" +
    " JOIN place AS shore ON shore.mile = bank.mile" +
    " JOIN water ON water.entity = shore.entity ORDER BY wait.entity",
  [],
);
if (waiting.length === 0) {
  return;
}

// The waiters whose river is down once this day drops its water a day.
const crossed = waiting.filter((herd) => herd.high <= 1);

// Every write of the day in one run, as reads came first.
ecs.run([
  { sql: "UPDATE wait SET days = days + 1", params: [] },
  {
    sql:
      "UPDATE water SET high = high - 1 WHERE high > 0 AND entity IN" +
      " (SELECT shore.entity FROM wait" +
      " JOIN place AS bank ON bank.entity = wait.entity" +
      " JOIN place AS shore ON shore.mile = bank.mile)",
    params: [],
  },
  ...crossed.flatMap((herd) => [
    { sql: "DELETE FROM busy WHERE entity = ?", params: [herd.entity] },
    { sql: "DELETE FROM wait WHERE entity = ?", params: [herd.entity] },
  ]),
]);
for (const herd of crossed) {
  ecs.say(
    `and the water drops: all ${lib.whole_text(herd.count)} swim it,` +
      " leaders first, and none is lost." +
      ` ${lib.days_text(herd.days + 1)} spent waiting.`,
  );
}
