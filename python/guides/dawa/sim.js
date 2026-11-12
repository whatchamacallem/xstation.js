// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Dawa's climb of Everest by the South Col route, the sim of his guide. It
// models the air at each camp by West's formula, the sleep rule of 500 m a
// night, the hour the sun loosens the icefall, a headache told or hidden,
// the weather window, the loads a new climber carries and the oxygen of the
// summit push, where the top and Teo's rescue cannot both happen. It keeps
// one row of `climber`, a row of `climb_log` for each choice and the rows of
// `keepsake`, in the world database `expedition`. A choice that fails is an
// outcome, and a throw is a bug of the table that calls it.
//
// Args: `action`, with its own. `setup`. `icefall` with `start`, a whole
// hour. `morning` with `answer`, `yes` or `no`. `exit`, then `resume`.
// `window` with `wait`, the days ahead of a forecast. `loads` with `carry`,
// `everything` or `one bottle`. `push`. `decide` with `choice`, `rescue` or
// `summit`. `keepsake`. Returns `say`, the text to show, and `outcome`.

// The store of the AI worker the script works through.
const store = engine.store;

// The world database that holds the climb.
const world = "expedition";

// The top in metres: 8848.86 m by the survey Nepal and China announced on 8 December 2020, rounded.
const summit_m = 8849;

// The camps of the South Col route, their heights in metres as commonly given, and the way up to each.
const camps = Object.freeze([
  Object.freeze({
    name: "Base Camp",
    at: "Base Camp",
    m: 5364,
    way: "the Khumbu Glacier",
  }),
  Object.freeze({
    name: "Camp 1",
    at: "Camp 1",
    m: 6065,
    way: "the Khumbu Icefall",
  }),
  Object.freeze({
    name: "Camp 2",
    at: "Camp 2",
    m: 6400,
    way: "the Western Cwm",
  }),
  Object.freeze({
    name: "Camp 3",
    at: "Camp 3",
    m: 7162,
    way: "the Lhotse Face",
  }),
  Object.freeze({
    name: "Camp 4",
    at: "Camp 4 on the South Col",
    m: 7906,
    way: "the Geneva Spur",
  }),
  Object.freeze({
    name: "South Summit",
    at: "the South Summit",
    m: 8749,
    way: "the Southeast Ridge",
  }),
]);

// Air pressure in mmHg at h km is exp(a less b h less c h h): J. B. West, J Appl Physiol 81 (1996) 1850.
const west = Object.freeze({ a: 6.63268, b: 0.1112, c: 0.00149 });

// Oxygen's share of dry air.
const oxygen_share = 0.2094;

// The pressure of water vapour in the lungs at 37 C, in mmHg.
const vapour_mmhg = 47;

// Above 3000 m sleep no more than 500 m higher a night: Wilderness Medical Society Clinical Practice Guidelines, 2019 update.
const sleep_rule = Object.freeze({ above_m: 3000, rise_m: 500 });

// The camp from which the climbers breathe bottled oxygen, the guide's world.
const oxygen_camp = "Camp 3";

// Dawa's rope takes 6 hours through the icefall, and the sun loosens its ice at 9:00, the guide's world.
const icefall = Object.freeze({ hours: 6, sun_hour: 9 });

// The camp where the rope waits for its weather window, the guide's world.
const window_camp = "Camp 2";

// Dawa's limit of the wind on the summit in km/h, the guide's world.
const wind_limit_kmh = 40;

// The radio forecast of the wind on the summit in km/h by the days ahead, the guide's world.
const forecast = Object.freeze([
  Object.freeze({ days: 1, kmh: 45 }),
  Object.freeze({ days: 3, kmh: 25 }),
]);

// Dawa's limit of a new climber's load in kg, his rule in the guide's world.
const load_limit_kg = 12;

// The expedition's gear in kg, and the bottles of your climb, yours and the spare, the guide's world.
const gear = Object.freeze({
  tent_kg: 4,
  stove_kg: 2,
  food_kg: 3,
  bottle_kg: 3,
  bottles: 2,
});

// A bottle's litres, and the litres a minute of a climber and of a sick one, the guide's world.
const oxygen = Object.freeze({ bottle_l: 1200, climb_lpm: 2, sick_lpm: 4 });

// The push leaves at 23:00 for the South Summit at 4:00, the top 90 minutes up, 60 back, 270 down to Camp 4, the guide's world.
const summit_push = Object.freeze({
  leave_hour: 23,
  south_hour: 4,
  up_minutes: 90,
  back_minutes: 60,
  col_minutes: 270,
});

// Metres in a kilometre, minutes in an hour, hours in a day, and a whole in percent.
const units = Object.freeze({
  m_per_km: 1000,
  minutes_per_hour: 60,
  hours_per_day: 24,
  percent: 100,
});

// Dawa's record of never leaving anyone behind, kept or broken.
const record = Object.freeze({ kept: "kept", broken: "broken" });

// The camp of the name, or a throw for a name the route does not hold.
function camp_find(name) {
  const camp = camps.find((each) => each.name === name);
  if (camp === undefined) {
    throw new Error(`dawa: the route has no camp ${JSON.stringify(name)}`);
  }
  return camp;
}

// The place of the camp of the name on the route, from the bottom.
function camp_index(name) {
  return camps.indexOf(camp_find(name));
}

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
function air_text(name, m) {
  const share = (units.percent * oxygen_at(m)) / oxygen_at(0);
  return (
    `${name}, ${m} m: the air presses ${whole_text(pressure_at(m))} mmHg, ` +
    `and you breathe in ${whole_text(oxygen_at(m))} mmHg of oxygen, ` +
    `${whole_text(share)} percent of what the sea gives.`
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

// The one climber row as an object of its columns, or a throw before `setup`.
function climber_read() {
  const [result] = store.sql_run(world, [
    { sql: "SELECT * FROM climber", params: [] },
  ]);
  if (result.rows.length !== 1) {
    throw new Error("dawa: there is no climber before setup");
  }
  const climber = {};
  result.columns.forEach((column, index) => {
    climber[column] = result.rows[0][index];
  });
  return climber;
}

// Writes every column of the climber row, each whole number by `Math.round`.
function climber_write(climber) {
  store.sql_run(world, [
    {
      sql:
        "UPDATE climber SET camp = ?, altitude_m = ?, ams = ?, hidden = ?, " +
        "rest_days = ?, load_kg = ?, bottles = ?, resume_camp = ?, " +
        "exits = ?, high_m = ?, record = ? WHERE id = 1",
      params: [
        climber.camp,
        Math.round(climber.altitude_m),
        Math.round(climber.ams),
        Math.round(climber.hidden),
        Math.round(climber.rest_days),
        Math.round(climber.load_kg),
        Math.round(climber.bottles),
        climber.resume_camp,
        Math.round(climber.exits),
        Math.round(climber.high_m),
        climber.record,
      ],
    },
  ]);
}

// Appends a row to the climb log: the beat, the choice as text and the outcome.
function log_append(beat, choice, outcome) {
  store.sql_run(world, [
    {
      sql: "INSERT INTO climb_log (beat, choice, outcome) VALUES (?, ?, ?)",
      params: [beat, choice, outcome],
    },
  ]);
}

// The argument of the name when it is one of the choices, else a throw for the table's bug.
function choice_get(args, name, choices) {
  const value = args[name];
  if (!choices.includes(value)) {
    throw new Error(
      `dawa: ${name} ${JSON.stringify(value)} is none of ` +
        JSON.stringify(choices),
    );
  }
  return value;
}

// The hour to start the icefall: a whole hour whose crossing ends the same day.
function start_get(args) {
  const start = args.start;
  const ends = start + icefall.hours;
  if (!Number.isInteger(start) || start < 0 || ends >= units.hours_per_day) {
    throw new Error(
      `dawa: start ${JSON.stringify(start)} is no hour whose crossing ` +
        "ends the same day",
    );
  }
  return start;
}

// Throws unless the climber is at the camp, as the table runs the beats in order.
function camp_require(climber, name) {
  if (climber.camp !== name) {
    throw new Error(`dawa: the climber is at ${climber.camp}, not ${name}`);
  }
}

// Puts the climber at the camp, keeping the highest place reached.
function camp_move(climber, camp) {
  climber.camp = camp.name;
  climber.altitude_m = camp.m;
  climber.high_m = Math.max(climber.high_m, camp.m);
}

// Climbs to the camp for a night: a rise over the sleep rule without bottled oxygen adds to the headache.
function camp_climb(climber, camp) {
  const rise = camp.m - climber.altitude_m;
  camp_move(climber, camp);
  const bottled = camp.m >= camp_find(oxygen_camp).m;
  if (camp.m <= sleep_rule.above_m || rise <= sleep_rule.rise_m || bottled) {
    return "";
  }
  climber.ams += 1;
  return (
    ` You sleep ${rise} m higher than last night, over the ` +
    `${sleep_rule.rise_m} m a night the doctors allow.`
  );
}

// The radio forecast as Dawa reads it.
function forecast_text() {
  const winds = forecast.map((each) => {
    const when =
      each.days === 1
        ? "tomorrow"
        : `in ${count_text(each.days, "day", "days")}`;
    return `${each.kmh} km/h ${when}`;
  });
  return `Dawa reads the radio forecast: summit winds ${winds.join(" and ")}.`;
}

// Rests a headache away: a day for each grade, a hidden one having grown by a grade each morning.
function headache_rest(climber) {
  const days = climber.ams;
  const hidden = climber.hidden;
  const once = days - hidden;
  const rest = count_text(days, "day", "days");
  climber.rest_days += days;
  climber.ams = 0;
  climber.hidden = 0;
  if (hidden === 0) {
    return `${rest} of rest at ${climber.camp} and it clears.`;
  }
  const how_long = hidden === 1 ? "a day" : count_text(hidden, "day", "days");
  return (
    `A headache hidden ${how_long} is a worse one: ${rest} of rest at ` +
    `${climber.camp} before it clears, where ${once} would have done if ` +
    "told at once."
  );
}

// The oxygen of the push at the South Summit, in litres and minutes.
function oxygen_reckon() {
  const day = units.hours_per_day;
  const hours = (summit_push.south_hour - summit_push.leave_hour + day) % day;
  const climbed = hours * units.minutes_per_hour;
  const left = oxygen.bottle_l - climbed * oxygen.climb_lpm;
  const round =
    summit_push.up_minutes +
    summit_push.back_minutes +
    summit_push.col_minutes;
  const needed = round * oxygen.climb_lpm;
  const borrowed = needed - left;
  const spare = oxygen.bottle_l - borrowed;
  const teo = summit_push.col_minutes * oxygen.sick_lpm;
  return { left, round, needed, borrowed, spare, teo };
}

// Puts the climber at Base Camp, Dawa's record kept.
function camp_setup() {
  const base = camps[0];
  store.sql_run(world, [
    {
      sql: "INSERT INTO climber VALUES (1, ?, ?, 0, 0, 0, 0, 0, '', 0, ?, ?)",
      params: [
        base.name,
        Math.round(base.m),
        Math.round(base.m),
        record.kept,
      ],
    },
  ]);
  return { say: air_text(base.at, base.m), outcome: "ready" };
}

// Crosses the icefall from the hour given, refused when the sun would loosen the ice first.
function icefall_cross(args) {
  const start = start_get(args);
  const climber = climber_read();
  camp_require(climber, camps[0].name);
  const done = start + icefall.hours;
  const late = done - icefall.sun_hour;
  let say;
  let outcome;
  if (late >= 0) {
    const when =
      late === 0
        ? "just as"
        : `${duration_text(late * units.minutes_per_hour)} after`;
    say =
      `Start at ${hour_text(start)} and the icefall's ` +
      `${duration_text(icefall.hours * units.minutes_per_hour)} keep you ` +
      `under the seracs until ${hour_text(done)}, ${when} the sun loosens ` +
      `the ice at ${hour_text(icefall.sun_hour)}.`;
    outcome = "refused";
  } else {
    const camp = camp_find("Camp 1");
    const rise = camp_climb(climber, camp);
    say =
      `Start at ${hour_text(start)} and you are through the icefall at ` +
      `${hour_text(done)}, ` +
      `${duration_text(-late * units.minutes_per_hour)} before the sun. ` +
      `${air_text(camp.at, camp.m)}${rise}`;
    outcome = "crossed";
    climber_write(climber);
  }
  log_append("icefall", String(start), outcome);
  return { say, outcome };
}

// Answers the morning's question on the way to the window camp: a hidden headache grows, a told one is rested away.
function morning_answer(args) {
  const answer = choice_get(args, "answer", ["no", "yes"]);
  const climber = climber_read();
  const at = camp_index(climber.camp);
  const waiting = camp_index(window_camp);
  if (at < camp_index("Camp 1") || at > waiting) {
    throw new Error(`dawa: there is no morning question at ${climber.camp}`);
  }
  const up = camps[at + 1];
  let say;
  let outcome;
  if (climber.ams > 0 && answer === "no") {
    climber.ams += 1;
    climber.hidden += 1;
    if (at < waiting) {
      const rise = camp_climb(climber, up);
      say = `Dawa takes your word. Up ${up.way} to ${air_text(up.at, up.m)}${rise}`;
    } else {
      say = `Dawa takes your word, and you wait with the rope at ${climber.camp}.`;
    }
    outcome = "hidden";
  } else {
    say =
      climber.ams > 0
        ? headache_rest(climber)
        : "Your head is clear this morning.";
    if (at < waiting) {
      const rise = camp_climb(climber, up);
      say += ` Up ${up.way} to ${air_text(up.at, up.m)}${rise}`;
    }
    say += ` ${forecast_text()}`;
    outcome = "told";
  }
  climber_write(climber);
  log_append("morning", answer, outcome);
  return { say, outcome };
}

// Takes the climber down to the camp below, the exit that always works.
function exit_down() {
  const climber = climber_read();
  if (climber.resume_camp !== "") {
    throw new Error("dawa: the climber is down already, waiting to resume");
  }
  const at = camp_index(climber.camp);
  climber.resume_camp = climber.camp;
  climber.exits += 1;
  let say;
  if (at === 0) {
    say = "We are at the bottom already.";
  } else {
    const camp = camps[at - 1];
    const drop = climber.altitude_m - camp.m;
    camp_move(climber, camp);
    say =
      `Dawa clips you to the fixed line and takes you down ${drop} m to ` +
      air_text(camp.at, camp.m);
  }
  climber_write(climber);
  log_append("exit", climber.resume_camp, "down");
  return { say, outcome: "down" };
}

// Brings the climber back up to the camp the exit left.
function resume_up() {
  const climber = climber_read();
  if (climber.resume_camp === "") {
    throw new Error("dawa: there is no exit to resume from");
  }
  const camp = camp_find(climber.resume_camp);
  const rise = camp.m - climber.altitude_m;
  camp_move(climber, camp);
  climber.resume_camp = "";
  const say =
    rise === 0
      ? `We go on from ${air_text(camp.at, camp.m)}`
      : `Back up ${rise} m to ${air_text(camp.at, camp.m)}`;
  climber_write(climber);
  log_append("resume", camp.name, "up");
  return { say, outcome: "up" };
}

// Judges a weather window by its forecast wind against Dawa's limit.
function window_judge(args) {
  const days = forecast.map((each) => each.days);
  const wait = choice_get(args, "wait", days);
  const climber = climber_read();
  camp_require(climber, window_camp);
  const wind = forecast.find((each) => each.days === wait);
  let say;
  let outcome;
  if (wind.kmh > wind_limit_kmh) {
    const when =
      wait === 1
        ? "Tomorrow's"
        : `In ${count_text(wait, "day", "days")} the`;
    say =
      `${when} ${wind.kmh} km/h on the summit is over Dawa's ` +
      `${wind_limit_kmh}: that window is not real.`;
    outcome = "false";
  } else {
    climber.rest_days += wait;
    say =
      `${count_text(wait, "more day", "more days")} of rest at ` +
      `${climber.camp}, and the jet stream lifts: ${wind.kmh} km/h on the ` +
      `summit, under Dawa's ${wind_limit_kmh}. The window is real.`;
    outcome = "real";
    climber_write(climber);
  }
  log_append("window", String(wait), outcome);
  return { say, outcome };
}

// Packs the loads for the high camps, refused over Dawa's limit, else up to the Col.
function loads_pack(args) {
  const carry = choice_get(args, "carry", ["everything", "one bottle"]);
  const climber = climber_read();
  camp_require(climber, window_camp);
  const bottles = carry === "everything" ? gear.bottles : 1;
  const kg =
    gear.tent_kg + gear.stove_kg + gear.food_kg + bottles * gear.bottle_kg;
  const carried = count_text(bottles, "bottle", "bottles");
  let say;
  let outcome;
  if (kg > load_limit_kg) {
    const what = carry === "everything" ? "Everything" : "That";
    say =
      `${what} is the tent at ${gear.tent_kg} kg, the stove at ` +
      `${gear.stove_kg}, food at ${gear.food_kg} and ${carried} at ` +
      `${gear.bottle_kg} each: ${kg} kg, over the ${load_limit_kg} Dawa ` +
      "lets a new climber carry.";
    outcome = "refused";
  } else {
    const at = camp_index(window_camp);
    const high = camps[at + 1];
    const col = camps[at + 2];
    climber.load_kg = kg;
    climber.bottles = bottles;
    const rises = camp_climb(climber, high) + camp_climb(climber, col);
    say =
      `The tent, the stove, food and ${carried}: ${kg} kg, within Dawa's ` +
      `${load_limit_kg}, and he carries the spare. Up ${high.way} to ` +
      `${high.name} at ${high.m} m, then to ${air_text(col.at, col.m)}` +
      `${rises} On oxygen from ${oxygen_camp} up; we leave at ` +
      `${hour_text(summit_push.leave_hour)} for the top.`;
    outcome = "carried";
    climber_write(climber);
  }
  log_append("loads", carry, outcome);
  return { say, outcome };
}

// Climbs from the Col to the South Summit, where Teo goes down and the oxygen cannot cover both.
function push_go() {
  const climber = climber_read();
  const col = camp_find("Camp 4");
  const south = camp_find("South Summit");
  camp_require(climber, col.name);
  const reckoned = oxygen_reckon();
  if (reckoned.spare >= reckoned.teo) {
    throw new Error("dawa: the spare covers the top and Teo, so no stake");
  }
  camp_move(climber, south);
  climber_write(climber);
  log_append("push", "go", "stopped");
  const say =
    `${air_text(sentence_start(south.at), south.m)} It is ` +
    `${hour_text(summit_push.south_hour)}, the top is ${summit_m - south.m} ` +
    "m above, and Teo is down, his bottle empty. Your bottle holds " +
    `${reckoned.left} litres, ` +
    `${duration_text(reckoned.left / oxygen.climb_lpm)} at ` +
    `${oxygen.climb_lpm} litres a minute. The top and back down to the Col ` +
    `takes ${duration_text(reckoned.round)} and ${reckoned.needed} litres, ` +
    `${reckoned.borrowed} of them from Dawa's spare, which leaves it ` +
    `${reckoned.spare}, and Teo needs ${reckoned.teo} at ` +
    `${oxygen.sick_lpm} litres a minute to get down. Not both.`;
  return { say, outcome: "stopped" };
}

// Follows the climber's call: Teo taken down on the spare, or the top and the record broken.
function decide_call(args) {
  const choice = choice_get(args, "choice", ["rescue", "summit"]);
  const climber = climber_read();
  const col = camp_find("Camp 4");
  camp_require(climber, camp_find("South Summit").name);
  const reckoned = oxygen_reckon();
  const down = duration_text(summit_push.col_minutes);
  let say;
  let outcome;
  if (choice === "rescue") {
    const used = summit_push.col_minutes * oxygen.climb_lpm;
    if (reckoned.teo > oxygen.bottle_l || used > reckoned.left) {
      throw new Error("dawa: the rescue runs out of oxygen, so no choice");
    }
    say =
      `Teo goes on Dawa's spare at ${oxygen.sick_lpm} litres a minute: ` +
      `${reckoned.teo} of its ${oxygen.bottle_l} litres for the ${down} ` +
      `down to the South Col. You use ${used} of your ${reckoned.left}. ` +
      `Everyone reaches ${col.name}, and Dawa has still never left anyone ` +
      "behind.";
    outcome = "rescued";
  } else {
    const lasts = reckoned.spare / oxygen.sick_lpm;
    const short = summit_push.col_minutes - lasts;
    const topped =
      summit_push.south_hour * units.minutes_per_hour + summit_push.up_minutes;
    climber.high_m = Math.max(climber.high_m, summit_m);
    climber.record = record.broken;
    say =
      `You and Dawa go on, and at ${clock_text(topped)} you stand on the ` +
      `top, ${summit_m} m, on ${reckoned.borrowed} litres of his spare. Teo ` +
      `goes down with the other rope on the ${reckoned.spare} left, ` +
      `${duration_text(lasts)} at ${oxygen.sick_lpm} litres a minute of the ` +
      `${down} he needs: his oxygen runs out ${short} minutes above the Col, ` +
      "and they carry him in alive. Dawa's record is broken.";
    outcome = "summited";
  }
  camp_move(climber, col);
  climber_write(climber);
  log_append("decide", choice, outcome);
  return { say, outcome };
}

// Gives the photograph of the high point and Dawa's scarf, by the call the climber made.
function keepsake_give() {
  const [decided] = store.sql_run(world, [
    {
      sql: "SELECT outcome FROM climb_log WHERE beat = 'decide'",
      params: [],
    },
  ]);
  if (decided.rows.length !== 1) {
    throw new Error("dawa: there is no decision to remember");
  }
  const south = camp_find("South Summit");
  const photograph =
    decided.rows[0][0] === "rescued"
      ? `A photograph from ${south.at}, ${south.m} m, ` +
        `${summit_m - south.m} m below the top, the morning you took Teo down.`
      : `A photograph from the top, ${summit_m} m.`;
  const scarf = "A white scarf from Dawa.";
  store.sql_run(world, [
    {
      sql: "INSERT INTO keepsake VALUES (?, ?)",
      params: ["photograph", photograph],
    },
    { sql: "INSERT INTO keepsake VALUES (?, ?)", params: ["scarf", scarf] },
  ]);
  return { say: `${photograph} ${scarf}`, outcome: "kept" };
}

// The function of each action by its name.
const actions = Object.freeze({
  setup: camp_setup,
  icefall: icefall_cross,
  morning: morning_answer,
  exit: exit_down,
  resume: resume_up,
  window: window_judge,
  loads: loads_pack,
  push: push_go,
  decide: decide_call,
  keepsake: keepsake_give,
});

if (!Object.hasOwn(actions, args.action)) {
  throw new Error(`dawa: there is no action ${JSON.stringify(args.action)}`);
}
return store.transaction_run(() => actions[args.action](args));
