// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The step system `ruth_turn`, kept at /_files/script/ruth_turn.js: takes the
// player's intent `turn`, its value the degrees of bank, and flies a level
// turn at the cruise: the load n = 1 / cos(bank), the stall at the 1 g stall
// times the square root of n, and, when that is under the cruise, the circle's
// radius V squared over g tan(bank) and its time round. Outcome stalled when
// the stall passes the cruise, else made, logged as the beat turn.
//
// Args: `ecs`. Reads `airframe`; writes nothing but its say and beat.

// The step's view of the world, and the lib.
const ecs = args.ecs;
const lib = ecs.lib;

// The player's intent to turn, or null when none waits this step.
const intent = ecs.take("turn");
if (intent === null) {
  return;
}
const bank = lib.whole_value(intent.value);
const aircraft = lib.aircraft_read(ecs);
const cruise = aircraft.cruise_mph;
const angle = bank * lib.RADIANS_PER_DEGREE;
const load = 1 / Math.cos(angle);
const stall = aircraft.min_mph * Math.sqrt(load);
const opening =
  `At ${bank} degrees of bank she pulls ${lib.tenths_text(load)} g and` +
  ` stalls at ${lib.whole_text(stall)} mph`;
if (stall > cruise) {
  ecs.say(
    `${opening}, over your ${cruise}: the wing quits and Ruth catches her.`,
  );
  ecs.log("turn", intent.value, "stalled");
  return;
}
const speed = lib.speed_feet(cruise);
const pull = lib.G * Math.tan(angle);
const radius = (speed * speed) / pull;
const seconds = (2 * Math.PI * speed) / pull;
ecs.say(
  `${opening}, under your ${cruise}: a circle ${lib.whole_text(radius)}` +
    ` feet in radius, flown round in ${lib.whole_text(seconds)} seconds.`,
);
ecs.log("turn", intent.value, "made");
