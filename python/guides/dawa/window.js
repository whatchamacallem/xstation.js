// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The step system `dawa_window`, kept at /_files/script/dawa_window.js: takes
// the intent `window`, its value the days ahead of a forecast, at the staging
// camp. A forecast wind over Dawa's limit is a window that is not real, an
// outcome; a wind within it is real, and the player rests the days waited.
// A value no forecast holds is a bug of the table, and throws.
//
// Args: `ecs`. Reads `at`, `camp`, `staging`, `forecast` and `limits`;
// writes `rest`. Says the window, and logs the beat `window` with the days
// and `false` or `real`.

// The step's view of the world, with its lib.
const ecs = args.ecs;
const lib = ecs.lib;

// The whole days of the intent's value, or a throw for a value that is no count of days, a bug of the table.
function days_get(value) {
  if (!/^[0-9]{1,2}$/.test(value)) {
    throw new Error(
      `dawa_window: the value ${JSON.stringify(value)} is no count of days.`,
    );
  }
  return Number(value);
}

// Judges the window of the days waited by its forecast wind against Dawa's limit.
function window_judge(intent) {
  const wait = days_get(intent.value);
  const player = intent.entity;
  const here = lib.climber_camp(ecs, player);
  const staging = lib.row_read(ecs, "SELECT camp FROM staging", []);
  if (here.entity !== staging.camp) {
    throw new Error(
      `dawa_window: the rope is at ${here.name}, not at the staging camp.`,
    );
  }
  const wind = lib.row_read(
    ecs,
    "SELECT kmh FROM forecast WHERE days_ahead = ?",
    [wait],
  );
  const limit = lib.row_read(ecs, "SELECT wind_kmh FROM limits", []);
  if (wind.kmh > limit.wind_kmh) {
    const when =
      wait === 1
        ? "Tomorrow's"
        : `In ${lib.count_text(wait, "day", "days")} the`;
    ecs.say(
      `${when} ${wind.kmh} km/h on the summit is over Dawa's ` +
        `${limit.wind_kmh}: that window is not real.`,
    );
    ecs.log("window", intent.value, "false");
    return;
  }
  ecs.run([
    {
      sql: "UPDATE rest SET days = days + ? WHERE entity = ?",
      params: [wait, player],
    },
  ]);
  ecs.say(
    `${lib.count_text(wait, "more day", "more days")} of rest at ` +
      `${here.name}, and the jet stream lifts: ${wind.kmh} km/h on the ` +
      `summit, under Dawa's ${limit.wind_kmh}. The window is real.`,
  );
  ecs.log("window", intent.value, "real");
}

const intent = ecs.take("window");
if (intent !== null) {
  window_judge(intent);
}
