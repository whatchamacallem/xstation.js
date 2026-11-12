// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The lib of Ruth Calloway's sim, the system `ruth_lib` of kind lib, kept at
// /_files/script/ruth_lib.js: ecs_step runs it with `{}` once a step, before
// her systems, which find its value at `ecs.lib`. It holds the units and
// standard gravity, the number formats of her says, the book's rate of climb
// and fuel burn, the parse of an intent's whole number, and the reads of the
// components most systems share: the aircraft, its pilot, the wind and the
// fields. Every figure of the model is a component value that ruth_spawn
// wrote; a figure kept as an integer of a stated scale, its column ending in
// `_x100` or `_x10`, is divided by that scale here, which gives the same double
// as its decimal literal.
//
// Args: none. Returns the lib, a frozen object.

// Feet in a mile.
const FEET_PER_MILE = 5280;
// Seconds in an hour.
const SECONDS_PER_HOUR = 3600;
// Minutes in an hour.
const MINUTES_PER_HOUR = 60;
// Seconds in a minute.
const SECONDS_PER_MINUTE = 60;
// Cents in a dollar.
const CENTS_PER_DOLLAR = 100;
// Radians in a degree.
const RADIANS_PER_DEGREE = Math.PI / 180;
// Standard gravity, feet a second a second.
const G = 32.174;
// Feet a second in a mile an hour: 5280 feet over 3600 seconds, 22 / 15.
const FPS_PER_MPH = FEET_PER_MILE / SECONDS_PER_HOUR;

// The scale of a figure kept in hundredths, and of one kept in tenths.
const HUNDREDTHS = 100;
const TENTHS = 10;

// The compass point opposite each: a heading into the wind, or with it.
const OPPOSITE = Object.freeze({
  north: "south",
  south: "north",
  east: "west",
  west: "east",
});

// The text of a whole number in an intent's value: digits alone.
const WHOLE_PATTERN = /^[0-9]+$/;

// The text of a number rounded to a whole, as `2000`.
function whole_text(value) {
  return String(Math.round(value));
}

// The text of a number rounded to tenths, as `1.5` or `6.0`.
function tenths_text(value) {
  return (Math.round(value * 10) / 10).toFixed(1);
}

// The text of whole cents as dollars, as `$46.85`.
function money_text(cents) {
  const dollars = Math.floor(cents / CENTS_PER_DOLLAR);
  const rest = String(cents % CENTS_PER_DOLLAR).padStart(2, "0");
  return "$" + dollars + "." + rest;
}

// The text of whole seconds as a clock, as `4:02`.
function clock_text(seconds) {
  const minutes = Math.floor(seconds / SECONDS_PER_MINUTE);
  const rest = String(seconds % SECONDS_PER_MINUTE).padStart(2, "0");
  return minutes + ":" + rest;
}

// The items joined by commas, with `and` before the last.
function list_text(items) {
  if (items.length < 2) {
    return items.join("");
  }
  return items.slice(0, -1).join(", ") + " and " + items[items.length - 1];
}

// The whole number an intent's value writes, thrown when it writes none.
function whole_value(value) {
  if (typeof value !== "string" || !WHOLE_PATTERN.test(value)) {
    throw new Error(
      `internal error: ruth needs a whole number, not ${JSON.stringify(value)}`,
    );
  }
  return Number(value);
}

// The member of a table of choices, thrown when the choice is not one.
function choice_get(table, choice) {
  if (!Object.hasOwn(table, choice)) {
    throw new Error(
      `internal error: ruth has no choice ${JSON.stringify(choice)}`,
    );
  }
  return table[choice];
}

// The one row of a read, thrown when the world holds none or several.
function sole_row(rows, what) {
  if (rows.length !== 1) {
    throw new Error(
      `internal error: ruth needs one row of ${what}, not ${rows.length}`,
    );
  }
  return rows[0];
}

// Feet a second at a speed in miles an hour.
function speed_feet(mph) {
  return mph * FPS_PER_MPH;
}

// Gallons burnt in minutes of flying, at gallons an hour.
function fuel_gallons(minutes, burn_gal_hr) {
  return (minutes * burn_gal_hr) / MINUTES_PER_HOUR;
}

// The book's rate of climb, and the minutes and gallons between two heights.
function climb_cost(aircraft, from_ft, to_ft) {
  const rate = aircraft.climb_ft / aircraft.climb_min;
  const minutes = (to_ft - from_ft) / rate;
  const gallons = fuel_gallons(minutes, aircraft.burn_gal_hr);
  return { rate, minutes, gallons };
}

// The one aircraft: its id, its height and its book figures, unscaled.
function aircraft_read(ecs) {
  const row = sole_row(
    ecs.rows(
      "SELECT airframe.entity AS entity, altitude.ft AS ft," +
        " airframe.gross_lb AS gross_lb," +
        " airframe.wing_sqft_x100 AS wing_sqft_x100, airframe.hp AS hp," +
        " airframe.max_mph AS max_mph, airframe.min_mph AS min_mph," +
        " airframe.climb_ft AS climb_ft, airframe.climb_min AS climb_min," +
        " airframe.tank_gal AS tank_gal," +
        " airframe.burn_gal_hr AS burn_gal_hr," +
        " airframe.level_off_ft AS level_off_ft," +
        " airframe.cruise_mph AS cruise_mph," +
        " airframe.glide_ratio_x100 AS glide_ratio_x100 FROM airframe" +
        " JOIN altitude ON altitude.entity = airframe.entity",
      [],
    ),
    "airframe and altitude",
  );
  return Object.freeze({
    entity: row.entity,
    ft: row.ft,
    gross_lb: row.gross_lb,
    wing_sqft: row.wing_sqft_x100 / HUNDREDTHS,
    hp: row.hp,
    max_mph: row.max_mph,
    min_mph: row.min_mph,
    climb_ft: row.climb_ft,
    climb_min: row.climb_min,
    tank_gal: row.tank_gal,
    burn_gal_hr: row.burn_gal_hr,
    level_off_ft: row.level_off_ft,
    cruise_mph: row.cruise_mph,
    glide_ratio: row.glide_ratio_x100 / HUNDREDTHS,
  });
}

// The one pilot's technique, the pull over a loop's top divided to g.
function pilot_read(ecs) {
  const row = sole_row(
    ecs.rows(
      "SELECT entity AS entity, loop_pull_g AS loop_pull_g," +
        " loop_top_g_x10 AS loop_top_g_x10, roll_seconds AS roll_seconds," +
        " stunt_ft AS stunt_ft FROM technique",
      [],
    ),
    "technique",
  );
  return Object.freeze({
    entity: row.entity,
    loop_pull_g: row.loop_pull_g,
    loop_top_g: row.loop_top_g_x10 / TENTHS,
    roll_seconds: row.roll_seconds,
    stunt_ft: row.stunt_ft,
  });
}

// The one wind: its speed in miles an hour and the quarter it blows from.
function wind_read(ecs) {
  return sole_row(
    ecs.rows(
      "SELECT entity AS entity, mph AS mph, quarter AS quarter FROM wind",
      [],
    ),
    "wind",
  );
}

// Each field in the order of its entity: its heading, the entity's name.
function fields_read(ecs) {
  const rows = ecs.rows(
    "SELECT field.entity AS entity, entity.name AS heading," +
      " field.name AS called, field.miles_x10 AS miles_x10 FROM field" +
      " JOIN entity ON entity.id = field.entity ORDER BY field.entity",
    [],
  );
  return rows.map((row) =>
    Object.freeze({
      entity: row.entity,
      heading: row.heading,
      called: row.called,
      miles: row.miles_x10 / TENTHS,
    }),
  );
}

return Object.freeze({
  FEET_PER_MILE,
  SECONDS_PER_HOUR,
  RADIANS_PER_DEGREE,
  G,
  FPS_PER_MPH,
  OPPOSITE,
  whole_text,
  tenths_text,
  money_text,
  clock_text,
  list_text,
  whole_value,
  choice_get,
  sole_row,
  speed_feet,
  fuel_gallons,
  climb_cost,
  aircraft_read,
  pilot_read,
  wind_read,
  fields_read,
});
