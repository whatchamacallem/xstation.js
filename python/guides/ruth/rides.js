// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The step system `ruth_rides`, kept at /_files/script/ruth_rides.js: takes
// the player's intent `rides`, its value how many, and sells them all
// afternoon from the grass. The rides may burn what the tank spares once the
// show's minutes are kept, else the outcome is refused with the most it
// allows; sold, the fares less the gasoline at its price, in whole cents, go
// into the purse of the one who sells them, outcome made, logged as the beat
// rides.
//
// Args: `ecs`. Reads `airframe`, `fares`, `purse` and `show`; writes
// `altitude` and `purse`.

// The step's view of the world, and the lib.
const ecs = args.ecs;
const lib = ecs.lib;

// The player's intent to sell rides, or null when none waits this step.
const intent = ecs.take("rides");
if (intent === null) {
  return;
}
const count = lib.whole_value(intent.value);
const aircraft = lib.aircraft_read(ecs);
const fares = lib.sole_row(
  ecs.rows(
    "SELECT fares.entity AS entity, fares.ride_cents AS ride_cents," +
      " fares.ride_min AS ride_min, fares.gas_cents_gal AS gas_cents_gal" +
      " FROM fares JOIN purse ON purse.entity = fares.entity",
    [],
  ),
  "fares and purse",
);
const show = lib.sole_row(
  ecs.rows("SELECT minutes AS minutes FROM show", []),
  "show",
);
const burn = aircraft.burn_gal_hr;
const minutes = count * fares.ride_min;
const gallons = lib.fuel_gallons(minutes, burn);
const spare = aircraft.tank_gal - lib.fuel_gallons(show.minutes, burn);
if (gallons > spare) {
  const most = Math.floor(spare / lib.fuel_gallons(fares.ride_min, burn));
  ecs.say(
    `${lib.count_text(count, "ride", "rides")} burn ${lib.tenths_text(gallons)} gallons, and the tank` +
      ` spares ${lib.tenths_text(spare)} once the show's ${show.minutes}` +
      ` minutes are kept: ${lib.count_text(most, "ride", "rides")} at most.`,
  );
  ecs.log("rides", intent.value, "refused");
  return;
}
const taken = count * fares.ride_cents;
const gas = Math.round(gallons * fares.gas_cents_gal);
ecs.run([
  {
    sql: "UPDATE altitude SET ft = 0 WHERE entity = ?",
    params: [aircraft.entity],
  },
  {
    sql: "UPDATE purse SET cents = cents + ? WHERE entity = ?",
    params: [taken - gas, fares.entity],
  },
]);
ecs.say(
  `${lib.count_text(count, "ride", "rides")} at ${lib.money_text(fares.ride_cents)} for` +
    ` ${fares.ride_min} minutes: ${lib.money_text(taken)} taken in` +
    ` ${minutes} minutes of flying, on ${lib.tenths_text(gallons)} gallons` +
    ` of gasoline at ${fares.gas_cents_gal} cents, ${lib.money_text(gas)}.` +
    ` ${lib.money_text(taken - gas)} clear, and` +
    ` ${lib.tenths_text(aircraft.tank_gal - gallons)} gallons left for the` +
    ` show's ${show.minutes} minutes.`,
);
ecs.log("rides", intent.value, "made");
