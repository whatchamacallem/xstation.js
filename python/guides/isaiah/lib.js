// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The lib of Isaiah Cole's cattle drive, the system `isaiah_lib` of kind lib,
// kept at `/_files/script/isaiah_lib.js`: the number formats of the drive's
// says, the seconds of a day, by which a tick of the clock is a day on the
// trail, and the checks the systems share of a choice's text and of a row
// found once. `ecs_step` runs it once a step, before the systems, and hands
// its frozen value to each as `ecs.lib`. It reads and writes no table.
//
// Args: none, `{}`. Returns the frozen object of `SECONDS_A_DAY`,
// `whole_text`, `money_text`, `days_text`, `row_one`, `choice_read` and
// `whole_read`.

// The seconds of a day, by which a tick of the drive's clock is a day.
const SECONDS_A_DAY = 86400;

// A whole number as the page shows it.
function whole_text(x) {
  return String(Math.round(x));
}

// Cents as dollars and cents, as `$11.00`.
function money_text(c) {
  return "$" + Math.floor(c / 100) + "." + String(c % 100).padStart(2, "0");
}

// A count of days with its word, as `1 day` or `11 days`.
function days_text(days) {
  return whole_text(days) + (days === 1 ? " day" : " days");
}

// The one row of the rows a system read, which must hold exactly one.
function row_one(rows, what) {
  if (rows.length !== 1) {
    throw new Error(
      `Isaiah's drive finds ${rows.length} rows of ${what}, where it needs` +
        ` one.`,
    );
  }
  return rows[0];
}

// The choice a text holds, which must be one of those given.
function choice_read(text, choices) {
  if (!choices.includes(text)) {
    throw new Error(
      `Isaiah's drive takes one of ${choices.join(", ")}, not` +
        ` ${JSON.stringify(text)}.`,
    );
  }
  return text;
}

// The whole number a text writes in decimal digits, as `20`.
function whole_read(text) {
  const value = Number(text);
  if (!/^[0-9]+$/.test(text) || !Number.isSafeInteger(value)) {
    throw new Error(
      `Isaiah's drive takes a whole number in digits, not` +
        ` ${JSON.stringify(text)}.`,
    );
  }
  return value;
}

return Object.freeze({
  SECONDS_A_DAY,
  whole_text,
  money_text,
  days_text,
  row_one,
  choice_read,
  whole_read,
});
