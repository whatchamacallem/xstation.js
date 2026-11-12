// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The report of Isaiah Cole's cattle drive, the script `isaiah_report` kept
// at `/_files/script/isaiah_report.js`: reads the tally man's book back at
// the goodbye. Its number is the drive's chosen output, the head the herd's
// `tally` counted in at Dodge City, framed by the head of its `bed` ground
// and its `losses`, paid at the ford and lost on the trail. It runs one
// SELECT, whose numbers SQL casts to text as the gold's query of `repeated`
// does, so it commits nothing and the end turn changes no database.
//
// Args: `world`, the world database, `drive`. Returns `say`, the book read
// back, and `outcome`, `told`.

// The store of the AI worker the script works through.
const store = engine.store;

// The world database, which the args must name.
if (typeof args.world !== "string" || args.world === "") {
  throw new Error(
    `isaiah_report takes world as the name of a database, not` +
      ` ${JSON.stringify(args.world)}.`,
  );
}
const world = args.world;

// The tally of each herd counted in, with its bed ground and its losses.
const [result] = store.sql_run(world, [
  {
    sql:
      "SELECT CAST(tally.head AS TEXT) AS counted," +
      " CAST(bed.head AS TEXT) AS bedded," +
      " CAST(losses.tolled AS TEXT) AS tolled," +
      " CAST(losses.lost AS TEXT) AS lost FROM tally" +
      " JOIN bed ON bed.entity = tally.entity" +
      " JOIN losses ON losses.entity = tally.entity ORDER BY tally.entity",
    params: [],
  },
]);
if (result.rows.length !== 1) {
  throw new Error(
    `isaiah_report needs the tally of one herd in ${world}, not` +
      ` ${result.rows.length}.`,
  );
}
const [counted, bedded, tolled, lost] = result.rows[0];

const say =
  `The tally man's book: ${counted} head counted in at Dodge City, of` +
  ` ${bedded} bedded on the flat, ${tolled} paid at the ford and ${lost}` +
  " lost on the trail.";
return { say, outcome: "told" };
