// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The step system `dawa_keepsake`, kept at /_files/script/dawa_keepsake.js:
// takes the intent `keepsake`, its value `yes`, once the call is made and no
// climber is down. It makes the items photograph and scarf, each with its
// `keepsake`: a photograph from the player's high point, the top when Dawa's
// record is broken, else the camp below it, the morning Teo was taken down;
// and a white scarf, Dawa's gift. A keepsake before the call is a bug of the
// table, and throws.
//
// Args: `ecs`. Reads `down`, `record`, `high` and `camp`; writes `entity` and
// `keepsake`. Says the keepsakes, and logs the beat `keepsake` with `yes` and
// `kept`.

// The step's view of the world, with its lib.
const ecs = args.ecs;
const lib = ecs.lib;

// Dawa's gift, which no rule of the climb turns into a mechanic.
const SCARF = "A white scarf from Dawa.";

// The photograph of the player's high point, by the call made.
function photograph_text(player) {
  const fallen = lib.row_read(ecs, "SELECT COUNT(*) AS count FROM down", []);
  const record = lib.row_read(ecs, "SELECT text FROM record", []);
  const top = lib.route_camp(ecs, lib.route_ends(ecs).top);
  const high = lib.row_read(
    ecs,
    "SELECT camp.place AS place, camp.altitude_m AS altitude_m," +
      " camp.ord AS ord FROM high JOIN camp ON camp.altitude_m = high.m" +
      " WHERE high.entity = ?",
    [player],
  );
  if (fallen.count === 0 && record.text === "broken" && high.ord === top.ord) {
    return `A photograph from ${top.place}, ${top.altitude_m} m.`;
  }
  if (fallen.count === 0 && record.text === "kept" && high.ord === top.ord - 1) {
    return (
      `A photograph from ${high.place}, ${high.altitude_m} m, ` +
      `${top.altitude_m - high.altitude_m} m below the top, the morning you ` +
      "took Teo down."
    );
  }
  throw new Error(
    `dawa_keepsake: there is no call to remember, with ${fallen.count}` +
      ` climbers down, the record ${record.text} and the high mark at` +
      ` ${high.place}.`,
  );
}

// Gives the photograph and the scarf, each an item with its keepsake.
function keepsake_give(intent) {
  if (intent.value !== "yes") {
    throw new Error(
      `dawa_keepsake: the value ${JSON.stringify(intent.value)} is not yes.`,
    );
  }
  const photograph = photograph_text(intent.entity);
  const items = [
    ["photograph", photograph],
    ["scarf", SCARF],
  ];
  ecs.run([
    {
      sql: "INSERT INTO entity (name) VALUES (?), (?)",
      params: items.map(([kind]) => kind),
    },
    ...items.map(([kind, text]) => ({
      sql:
        "INSERT INTO keepsake (entity, kind, text) SELECT id, ?, ? FROM entity" +
        " WHERE name = ?",
      params: [kind, text, kind],
    })),
  ]);
  ecs.say(`${photograph} ${SCARF}`);
  ecs.log("keepsake", intent.value, "kept");
}

const intent = ecs.take("keepsake");
if (intent !== null) {
  keepsake_give(intent);
}
