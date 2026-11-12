// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The tick system `isaiah_wage` of Isaiah Cole's cattle drive, kept at
// `/_files/script/isaiah_wage.js`: pays each rider of `wage`, the player and
// Isaiah, a day's wage each tick, a day on the trail, its `wage.cents_a_day`
// added to its `wage.earned`. It says nothing, and the count at the gate
// reads what was earned.
//
// Args: `ecs`, of the contract of `ecs_step`. Reads and writes `wage`.

// The step's methods.
const ecs = args.ecs;

ecs.run([
  { sql: "UPDATE wage SET earned = earned + cents_a_day", params: [] },
]);
