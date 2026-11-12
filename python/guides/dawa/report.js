// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The report of Dawa's climb, `dawa_report`, kept at
// /_files/script/dawa_report.js and run once by the guide at the goodbye, not
// by ecs_step. It reads, by SELECTs alone, the litres the spare gave, the
// `full_l` less the `left_l` of the bottle the guide carries, the holder of
// `limits`, with its whole; the camp the followed climber, the holder of
// `ams`, came down to; and Dawa's record, kept when the spare brought Teo
// down, broken when it brought the player down from the top. It commits
// nothing, so the goodbye writes no row of the world. A spare that gave
// nothing, or a record neither kept nor broken, is a bug of the table, and
// throws.
//
// Args: `world`, the world database. Returns `say`, what the spare gave told
// again, and `outcome`, `told`.

// The store of the AI worker the script works through.
const store = engine.store;

// The world database, which the args must name.
if (typeof args.world !== "string" || args.world === "") {
  throw new Error(
    `dawa_report takes world as the name of a database, not` +
      ` ${JSON.stringify(args.world)}.`,
  );
}
const world = args.world;

// The one row a SELECT reads from the world, as an object of its columns.
function row_read(sql) {
  const [result] = store.sql_run(world, [{ sql, params: [] }]);
  if (result.rows.length !== 1) {
    throw new Error(
      `dawa_report reads ${result.rows.length} rows of ${JSON.stringify(sql)}` +
        ` in ${world}, where it needs one.`,
    );
  }
  return Object.fromEntries(
    result.columns.map((column, index) => [column, result.rows[0][index]]),
  );
}

// Tells again what the spare gave, by Dawa's record.
function spare_told() {
  const spare = row_read(
    "SELECT bottle.full_l AS full_l, bottle.full_l - bottle.left_l AS used_l" +
      " FROM bottle JOIN limits ON limits.entity = bottle.holder",
  );
  const you = row_read(
    "SELECT camp.name AS camp FROM ams JOIN at ON at.entity = ams.entity" +
      " JOIN camp ON camp.entity = at.camp",
  );
  const record = row_read("SELECT text FROM record");
  if (spare.used_l === 0) {
    throw new Error("dawa_report: the spare gave nothing to tell.");
  }
  const gave = `Dawa's spare gave ${spare.used_l} of its ${spare.full_l} litres`;
  if (record.text === "kept") {
    return `${gave} to bring Teo down to ${you.camp}, and nobody was left behind.`;
  }
  if (record.text === "broken") {
    return `${gave} to bring you down from the top to ${you.camp}, and Dawa's record is broken.`;
  }
  throw new Error(
    `dawa_report: Dawa's record is ${JSON.stringify(record.text)}, neither` +
      " kept nor broken.",
  );
}

return { say: spare_told(), outcome: "told" };
