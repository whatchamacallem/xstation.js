// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The step system `dawa_icefall`, kept at /_files/script/dawa_icefall.js:
// takes the intent `icefall`, its value the whole hour of the day, 0 to 23,
// to start through the Khumbu Icefall from the bottom of the route. The end
// of the crossing is taken modulo the day, so a late start ends in the small
// hours, before the next sun. A start whose crossing ends once the sun has
// loosened the ice on the day it ends is refused, an outcome, and the rope
// stays; else the world's day is set to that hour and the rope starts its
// climb to the camp above, a tick at a time for the icefall's hours, and
// dawa_move tells the arrival. A value that is no hour of the day is a bug of
// the table, and throws. Without the intent it does nothing.
//
// Args: `ecs`. Reads `at`, `camp`, `icefall`, `sun` and the clock; writes
// `day`, `climb` and `busy`. Says the crossing or its refusal, and logs the
// beat `icefall` with the hour and `crossed` or `refused`.

// The step's view of the world, with its lib.
const ecs = args.ecs;
const lib = ecs.lib;

// The whole hour of the day of the intent's value, or a throw for a value that is no hour of the day, a bug of the table.
function hour_get(value) {
  const hour = Number(value);
  if (!/^[0-9]{1,2}$/.test(value) || hour >= lib.units.hours_per_day) {
    throw new Error(
      `dawa_icefall: the value ${JSON.stringify(value)} is no whole hour of` +
        " the day.",
    );
  }
  return hour;
}

// Crosses from the hour given, or refuses it when the sun would loosen the ice first.
function icefall_cross(intent) {
  const units = lib.units;
  const start = hour_get(intent.value);
  const here = lib.climber_camp(ecs, intent.entity);
  if (here.ord !== lib.route_ends(ecs).bottom) {
    throw new Error(
      `dawa_icefall: the rope is at ${here.name}, not at the bottom of the` +
        " route.",
    );
  }
  const rule = lib.row_read(
    ecs,
    "SELECT icefall.hours AS hours, sun.loosen_hour AS loosen_hour" +
      " FROM icefall JOIN sun ON sun.entity = icefall.entity",
    [],
  );
  const done = (start + rule.hours) % units.hours_per_day;
  const late = done - rule.loosen_hour;
  const minutes = rule.hours * units.minutes_per_hour;
  if (late >= 0) {
    const when =
      late === 0
        ? "just as"
        : `${lib.duration_text(late * units.minutes_per_hour)} after`;
    ecs.say(
      `Start at ${lib.hour_text(start)} and the icefall's ` +
        `${lib.duration_text(minutes)} keep you under the seracs until ` +
        `${lib.hour_text(done)}, ${when} the sun loosens the ice at ` +
        `${lib.hour_text(rule.loosen_hour)}.`,
    );
    ecs.log("icefall", intent.value, "refused");
    return;
  }
  const above = lib.route_camp(ecs, here.ord + 1);
  const ticks = minutes / lib.tick_minutes(ecs);
  ecs.run([
    ...lib.day_set(start * units.minutes_per_hour),
    ...lib.climb_start(here.entity, above.entity, ticks),
  ]);
  ecs.say(
    `Start at ${lib.hour_text(start)} and you are through the icefall at ` +
      `${lib.hour_text(done)}, ` +
      `${lib.duration_text(-late * units.minutes_per_hour)} before the sun.`,
  );
  ecs.log("icefall", intent.value, "crossed");
}

const intent = ecs.take("icefall");
if (intent !== null) {
  icefall_cross(intent);
}
