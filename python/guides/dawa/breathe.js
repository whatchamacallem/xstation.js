// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The tick system `dawa_breathe`, kept at /_files/script/dawa_breathe.js:
// each tick, every climber who is busy climbing and breathes bottled oxygen,
// at or above the camp from which the rope breathes it, draws its litres a
// minute times the tick's minutes from its bottle, in one statement for all
// the bottles. A bottle that holds less than its breathers draw in a tick is
// a bug of the table, and throws. It says nothing.
//
// Args: `ecs`. Reads `breathe`, `busy`, `at`, `camp`, `oxygen`, `bottle` and
// the clock; writes `bottle`.

// The step's view of the world, with its lib.
const ecs = args.ecs;
const lib = ecs.lib;

// The breathers who draw this tick: busy, and at or above the height bound as the parameter.
const DRAWING =
  "FROM breathe JOIN busy ON busy.entity = breathe.entity" +
  " JOIN at ON at.entity = breathe.entity" +
  " JOIN camp ON camp.entity = at.camp WHERE camp.altitude_m >= ?";

// Draws a tick's oxygen from every bottle a busy climber breathes.
function oxygen_draw() {
  const minutes = lib.tick_minutes(ecs);
  const floor = lib.oxygen_read(ecs).altitude_m;
  const draws = ecs.rows(
    "SELECT bottle.entity AS bottle, bottle.left_l AS left_l," +
      " SUM(breathe.lpm) AS lpm FROM bottle JOIN breathe" +
      " ON breathe.bottle = bottle.entity" +
      " JOIN busy ON busy.entity = breathe.entity" +
      " JOIN at ON at.entity = breathe.entity" +
      " JOIN camp ON camp.entity = at.camp WHERE camp.altitude_m >= ?" +
      " GROUP BY bottle.entity ORDER BY bottle.entity",
    [floor],
  );
  if (draws.length === 0) {
    return;
  }
  for (const draw of draws) {
    if (draw.lpm * minutes > draw.left_l) {
      throw new Error(
        `dawa_breathe: the bottle ${draw.bottle} holds ${draw.left_l}` +
          ` litres, less than the ${draw.lpm * minutes} its breathers draw` +
          " in a tick.",
      );
    }
  }
  ecs.run([
    {
      sql:
        "UPDATE bottle SET left_l = left_l - ? * (SELECT SUM(breathe.lpm) " +
        DRAWING +
        " AND breathe.bottle = bottle.entity) WHERE entity IN" +
        " (SELECT breathe.bottle " +
        DRAWING +
        ")",
      params: [minutes, floor, floor],
    },
  ]);
}

oxygen_draw();
