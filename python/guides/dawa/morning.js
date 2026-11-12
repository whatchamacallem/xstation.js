// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The step system `dawa_morning`, kept at /_files/script/dawa_morning.js:
// takes the intent `morning`, its value `no` or `yes`, the player's answer to
// whether the head hurts, on the mornings from the camp above the bottom to
// the staging camp. A headache hidden grows a grade and counts a morning
// hidden; a headache told is rested away, a day of rest for each grade; a
// clear head is said so. Below the staging camp the rope then climbs on at
// once to the camp above, its time stated by no band, with the air there and
// a night over the sleep rule, and a told answer ends with the forecast.
//
// Args: `ecs`. Reads `at`, `camp`, `staging`, `ams`, `rest`, `oxygen` and
// `forecast`; writes `ams`, `rest`, `at` and `high`. Says the morning, and
// logs the beat `morning` with the answer and `hidden` or `told`.

// The step's view of the world, with its lib.
const ecs = args.ecs;
const lib = ecs.lib;

// The radio forecast as Dawa reads it, the forecasts in the order of their days ahead.
function forecast_text() {
  const forecasts = ecs.rows(
    "SELECT days_ahead, kmh FROM forecast ORDER BY days_ahead",
    [],
  );
  const winds = forecasts.map((each) => {
    const when =
      each.days_ahead === 1
        ? "tomorrow"
        : `in ${lib.count_text(each.days_ahead, "day", "days")}`;
    return `${each.kmh} km/h ${when}`;
  });
  return `Dawa reads the radio forecast: summit winds ${winds.join(" and ")}.`;
}

// A headache rested away at the camp: a day for each grade, a hidden one having grown a grade each morning.
function rest_text(head, camp) {
  const once = head.grade - head.hidden;
  const rest = lib.count_text(head.grade, "day", "days");
  if (head.hidden === 0) {
    return `${rest} of rest at ${camp.name} and it clears.`;
  }
  const how_long =
    head.hidden === 1 ? "a day" : lib.count_text(head.hidden, "day", "days");
  return (
    `A headache hidden ${how_long} is a worse one: ${rest} of rest at ` +
    `${camp.name} before it clears, where ${once} would have done if ` +
    "told at once."
  );
}

// Answers the morning's question, then climbs on below the staging camp.
function morning_answer(intent) {
  const answer = intent.value;
  if (answer !== "no" && answer !== "yes") {
    throw new Error(
      `dawa_morning: the value ${JSON.stringify(answer)} is neither no nor` +
        " yes.",
    );
  }
  const player = intent.entity;
  const here = lib.climber_camp(ecs, player);
  const staging = lib.row_read(
    ecs,
    "SELECT camp.ord AS ord FROM staging JOIN camp" +
      " ON camp.entity = staging.camp",
    [],
  );
  if (here.ord <= lib.route_ends(ecs).bottom || here.ord > staging.ord) {
    throw new Error(`dawa_morning: there is no morning question at ${here.name}.`);
  }
  const head = lib.row_read(
    ecs,
    "SELECT ams.grade AS grade, ams.hidden AS hidden, rest.days AS days" +
      " FROM ams JOIN rest ON rest.entity = ams.entity WHERE ams.entity = ?",
    [player],
  );
  const after = { grade: head.grade, hidden: head.hidden, days: head.days };
  const climbs = here.ord < staging.ord;
  const hiding = head.grade > 0 && answer === "no";
  const said = [];
  const statements = [];
  if (hiding) {
    after.grade += 1;
    after.hidden += 1;
    said.push(
      climbs
        ? "Dawa takes your word."
        : `Dawa takes your word, and you wait with the rope at ${here.name}.`,
    );
  } else {
    said.push(
      head.grade > 0
        ? rest_text(head, here)
        : "Your head is clear this morning.",
    );
    after.days += head.grade;
    after.grade = 0;
    after.hidden = 0;
  }
  if (climbs) {
    const up = lib.route_camp(ecs, here.ord + 1);
    said.push(`Up ${up.way} to ${lib.air_text(up.place, up.altitude_m)}`);
    const bottled = up.altitude_m >= lib.oxygen_read(ecs).altitude_m;
    const night = lib.night_text(here.altitude_m, up.altitude_m, bottled);
    if (night !== null) {
      after.grade += 1;
      said.push(night);
    }
    statements.push(...lib.rope_move(here.entity, up.entity));
  }
  if (!hiding) {
    said.push(forecast_text());
  }
  statements.push(
    {
      sql: "UPDATE ams SET grade = ?, hidden = ? WHERE entity = ?",
      params: [after.grade, after.hidden, player],
    },
    {
      sql: "UPDATE rest SET days = ? WHERE entity = ?",
      params: [after.days, player],
    },
  );
  ecs.run(statements);
  ecs.say(said.join(" "));
  ecs.log("morning", answer, hiding ? "hidden" : "told");
}

const intent = ecs.take("morning");
if (intent !== null) {
  morning_answer(intent);
}
