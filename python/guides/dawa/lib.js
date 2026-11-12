// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The lib of Dawa's climb, the system `dawa_lib` of kind lib, kept at
// /_files/script/dawa_lib.js. ecs_step runs it with `{}` once a step before
// the systems, and dawa_spawn runs it once for the say of the first camp. It
// holds the units; the published rules with their sources: West's formula of
// the pressure of the air, the oxygen breathed in and the sleep rule of the
// doctors; the number formats of the says; and the readers and statements
// the systems share. It writes nothing, and every constant of the guide's
// world is a component that dawa_spawn made.
//
// Args: none. Returns a frozen object of `units`, `air_text`, `night_text`,
// `whole_text`, `count_text`, `clock_text`, `hour_text`, `duration_text`,
// `sentence_start`, `row_read`, `tick_minutes`, `route_ends`, `route_camp`,
// `climber_camp`, `oxygen_read`, `rope_move`, `climb_start` and `day_set`.

// Metres in a kilometre, seconds in a minute, minutes in an hour, hours in a day, and a whole in percent.
const units = Object.freeze({
  m_per_km: 1000,
  seconds_per_minute: 60,
  minutes_per_hour: 60,
  hours_per_day: 24,
  percent: 100,
});

// Air pressure in mmHg at h km is exp(a less b h less c h h): J. B. West, J Appl Physiol 81 (1996) 1850.
const west = Object.freeze({ a: 6.63268, b: 0.1112, c: 0.00149 });

// Oxygen's share of dry air.
const oxygen_share = 0.2094;

// The pressure of water vapour in the lungs at 37 C, in mmHg.
const vapour_mmhg = 47;

// Above 3000 m sleep no more than 500 m higher a night: Wilderness Medical Society Clinical Practice Guidelines, 2019 update.
const sleep_rule = Object.freeze({ above_m: 3000, rise_m: 500 });

// The columns of a camp as its readers give them.
const CAMP_COLUMNS =
  "camp.entity AS entity, camp.name AS name, camp.place AS place," +
  " camp.altitude_m AS altitude_m, camp.ord AS ord, camp.way AS way";

// The air pressure in mmHg at a height in metres, by West's formula.
function pressure_at(m) {
  const h = m / units.m_per_km;
  return Math.exp(west.a - west.b * h - west.c * h * h);
}

// The pressure of the oxygen breathed in, in mmHg, at a height in metres.
function oxygen_at(m) {
  return oxygen_share * (pressure_at(m) - vapour_mmhg);
}

// A number rounded to a whole, as text.
function whole_text(x) {
  return String(Math.round(x));
}

// The sentence of the air at a place: its pressure, the oxygen breathed, and that oxygen's share of the sea's.
function air_text(place, m) {
  const share = (units.percent * oxygen_at(m)) / oxygen_at(0);
  return (
    `${place}, ${m} m: the air presses ${whole_text(pressure_at(m))} mmHg, ` +
    `and you breathe in ${whole_text(oxygen_at(m))} mmHg of oxygen, ` +
    `${whole_text(share)} percent of what the sea gives.`
  );
}

// The sentence of a night slept over the sleep rule without bottled oxygen, or null for a night within it.
function night_text(from_m, to_m, bottled) {
  const rise = to_m - from_m;
  if (to_m <= sleep_rule.above_m || rise <= sleep_rule.rise_m || bottled) {
    return null;
  }
  return (
    `You sleep ${rise} m higher than last night, over the ` +
    `${sleep_rule.rise_m} m a night the doctors allow.`
  );
}

// A count and its noun, the singular for one.
function count_text(n, one, many) {
  return `${n} ${n === 1 ? one : many}`;
}

// A time of day from whole minutes after midnight, as 4:00 or 5:30.
function clock_text(minutes) {
  const day = units.hours_per_day * units.minutes_per_hour;
  const time = minutes % day;
  const hour = Math.floor(time / units.minutes_per_hour);
  const minute = String(time % units.minutes_per_hour).padStart(2, "0");
  return `${hour}:${minute}`;
}

// A whole hour of the day as a time, as 9:00.
function hour_text(hour) {
  return clock_text(hour * units.minutes_per_hour);
}

// A duration from whole minutes, as 1 hour, 5 hours or 4 hours 30 minutes.
function duration_text(minutes) {
  const hours = Math.floor(minutes / units.minutes_per_hour);
  const rest = minutes % units.minutes_per_hour;
  const text = count_text(hours, "hour", "hours");
  return rest === 0 ? text : `${text} ${rest} minutes`;
}

// The text with its first letter a capital, to start a sentence.
function sentence_start(text) {
  return text.charAt(0).toUpperCase() + text.slice(1);
}

// The one row a statement reads through a system's `ecs`, or a throw naming what it read.
function row_read(ecs, sql, params) {
  const rows = ecs.rows(sql, params);
  if (rows.length !== 1) {
    throw new Error(
      `${ecs.system} reads ${rows.length} rows of ${JSON.stringify(sql)}` +
        ` with ${JSON.stringify(params)}, where it needs one.`,
    );
  }
  return rows[0];
}

// The whole minutes a tick of the clock stands for.
function tick_minutes(ecs) {
  const clock = row_read(ecs, "SELECT tick_seconds FROM clock", []);
  const minutes = clock.tick_seconds / units.seconds_per_minute;
  if (!Number.isInteger(minutes)) {
    throw new Error(
      `${ecs.system}: a tick of ${clock.tick_seconds} seconds is no whole` +
        " number of minutes.",
    );
  }
  return minutes;
}

// The places on the route of its lowest camp and its highest, the top.
function route_ends(ecs) {
  return row_read(
    ecs,
    "SELECT MIN(ord) AS bottom, MAX(ord) AS top FROM camp",
    [],
  );
}

// The camp at a place on the route.
function route_camp(ecs, ord) {
  return row_read(ecs, `SELECT ${CAMP_COLUMNS} FROM camp WHERE ord = ?`, [
    ord,
  ]);
}

// The camp a climber is at.
function climber_camp(ecs, entity) {
  return row_read(
    ecs,
    `SELECT ${CAMP_COLUMNS} FROM at JOIN camp ON camp.entity = at.camp` +
      " WHERE at.entity = ?",
    [entity],
  );
}

// The rule of bottled oxygen: the camp from which the rope breathes it, its height, and the flows of a climber and of a sick one.
function oxygen_read(ecs) {
  return row_read(
    ecs,
    "SELECT camp.name AS name, camp.altitude_m AS altitude_m," +
      " oxygen.climb_lpm AS climb_lpm, oxygen.sick_lpm AS sick_lpm" +
      " FROM oxygen JOIN camp ON camp.entity = oxygen.camp",
    [],
  );
}

// The statements that move the rope at one camp to another at once, raising the high mark it holds.
function rope_move(from_camp, to_camp) {
  return [
    {
      sql:
        "UPDATE high SET m = MAX(m, (SELECT altitude_m FROM camp" +
        " WHERE camp.entity = ?)) WHERE entity IN (SELECT entity FROM at" +
        " WHERE camp = ?)",
      params: [to_camp, from_camp],
    },
    { sql: "UPDATE at SET camp = ? WHERE camp = ?", params: [to_camp, from_camp] },
  ];
}

// The statements that start the rope at one camp climbing to another, busy for the ticks given.
function climb_start(from_camp, to_camp, ticks) {
  if (!Number.isInteger(ticks) || ticks < 1) {
    throw new Error(
      `dawa_lib: a climb of ${ticks} ticks is no whole number of ticks.`,
    );
  }
  return [
    {
      sql:
        "INSERT INTO climb (entity, to_camp, ticks_left) SELECT entity, ?, ?" +
        " FROM at WHERE camp = ? ORDER BY entity",
      params: [to_camp, ticks, from_camp],
    },
    {
      sql:
        "INSERT INTO busy (entity) SELECT entity FROM at WHERE camp = ?" +
        " ORDER BY entity",
      params: [from_camp],
    },
  ];
}

// The statements that set the world's day to whole minutes after midnight, at the start of a climb against the clock.
function day_set(minute) {
  return [
    { sql: "DELETE FROM day", params: [] },
    {
      sql: "INSERT INTO day (entity, minute) SELECT entity, ? FROM clock",
      params: [minute],
    },
  ];
}

return Object.freeze({
  units,
  air_text,
  night_text,
  whole_text,
  count_text,
  clock_text,
  hour_text,
  duration_text,
  sentence_start,
  row_read,
  tick_minutes,
  route_ends,
  route_camp,
  climber_camp,
  oxygen_read,
  rope_move,
  climb_start,
  day_set,
});
