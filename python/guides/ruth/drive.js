// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The tick system `ruth_drive`, kept at /_files/script/ruth_drive.js: each
// tick, moves every racer still busy its ground speed times the clock's
// seconds a tick, in whole feet by integer arithmetic, at most to the end of
// the course, counts the tick it drove, and ends the busy of each racer at the
// course's end. A ground speed that moves no whole number of feet a tick
// throws, as no throttle of the table gives one. It says and logs nothing.
//
// Args: `ecs`. Reads `racer`, `busy`, `course` and `clock`; writes `racer`
// and `busy`.

// The tick's view of the world, and the lib.
const ecs = args.ecs;
const lib = ecs.lib;

// The racers still busy, none outside a race.
const racing = ecs.rows(
  "SELECT racer.entity AS entity, racer.ground_mph AS ground_mph FROM racer" +
    " JOIN busy ON busy.entity = racer.entity ORDER BY racer.entity",
  [],
);
if (racing.length === 0) {
  return;
}
const course = lib.sole_row(
  ecs.rows("SELECT feet AS feet FROM course", []),
  "course",
);
const clock = lib.sole_row(
  ecs.rows("SELECT tick_seconds AS tick_seconds FROM clock", []),
  "clock",
);
for (const racer of racing) {
  // The feet of a tick times the seconds of an hour, a whole multiple of them.
  const numerator = racer.ground_mph * lib.FEET_PER_MILE * clock.tick_seconds;
  if (numerator % lib.SECONDS_PER_HOUR !== 0) {
    throw new Error(
      `internal error: ruth_drive moves the racer ${racer.entity} at` +
        ` ${racer.ground_mph} mph no whole number of feet in` +
        ` ${clock.tick_seconds} seconds`,
    );
  }
}
ecs.run([
  {
    sql:
      "UPDATE racer SET feet = MIN(feet + ground_mph * ? * ? / ?, ?)," +
      " ticks = ticks + 1 WHERE entity IN (SELECT entity FROM busy)",
    params: [
      lib.FEET_PER_MILE,
      clock.tick_seconds,
      lib.SECONDS_PER_HOUR,
      course.feet,
    ],
  },
  {
    sql:
      "DELETE FROM busy WHERE entity IN" +
      " (SELECT entity FROM racer WHERE feet = ?)",
    params: [course.feet],
  },
]);
