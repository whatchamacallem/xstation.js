// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The tick system `isaiah_travel` of Isaiah Cole's cattle drive, kept at
// `/_files/script/isaiah_travel.js`: moves each entity of `travel` along the
// trail by its `pace.miles` a tick, its `place.mile` at most that of its
// `travel.goal`. An entity that reaches its goal ends its travel: its `busy`
// and `travel` rows go. It says nothing, as the trail between the beats
// passes in the step that set out.
//
// Args: `ecs`, of the contract of `ecs_step`. Reads `travel`, `pace` and
// `place`. Writes `place.mile`, `busy` and `travel`.

// The step's methods.
const ecs = args.ecs;

// The entities of `travel` that stand at their goal.
const ARRIVED =
  "SELECT travel.entity FROM travel" +
  " JOIN place ON place.entity = travel.entity" +
  " JOIN place AS goal ON goal.entity = travel.goal" +
  " WHERE place.mile = goal.mile";

ecs.run([
  {
    sql:
      "UPDATE place SET mile = MIN(mile + (SELECT pace.miles FROM pace" +
      " WHERE pace.entity = place.entity), (SELECT goal.mile FROM travel" +
      " JOIN place AS goal ON goal.entity = travel.goal" +
      " WHERE travel.entity = place.entity))" +
      " WHERE entity IN (SELECT entity FROM travel)",
    params: [],
  },
  { sql: `DELETE FROM busy WHERE entity IN (${ARRIVED})`, params: [] },
  { sql: `DELETE FROM travel WHERE entity IN (${ARRIVED})`, params: [] },
]);
