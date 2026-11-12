// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The tick system `dawa_rescue`, kept at /_files/script/dawa_rescue.js: once
// a climber who is down, the holder of `down`, breathes from the bottle the
// guide carries, the holder of `limits`, and climbs no more, his descent is
// told from what the ticks measured: the litres he drew of that bottle, and
// from them the minutes of the way down at his flow; the litres the followed
// climber, the holder of `ams`, drew in those minutes, and what the bottle
// held before them. Everyone is at the camp below with Dawa's record kept,
// and the climber is down no more. A rescue with the record broken is a bug
// of the table, and throws.
//
// Args: `ecs`. Reads `down`, `breathe`, `bottle`, `limits`, `climb`, `ams`,
// `at`, `camp` and `record`; writes `down`. Says the descent.

// The step's view of the world, with its lib.
const ecs = args.ecs;
const lib = ecs.lib;

// Tells the descent of the climber who is down once it has ended.
function descent_end() {
  const carried = ecs.rows(
    "SELECT down.entity AS entity, breathe.lpm AS lpm," +
      " bottle.full_l AS full_l, bottle.left_l AS left_l FROM down" +
      " JOIN breathe ON breathe.entity = down.entity" +
      " JOIN bottle ON bottle.entity = breathe.bottle" +
      " JOIN limits ON limits.entity = bottle.holder" +
      " WHERE down.entity NOT IN (SELECT entity FROM climb)" +
      " ORDER BY down.entity",
    [],
  );
  if (carried.length === 0) {
    return;
  }
  if (carried.length > 1) {
    throw new Error(
      `dawa_rescue: ${carried.length} climbers are down on the guide's` +
        " bottle, where the rope carries one.",
    );
  }
  const [teo] = carried;
  const used = teo.full_l - teo.left_l;
  const minutes = used / teo.lpm;
  if (!Number.isInteger(minutes) || minutes === 0) {
    throw new Error(
      `dawa_rescue: ${used} litres at ${teo.lpm} a minute is no descent of` +
        " whole minutes.",
    );
  }
  const you = lib.row_read(
    ecs,
    "SELECT breathe.lpm AS lpm, bottle.left_l AS left_l, camp.name AS camp" +
      " FROM ams JOIN breathe ON breathe.entity = ams.entity" +
      " JOIN bottle ON bottle.entity = breathe.bottle" +
      " JOIN at ON at.entity = ams.entity JOIN camp ON camp.entity = at.camp",
    [],
  );
  const record = lib.row_read(ecs, "SELECT text FROM record", []);
  if (record.text !== "kept") {
    throw new Error(
      `dawa_rescue: the descent ends with Dawa's record ${record.text}.`,
    );
  }
  const drawn = you.lpm * minutes;
  ecs.run([{ sql: "DELETE FROM down WHERE entity = ?", params: [teo.entity] }]);
  ecs.say(
    `Teo goes on Dawa's spare at ${teo.lpm} litres a minute: ${used} of its ` +
      `${teo.full_l} litres for the ${lib.duration_text(minutes)} down to ` +
      `the South Col. You use ${drawn} of your ${you.left_l + drawn}. ` +
      `Everyone reaches ${you.camp}, and Dawa has still never left anyone ` +
      "behind.",
  );
}

descent_end();
