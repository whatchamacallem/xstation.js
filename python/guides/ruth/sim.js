// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Ruth Calloway's flight model, turn based: each run is one turn the player
// flies in a Curtiss JN-4D, by the figures of its 1918 specifications, the
// Curtiss JN4-D Specifications and Operating Instructions as reproduced at
// airminded.net/jenny/jn4_spec.html, and the physics of a level turn, a loop
// of two arcs, a weightless roll, a glide and a landing in the wind. Its state
// is the one row of `jenny` in the world `summer`, with `flight`, the log of
// the turns, and `keepsake`. Args: `action`, one of `setup` with `partner`,
// `climb`, `exit`, `resume`, `turn` with `bank` in degrees, `loop` with
// `entry_mph`, `roll` with `nose_deg`, `buzz` with `feet`, `rides` with
// `count`, `race` with `throttle`, `full throttle` or `cruise`, `wing_walk`
// with `walker`, Ruth or the partner, `field` with `field`, `north` or
// `south`, `landing` with `direction`, `into the wind` or `with the wind`,
// and `keepsake`. Numbers are whole. Returns `say`, the text the page shows,
// and `outcome`, one word of the action's. A choice that fails is an outcome;
// a throw is a broken table: an unknown action or args of the wrong form.

// The store of the AI worker, which holds the world's tables.
const store = engine.store;

// The world database of the guide, which holds the tables of the sim.
const WORLD = "summer";

// 1918 specifications: gross weight loaded, two of 165 pounds and full fuel.
const GROSS_LB = 1920;
// 1918 specifications: total supporting surface, square feet.
const WING_SQFT = 352.56;
// 1918 specifications: the `OX-5` rated at 1400 rpm, horsepower.
const HP = 90;
// 1918 specifications: speed, maximum, horizontal flight, mph.
const MAX_MPH = 75;
// 1918 specifications: speed, minimum, horizontal flight, the stall at 1 g.
const MIN_MPH = 45;
// 1918 specifications: climb in 10 minutes, feet.
const CLIMB_FT = 2000;
// 1918 specifications: the minutes of that climb.
const CLIMB_MIN = 10;
// 1918 specifications: fuel tank capacity, gallons.
const TANK_GAL = 21;
// 1918 specifications: fuel consumption, gallons an hour.
const BURN_GAL_HR = 9;
// 1918 operating instructions: final leveling off about fifty feet up.
const LEVEL_OFF_FT = 50;
// P. M. Bowers, Curtiss Aircraft 1907 to 1947 (1979), p. 156: cruise, mph.
const CRUISE_MPH = 60;
// B. van der Zalm (2018), aircraftinvestigation.info: lift to drag, computed.
const GLIDE_RATIO = 10.66;
// Standard gravity, feet a second a second.
const G = 32.174;
// Feet a second in a mile an hour: 5280 feet over 3600 seconds.
const FPS_PER_MPH = 22 / 15;
// Ruth's technique: the pull at the bottom of the loop, in g.
const LOOP_PULL_G = 4;
// Ruth's technique: light over the top of the loop, in g.
const LOOP_TOP_G = 0.5;
// Ruth's count for a roll, seconds.
const ROLL_SECONDS = 4;
// The introduction, "Five dollars buys ten minutes": a ride, cents.
const RIDE_CENTS = 500;
// The introduction: the minutes a ride buys.
const RIDE_MIN = 10;
// U.S. DOE Vehicle Technologies Office, Fact 915 (2016): 1929 pump price.
const GAS_CENTS_GAL = 21;
// The Henry Ford: the Model T's top speed of about 45 mph.
const MOTORCAR_MPH = 45;
// The guide's world: the day's wind, from the north, mph.
const WIND_MPH = 15;
// The guide's world: the county road race, miles.
const RACE_MI = 5;
// The guide's world: the fair's race purse, cents.
const PURSE_CENTS = 2500;
// The guide's world: the evening show's flying, minutes.
const SHOW_MIN = 40;
// The guide's world: where Ruth teaches, feet.
const STUNT_FT = 2000;
// The guide's world: the wing walk's height, where the engine quits, feet.
const SHOW_FT = 1000;
// The guide's world: the north hayfield's distance, miles.
const NORTH_MI = 1.5;
// The guide's world: the south pasture's distance, miles.
const SOUTH_MI = 3;

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

// The throttles of the race by the choice's text: the words and the airspeed.
const THROTTLES = Object.freeze({
  "full throttle": { name: "Full throttle", mph: MAX_MPH },
  cruise: { name: "Cruise", mph: CRUISE_MPH },
});

// The fields in reach by the choice's text, the wind being from the north.
const FIELDS = Object.freeze({
  north: { name: "north hayfield", miles: NORTH_MI, wind: "into", sign: -1 },
  south: { name: "south pasture", miles: SOUTH_MI, wind: "with", sign: 1 },
});

// The ways to land by the choice's text: the words and the wind's sign.
const LANDINGS = Object.freeze({
  "into the wind": { name: "Into the wind", sign: -1 },
  "with the wind": { name: "With the wind", sign: 1 },
});

// What a handbill brags of: a beat and outcome of `flight`, then its words.
const FEATS = Object.freeze([
  ["loop", "made", "loops"],
  ["roll", "made", "rolls"],
  ["wing_walk", "walked", "the wing walk"],
  ["race", "won", "a motorcar beaten"],
]);

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

// The whole number an argument holds, thrown when it holds none.
function whole_arg(args, name) {
  const value = args[name];
  if (!Number.isInteger(value)) {
    throw new Error(`internal error: ruth needs a whole number at ${name}`);
  }
  return value;
}

// The text an argument holds, thrown when it holds none.
function text_arg(args, name) {
  const value = args[name];
  if (typeof value !== "string") {
    throw new Error(`internal error: ruth needs a text at ${name}`);
  }
  return value;
}

// The member of a table of choices, thrown when the choice is not one.
function choice_get(table, choice) {
  if (!Object.hasOwn(table, choice)) {
    throw new Error(`internal error: ruth has no choice ${choice}`);
  }
  return table[choice];
}

// Feet a second at a speed in miles an hour.
function speed_feet(mph) {
  return mph * FPS_PER_MPH;
}

// Gallons burnt in minutes of flying.
function fuel_gallons(minutes) {
  return (minutes * BURN_GAL_HR) / MINUTES_PER_HOUR;
}

// The book's rate of climb, and the minutes and gallons between two heights.
function climb_cost(from_ft, to_ft) {
  const rate = CLIMB_FT / CLIMB_MIN;
  const minutes = (to_ft - from_ft) / rate;
  return { rate, minutes, gallons: fuel_gallons(minutes) };
}

// The one row of `jenny`: the partner, the heights, the exits and the purse.
function jenny_read() {
  const [result] = store.sql_run(WORLD, [
    {
      sql:
        "SELECT partner, altitude_ft, resume_ft, exits, purse_cents" +
        " FROM jenny WHERE id = 1",
      params: [],
    },
  ]);
  const [partner, altitude_ft, resume_ft, exits, purse_cents] =
    result.rows[0];
  return { partner, altitude_ft, resume_ft, exits, purse_cents };
}

// Writes the row of `jenny` back, all but the partner.
function jenny_write(jenny) {
  store.sql_run(WORLD, [
    {
      sql:
        "UPDATE jenny SET altitude_ft = ?, resume_ft = ?, exits = ?," +
        " purse_cents = ? WHERE id = 1",
      params: [
        jenny.altitude_ft,
        jenny.resume_ft,
        jenny.exits,
        jenny.purse_cents,
      ],
    },
  ]);
}

// Logs a turn in `flight` and returns its say and its outcome.
function turn_end(beat, choice, say, outcome) {
  store.sql_run(WORLD, [
    {
      sql: "INSERT INTO flight (beat, choice, outcome) VALUES (?, ?, ?)",
      params: [beat, choice, outcome],
    },
  ]);
  return { say, outcome };
}

// Sets out the Jenny on the ground with the partner, and tells her figures.
function jenny_setup(args) {
  const partner = text_arg(args, "partner");
  store.sql_run(WORLD, [
    { sql: "INSERT INTO jenny VALUES (1, ?, 0, 0, 0, 0)", params: [partner] },
  ]);
  const say =
    `The Jenny: a Curtiss JN-4D with a ${HP} horsepower OX-5,` +
    ` ${WING_SQFT} square feet of wing, and ${GROSS_LB} pounds aboard with` +
    ` the two of us and ${TANK_GAL} gallons of gasoline. She stalls at` +
    ` ${MIN_MPH} mph, cruises at ${CRUISE_MPH} and tops out at ${MAX_MPH}.`;
  return { say, outcome: "ready" };
}

// Climbs at the book's rate to where Ruth teaches.
function climb_fly() {
  const jenny = jenny_read();
  const cost = climb_cost(jenny.altitude_ft, STUNT_FT);
  jenny.altitude_ft = STUNT_FT;
  jenny_write(jenny);
  const say =
    `Up to ${STUNT_FT} feet in ${whole_text(cost.minutes)} minutes, the` +
    ` book's ${whole_text(cost.rate)} feet a minute, on` +
    ` ${tenths_text(cost.gallons)} gallons of gasoline.`;
  return turn_end("climb", String(STUNT_FT), say, "made");
}

// Sets her down like a feather, as Ruth promised: a glide, throttle closed.
function feather_land() {
  const jenny = jenny_read();
  const height = jenny.altitude_ft;
  jenny.exits += 1;
  if (height === 0) {
    jenny_write(jenny);
    const say = "We're on the grass already.";
    return turn_end("exit", String(height), say, "grounded");
  }
  const speed = speed_feet(CRUISE_MPH);
  const distance = height * GLIDE_RATIO;
  const sink = speed / GLIDE_RATIO;
  const seconds = Math.round(distance / speed);
  jenny.altitude_ft = 0;
  jenny.resume_ft = height;
  jenny_write(jenny);
  const say =
    `Throttle closed at ${height} feet. Gliding at ${CRUISE_MPH} mph,` +
    ` ${GLIDE_RATIO} feet on for every foot down, she sinks` +
    ` ${tenths_text(sink)} feet a second and settles onto the grass` +
    ` ${whole_text(distance)} feet on, in ${clock_text(seconds)}, like a` +
    ` feather.`;
  return turn_end("exit", String(height), say, "landed");
}

// Climbs back to the height the exit left, or waits when there is none.
function climb_resume() {
  const jenny = jenny_read();
  const height = jenny.resume_ft;
  if (height === 0) {
    return turn_end("resume", String(height), "Ready when you are.", "made");
  }
  const cost = climb_cost(jenny.altitude_ft, height);
  jenny.altitude_ft = height;
  jenny.resume_ft = 0;
  jenny_write(jenny);
  const say =
    `Back up to ${height} feet in ${whole_text(cost.minutes)} minutes, on` +
    ` ${tenths_text(cost.gallons)} gallons more.`;
  return turn_end("resume", String(height), say, "made");
}

// A level turn at cruise: its load, the stall speed it brings, its circle.
function bank_turn(args) {
  const bank = whole_arg(args, "bank");
  const angle = bank * RADIANS_PER_DEGREE;
  const load = 1 / Math.cos(angle);
  const stall = MIN_MPH * Math.sqrt(load);
  const opening =
    `At ${bank} degrees of bank she pulls ${tenths_text(load)} g and` +
    ` stalls at ${whole_text(stall)} mph`;
  if (stall > CRUISE_MPH) {
    const say =
      `${opening}, over your ${CRUISE_MPH}: the wing quits and Ruth` +
      ` catches her.`;
    return turn_end("turn", String(bank), say, "stalled");
  }
  const speed = speed_feet(CRUISE_MPH);
  const pull = G * Math.tan(angle);
  const radius = (speed * speed) / pull;
  const seconds = (2 * Math.PI * speed) / pull;
  const say =
    `${opening}, under your ${CRUISE_MPH}: a circle ${whole_text(radius)}` +
    ` feet in radius, flown round in ${whole_text(seconds)} seconds.`;
  return turn_end("turn", String(bank), say, "made");
}

// A loop of two arcs, energy kept: made when the top is fast enough to fly.
function loop_fly(args) {
  const entry = whole_arg(args, "entry_mph");
  const kept = (1 - 2 / (LOOP_PULL_G - 1)) / (1 + 2 / (LOOP_TOP_G + 1));
  const needed = MIN_MPH * Math.sqrt(LOOP_TOP_G);
  const wanted = needed / Math.sqrt(kept);
  const bottom = speed_feet(entry);
  const top_squared = bottom * bottom * kept;
  const top = Math.sqrt(top_squared) / FPS_PER_MPH;
  if (top < needed) {
    const say =
      `Pulling ${LOOP_PULL_G} g at ${entry} mph, she comes over the top at` +
      ` ${whole_text(top)} mph, under the ${whole_text(needed)} she needs` +
      ` for ${LOOP_TOP_G} g up there: she hangs, falls off sideways, and` +
      ` Ruth flies her out. The loop wants ${whole_text(wanted)} mph at` +
      ` the bottom.`;
    return turn_end("loop", String(entry), say, "fell");
  }
  const cruise = speed_feet(CRUISE_MPH);
  const dive = (bottom * bottom - cruise * cruise) / (2 * G);
  const bottom_radius = (bottom * bottom) / (G * (LOOP_PULL_G - 1));
  const top_radius = top_squared / (G * (LOOP_TOP_G + 1));
  const say =
    `Dive ${whole_text(dive)} feet to ${entry} mph and pull ${LOOP_PULL_G}` +
    ` g: she comes over the top at ${whole_text(top)} mph,` +
    ` ${whole_text(bottom_radius + top_radius)} feet above where you` +
    ` pulled, and down the back at ${entry} again. A loop.`;
  return turn_end("loop", String(entry), say, "made");
}

// A roll at full speed, weightless for Ruth's count: the height it moves.
function roll_fly(args) {
  const nose = whole_arg(args, "nose_deg");
  const speed = speed_feet(MAX_MPH);
  const fall = (G * ROLL_SECONDS * ROLL_SECONDS) / 2;
  const rise = speed * Math.sin(nose * RADIANS_PER_DEGREE) * ROLL_SECONDS;
  const change = rise - fall;
  const moved = Math.round(change);
  const wanted =
    Math.asin((G * ROLL_SECONDS) / (2 * speed)) / RADIANS_PER_DEGREE;
  const jenny = jenny_read();
  jenny.altitude_ft += moved;
  jenny_write(jenny);
  const opening =
    `Nose ${nose} degrees up at ${MAX_MPH} mph and ${ROLL_SECONDS}` +
    ` seconds round: she comes out`;
  if (change < 0) {
    const say =
      `${opening} ${-moved} feet low. A roll at ${MAX_MPH} wants` +
      ` ${whole_text(wanted)} degrees of nose to keep her height.`;
    return turn_end("roll", String(nose), say, "sank");
  }
  const say = `${opening} ${moved} feet high. A roll.`;
  return turn_end("roll", String(nose), say, "made");
}

// Buzzes Main Street at the height picked, never under the book's.
function street_buzz(args) {
  const feet = whole_arg(args, "feet");
  if (feet < LEVEL_OFF_FT) {
    const say =
      `Under the ${LEVEL_OFF_FT} feet the book gives for leveling off?` +
      ` I'm bold. I'm not stupid.`;
    return turn_end("buzz", String(feet), say, "refused");
  }
  const jenny = jenny_read();
  jenny.altitude_ft = feet;
  jenny_write(jenny);
  const say =
    `Down Main Street at ${feet} feet and ${MAX_MPH} mph,` +
    ` ${whole_text(speed_feet(MAX_MPH))} feet a second, and the handbills` +
    ` go over the side.`;
  return turn_end("buzz", String(feet), say, "made");
}

// Sells rides all afternoon, keeping gasoline for the show: what is clear.
function rides_sell(args) {
  const count = whole_arg(args, "count");
  const minutes = count * RIDE_MIN;
  const gallons = fuel_gallons(minutes);
  const spare = TANK_GAL - fuel_gallons(SHOW_MIN);
  if (gallons > spare) {
    const most = Math.floor(spare / fuel_gallons(RIDE_MIN));
    const say =
      `${count} rides burn ${tenths_text(gallons)} gallons, and the tank` +
      ` spares ${tenths_text(spare)} once the show's ${SHOW_MIN} minutes` +
      ` are kept: ${most} rides at most.`;
    return turn_end("rides", String(count), say, "refused");
  }
  const taken = count * RIDE_CENTS;
  const gas = Math.round(gallons * GAS_CENTS_GAL);
  const jenny = jenny_read();
  jenny.altitude_ft = 0;
  jenny.purse_cents += taken - gas;
  jenny_write(jenny);
  const say =
    `${count} rides at ${money_text(RIDE_CENTS)} for ${RIDE_MIN} minutes:` +
    ` ${money_text(taken)} taken in ${minutes} minutes of flying, on` +
    ` ${tenths_text(gallons)} gallons of gasoline at ${GAS_CENTS_GAL}` +
    ` cents, ${money_text(gas)}. ${money_text(taken - gas)} clear, and` +
    ` ${tenths_text(TANK_GAL - gallons)} gallons left for the show's` +
    ` ${SHOW_MIN} minutes.`;
  return turn_end("rides", String(count), say, "made");
}

// Races the motorcar down the county road, into the wind, for the purse.
function road_race(args) {
  const throttle = text_arg(args, "throttle");
  const { name, mph } = choice_get(THROTTLES, throttle);
  const ground = mph - WIND_MPH;
  const course = RACE_MI * SECONDS_PER_HOUR;
  const plane = Math.round(course / ground);
  const car = Math.round(course / MOTORCAR_MPH);
  const jenny = jenny_read();
  jenny.altitude_ft = LEVEL_OFF_FT;
  const opening =
    `${name}: ${mph} mph into a ${WIND_MPH} mph wind is ${ground} over the` +
    ` road, ${tenths_text(RACE_MI)} miles in ${clock_text(plane)}. The` +
    ` motorcar at ${MOTORCAR_MPH} takes ${clock_text(car)}.`;
  if (plane < car) {
    jenny.purse_cents += PURSE_CENTS;
    jenny_write(jenny);
    const say =
      `${opening} You win by ${clock_text(car - plane)} and the fair's` +
      ` ${money_text(PURSE_CENTS)} purse: ${money_text(jenny.purse_cents)}` +
      ` in the cigar box.`;
    return turn_end("race", throttle, say, "won");
  }
  jenny_write(jenny);
  const say =
    `${opening} A dead heat, and the fair keeps its` +
    ` ${money_text(PURSE_CENTS)} purse.`;
  return turn_end("race", throttle, say, "tied");
}

// The wing walk at the show, then the engine quits over open country.
function wing_walk(args) {
  const walker = text_arg(args, "walker");
  const jenny = jenny_read();
  const walks = {
    Ruth: "Ruth walks the top wing while you hold her straight and level",
    [jenny.partner]:
      "You walk the top wing while Ruth holds her straight and level",
  };
  const opening = choice_get(walks, walker);
  jenny.altitude_ft = SHOW_FT;
  jenny_write(jenny);
  const say =
    `${opening} at ${CRUISE_MPH} mph and ${SHOW_FT} feet. Then, over open` +
    ` country, the OX-5 coughs and quits: ${SHOW_FT} feet up, the wind` +
    ` ${WIND_MPH} mph from the north, the north hayfield` +
    ` ${tenths_text(NORTH_MI)} miles off and the south pasture` +
    ` ${tenths_text(SOUTH_MI)}.`;
  return turn_end("wing_walk", walker, say, "walked");
}

// Glides for a field with the engine dead: how far her height carries her.
function field_glide(args) {
  const choice = text_arg(args, "field");
  const field = choice_get(FIELDS, choice);
  const height = jenny_read().altitude_ft;
  const ground = CRUISE_MPH + field.sign * WIND_MPH;
  const reach = Math.round((height * GLIDE_RATIO * ground) / CRUISE_MPH);
  const margin = reach - Math.round(field.miles * FEET_PER_MILE);
  const opening =
    `Gliding ${choice} ${field.wind} the wind at ${ground} mph over the` +
    ` ground, ${height} feet carries you ${reach} feet,` +
    ` ${tenths_text(reach / FEET_PER_MILE)} miles, and the ${field.name}` +
    ` is ${tenths_text(field.miles)} miles off:`;
  if (margin < 0) {
    const say = `${opening} ${-margin} feet short.`;
    return turn_end("field", choice, say, "short");
  }
  const say = `${opening} ${margin} feet to spare.`;
  return turn_end("field", choice, say, "reached");
}

// Touches down at the stall through the air: her speed over the hay.
function hay_landing(args) {
  const direction = text_arg(args, "direction");
  const landing = choice_get(LANDINGS, direction);
  const ground = MIN_MPH + landing.sign * WIND_MPH;
  const jenny = jenny_read();
  jenny.altitude_ft = 0;
  jenny_write(jenny);
  const opening =
    `${landing.name} she touches down at ${MIN_MPH} mph through the air` +
    ` and ${ground} over the hay, and rolls`;
  if (ground < MIN_MPH) {
    const say = `${opening} to a stop. Down safe.`;
    return turn_end("landing", direction, say, "landed");
  }
  const say = `${opening} long, past the fence posts. Down, and lucky.`;
  return turn_end("landing", direction, say, "landed long");
}

// Prints the handbill, the partner's name beside Ruth's, and keeps it.
function handbill_print() {
  const jenny = jenny_read();
  const [result] = store.sql_run(WORLD, [
    { sql: "SELECT beat, outcome FROM flight", params: [] },
  ]);
  const flown = new Set(result.rows.map((row) => row[0] + " " + row[1]));
  const feats = FEATS.filter((feat) => flown.has(feat[0] + " " + feat[1]));
  const words = feats.map((feat) => feat[2]);
  const list = words.length > 0 ? ": " + list_text(words) : "";
  const text =
    `RUTH CALLOWAY AND ${jenny.partner.toUpperCase()}, AERIAL ACROBATS` +
    `${list}! Rides ${money_text(RIDE_CENTS)} for ${RIDE_MIN} minutes.`;
  store.sql_run(WORLD, [
    { sql: "INSERT INTO keepsake VALUES (?, ?)", params: ["handbill", text] },
  ]);
  return { say: text, outcome: "kept" };
}

// The actions by the name the table gives at `action`.
const actions = Object.freeze({
  setup: jenny_setup,
  climb: climb_fly,
  exit: feather_land,
  resume: climb_resume,
  turn: bank_turn,
  loop: loop_fly,
  roll: roll_fly,
  buzz: street_buzz,
  rides: rides_sell,
  race: road_race,
  wing_walk,
  field: field_glide,
  landing: hay_landing,
  keepsake: handbill_print,
});

if (!Object.hasOwn(actions, args.action)) {
  throw new Error(`internal error: ruth has no action ${args.action}`);
}
return store.transaction_run(() => actions[args.action](args));
