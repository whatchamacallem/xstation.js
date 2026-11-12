// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The step system `ruth_loop`, kept at /_files/script/ruth_loop.js: takes the
// player's intent `loop`, its value the speed at the bottom in mph, and flies
// a loop of two arcs with energy kept, the pilot's pull at the bottom and her
// light pull over the top. The top's speed squared is the entry's times
// (1 - 2 / (pull - 1)) / (1 + 2 / (top + 1)); the loop is made when it reaches
// the stall at the top's pull, and says the dive from the cruise and the
// height of the top. Outcome fell or made, logged as the beat loop.
//
// Args: `ecs`. Reads `airframe` and `technique`; writes nothing but its say
// and beat.

// The step's view of the world, and the lib.
const ecs = args.ecs;
const lib = ecs.lib;

// The player's intent to loop, or null when none waits this step.
const intent = ecs.take("loop");
if (intent === null) {
  return;
}
const entry = lib.whole_value(intent.value);
const aircraft = lib.aircraft_read(ecs);
const pilot = lib.pilot_read(ecs);
const pull_g = pilot.loop_pull_g;
const top_g = pilot.loop_top_g;
const kept = (1 - 2 / (pull_g - 1)) / (1 + 2 / (top_g + 1));
const needed = aircraft.min_mph * Math.sqrt(top_g);
const wanted = needed / Math.sqrt(kept);
const bottom = lib.speed_feet(entry);
const top_squared = bottom * bottom * kept;
const top = Math.sqrt(top_squared) / lib.FPS_PER_MPH;
if (top < needed) {
  ecs.say(
    `Pulling ${pull_g} g at ${entry} mph, she comes over the top at` +
      ` ${lib.whole_text(top)} mph, under the ${lib.whole_text(needed)} she` +
      ` needs for ${top_g} g up there: she hangs, falls off sideways, and` +
      ` Ruth flies her out. The loop wants ${lib.whole_text(wanted)} mph at` +
      ` the bottom.`,
  );
  ecs.log("loop", intent.value, "fell");
  return;
}
const cruise = lib.speed_feet(aircraft.cruise_mph);
const dive = (bottom * bottom - cruise * cruise) / (2 * lib.G);
const bottom_radius = (bottom * bottom) / (lib.G * (pull_g - 1));
const top_radius = top_squared / (lib.G * (top_g + 1));
ecs.say(
  `Dive ${lib.whole_text(dive)} feet to ${entry} mph and pull ${pull_g}` +
    ` g: she comes over the top at ${lib.whole_text(top)} mph,` +
    ` ${lib.whole_text(bottom_radius + top_radius)} feet above where you` +
    ` pulled, and down the back at ${entry} again. A loop.`,
);
ecs.log("loop", intent.value, "made");
