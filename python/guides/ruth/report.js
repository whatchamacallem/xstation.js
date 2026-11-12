// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The report of Ruth Calloway's sim, kept at /_files/script/ruth_report.js and
// run once, at the goodbye: reads the chosen output, the cents of the one
// `purse`, Ruth's, said as dollars, and what frames it: the text of the one
// `name`, the partner's, and the fair's `prize` when `beat_log` holds the
// race won. It reads by SELECTs alone, so it commits nothing, and prints the
// money by SQL's printf of integers, as the gold's query of the repeat
// prints it.
//
// Args: `world`, the world database. Returns `say` and `outcome` told.

// The store of the AI worker the script works through.
const store = engine.store;

// The world database, which the args must name.
if (typeof args.world !== "string" || args.world === "") {
  throw new Error(
    `ruth_report takes world as the name of a database, not` +
      ` ${JSON.stringify(args.world)}.`,
  );
}
const world = args.world;

// The one row of a SELECT on the world, each column by its name.
function row_read(sql, params) {
  const [result] = store.sql_run(world, [{ sql, params }]);
  if (result.rows.length !== 1) {
    throw new Error(
      `internal error: ruth_report reads ${result.rows.length} rows of` +
        ` ${JSON.stringify(sql)}, where it needs one.`,
    );
  }
  const [row] = result.rows;
  return Object.fromEntries(
    result.columns.map((name, index) => [name, row[index]]),
  );
}

const purse = row_read(
  "SELECT printf('$%d.%02d', cents / 100, cents % 100) AS money FROM purse",
  [],
);
const player = row_read("SELECT text AS partner FROM name", []);
const prize = row_read(
  "SELECT printf('$%d.%02d', cents / 100, cents % 100) AS money," +
    " (SELECT COUNT(*) FROM beat_log WHERE beat = ? AND outcome = ?) AS won" +
    " FROM prize",
  ["race", "won"],
);

const opening =
  `${player.partner}, the cigar box holds ${purse.money} for the summer`;
const say =
  prize.won > 0
    ? `${opening}, with the fair's ${prize.money} purse in it.`
    : `${opening}.`;
return { say, outcome: "told" };
