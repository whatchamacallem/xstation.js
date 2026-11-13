# Test plan

Every test case of the project, one bullet each, under the one option of `./test_posix.sh` that first runs it, each section in the order the cases run. Made from the code on 2026-11-12 without running a test: the Python suites as unittest's loader lists them, the TypeScript blocks in the order their realm runs them, the line cases from their gold, and the rungs of the end to end programs from their code and gold. On 2026-11-12 the cases no option ran moved under `--test-all`, failing_suite with them though `--test-normal` already runs it as a fixture.

## 1 The options

```text
option           section  cases added  what it adds
(none)           2        83           the guide tests of Isaiah Cole, Ruth Calloway and Dawa
--test-normal    3        2191         the smoke-test suites and blocks, test_posix.py's checks,
                                       the smoke-test rungs of the wire, browser and demo tests
--test-all       4        147          what is labelled test-all, the formatters, the line count,
                                       the Windows relay's suite, the block and suite that fail by design
--test-disabled  5        147          every disabled suite, test, root and rung, no line count
```

Each of the four options runs everything of the rows above it in the table, but for the line count, section 6.1. Given two, the run is at the higher. The run order at every level is: the bring up, which fetches each pinned file not in place and builds ttyd when its inputs changed and is no test case; the TAP stream; the checks of test_posix.py; the wire, browser and demo tests; the guide tests. The switches `--anthropic`, `--debug` and `--verbose` are passed on to every program and choose no case but as section 6 says.

A Python case is named `Class.test_method`, its text the comment above the method. A TypeScript unittest case is named the same way. A line case is named by its gold, with the lines it sends and those it expects. A rung is named as its program prints it. The counts count cases, ttyd starts and root ends of the rung programs included.

## 2 No option: `./test_posix.sh`

The end to end level: the three guide programs, in this order, each walking its guide on the engine page through the scripted AI, under the smoke-test deadline of 180 s for the whole run. Every higher option runs these last, after everything it adds.

### 2.1 test_guide_isaiah.py, Isaiah Cole

18 rungs, 22 of them steps, every rung labelled smoke-test. Each step types its line with no click, waits for its band with the box enabled, and checks the picture and database rows when its gold names them.

- `served`: the engine page builds, a debug root serves the guide's built table through ttyd, the first render shows the band "How can I help you?" with the hyperposition picture, and the server's databases are copied before any commit.
- `creation` step 1: types "Take me on a cattle drive"; checks band, picture 16 px, rows of metaverse.universe, metaverse._kv: "A campfire, and past its edge more stars than seem reasonable. Out in the dark a great many large animals a..."
- `confirm` step 1: types "No thanks, take me back"; checks band, picture 4 px, rows of metaverse._kv: "How can I help you?"
- `confirm` step 2: types "Actually, the cattle drive"; checks band, picture 16 px, rows of metaverse._kv: "Isaiah looks up from the fire and fills the cup again. "Still hot. The horse is still saddled, if you'd lik..."
- `confirm` step 3: types "yes"; checks band: "Isaiah stands and gives you the reins of a gentle bay. "Good. We'll go out slow. Ask me anything on the way..."
- `talk` step 1: types "How long have you been riding night guard?"; checks band: "Isaiah smiles a little under the hat. "Every night since Texas. Early on I sang so badly the cook threw a b..."
- `build` step 1: types "Let's ride out"; checks band: "2000 head bedded on the flat and 100 miles to Dodge City: 10 days at 10 miles a day. The herd's calm is 5 o..."
- `night guard` step 1: types "Streets of Laredo"; checks band, rows of drive.system, drive.calm, drive.song, drive.clock: "You ride the slow circle singing Streets of Laredo, and the herd's calm comes up from 5 to 8 of 10. "Now li..."
- `night guard` step 2: types "I'll ride back to the fire"; checks band, rows of drive.exits, drive.clock: "You ride back to the fire and the coffee. Isaiah keeps the circle alone, singing, and the 2000 head stay do..."
- `night guard` step 3: types "Ride out again"; checks band: "You ride out again to the herd: 2000 head, calm 8 of 10. "Now listen to them breathe. Settled, or restless?""
- `reading` step 1: types "Restless"; checks band: "Long slow breaths and the cud going: calm 8 of 10 is settled, not restless. "Listen again, slower. Settled,..."
- `reading` step 2: types "Settled"; checks band: "Long slow breaths and the cud going: calm 8 of 10, settled, and you read it right. Thunder rolls in, and li..."
- `stampede` step 1: types "East"; checks band, rows of drive.head, drive.hidden, drive.calm: "You ride for the leaders on the east flank and bend the run west into a circle, short of the breaks. At sun..."
- `tracking` step 1: types "Which way did they go?"; checks band: "Isaiah thinks on that, then lets it go. "They'll have gone where there's cover. The ridge, the creek or the..."
- `tracking` step 2: types "The ridge"; checks band: "Up on the ridge: 12 head in the cedars, driven back. 1972 with the herd, 28 still out, looks used 1 of 3. "..."
- `tracking` step 3: types "The creek"; checks band: "Along the creek: 25 head in the willows, driven back. 1997 with the herd, 3 still out, looks used 2 of 3. "..."
- `tracking` step 4: types "The draw"; checks band, rows of drive.head, drive.looks, drive.place, drive.wage, drive.clock: "Down in the draw: 3 head in the plum thicket, driven back. 2000 with the herd, 0 still out, looks used 3 of..."
- `river` step 1: types "Wait a day"; checks band, rows of drive.water, drive.wage, drive.clock: "You hold the herd a day on the south bank of the Cimarron and the water drops: all 2000 swim it, leaders fi..."
- `toll` step 1: types "10"; checks band: "You offer 10 head. The outfit's boss spits: 20 is the least he takes. The boss folds his arms and waits. "M..."
- `toll` step 2: types "20"; checks band, rows of drive.head, drive.losses, drive.place, drive.clock: "You offer 20 head and the rope comes down: 1980 head cross the ford. Dodge City comes up out of the grass,..."
- `dodge` step 1: types "Count them in"; checks band, picture 16 px, rows of drive._kv, drive.tally, drive.wage: "At the stockyard gate the tally man counts 1980 head: 2000 from the bed ground, 20 paid at the ford and 0 l..."
- `keepsake` step 1: types "yes"; checks band, rows of drive.keepsake, drive.entity, drive.beat_log, drive.output, drive.clock: "Trail name: Laredo. Rode night guard with Isaiah Cole, turned the stampede, tracked 40 head and brought 198..."
- `goodbye` step 1: types "So long"; checks band: "The tally man's book: 1980 head counted in at Dodge City, of 2000 bedded on the flat, 20 paid at the ford a..."
- `audit`: every request of the audit has its reply, audit_read.failure_check passes, audit_read.guide_check holds the audit to the built table and the gold, build/audit/isaiah.txt is written, and `_audit.txt` holds one engine start.
- `left`: leaving the page ends the server's bootstrap.py, and ttyd stops with the gold's code 0.
- `databases`: the server's databases are copied to build/test_guide_isaiah/databases/, and audit_read.databases_check replays every commit of the audit onto the start copy and finds the end copy, table for table.
- `repeated`: audit_read.repeat_check finds the gold's query on drive, `SELECT CAST(tally.head AS TEXT) FROM tally JOIN entity ON entity.id = tally.entity WHERE entity.name = ?` with ["herd"], said in the last band, by the model reply and a tool result of the end turn, in no text of the table, with nothing but turns committed in that turn, and said in an earlier band.

### 2.2 test_guide_ruth.py, Ruth Calloway

20 rungs, 26 of them steps, every rung labelled smoke-test. Each step types its line with no click, waits for its band with the box enabled, and checks the picture and database rows when its gold names them.

- `served`: the engine page builds, a debug root serves the guide's built table through ttyd, the first render shows the band "How can I help you?" with the hyperposition picture, and the server's databases are copied before any commit.
- `creation` step 1: types "Take me flying"; checks band, picture 16 px, rows of metaverse.universe, metaverse._kv: "Flat bright daylight, a hayfield mown short, gasoline and warm varnish. A biplane stands a few yards off, i..."
- `confirm` step 1: types "What if I hate it?"; checks band: "Then you tap your head twice and I set us down like a feather. No questions, no teasing. So, are you coming?"
- `confirm` step 2: types "Yes"; checks band: "That's the spirit. I don't fly with strangers, so what do I call you?"
- `confirm` step 3: types "Sam"; checks band: "Sam. I work my way from town to town all summer selling rides, and I'm short a partner. Ask me anything whi..."
- `talk` step 1: types "Why are you short a partner?"; checks band: "My last partner married a feed merchant in May and swore off the sky. This summer's purse is mine to win al..."
- `build` step 1: types "Let's go"; checks band: "The Jenny: a Curtiss JN-4D with a 90 horsepower OX-5, 352.56 square feet of wing, and 1920 pounds aboard wi..."
- `first flight` step 1: types "Take her up"; checks band, rows of summer.entity, summer.name, summer.altitude, summer.clock, summer.beat_log: "Up to 2000 feet in 10 minutes, the book's 200 feet a minute, on 1.5 gallons of gasoline. Easy, like I promi..."
- `first flight` step 2: types "I tap my head twice"; checks band, rows of summer.altitude, summer.exits: "Throttle closed at 2000 feet. Gliding at 60 mph, 10.66 feet on for every foot down, she sinks 8.3 feet a se..."
- `first flight` step 3: types "Go on"; checks band, rows of summer.altitude, summer.resume: "Back up to 2000 feet in 10 minutes, on 1.5 gallons more. Easy, like I promised. Feel her ride the air? Say..."
- `first flight` step 4: types "Your stick"; checks band: "She's yours. Turns first: how many degrees of bank do you give her?"
- `turns` step 1: types "60"; checks band: "At 60 degrees of bank she pulls 2.0 g and stalls at 64 mph, over your 60: the wing quits and Ruth catches h..."
- `turns` step 2: types "30"; checks band: "At 30 degrees of bank she pulls 1.2 g and stalls at 48 mph, under your 60: a circle 417 feet in radius, flo..."
- `loop` step 1: types "80"; checks band: "Pulling 4 g at 80 mph, she comes over the top at 30 mph, under the 32 she needs for 0.5 g up there: she han..."
- `loop` step 2: types "90"; checks band: "Dive 150 feet to 90 mph and pull 4 g: she comes over the top at 34 mph, 232 feet above where you pulled, an..."
- `roll` step 1: types "20"; checks band: "Nose 20 degrees up at 75 mph and 4 seconds round: she comes out 107 feet low. A roll at 75 wants 36 degrees..."
- `roll` step 2: types "40"; checks band, rows of summer.altitude: "Nose 40 degrees up at 75 mph and 4 seconds round: she comes out 25 feet high. A roll. Here's the next town...."
- `main street` step 1: types "50"; checks band: "Down Main Street at 50 feet and 75 mph, 110 feet a second, and the handbills go over the side. Rides pay fo..."
- `rides` step 1: types "lots"; checks band: "Say again? The wind took that. Rides pay for the gasoline, and the pasture past town is full of folks wavin..."
- `rides` step 2: types "10"; checks band, rows of summer.purse, summer.altitude: "10 rides at $5.00 for 10 minutes: $50.00 taken in 100 minutes of flying, on 15.0 gallons of gasoline at 21..."
- `race` step 1: types "Full throttle"; checks band, rows of summer.purse, summer.clock, summer.output, summer.racer, summer.altitude: "Full throttle: 75 mph into a 15 mph wind is 60 over the road, 5.0 miles in 5:00. The motorcar at 45 takes 6..."
- `wing walk` step 1: types "I'll fly, you walk"; checks band, rows of summer.altitude, summer.engine_out: "Ruth walks the top wing while you hold her straight and level at 60 mph and 1000 feet. Then, over open coun..."
- `engine out` step 1: types "The south pasture"; checks band: "Gliding south with the wind at 75 mph over the ground, 1000 feet carries you 13325 feet, 2.5 miles, and the..."
- `engine out` step 2: types "The north hayfield"; checks band: "Gliding north into the wind at 45 mph over the ground, 1000 feet carries you 7995 feet, 1.5 miles, and the..."
- `engine out` step 3: types "Into the wind"; checks band, rows of summer.engine_out: "Into the wind she touches down at 45 mph through the air and 30 over the hay, and rolls to a stop. Down saf..."
- `keepsake` step 1: types "Yes please"; checks band, picture 16 px, rows of summer.purse, summer.beat_log, summer.keepsake, summer.clock, summer.output, summer.altitude, summer.exits: "RUTH CALLOWAY AND SAM, AERIAL ACROBATS: loops, rolls, the wing walk and a motorcar beaten! Rides $5.00 for..."
- `goodbye` step 1: types "So long, Ruth"; checks band: "Sam, the cigar box holds $71.85 for the summer, with the fair's $25.00 purse in it. The Jenny's still mine,..."
- `audit`: every request of the audit has its reply, audit_read.failure_check passes, audit_read.guide_check holds the audit to the built table and the gold, build/audit/ruth.txt is written, and `_audit.txt` holds one engine start.
- `left`: leaving the page ends the server's bootstrap.py, and ttyd stops with the gold's code 0.
- `databases`: the server's databases are copied to build/test_guide_ruth/databases/, and audit_read.databases_check replays every commit of the audit onto the start copy and finds the end copy, table for table.
- `repeated`: audit_read.repeat_check finds the gold's query on summer, `SELECT printf('$%d.%02d', cents / 100, cents % 100) FROM purse JOIN entity ON entity.id = purse.entity WHERE entity.name = ?` with ["ruth"], said in the last band, by the model reply and a tool result of the end turn, in no text of the table, with nothing but turns committed in that turn, and said in an earlier band.

### 2.3 test_guide_dawa.py, Dawa

17 rungs, 20 of them steps, every rung labelled smoke-test. Each step types its line with no click, waits for its band with the box enabled, and checks the picture and database rows when its gold names them.

- `served`: the engine page builds, a debug root serves the guide's built table through ttyd, the first render shows the band "How can I help you?" with the hyperposition picture, and the server's databases are copied before any commit.
- `creation` step 1: types "Take me to Everest"; checks band, picture 16 px, rows of metaverse.universe, metaverse._kv: "Pink on white, very high up: the first sun finding a wall of snow while everything below is blue. A rattle..."
- `confirm` step 1: types "Not yet"; checks band: "Dawa nods and fills your mug again. No hurry. The mountain is not going anywhere. Will you come on my rope?"
- `confirm` step 2: types "All right, I'll come"; checks band: "Dawa ties you onto his rope behind Teo, who climbs with us, and checks your knot the way he checks his own...."
- `talk` step 1: types "Why have you never left anyone behind?"; checks band: "Dawa looks at the snow a while. When I was young I carried for a team, and a man on it could not walk down..."
- `build` step 1: types "Ready"; checks band: "Base Camp, 5364 m: the air presses 401 mmHg, and you breathe in 74 mmHg of oxygen, 50 percent of what the s..."
- `icefall` step 1: types "Whenever"; checks band: "I did not understand. Say it slowly, please. The icefall is ahead, and we must be through it before the sun..."
- `icefall` step 2: types "7"; checks band, rows of expedition.entity, expedition.system, expedition.clock, expedition.at, expedition.beat_log: "Start at 7:00 and the icefall's 6 hours keep you under the seracs until 13:00, 4 hours after the sun loosen..."
- `icefall` step 3: types "2"; checks band, rows of expedition.output, expedition.clock, expedition.day, expedition.entity: "Start at 2:00 and you are through the icefall at 8:00, 1 hour before the sun. Camp 1, 6065 m: the air press..."
- `morning` step 1: types "No, I'm fine"; checks band: "Dawa takes your word. Up the Western Cwm to Camp 2, 6400 m: the air presses 351 mmHg, and you breathe in 64..."
- `morning` step 2: types "Yes, it hurts"; checks band: "A headache hidden a day is a worse one: 2 days of rest at Camp 2 before it clears, where 1 would have done..."
- `window` step 1: types "Take me down"; checks band, rows of expedition.entity, expedition.resume, expedition.at: "Dawa clips you to the fixed line and takes you down 335 m to Camp 1, 6065 m: the air presses 366 mmHg, and..."
- `window` step 2: types "Let's go up again"; checks band: "Back up 335 m to Camp 2, 6400 m: the air presses 351 mmHg, and you breathe in 64 mmHg of oxygen, 43 percent..."
- `window` step 3: types "Go tomorrow"; checks band: "Tomorrow's 45 km/h on the summit is over Dawa's 40: that window is not real. When do we go up?"
- `window` step 4: types "Wait three days"; checks band: "3 more days of rest at Camp 2, and the jet stream lifts: 25 km/h on the summit, under Dawa's 40. The window..."
- `loads` step 1: types "Everything"; checks band: "Everything is the tent at 4 kg, the stove at 2, food at 3 and 2 bottles at 3 each: 15 kg, over the 12 Dawa..."
- `loads` step 2: types "Leave one bottle"; checks band: "The tent, the stove, food and 1 bottle: 12 kg, within Dawa's 12, and he carries the spare. Up the Lhotse Fa..."
- `summit push` step 1: types "Go"; checks band, rows of expedition.output, expedition.day, expedition.bottle, expedition.breathe, expedition.down: "The South Summit, 8749 m: the air presses 256 mmHg, and you breathe in 44 mmHg of oxygen, 29 percent of wha..."
- `decision` step 1: types "We take Teo down"; checks band, rows of expedition.output, expedition.day, expedition.bottle, expedition.breathe, expedition.down, expedition.at: "Teo goes on Dawa's spare at 4 litres a minute: 1080 of its 1200 litres for the 4 hours 30 minutes down to t..."
- `keepsake` step 1: types "Yes"; checks band, picture 16 px, rows of expedition.entity, expedition.record, expedition.clock, expedition.beat_log, expedition.keepsake, expedition.intent: "A photograph from the South Summit, 8749 m, 100 m below the top, the morning you took Teo down. A white sca..."
- `goodbye` step 1: types "Goodbye, Dawa"; checks band: "Dawa's spare gave 1080 of its 1200 litres to bring Teo down to Camp 4, and nobody was left behind. Dawa tak..."
- `audit`: every request of the audit has its reply, audit_read.failure_check passes, audit_read.guide_check holds the audit to the built table and the gold, build/audit/dawa.txt is written, and `_audit.txt` holds one engine start.
- `left`: leaving the page ends the server's bootstrap.py, and ttyd stops with the gold's code 0.
- `databases`: the server's databases are copied to build/test_guide_dawa/databases/, and audit_read.databases_check replays every commit of the audit onto the start copy and finds the end copy, table for table.
- `repeated`: audit_read.repeat_check finds the gold's query on expedition, `SELECT CAST(full_l - left_l AS TEXT) FROM bottle JOIN entity ON entity.id = bottle.entity WHERE entity.name = ?` with ["spare"], said in the last band, by the model reply and a tool result of the end turn, in no text of the table, with nothing but turns committed in that turn, and said in an earlier band.

## 3 `--test-normal`

Adds, in this order, before the guide tests of section 2: the TAP stream of every suite and block labelled smoke-test that is not disabled, the checks of test_posix.py without formatting, then the smoke-test rungs of the wire, browser and demo tests. A test marked disabled inside one of these suites shows as a SKIP point here and runs at `--test-disabled`, section 5. The whole run keeps the smoke-test deadline of 180 s.

### 3.1 The TAP stream

#### 3.1.1 Python unit suites

##### test_tap_consumer

unittest, 43 cases, label smoke-test. Tests the TAP consumer.

- `TestFaults.test_bail_indented`: A bail out indented into a block is a fault.
- `TestFaults.test_bail_yaml`: A bail out inside a failed point's block counts no second failure.
- `TestFaults.test_diagnostic_early`: A diagnostic line before the first point of a block is a fault.
- `TestFaults.test_diagnostic_outside`: A diagnostic line between blocks is a fault.
- `TestFaults.test_line_bailed`: A line after a bail out is ignored, one of no known kind too.
- `TestFaults.test_line_trailing`: A line after the parent plan is a fault.
- `TestFaults.test_line_unknown`: A line of no known kind inside a block is a fault.
- `TestFaults.test_newline_missing`: A stream with its plan line present but its last newline cut is a fault.
- `TestFaults.test_number_gap`: A point out of sequence is a fault.
- `TestFaults.test_parent_mismatch`: A parent line that disagrees with its block is a fault.
- `TestFaults.test_parent_plan`: A parent plan that differs from the blocks is a fault.
- `TestFaults.test_plan_mismatch`: A block plan that differs from its points is a fault at the parent.
- `TestFaults.test_plan_missing`: A stream cut before its parent plan is not well formed.
- `TestFaults.test_skip_failed`: A failed point that claims a skip is a fault.
- `TestFaults.test_version_wrong`: A version other than 14 is a fault, and so is an empty text.
- `TestFaults.test_yaml_attribute`: An attribute other than `duration_ms` is refused.
- `TestFaults.test_yaml_depth`: A block at a depth other than its point's is a fault.
- `TestFaults.test_yaml_missing`: A point without its YAML block is a fault at the line after it.
- `TestFaults.test_yaml_order`: The block's lines out of their order are a fault.
- `TestFaults.test_yaml_outside`: A YAML line that follows no point, or a second block, is a fault.
- `TestParser.test_bail_line`: A bail out line has its reason, empty when it gives none.
- `TestParser.test_diagnostic_line`: A diagnostic line keeps its text, a blank one too.
- `TestParser.test_plan_line`: A plan line has its depth and the number of points it plans.
- `TestParser.test_result_directive`: A directive skips or marks a point to do, with its text after it.
- `TestParser.test_result_line`: A point has its depth, grade, number, description and directive.
- `TestParser.test_text_lines`: The text splits at newlines only, a last line with none counts too.
- `TestParser.test_unknown_line`: A line of no kind the producers write is unknown, with its text.
- `TestParser.test_version_line`: The version line names its version.
- `TestParser.test_yaml_line`: The three lines of a YAML block are YAML at either depth, and no other.
- `TestStats.test_bail_alone`: A bail out alone, before any version line, ends a stream of one failure.
- `TestStats.test_bail_between`: A bail out between blocks ends the stream and counts one failure.
- `TestStats.test_bail_passed`: A bail out after a passing point ends the stream with one failure.
- `TestStats.test_bail_planned`: A bail out before the first point of a block counts one failure.
- `TestStats.test_bail_todo`: A bail out after an expected failure counts one failure.
- `TestStats.test_bail_versioned`: A bail out right after the version line counts one failure.
- `TestStats.test_failfast_stream`: A failfast stream is well formed with the plan of the block it cut.
- `TestStats.test_failing_stream`: A failing block counts its failures and is well formed.
- `TestStats.test_fixture_stream`: A fixture's failure may add a point beyond the plan before the bail.
- `TestStats.test_passing_stream`: Passing blocks, one of them empty, are well formed.
- `TestStats.test_todo_stream`: An expected failure passes and an unexpected success fails.
- `TestStreamReader.test_bail_ended`: A bail out ends the stream before a point's block, a line after ignored.
- `TestStreamReader.test_line_refused`: A line that does not fit where it stands is refused and counts nothing.
- `TestStreamReader.test_lines_read`: Each line fits, the counts grow as the points come, and the plan ends it.

##### test_tap_producer

unittest, 45 cases, label smoke-test. Tests the TAP producer.

- `TestExpectation.test_failure_other`: A suite that fails another way does not match the stated failure.
- `TestExpectation.test_line_missing`: A stated line the run lacks leaves the streams different.
- `TestExpectation.test_run_unstated`: A run of diagnostics the expectation does not state is kept whole.
- `TestExpectation.test_stated_lines`: Diagnostic lines not stated are dropped, stated ones kept in order.
- `TestFailures.test_assertion_fails`: A failed assertion is a failing point with the assertion's text.
- `TestFailures.test_class_setup`: An error in `setUpClass` is a point of its own and ends the stream.
- `TestFailures.test_class_teardown`: An error in `tearDownClass` is a point after the tests and ends it.
- `TestFailures.test_error_raised`: An error in a test is a failing point with the error's text.
- `TestFailures.test_failfast_bails`: With failfast the first failure ends the stream with a bail out line.
- `TestFailures.test_failure_expected`: An expected failure is a `TODO` point that does not fail the block.
- `TestFailures.test_fixture_skip`: A skip outside a running test raises with its reason.
- `TestFailures.test_load_failfast`: With failfast a module that does not load ends the stream.
- `TestFailures.test_load_fails`: A module that does not load is one failing point with its traceback.
- `TestFailures.test_mixed_outcomes`: Without failfast every test runs and the failures fail the block.
- `TestFailures.test_module_setup`: An error in `setUpModule` is a point of its own and ends the stream.
- `TestFailures.test_outcome_missing`: A test that ends with no outcome raises when its point is due.
- `TestFailures.test_outcomes_two`: A second outcome of one test adds its diagnostics to the same point.
- `TestFailures.test_setup_raises`: An error in `setUp` fails the test's point.
- `TestFailures.test_skip_fails`: A skip that a failure follows is a diagnostic line of the failing point.
- `TestFailures.test_skip_reason`: A skip is a passing point with its reason.
- `TestFailures.test_subtest_failfast`: With failfast a failed subtest ends the stream.
- `TestFailures.test_subtest_fails`: A failed subtest fails its test's one point, naming the subtest.
- `TestFailures.test_success_unexpected`: An unexpected success fails its point and says so.
- `TestFailures.test_teardown_raises`: An error in `tearDown` fails the point of a test that passed.
- `TestRelay.test_relay_bails`: The realm's bail out ends the stream, which then takes no other block.
- `TestRelay.test_relay_closed`: With no relay open, a fed line and an end are refused.
- `TestRelay.test_relay_disagrees`: A realm's parent line that the consumer's count contradicts fails it.
- `TestRelay.test_relay_fails`: A failing block fails its parent line, and the stream goes on to its end.
- `TestRelay.test_relay_gated`: A realm line the relay passes on unchanged meets the consumer's check.
- `TestRelay.test_relay_misfit`: A realm line out of its place in the realm's stream is refused.
- `TestRelay.test_relay_name`: A relay takes no block name that would break its parent line.
- `TestRelay.test_relay_open`: No module, relay or end of the stream starts while a relay is open.
- `TestRelay.test_relay_passes`: A passing block is relayed unchanged, its parent line numbered anew.
- `TestRelay.test_relay_todo`: An expected failure, which the consumer does not count, passes the block.
- `TestRelay.test_relay_unfinished`: A realm whose stream ends before its parent plan or a bail out fails.
- `TestRunner.test_bail_ends`: A stream that bailed out takes no other module and writes no plan.
- `TestRunner.test_end_twice`: The stream ends once, and takes no module after its end.
- `TestRunner.test_module_fails`: Without failfast a failed module is graded and the stream goes on.
- `TestRunner.test_modules_pass`: Blocks plan first, parents follow, and the parent plan comes last.
- `TestRunner.test_name_refused`: A module name that would break its lines is refused before any block.
- `TestRunner.test_stream_once`: The stream is set once, and a block before it is refused.
- `TestTracker.test_diagnostics_blank`: A blank line of diagnostic text is still a diagnostic line.
- `TestTracker.test_line_refused`: Text that would break its line is refused with its diagnostics.
- `TestTracker.test_plan_first`: A plan set first is written at once, before the points.
- `TestTracker.test_points_numbered`: Points are numbered in order and the plan that comes last counts them.

##### test_internationalization

unittest, 10 cases, label smoke-test. Tests the lookup and the placeholder rule of the strings module on the texts of the real strings file, each found by its placeholders, then the real strings file and the names the sources look up in it, then the read at import, in scratch checkouts under build/ that hold the module as a link, so that its lines count as the module's own.

- `TestImport.test_file_beside`: The file of the `i18n` directory beside the module's own is the one read.
- `TestImport.test_file_list`: A file that is not a JSON object is refused.
- `TestImport.test_value_number`: A value that is not a string is refused, by its name.
- `TestLookup.test_arguments_few`: Fewer arguments than placeholders raises.
- `TestLookup.test_arguments_many`: More arguments than placeholders raises.
- `TestLookup.test_braces_argument`: Braces an argument holds pass through, not read as a placeholder.
- `TestLookup.test_index_repeat`: A repeated index counts once and each argument is made into text.
- `TestLookup.test_name_missing`: A name the table lacks raises, naming it.
- `TestStrings.test_file_names`: Every literal name the sources pass to `i18n` is in the file.
- `TestStrings.test_file_values`: Every value of the file is a string with gapless placeholders.

##### test_reformat

unittest, 18 cases, label smoke-test. Tests of reformat's table, of its check and its formatting of PowerShell files, which start no command on Linux, of its matching of whitelist lines, the matching on a scratch tree under build/, each refusal compared with its message, and of the file run as a program, in a forked child whose PATH finds no formatter.

- `TestCommands.test_windows_none`: A check and a formatting of PowerShell files start no command.
- `TestMatch.test_case_kept`: A name is matched with its case.
- `TestMatch.test_directory_missing`: A line whose directory is missing is refused as matching nothing.
- `TestMatch.test_directory_refused`: A line that matches a directory is refused.
- `TestMatch.test_glob_matched`: A `*` matches every name of its directory but the hidden ones.
- `TestMatch.test_hidden_matched`: A last part that starts with a dot matches the hidden names.
- `TestMatch.test_literal_matched`: A literal line matches its file, and a file matched twice comes once.
- `TestMatch.test_nothing_refused`: A line that matches no name is refused.
- `TestMatch.test_pattern_refused`: A line that is not a path with wildcards in its last part is refused.
- `TestMatch.test_question_matched`: A `?` matches one character.
- `TestProgram.test_formatter_missing`: With no arguments it formats the whitelist, failing at the first program.
- `TestTable.test_linux_rows`: Every other row is read as `utf-8` and checked and formatted on Linux.
- `TestTable.test_row_found`: A path finds the row of its last extension.
- `TestTable.test_row_missing`: A path whose extension has no row, or that has none, is refused.
- `TestTable.test_rows_read`: The table holds a row of the seven fields for each whitelisted extension.
- `TestTable.test_windows_rows`: The PowerShell rows are read as `utf-8-sig` and formatted on Windows.
- `TestWhitelist.test_powershell_listed`: The whitelist lists the eight PowerShell files.
- `TestWhitelist.test_rows_cover`: Every whitelisted file has a row of the table.

##### test_test

unittest, 57 cases, label smoke-test. Tests of the infrastructure for testing.

- `TestAlarm.test_deadline_passed`: A deadline already passed before the suite starts raises at once.
- `TestAlarm.test_deadline_sooner`: A deadline sooner than the module's own seconds arms the alarm.
- `TestAlarm.test_no_alarm`: No seconds of its own and no run limit arm no alarm.
- `TestAlarm.test_own_alarm`: With no run limit, a module's own seconds arm its alarm.
- `TestAlarm.test_own_sooner`: Own seconds sooner than the deadline arm the alarm.
- `TestAlarm.test_part_deadline`: A part with no alarm of its own gets the seconds left in the run.
- `TestAlarm.test_tie_own`: A tie between the two goes to the module's own alarm.
- `TestDisabled.test_category_refused`: A category other than the three raises.
- `TestDisabled.test_runs_chosen`: `test-disabled` alone takes what is disabled.
- `TestDisabled.test_setting_kept`: A run's setting holds until the next, which turns it off again.
- `TestHarness.test_copies_whole`: A copy holds the whole file, and changing it changes no later read.
- `TestHarness.test_id_past_value`: An id that goes on past a value that is not an object raises.
- `TestHarness.test_id_unknown`: An id one of whose keys is missing raises, naming the file and the id.
- `TestHarness.test_language_unknown`: An id of no language raises, naming the gold.
- `TestHarness.test_nested_id`: A nested id names the value of its keys joined by `.`.
- `TestHarness.test_read_once`: Files are read once: two gets of an id are the object of the first read.
- `TestHarness.test_suite_id`: A language and a suite name that suite's whole gold file.
- `TestHarness.test_suite_unknown`: An id of a suite with no gold file raises, naming the file it sought.
- `TestHarness.test_top_id`: A top level id names its value: a setting, a language's whole gold.
- `TestLabelBook.test_leave_outside`: Leaving when no root runs, as after a root left out, raises.
- `TestLabelBook.test_normal_all`: A `test-all` run runs a `test-all` root and its rungs.
- `TestLabelBook.test_outside_root`: A rung outside any root runs as its label says and raises nothing.
- `TestLabelBook.test_root_empty`: A `smoke-test` root left with no `smoke-test` rung raises in either run.
- `TestLabelBook.test_root_nested`: A root entered while another root runs raises.
- `TestLabelBook.test_root_skipped`: A `smoke-test` run leaves a `test-all` root out.
- `TestLabelBook.test_rungs_chosen`: A `smoke-test` run of a `smoke-test` root runs its `smoke-test` rungs.
- `TestLabelBook.test_smoke_hidden`: A `smoke-test` rung in a `test-all` root raises.
- `TestLimit.test_category_refused`: A category other than the three raises.
- `TestLimit.test_normal_unlimited`: A `test-all` or `test-disabled` run has no limit of its own.
- `TestLimit.test_smoke_limit`: A `smoke-test` run has the gold's `smoke_seconds`, as a float.
- `TestLineCount.test_all_counted`: Lines run at import count outside a suite, lines of functions in one.
- `TestLineCount.test_annotations`: The lines of a signature that hold only annotations do not count.
- `TestLineCount.test_branch_unrun`: A branch never taken holds the first line never run.
- `TestLineCount.test_exempt`: The marked `if` and `raise` are exempt with their blocks, the `else` not.
- `TestLineCount.test_file_unrun`: A file never run has its first line never run.
- `TestLineCount.test_forked_child`: Function lines a fork runs count in suites only, though SIGKILL ends it.
- `TestLineCount.test_other_file`: A suite counts the function lines of its own files only.
- `TestLineCount.test_real_path`: A file run and named through a symbolic link counts as its real path.
- `TestLineCount.test_stopped`: A count stopped counts nothing more, and keeps what it counted.
- `TestLineCount.test_suite_only`: Function lines count only in a suite, though a run outside disabled them.
- `TestLineCount.test_two_counts`: Two counts at once count apart, each only in its own suites.
- `TestOptionWords.test_category_refused`: A category other than the three raises.
- `TestOptionWords.test_disabled_option`: A `test-disabled` run has its one option.
- `TestOptionWords.test_normal_option`: A `test-all` run has its one option.
- `TestOptionWords.test_smoke_none`: A `smoke-test` run has no option word.
- `TestOptionWords.test_words_parsed`: The words parse back to their category.
- `TestOptions.test_default_smoke`: No option gives `smoke-test`.
- `TestOptions.test_disabled_given`: The option `--test-disabled` gives `test-disabled`.
- `TestOptions.test_normal_given`: The option `--test-all` gives `test-all`.
- `TestOptions.test_options_raised`: Two options give the higher in either order, so that none contradicts.
- `TestOptions.test_other_refused`: An option of neither name, though the start of one, exits with code 2.
- `TestOptions.test_smoke_refused`: The default's name is no option: `--smoke-test` exits with the code 2.
- `TestSelection.test_category_refused`: A category other than the three raises.
- `TestSelection.test_disabled_label`: The category `test-disabled` is no label.
- `TestSelection.test_label_refused`: A label other than the two raises.
- `TestSelection.test_normal_runs`: A `test-all` suite runs in a run of the two higher categories.
- `TestSelection.test_smoke_runs`: A `smoke-test` suite runs in a run of any category.

##### test_jslb

unittest, 77 cases, label smoke-test. Tests of jslb.

- `TestBuild.test_blob_bytes`: A blob of bytes is measured and keeps the same bytes object as `d`.
- `TestBuild.test_blob_path`: A blob given as a file path measures the file and keeps the path.
- `TestBuild.test_blob_reserved`: A field that `blob_make` sets cannot be given as a handler field.
- `TestBuild.test_header_defaults`: A header holds only its type when every field is at its default.
- `TestBuild.test_header_full`: Every field is set, in order, with full names.
- `TestBuild.test_header_short`: Every field is set, in order, with short names.
- `TestBuild.test_line_counted`: A header that already counts blobs is refused.
- `TestBuild.test_line_empty`: A line with no blobs leaves the count out.
- `TestBuild.test_line_full`: A full header gives the blob headers full names for size and key.
- `TestBuild.test_line_numbering`: Blob headers are numbered from 1 and counted in a copy of the header.
- `TestDecode.test_blob_empty`: A line whose blobs are all empty is complete at its CR.
- `TestDecode.test_blob_max`: A blob of `blob_max` bytes is read, one more refused before buffering.
- `TestDecode.test_blobs_summed`: Blobs of `blob_max` in all pass with a longest line, one byte more not.
- `TestDecode.test_constant_refused`: The `NaN` and `Infinity` constants are refused as not JSON.
- `TestDecode.test_count_mismatch`: A blob count that differs from the blob headers is refused.
- `TestDecode.test_data_sent`: A blob header that carries `d` or `data` on the wire is refused.
- `TestDecode.test_decode_blobs`: Blobs follow the CR, each `d` set to its bytes, empty ones too.
- `TestDecode.test_decode_line`: A line decodes to an `Object` with integer keys, nested objects too.
- `TestDecode.test_decode_pieces`: Lines come back when their last byte arrives, several in one call.
- `TestDecode.test_digits_text`: Digits in a key or a string are no number, however many they are.
- `TestDecode.test_double_read`: A token with an exponent within the doubles reads as its float.
- `TestDecode.test_fault_deferred`: Lines before a fault are returned and the next call raises the fault.
- `TestDecode.test_forms_mixed`: Short and full names in one line are refused, across headers too.
- `TestDecode.test_header_gap`: A gap in the blob headers is refused.
- `TestDecode.test_header_missing`: A line without header 0 is refused.
- `TestDecode.test_header_object`: A header that is not a JSON object is refused.
- `TestDecode.test_idle_states`: The decoder is idle between messages only, and never after a fault.
- `TestDecode.test_integer_digits`: Integers of 17, 310 and 4301 digits are refused before `int` reads them.
- `TestDecode.test_integer_edges`: `2**53` either way reads as an `int`, one past either is refused.
- `TestDecode.test_integral_floats`: An integral float count or size is read as an `int`, in either form.
- `TestDecode.test_key_long`: A key too long for an `int` is refused as not JSON.
- `TestDecode.test_line_early`: A line is refused once it passes `line_max`, before its CR arrives.
- `TestDecode.test_line_field`: An unknown field in the line header is refused.
- `TestDecode.test_line_max`: A line of `line_max` bytes with its CR is read, one byte more is not.
- `TestDecode.test_mark_refused`: A leading byte order mark is refused as not JSON.
- `TestDecode.test_nesting_deep`: Arrays nested past the parser's depth are refused as not JSON.
- `TestDecode.test_number_first`: The first refused token in the text is the one reported.
- `TestDecode.test_number_overflow`: A token whose float overflows to an infinity is refused.
- `TestDecode.test_payload_digits`: A payload key of decimal digits is refused.
- `TestDecode.test_size_integer`: A size past `2**53` is a refused integer before it is a bad size.
- `TestDecode.test_size_invalid`: A size that is not a non negative integer is refused.
- `TestDecode.test_text_invalid`: A line that is not strict `UTF-8` or not a JSON object is refused.
- `TestDecode.test_type_missing`: A line header without a type string is refused.
- `TestEncode.test_double_range`: Doubles past `2**53` either way are written as Python writes a float.
- `TestEncode.test_encode_blobs`: Each blob's `d` follows the JSON as the same bytes object or path.
- `TestEncode.test_encode_checked`: The encoder refuses a line that the decoder would refuse.
- `TestEncode.test_encode_empty`: A line with no blobs is its JSON text with no spaces and a CR.
- `TestEncode.test_encode_order`: Integer keys come first in ascending order, in nested objects too.
- `TestEncode.test_encode_text`: Text is raw `UTF-8`, escaped as JSON does, with no CR but the last.
- `TestEncode.test_float_refused`: `NaN` and the infinities are refused.
- `TestEncode.test_integer_limits`: Integers within `2**53` either way are written, larger ones refused.
- `TestEncode.test_key_refused`: A key that would decode as another key or type is refused.
- `TestEncode.test_size_differs`: A blob whose `d` is missing or of another size is refused.
- `TestFields.test_field_defaults`: An absent field gives its default, or `None` when it has none.
- `TestFields.test_field_forms`: A header holding both forms of a field raises.
- `TestFields.test_field_full`: Either name form finds each field of full headers, blob headers too.
- `TestFields.test_field_refused`: An absent required field raises, as does a name that is no field.
- `TestFields.test_field_short`: Either name form finds each field of a short header.
- `TestFields.test_headers_probing`: Probing stops at the first missing integer key, strings included.
- `TestFields.test_payload_keys`: The payload is every string key, in order.
- `TestJsonDecode.test_constant_refused`: The `NaN` and `Infinity` constants are refused as not JSON.
- `TestJsonDecode.test_not_json`: A text that is not JSON is refused, the parser's error its cause.
- `TestJsonDecode.test_numbers_read`: The tokens a line reads, read here the same.
- `TestJsonDecode.test_numbers_refused`: The tokens a line refuses, refused here the same.
- `TestJsonDecode.test_values`: Any JSON value is returned, objects as `Object`s with `int` digit keys.
- `TestObject.test_attribute_missing`: A missing key is a missing attribute, so `hasattr` is false.
- `TestObject.test_attribute_read`: A string key reads as an attribute.
- `TestObject.test_attribute_shadowed`: A key named like a dict method reads only with `[]`, as the method wins.
- `TestRender.test_render_blobs`: The JSON text is followed by one tag per blob, numbered from 1.
- `TestRender.test_render_plain`: A line with no blobs renders as its JSON text alone.
- `TestStream.test_close_failure`: A failed close, after a failed write, raises with that error as context.
- `TestStream.test_hash_sent`: A sent `sha256` is replaced on a streamed blob and kept on one in memory.
- `TestStream.test_stream_bytes`: A streamed blob fed one byte at a time gives the same file and hash.
- `TestStream.test_stream_closed`: A streamed blob's file closes when it cannot grow, now or after a line.
- `TestStream.test_stream_exact`: A blob of exactly `overflow_bytes` stays in memory, with no file.
- `TestStream.test_stream_existing`: A sink path that already exists is refused and left as it was.
- `TestStream.test_stream_sink`: A blob one byte over goes to the sink's file, hashed, `d` its path.

##### test_audit

unittest, 25 cases, label smoke-test. Tests the audit document on scratch roots in `build/`.

- `TestFile.test_appended`: Two opens append to one file, each entry under its own start.
- `TestFile.test_full`: An entry past `blob_max` raises and writes nothing.
- `TestFile.test_hard_exit`: A process ended by SIGKILL leaves every entry it wrote.
- `TestFile.test_not_open`: Each call raises before the open, a lane's record too, and a second open.
- `TestFile.test_processes`: Two processes writing at once leave every entry whole.
- `TestFile.test_starts`: Each role's open writes its start heading with the process id.
- `TestLayout.test_dump`: A dump lays out each database in name order, history counted.
- `TestLayout.test_line_blobs`: A line with a blob is its JSON text over many lines, then the marker.
- `TestLayout.test_line_plain`: A line with no blob has no marker, and keeps its text beyond ASCII.
- `TestLayout.test_note`: A note's every line is indented under its label.
- `TestLayout.test_own_skipped`: The audit's own lines are never recorded, either way.
- `TestLayout.test_record_alike`: The server's lines laid out as a page's record, each blob's sha256 added.
- `TestShown.test_digits_kept`: A key of digits in an item compares alike in a later process.
- `TestShown.test_lines_thin`: Each request, reply and commit holds only what the document did not show.
- `TestShown.test_lines_whole`: Reading the document makes each line whole again.
- `TestShown.test_new_written`: A prompt shown before is a count, a new prompt and tool list are whole.
- `TestShown.test_odd_written`: Items the document did not show, other lines and a partial commit.
- `TestShown.test_omitted_written`: The text that omits a debug mode tool list is written whole, no count.
- `TestShown.test_reopened_blobs`: A later process reads back a line of a lane that carries blobs.
- `TestShown.test_reopened_kept`: A later process reads the three lanes back, as a page load's does.
- `TestShown.test_scenes_kept`: Scenes in turn, then a later process: each restart is a count alone.
- `TestShown.test_whole_kept`: A line of no count reads as it is, as a document older than the count.
- `TestShown.test_whole_undoes`: Each thin line made whole is the line, the shown state alike after it.
- `TestTail.test_fit`: An entry that does not fit the limit ends the tail, older ones too.
- `TestTail.test_order`: The newest entries, at most the count, oldest first.

##### test_audit_read

unittest, 34 cases, label smoke-test. Tests the audit's reader on documents the real audit module writes in scratch roots in `build/`, whose suite has passed.

- `TestDatabases.test_commit_refused`: A commit the store refuses, a database the start holds, fails at it.
- `TestDatabases.test_lines_told`: Each kind of cell is told, a long string whole, the store's tables once.
- `TestDatabases.test_replay_passed`: The replay of each kind of commit makes the server's databases.
- `TestDatabases.test_row_differs`: A row the server holds that no commit made fails at its table.
- `TestDatabases.test_value_differs`: A value the server holds that the record did not put fails at its put.
- `TestDigest.test_dump_told`: A dump is shown whole, and a second of the same text names the first.
- `TestDigest.test_empty_told`: A document with no entry tells nothing, then a summary of nothing.
- `TestDigest.test_lines_told`: Every other kind of line is told, a long string named again, restarts.
- `TestDigest.test_walk_told`: A walk tells the player, the model, the tools, the bands and commits.
- `TestFailures.test_each_failure`: Each row of the gold's failures raises its text.
- `TestFailures.test_request_opened`: A request with no reply is open, and a later reply closes it.
- `TestFailures.test_start_apart`: A reply in a later start of the engine answers nothing of an earlier.
- `TestForm.test_form_refused`: Each of the gold's texts raises naming the line that does not fit.
- `TestGuide.test_dump_passed`: A dump, the answer to an input of 0 in debug mode, is no fault.
- `TestGuide.test_each_fault`: Each fault of the gold, put in the walk, fails at its first message.
- `TestGuide.test_reply_missing`: A table with no reply to the player's text fails at the model's reply.
- `TestGuide.test_walk_passed`: A walk its table and gold expect passes both checks.
- `TestProgram.test_check_failed`: `--check` on a run with a failure exits 1, naming its line.
- `TestProgram.test_check_passed`: `--check` on a run with no failure exits 0, the verdict after the digest.
- `TestProgram.test_digest_only`: Without `--check` the digest prints under its title, with no verdict.
- `TestProgram.test_guide_refused`: `--guide` reads a real guide's table and gold, and fails a walk not its.
- `TestRead.test_blobs_read`: A blob's mark after the JSON leaves the JSON read.
- `TestRead.test_dumps_passed`: Two dumps of each side pass the check, as a person asked for them.
- `TestRead.test_entries_read`: The entries in order, with their lines, starts, labels, types and counts.
- `TestRead.test_lanes_thinner`: Each lane of the conversation writes fewer bytes than it sent.
- `TestRead.test_lines_whole`: Each line is read whole, as it was sent, though the document is thin.
- `TestRead.test_run_passed`: The run has no failure, and every request its reply.
- `TestRead.test_scenes_passed`: Scenes in turn across a reload write the prompt once and no item twice.
- `TestRepeated.test_band_missing`: A record with no band yet fails before it reads a turn.
- `TestRepeated.test_each_refusal`: Each fault of the gold, put in the walk, fails naming the line it says.
- `TestRepeated.test_own_text`: A content of the table that holds the output fails, named by its place.
- `TestRepeated.test_query_refused`: A query of no row, two rows, a number, an empty text or two texts fails.
- `TestRepeated.test_read_only`: Read only: a query that writes raises, and the database keeps its rows.
- `TestRepeated.test_repeat_passed`: A told walk passes, its evidence naming the line that shows each part.

##### test_switches

unittest, 15 cases, label smoke-test. Tests the switches of a run.

- `TestApply.test_apply_each`: Each switch takes its parameter, its variable `1` when on, else unset.
- `TestImport.test_import_off`: With no variable set every switch is off.
- `TestImport.test_import_on`: Each variable set before the import turns on its switch alone.
- `TestOptions.test_options_all`: All three together turn on all three.
- `TestOptions.test_options_each`: Each option turns on its switch and sets its variable to `1`, alone.
- `TestOptions.test_options_none`: No option turns nothing on and sets no variable.
- `TestParameters.test_parameter_extra`: A key that names no switch, the old setting `verbose_level` among, fails.
- `TestParameters.test_parameter_missing`: Each missing key is refused, naming the file and the key.
- `TestParameters.test_parameter_type`: A value that is not a bool is refused, naming its key and the value.
- `TestParameters.test_parameters_door`: The decoders read the file, refusing a number that overflows a double.
- `TestParameters.test_parameters_object`: A file whose JSON is not an object is refused naming the file.
- `TestParameters.test_parameters_written`: Each write is read back as written, the three by name.
- `TestVariable.test_variable_on`: A variable of `1` is true.
- `TestVariable.test_variable_refused`: Any other value is refused, naming the variable and the value.
- `TestVariable.test_variable_unset`: An unset variable is false.

##### test_third_party_fetch

unittest, 12 cases, label smoke-test. Tests of third_party_fetch.

- `TestFetch.test_existing_replaced`: An existing file with another digest is replaced by the fetched bytes.
- `TestFetch.test_existing_reused`: An existing file with the right digest is returned without a fetch.
- `TestFetch.test_good_digest`: A good digest makes the library, writes the bytes and returns the path.
- `TestFetch.test_malformed_digest`: A digest that is not 64 lowercase hex characters raises naming the pin.
- `TestFetch.test_wrong_digest`: A wrong digest raises naming both digests and leaves no file.
- `TestPackage.test_package_absent`: An absent file is refused, naming the command that places it.
- `TestPackage.test_package_path`: ttyd's archive from the package manager is the first of the gold's.
- `TestPackage.test_package_placed`: A file there with its digest is returned, with no fetch.
- `TestPackage.test_package_wrong`: A file with another digest is refused, showing both digests.
- `TestPins.test_pins_placed`: Each pin is at its path with its digest, and a second fetch keeps it.
- `TestProgram.test_program_packaged`: With `--anthropic` ttyd's pin is the package manager's file, checked.
- `TestProgram.test_program_placed`: With the pins in place the program returns and prints nothing.

##### test_devtools

unittest, 74 cases, label smoke-test. Tests the parts of devtools.py that need no browser.

- `TestAddress.test_parse_malformed`: Text that isn't a port then a path fails loud.
- `TestAddress.test_parse_pair`: The port and the path are split from the file's two lines.
- `TestClient.test_call_error`: An error reply fails loud with the method and DevTools' message.
- `TestClient.test_call_mismatch`: A reply to another call fails loud.
- `TestClient.test_call_named`: A call on a named session carries it, even for a target method.
- `TestClient.test_call_ping`: A ping during a call is answered with a pong.
- `TestClient.test_call_reply`: A reply is matched by its id and events before it are passed on.
- `TestClient.test_call_timeout`: A call nothing answers fails when its timer ends, naming the method.
- `TestClient.test_deadline_first`: A deadline before the client's own wait ends a call, naming the call.
- `TestClient.test_deadline_later`: A deadline after the client's own wait leaves that wait as it is.
- `TestClient.test_deadline_passed`: A deadline already passed ends a later wait at once.
- `TestClient.test_limit_alone`: A limit ends a wait at its end alone, past the client's own wait.
- `TestClient.test_pump_events`: Events are passed on until the condition holds.
- `TestClient.test_pump_reply`: A reply while no call waits fails loud.
- `TestClient.test_pump_timeout`: An event that never comes fails when its timer ends.
- `TestCommand.test_run_failed`: A command that fails raises its exit code and its stderr.
- `TestCommand.test_run_output`: The command runs in the folder given, its stdout read as `UTF-8`.
- `TestCommand.test_run_timeout`: A command past its time is killed and fails, naming what it waited for.
- `TestDescriptors.test_raise_above`: The end moves above 4, closed at an exec, and the old number closes.
- `TestFrames.test_decode_cycle`: A frame encoded with a mask decodes to its payload.
- `TestFrames.test_decode_fragment`: A fragment that doesn't end its message decodes with its flag clear.
- `TestFrames.test_decode_lengths`: Lengths of 2 bytes and of 8 bytes decode.
- `TestFrames.test_decode_masked`: A masked frame is unmasked.
- `TestFrames.test_decode_plain`: A frame as a server sends it, with no mask, decodes.
- `TestFrames.test_decode_short`: A frame cut short fails loud.
- `TestFrames.test_encode_cycle`: The mask repeats every 4 bytes.
- `TestFrames.test_encode_lengths`: The length field grows to 2 bytes at 126 and to 8 bytes at 65536.
- `TestFrames.test_encode_masked`: A masked text frame is RFC 6455's example.
- `TestHandshake.test_accept_sample`: The sample key gives the accept value RFC 6455 gives.
- `TestHandshake.test_check_accepted`: An answer that switches protocols with the right accept value passes.
- `TestHandshake.test_check_key`: A wrong accept value, or none, fails loud.
- `TestHandshake.test_check_status`: An answer that isn't a switch of protocols, or is empty, fails loud.
- `TestHandshake.test_head_read`: The head is read up to the blank line and no further.
- `TestHandshake.test_open_accepted`: An upgrade goes out with a new key, and its answer leaves what follows.
- `TestHandshake.test_open_ended`: A connection that ends inside its answer fails loud.
- `TestHandshake.test_open_timeout`: An answer that never comes fails when its timer ends.
- `TestHandshake.test_open_wrong`: An answer that accepts another key fails loud.
- `TestHandshake.test_request_text`: The upgrade request has each header, ended by a blank line.
- `TestMessages.test_read_between`: A ping between fragments is answered and the fragments still join.
- `TestMessages.test_read_close`: A close frame fails loud.
- `TestMessages.test_read_fragments`: Fragments are joined, as in RFC 6455's example.
- `TestMessages.test_read_order`: A frame out of order, or of an opcode DevTools doesn't use, fails loud.
- `TestMessages.test_read_ping`: A ping is answered with a pong holding its payload.
- `TestMessages.test_read_pong`: A pong is ignored.
- `TestMessages.test_read_single`: A message in one frame is returned as it is.
- `TestPage.test_console_values`: Each kind of console argument becomes text.
- `TestPage.test_exception_bare`: An exception with nothing but its text gives that text.
- `TestPage.test_exception_error`: An Error's description is its message and its stack, and is all given.
- `TestPage.test_exception_value`: A thrown value gets its text and its stack frames, numbered from 1.
- `TestPage.test_lifecycle_kept`: A lifecycle event is kept by loader and name, other events are ignored.
- `TestPath.test_match_count`: A pattern gives its one match, and any other count fails loud.
- `TestPath.test_path_anthropic`: With the switch on the browser is looked for in the cloud container's.
- `TestPath.test_path_stock`: With the switch off the path is the one the driver may start.
- `TestScripts.test_command_encoded`: The script goes in as base64 of its `UTF-16` little endian bytes.
- `TestScripts.test_relay_ascii`: The relay script is plain ASCII with LF line ends.
- `TestScripts.test_relay_port`: The relay script sets the port first and has its here string whole.
- `TestTimers.test_bytes_joined`: Short reads are joined until the count is reached.
- `TestTimers.test_bytes_short`: A reader that runs dry first fails loud.
- `TestTimers.test_pipe_ended`: A pipe whose writer is gone reads as empty.
- `TestTimers.test_pipe_read`: A pipe gives no more than the count asked for.
- `TestTimers.test_pipe_timeout`: A pipe nothing is written to fails when its timer ends.
- `TestTimers.test_timer_expired`: A wait with no time left fails, naming what it waited for.
- `TestTimers.test_timer_running`: A wait with time left returns it.
- `TestTrace.test_data_joined`: Trace data is joined in order, and its end is kept with its loss.
- `TestTrace.test_find_main`: A load on a renderer's main thread is found, on any other it is not.
- `TestTrace.test_find_names`: Each name Chrome's versions give a synchronous load is found.
- `TestTrace.test_find_none`: A main thread that ran no synchronous load gives nothing.
- `TestTrace.test_find_renderers`: The main threads of two renderers both count.
- `TestTrace.test_find_unnamed`: A trace that names no renderer's main thread fails loud.
- `TestTrace.test_take_lost`: A trace that lost none is given, and one that lost events fails loud.
- `TestUnstarted.test_client_unstarted`: Its client fails loud, naming the with block that starts it.
- `TestWorkers.test_pause_kept`: A pause is kept by the session it came on.
- `TestWorkers.test_worker_attached`: An attached worker is kept by its title, and an attached page is not.
- `TestWorkers.test_worker_detached`: A detached worker is forgotten with its pause, and the others stay.

##### test_local_http

unittest, 9 cases, label smoke-test. Tests the local HTTP server with the standard library's own client against the real server, on the script of this suite's gold.

- `TestAnswers.test_closed_refused`: The closed port is held bound, and a connection to it is refused.
- `TestAnswers.test_file_served`: A file of the directory is served at its path, with its type and length.
- `TestAnswers.test_paths_answered`: Each path with no delay answers GET and POST with its status and body.
- `TestAnswers.test_stop_frees`: The server holds its signal while it serves, and gives it back at stop.
- `TestFailures.test_failure_first`: Only the first failure is raised: a later one ends its request alone.
- `TestFailures.test_file_unknown`: A path under the files' prefix that names no file in them fails.
- `TestFailures.test_file_untyped`: A file whose type the table does not know fails.
- `TestFailures.test_path_unknown`: A path neither the script nor the files hold fails the run.
- `TestFailures.test_request_refused`: A request the standard library would refuse fails, as HEAD and bad text.

##### test_stall_loop

unittest, 2 cases, label smoke-test. Tests the main loop file that never prepares.

- `TestPrepare.test_prepare_endless`: The child still runs after the wait, and the hangup kills it.
- `TestRun.test_run_raises`: The call raises with the root in its message.

##### test_vectors_make

unittest, 9 cases, label smoke-test. Tests of vectors_make.

- `TestProgram.test_program_written`: It leaves `build/vectors` holding just what `vectors_write` makes.
- `TestVectorsWrite.test_digests_written`: Each input has its size and its digest, both in lowercase hex.
- `TestVectorsWrite.test_directory_made`: A directory that does not exist yet is made and filled.
- `TestVectorsWrite.test_dump_written`: Each row of the view names a value the operations put, its size theirs.
- `TestVectorsWrite.test_modules_written`: Each block has entries, an input in lowercase hex beside its digest.
- `TestVectorsWrite.test_numbers_written`: Each number vector is the line of its token alone, within `line_max`.
- `TestVectorsWrite.test_sidecars_paired`: Vectors pair with sidecars, both kinds, the two digest files the others.
- `TestVectorsWrite.test_stale_removed`: A file that an earlier run left in the directory is removed.
- `TestVectorsWrite.test_window_edge`: Blobs of `blob_max` in all make a success vector, one byte more a fault.

##### test_substrate

unittest, 45 cases, label smoke-test. Tests of the server substrate on scratch roots under build/.

- `TestCrash.test_kill_between`: The killed put leaves a file and no row, and `kv_check` removes it.
- `TestDatabases.test_create_failed`: A create whose open fails removes its file, so a later create succeeds.
- `TestDatabases.test_create_twice`: A second create, a second open, a missing file and a close all raise.
- `TestDatabases.test_database_busy`: Closing, dropping or restoring a database a transaction wrote raises.
- `TestDatabases.test_drop_files`: Dropping removes the file and the cache files no other database names.
- `TestDatabases.test_names_bad`: A name that is not a C identifier raises and makes no file.
- `TestDatabases.test_schema_partial`: A file with only some of the substrate's tables raises, its tables kept.
- `TestDatabases.test_schema_version`: A file whose `schema` row is not the substrate's version raises.
- `TestDatabases.test_tables_created`: A new database gets the substrate's tables and the `schema` row 1 alone.
- `TestDatabases.test_tables_foreign`: A database file made elsewhere gets the tables when first opened.
- `TestDatabases.test_tables_recorded`: Its tables are what `API/sql/substrate.sql` makes, statement for statement.
- `TestDatabases.test_wal_left`: A write ahead log another connection keeps beside a dropped file raises.
- `TestDocuments.test_document_cached`: A document over `overflow_bytes` reads back whole from its cache file.
- `TestDocuments.test_document_heads`: Each put writes its id's next version and moves its head, versions stay.
- `TestDocuments.test_documents_bad`: Documents that would not round trip, or are malformed, raise.
- `TestDocuments.test_nested_text`: A nested document is stored as the body's text in its doc.put line.
- `TestDocuments.test_round_trip`: Encoding moves refs into shared headers and decoding restores the text.
- `TestDocuments.test_spaces_kept`: A string whose key part holds white space stays text in the body.
- `TestDocuments.test_version_exists`: A put whose next version is already a row raises and moves no head.
- `TestRefs.test_ref_database`: An internal ref needs a database and an external ref takes none.
- `TestRefs.test_refs_bad`: An empty ref, a missing key and a bad database name raise.
- `TestRefs.test_split_forms`: Each form splits into its database, its key and its version.
- `TestSnapshot.test_restore_bytes`: The same restore with the cache file given as its bytes.
- `TestSnapshot.test_restore_files_lost`: A restore with one of its two cache files streamed loses one value.
- `TestSnapshot.test_restore_foreign`: A file without the substrate's tables raises and the old one stays open.
- `TestSnapshot.test_snapshot_missing_file`: A snapshot leaves out a deleted cache file, without raising.
- `TestSnapshot.test_snapshot_restore`: A restore brings back the rows of the snapshot.
- `TestSnapshot.test_snapshots_apart`: Two snapshots of one database taken apart hold their own bytes.
- `TestSnapshot.test_value_held`: A cached value stays held through a snapshot and its restore.
- `TestSql.test_sql_results`: Statements return columns, rows and changes, a read changing none.
- `TestSql.test_trigger_name`: A trigger raising a string's name raises that string, adding no row.
- `TestTransactions.test_transaction_split`: A failure after one of two databases was written rolls both back.
- `TestTransactions.test_transaction_whole`: Writes in one `transaction_run` commit together or roll back together.
- `TestTurns.test_prompt_first`: The prompt's rows come before turn 1, and the key refuses a second one.
- `TestTurns.test_turns_append`: Turns number from 1 in their scene, a bad scene or content raises.
- `TestValues.test_cache_shared`: A cache file stays while any row of any database names its hash.
- `TestValues.test_check_foreign`: A file without `_kv` under the root names no cache file to `kv_check`.
- `TestValues.test_digest_same`: A put of the digest a row holds keeps the row and brings back its file.
- `TestValues.test_file_lost`: A row whose cache file is gone stays listed and put over, its get raises.
- `TestValues.test_file_moved`: A file the stream decoder wrote over `overflow_bytes` moves into place.
- `TestValues.test_overflow_boundary`: A value of exactly `overflow_bytes` stays in its row, one byte more not.
- `TestValues.test_refs_both`: A value put by one ref form is read by the other, listed, deleted twice.
- `TestView.test_document_lost`: A restore with no file loses a document's current version, which raises.
- `TestView.test_view_lost`: A restore without the files of the rows over `overflow_bytes` loses them.
- `TestView.test_view_vector`: The view of the operations' database is the vector's, as a JSON value.

##### test_substrate_limit

unittest, 2 cases, label smoke-test. Tests of the server substrate's largest database on scratch roots under build/.

- `TestFull.test_full_refused`: The put past `blob_max` fails full, and the file, rows and limit hold.
- `TestLimitSet.test_limit_refused`: Each statement that sets the limit is refused, and the limit holds.

##### test_verbose

unittest, 12 cases, label smoke-test. Tests the note of console, which goes into the root's audit, and the three levels of the shell's runner, whose start and end of a program are such notes at levels 1 and 2.

- `TestCommand.test_command_chosen`: Level 2 runs the verbose command line, levels 0 and 1 the plain one.
- `TestCommand.test_command_code`: Level 0 returns the exit code of the program.
- `TestCommand.test_command_flushed`: Every level writes what Python holds for both streams before it runs.
- `TestCommand.test_command_input`: Every level passes the input through, so a console reads its terminal.
- `TestCommand.test_command_noted`: Levels 1 and 2 pass the output through and note its start and its exit.
- `TestCommand.test_command_pass`: Level 0 passes the output through and notes nothing.
- `TestCommand.test_command_start`: A program that cannot start raises at every level, noted at 1 and 2.
- `TestCommand.test_command_unopened`: Level 0 needs no audit, and levels 1 and 2 refuse before they run.
- `TestCommand.test_level_unknown`: A level outside 0 to 2 raises, runs nothing and notes nothing.
- `TestNote.test_audit_unopened`: A note before the audit is opened raises the audit's refusal.
- `TestNote.test_hard_exit`: The notes of a program that ends at once are in the audit.
- `TestNote.test_note_written`: Each text is a note of console in the audit, each line of it indented.

##### test_dispatch

unittest, 33 cases, label smoke-test. Tests registration, dispatch by type and version on lines of the gold, the reply rules for requests and notifications, a `Failure`'s reply, a `Stream`'s reply and its pushes, left unread, the reply and error lines it builds, each compared whole with a gold line in its name form, the cascades against those built here from the raised exceptions by the rule of `cause`, and the ids from 102.

- `TestCause.test_cause_first`: `__cause__` is taken before `__context__` when both are set.
- `TestCause.test_chain`: A chain by `from` and by context nests each cause, the first innermost.
- `TestCause.test_context_suppressed`: `from None` suppresses the context, so the cascade ends at the raise.
- `TestDispatch.test_failure_notification`: A notification's `Failure` raises as a reply does, its error the cause.
- `TestDispatch.test_failure_request`: A request's `Failure` is returned, its reply given `r` as a reply is.
- `TestDispatch.test_handler_called`: Only the handler of the line's type and version is called.
- `TestDispatch.test_handler_raises`: An exception from a handler propagates unchanged.
- `TestDispatch.test_id_refused`: An id that is not an integer of at least 1 raises before any call.
- `TestDispatch.test_notification_none`: A notification whose handler returns nothing returns nothing.
- `TestDispatch.test_notification_reply`: A notification whose handler returns a reply raises.
- `TestDispatch.test_pair_unknown`: A type or a version that nothing registered raises.
- `TestDispatch.test_payload_only`: The handler gets the line and the payload only, blobs stay in the line.
- `TestDispatch.test_reply_unset`: A reply without `r` gets it, spelled in the name form of its header.
- `TestDispatch.test_request_none`: A request whose handler returns nothing raises.
- `TestDispatch.test_request_reply`: A request gets the reply its handler returned, with `r` set to its `i`.
- `TestDispatch.test_stream_full`: The reply of a `Stream` gets `r` in the name form of its header.
- `TestDispatch.test_stream_notification`: A notification's `Stream` raises as a reply does, with no cause.
- `TestDispatch.test_stream_request`: A request's `Stream` is returned, `r` set on its reply, not its pushes.
- `TestDispatch.test_stream_unread`: The dispatch leaves a generator of pushes unread, for the main loop.
- `TestDispatch.test_version_refused`: A version that is not an integer raises before any call.
- `TestError.test_cascade_carried`: The payload is the cascade, under the full key `cause`.
- `TestError.test_full_error`: The error line of a full name request uses full names.
- `TestError.test_no_line`: The error line of no line has no `r`, in short names when not `full`.
- `TestError.test_no_line_full`: The error line of no line uses full names when `full`.
- `TestError.test_notification_error`: The error line of a notification has no `r`.
- `TestError.test_request_error`: The error line of a request has `r` and the line's short names.
- `TestIdNext.test_ids_count`: The ids of a port count up from 102, as 101 is the first line's.
- `TestIdNext.test_ports_separate`: Each port counts on its own.
- `TestRegistration.test_pairs_differ`: The same type at another version, and another type, register.
- `TestRegistration.test_twice_raises`: A second registration of a pair raises and the first one stays.
- `TestReply.test_blobs_numbered`: Blobs are numbered from 1 and counted, and stay apart from the payload.
- `TestReply.test_full_names`: A full name reply has `type` and `reply` and nothing else of the request.
- `TestReply.test_short_names`: A short name reply has `t` and `r` and nothing else of the request.

##### test_settings

unittest, 19 cases, label smoke-test. Tests the settings check on good objects, plain and as read off the wire, each object a `jslb.Object`, the class the decoder makes, and on copies with a missing key, an extra key or a wrong type, a list or a dict of strings with one wrong item among them, the load from scratch files, and the real file.

- `TestCheck.test_bool_wrong`: A value that is not a bool is refused where a bool belongs.
- `TestCheck.test_empty_pass`: Empty lists and tables of strings pass, as no item is wrong.
- `TestCheck.test_good_object`: A good plain object passes and the check leaves it as it was.
- `TestCheck.test_int_wrong`: A value that is not an int is refused where an int belongs.
- `TestCheck.test_key_extra`: An extra key, the provider file's and the old windows' among them, fails.
- `TestCheck.test_key_missing`: Each missing key, at the top level or in a nested object, is refused.
- `TestCheck.test_list_wrong`: A list with a wrong item, or no list, is refused as a list of strings.
- `TestCheck.test_nested_objects`: A good object off the wire, its nested objects decoder objects, passes.
- `TestCheck.test_object_wrong`: A value that is not an object is refused where an object belongs.
- `TestCheck.test_str_wrong`: A value that is not a string is refused where a string belongs.
- `TestCheck.test_table_wrong`: A dict with a wrong key or value, or no dict, is refused as a table.
- `TestLoad.test_copy_equal`: The API text of the settings is the file the checkout reads.
- `TestLoad.test_file_absent`: A file that does not exist raises and nothing is defaulted.
- `TestLoad.test_file_real`: The settings file at the top level of the checkout loads and checks.
- `TestLoad.test_load_extra`: A file with an extra key is refused.
- `TestLoad.test_load_good`: A good file loads to the object as read, with the order of its keys.
- `TestLoad.test_load_missing`: A file with a missing key is refused.
- `TestLoad.test_load_object`: A file whose JSON is not an object is refused naming the file.
- `TestLoad.test_load_type`: A file with a value of the wrong type is refused.

##### test_engine_audit

unittest, 9 cases, label smoke-test. Tests the audit's handlers in forked children, each on a scratch root in `build/` with the real dispatcher and a real audit, so that a registration never reaches another test.

- `TestDump.test_dumps`: The browser's views from the blob, then the server's own store's.
- `TestRecord.test_blob_missing`: A record with no blob is refused, and the audit holds nothing.
- `TestRecord.test_note`: A note's text is indented under its label.
- `TestRecord.test_record_bytes`: A blob of bytes is laid out as the gold's body under its label.
- `TestRecord.test_record_file`: A blob the sink finished is read from its file, which then goes.
- `TestRegister.test_debug_off`: Outside debug mode nothing is registered.
- `TestRegister.test_not_registered`: Before the registration the tail and the dumps are refused, unwritten.
- `TestTail.test_fit`: A reply one byte past the entries' fits them, one at `line_max` does not.
- `TestTail.test_newest`: The newest entries, at most the count, oldest first.

##### test_engine_db

unittest, 18 cases, label smoke-test. Tests the handlers of `db.create`, `db.drop` and `db.sync`, and `restore_lines`, on a real store on a scratch root in `build/`.

- `TestCreate.test_database_created`: A create makes the line's database in the store and opens it.
- `TestCreate.test_full_names`: A line in full names is applied as one in short names.
- `TestCreate.test_request_none`: A create with `i` is applied and answered with nothing, as a push is.
- `TestDrop.test_database_dropped`: A drop closes the line's database and deletes its file.
- `TestDrop.test_full_names`: A line in full names is applied as one in short names.
- `TestDrop.test_request_none`: A drop with `i` is applied and answered with nothing, as a push is.
- `TestRegister.test_called_early`: Before the registration each handler and `restore_lines` raise.
- `TestRegister.test_handlers_registered`: Each handler is registered once, under its type at version 0.
- `TestRestoreLines.test_lines_empty`: No cache file: the database file's line alone, `files` 0.
- `TestRestoreLines.test_lines_large`: A database filled to `blob_max` goes whole as blob 1.
- `TestRestoreLines.test_lines_made`: Two cache files: the database file's line, then one line for each file.
- `TestSync.test_built_when_reached`: Each database's snapshot is taken as the stream reaches it, not before.
- `TestSync.test_file_lost`: A cache file the server lost is left out, and the sync goes on.
- `TestSync.test_full_names`: With debug on and a request in full names every line is in full names.
- `TestSync.test_no_database`: A store with no database sends no push, and the reply names none.
- `TestSync.test_pushes_full`: Debug on: the pushes are in full names, the reply in the request's.
- `TestSync.test_pushes_short`: Debug off: the pushes are in short names, the reply in the request's.
- `TestSync.test_short_names`: With debug off and a request in short names every line is in short names.

##### test_engine_doc

unittest, 5 cases, label smoke-test. Tests the handler of `doc.put` on a real store on a scratch root in `build/`.

- `TestPut.test_document_put`: The scene goes to the store with its database, id and body.
- `TestPut.test_full_names`: A line in full names is applied as one in short names.
- `TestPut.test_request_none`: A put with `i` is applied and answered with nothing, as a push is.
- `TestRegister.test_called_early`: Called before the registration the handler raises.
- `TestRegister.test_handlers_registered`: The handler is registered once, under its type at version 0.

##### test_engine_kv

unittest, 13 cases, label smoke-test. Tests the handlers of `kv.put` and `kv.delete` on a real store on a scratch root in `build/`.

- `TestDelete.test_full_names`: A line in full names is applied as one in short names.
- `TestDelete.test_key_deleted`: A delete removes the row of the header's key.
- `TestDelete.test_key_missing`: A line with no key raises.
- `TestDelete.test_request_none`: A delete with `i` is applied and answered with nothing, as a push is.
- `TestPut.test_bytes_identical`: Every byte value goes to the store as given.
- `TestPut.test_full_names`: A line in full names is applied as one in short names.
- `TestPut.test_line_incomplete`: A line with no blob raises, and so does a line with no key.
- `TestPut.test_request_none`: A put with `i` is applied and answered with nothing, as a push is.
- `TestPut.test_streamed_put`: A value the decoder streamed goes to the store as the path it took.
- `TestPut.test_value_empty`: An empty value goes to the store as given.
- `TestPut.test_value_stored`: The image goes to the store under the header's key. Nothing answers.
- `TestRegister.test_called_early`: Called before the registration each handler raises.
- `TestRegister.test_handlers_registered`: Each handler is registered once, under its type at version 0.

##### test_engine_sql

unittest, 7 cases, label smoke-test. Tests the handler of `sql.run` on a real store on a scratch root in `build/`.

- `TestRefused.test_statement_malformed`: A statement with a key missing or a key too many raises.
- `TestRegister.test_called_early`: Called before the registration the handler raises.
- `TestRegister.test_handlers_registered`: The handler is registered once, under its type at version 0.
- `TestRun.test_full_names`: A line in full names is applied as one in short names.
- `TestRun.test_parameters_bound`: Text with quotes and beyond ASCII stays a parameter, whole.
- `TestRun.test_request_none`: A run with `i` is applied and answered with nothing, as a push is.
- `TestRun.test_universe_statements`: The universe database's statements run in order: its table, its row.

##### test_engine_tap

unittest, 13 cases, label smoke-test. Tests `tap.line` and `error_take` in forked children, each registered on a scratch root in `build/` with the real dispatcher, so the root and the handler never reach another test.

- `TestAppend.test_directory_made`: The directory is made when it is absent.
- `TestAppend.test_file_appended`: A file that exists is appended to and keeps its lines.
- `TestAppend.test_lines_visible`: Each line is in the file as soon as it is handled.
- `TestAppend.test_run_replay`: A run's lines replay into one file, line for line, and no other.
- `TestAppend.test_text_encoded`: The text is written as `UTF-8` with the newline after it, and no other.
- `TestAppend.test_write_short`: The line is one unbuffered write, so a write cut short raises.
- `TestErrorTake.test_bail_appended`: The bail out ends the stream's file, its message on one line.
- `TestErrorTake.test_bail_first`: Before any line of the stream, the bail out makes the file alone.
- `TestErrorTake.test_bail_short`: The bail out is one unbuffered write, so a write cut short raises.
- `TestErrorTake.test_take_early`: Called before the registration it raises and writes nothing.
- `TestRefuse.test_called_early`: Called before the registration the handler raises.
- `TestRefuse.test_handlers_registered`: The handler is registered under its type at version 0, a repeat refused.
- `TestRefuse.test_language_unknown`: A language other than typescript raises and writes nothing.

##### test_engine_turn

unittest, 8 cases, label smoke-test. Tests the handlers of `turn.append` and `turn.prompt` on a real store on a scratch root in `build/`.

- `TestAppend.test_full_names`: A line in full names is applied as one in short names.
- `TestAppend.test_items_whole`: A reply's items, a call's output and the answer go whole, in order.
- `TestAppend.test_request_none`: An append with `i` is applied and answered with nothing, as a push is.
- `TestAppend.test_text_wide`: Text beyond ASCII is passed as raw characters, not as escapes.
- `TestAppend.test_turn_appended`: The player's turn, one message, goes to the store as canonical JSON.
- `TestPrompt.test_prompt_stored`: The two messages of a prompt are stored before the player's first turn.
- `TestRegister.test_called_early`: Called before the registration the handler raises.
- `TestRegister.test_handlers_registered`: The handler is registered once, under its type at version 0.

##### test_jslb_vectors

unittest, 2 cases, label smoke-test. Tests of jslb on the vectors that vectors_make.py writes into build/vectors before any test here reads them, each read whole, by single bytes and split at every offset with its sidecar's limits.

- `TestVectors.test_vectors_error`: Each error vector gives its lines, then its fault, however it is fed.
- `TestVectors.test_vectors_success`: Each success vector, and the bytes it encodes to, decode to its sidecar.

##### test_mcp

unittest, 29 cases, label smoke-test. Tests the MCP server on messages handed to it, the client against a server through direct function calls and through a transport that answers later, with the tools of API/mcp/tools.json.

- `TestClient.test_error_absent`: A result with no `isError` member is not an error.
- `TestClient.test_error_data`: An error response carries its data to the exception.
- `TestClient.test_error_pops`: An error response ends the wait for its id, so a second one is unknown.
- `TestClient.test_id_refused`: A reply whose id is not an integer raises and leaves the wait in place.
- `TestClient.test_ids_count`: Ids run from 1 in each client, and a notification takes none.
- `TestClient.test_initialize_flow`: Initializing sends the request, then the notification, then calls back.
- `TestClient.test_reply_later`: A reply that comes later reaches the callback once, and only once.
- `TestClient.test_reply_unknown`: A reply nobody asked for raises.
- `TestClient.test_request_received`: A request or a notification sent to the client raises.
- `TestClient.test_tool_call`: The result passed on is the tool's content and error flag.
- `TestClient.test_tool_error`: An error response raises out of `message_handle`, with no callback.
- `TestClient.test_tools_list`: The tools passed on equal the ones registered, `permit` read back.
- `TestServer.test_call_bare`: Absent arguments reach the function as an empty object.
- `TestServer.test_call_flagged`: A result flagged as an error is still a result, not an error response.
- `TestServer.test_call_params`: Params without a name or with arguments that are no object are invalid.
- `TestServer.test_call_permit`: The server only lists the permit flag: it runs a permit tool called.
- `TestServer.test_call_raises`: A tool's exception answers an `isError` result holding its cascade.
- `TestServer.test_call_result`: A call passes the arguments to the function and returns its result.
- `TestServer.test_call_unknown`: A tool nobody registered is invalid params, named in the message.
- `TestServer.test_initialize_reply`: The initialize reply holds the revision, tools only and the identity.
- `TestServer.test_list_permit`: Only a permit tool carries `_meta`.
- `TestServer.test_list_shape`: The listed tools equal the API file entry by entry, key order included.
- `TestServer.test_method_raises`: An exception of a method that is no `RpcError` answers with its cascade.
- `TestServer.test_method_unknown`: An unknown method is not found, named in the message, with the same id.
- `TestServer.test_notification_none`: A notification, known or not, is never answered.
- `TestServer.test_ping_reply`: Ping answers an empty result and echoes a number or a string id.
- `TestServer.test_request_invalid`: A message that is no request is invalid, with the id only if it is valid.
- `TestServer.test_rpc_tool`: A tool's `RpcError` is a tool's exception too: an `isError` result.
- `TestServer.test_tool_twice`: Registering a name twice raises.

##### test_page_build

unittest, 59 cases, label smoke-test. Tests the parts of page_build.py that start no program but python3 and call into no project module but jslb.py, whose suite has passed.

- `TestApiConfig.test_files_listed`: It lists exactly the files of `API/ts`, each once.
- `TestApiConfig.test_options_own`: It extends the base and emits nothing, its only option.
- `TestApiConfig.test_text_checked`: The base leaves the `.d.ts` files checked, or nothing would be.
- `TestCommand.test_name_alone`: A name with no template, the command line before the templates, unbuilt.
- `TestCommand.test_option_refused`: The old `--test` option is refused with the usage code 2, unbuilt.
- `TestCommand.test_script_forked`: As the program, the file's last line reaches the build through `main`.
- `TestCompileDue.test_absent_due`: With no stamp a compile is due.
- `TestCompileDue.test_equal_due`: A stamp of the same time as the newest source makes one due.
- `TestCompileDue.test_folder_due`: A folder newer than the stamp, as a file removed leaves it, is due.
- `TestCompileDue.test_folder_refused`: A checkout lacking a folder of the sources is refused.
- `TestCompileDue.test_fresh_skipped`: A fresh stamp skips the work and keeps its time.
- `TestCompileDue.test_newer_fresh`: A stamp newer than every source and folder leaves none due.
- `TestCompileDue.test_output_kept`: A work that writes the file, as tsc a bundle, keeps its bytes.
- `TestCompileDue.test_source_due`: A source of either folder newer than the stamp makes one due.
- `TestCompileDue.test_work_dated`: A due work runs once, and the stamp it leaves is dated to its start.
- `TestCompileDue.test_work_failed`: A work that raises leaves no stamp, so the next compile is due too.
- `TestCompiler.test_api_absent`: The check of the API text is refused the same way.
- `TestCompiler.test_tsc_absent`: A `PATH` with no tsc is refused by name, and nothing is written.
- `TestEmbed.test_comment_script`: A comment opener with a script start tag is refused, alone it is not.
- `TestEmbed.test_nul_refused`: A `NUL` character is refused.
- `TestEmbed.test_script_end`: A script piece holding its end tag, in any case, is refused.
- `TestEmbed.test_style_end`: A style piece holding its end tag is refused, a script end tag is not.
- `TestGold.test_copy_refused`: A page with no gold line, or with two, is refused, and nothing written.
- `TestGold.test_gold_line`: The gold is one line of JSON with no space between its tokens.
- `TestGold.test_gold_refused`: Gold with a key but the TypeScript language's is refused.
- `TestGold.test_page_copied`: The copy is the page with the other gold on its one gold line.
- `TestGold.test_suite_refused`: A suite's gold file that holds no JSON object is refused by its path.
- `TestHash.test_hash_abc`: The digest of `abc` is the example of `FIPS 180-2`.
- `TestHash.test_hash_utf8`: A character beyond ASCII is written and hashed as `UTF-8`.
- `TestMarkers.test_marker_absent`: A marker the template lacks is refused.
- `TestMarkers.test_marker_twice`: A marker the template holds twice is refused.
- `TestMarkers.test_marker_unknown`: A marker in the template that no piece names is refused.
- `TestMarkers.test_markers_filled`: Each marker takes its piece, and a piece is not searched for markers.
- `TestMarkers.test_merge_checked`: The marker decides which element a piece is checked against.
- `TestMarkers.test_template_engine`: The engine template holds the same markers once, from the same pieces.
- `TestMarkers.test_template_headless`: The headless template holds the same markers once, from the same pieces.
- `TestMarkers.test_template_tests`: The test template holds each page marker and the vectors marker once.
- `TestMarkers.test_wasm_base64`: The wasm bytes reach the page as base64 inside the string literal.
- `TestMembers.test_tar_absent`: A tar without the member is refused.
- `TestMembers.test_tar_package`: The package members of a gzipped tar are found, folders ignored.
- `TestMembers.test_zip_absent`: A suffix that starts inside a folder name is no match, and is refused.
- `TestMembers.test_zip_ambiguous`: Two members ending in the suffix are refused.
- `TestMembers.test_zip_bare`: A member at the top of the archive is found by its whole name.
- `TestMembers.test_zip_prefixed`: Members under a leading folder are found, folders and the rest ignored.
- `TestTable.test_backslash_kept`: Backslashes in the JSON text reach the bundle unchanged.
- `TestTable.test_identifier_absent`: A bundle without the identifier is refused.
- `TestTable.test_identifier_twice`: A bundle holding the identifier twice is refused.
- `TestTable.test_identifier_whole`: A longer identifier holding the name is not the identifier.
- `TestTable.test_table_invalid`: A table that does not parse as JSON is refused.
- `TestTable.test_table_replaced`: The identifier is replaced by the JSON text, unmodified.
- `TestTemplates.test_elements_same`: Its elements are those of the test template, but the TAP stream's `pre`.
- `TestTemplates.test_engine_body`: The engine template's body is the page's layout, its scripts after it.
- `TestTemplates.test_engine_output`: The engine template holds no `pre`, as it shows no TAP stream.
- `TestTemplates.test_engine_scripts`: The engine template's scripts are the test template's, its entry last.
- `TestTemplates.test_head_same`: The head of the headless template is that of the test template.
- `TestTemplates.test_scripts_same`: Its scripts are those of the test template in order, its own entry last.
- `TestTemplates.test_template_absent`: A template `html/` lacks is refused by name, and no page is written.
- `TestVectors.test_vectors_decoded`: Every file is carried, sorted by name, and decodes to its bytes.
- `TestVectors.test_vectors_empty`: An empty folder gives an empty object.

##### test_page_build_node

unittest, 10 cases, label smoke-test. Tests the Node bundle of page_build.py with the real tsc and node, a split suite of page_build that waits on no program, both being approved, and on no archive.

- `TestBundle.test_block_run`: The realm answers `tap.start`, sends the passing block, and exits 0.
- `TestBundle.test_compile_dated`: The compile is dated to its start, before the bundle written after it.
- `TestBundle.test_compile_reused`: A second build in the directory reuses the compile, left untouched.
- `TestBundle.test_first_refused`: A first line of another type is refused: nothing back, and exit 1.
- `TestBundle.test_gold_defined`: The third line defines the gold of every TypeScript suite's file.
- `TestBundle.test_path_returned`: The path returned is the bundle's place in the scratch directory.
- `TestBundle.test_strict_first`: The strict line comes first, so the whole bundle is strict code.
- `TestBundle.test_table_once`: The bundle after the three lines holds the table once, its name gone.
- `TestBundle.test_vectors_defined`: The second line defines the vectors written anew, each file as base64.
- `TestCompile.test_compile_failed`: The compile raises, tsc's exit code named and its output in the cause.

##### test_tap_loop

unittest, 10 cases, label smoke-test. Tests the TAP suite server, tap_loop.py, in forked children over pipes, with roots in `build/` whose settings are the checkout's with the gold's overflow_bytes and whose parameters are the run's with debug as each test sets it, which a serving child sets as `bootstrap.py` does, and its error texts against the gold.

- `TestPrepare.test_prepare_bare`: The root gains nothing, and nothing is returned or written.
- `TestRun.test_blob_refused`: A blob over `overflow_bytes` is refused before its line is served.
- `TestRun.test_end_partial`: The input ending inside a line: an `error` line with no id.
- `TestRun.test_output_partial`: Stdout ending inside a line fails the run, after the lines that ended.
- `TestRun.test_reply_refused`: A line carrying `r` is refused before dispatch, with no id answered.
- `TestRun.test_run_failed`: A run whose failing tests are not those expected replies its code.
- `TestRun.test_run_full`: In debug mode the pushes and the reply have full names.
- `TestRun.test_run_refused`: What a refusing driver writes to stderr reaches the reply, none pushed.
- `TestRun.test_run_served`: Each line of the driver's stream is pushed, then its code and stderr.
- `TestRun.test_type_unknown`: A type with no handler gets one `error` line with its id.

##### test_ttyd_build

unittest, 7 cases, label smoke-test. Tests of ttyd_build with the real archive, patches, patch, cmake and the compiler. Its disabled tests are listed in section 5.

- `TestCheckout.test_archive_packaged`: Under the switch anthropic the archive is the package manager's file.
- `TestCheckout.test_build_kept`: The path is the settings' build directory's, and a second call keeps it.
- `TestCheckout.test_size_refused`: The patch's option refuses a size below 0 with its line.
- `TestCheckout.test_size_taken`: The patch's option takes the settings' size.
- `TestCheckout.test_version_written`: The version option writes the gold's line and exits 0.
- `TestInputs.test_link_stripped`: A hard link's target loses its first part as its name does, as `tar`'s.
- `TestInputs.test_patch_refused`: A patch that does not apply raises naming it, the log's lines in cause.

##### test_api_match

unittest, 35 cases, label smoke-test. Tests the matches of the API text against the code on scratch checkouts in `build/`, by the real tsc. Its disabled tests are listed in section 5.

- `TestGold.test_gold_passed`: A gold equal to the text passes, comments and white space aside.
- `TestGold.test_schema_refused`: Statements the text does not hold.
- `TestGold.test_tools_refused`: Tools the text does not hold.
- `TestHandlers.test_default_refused`: A field that may be left out takes a default.
- `TestHandlers.test_field_code`: A keyword that is no field of the payload.
- `TestHandlers.test_field_text`: A payload field the handler does not take.
- `TestHandlers.test_payload_absent`: A line type with no payload in the text.
- `TestHandlers.test_payload_named`: The spelled name of a payload, its exceptions and its word marks.
- `TestMembers.test_exports_only`: A namespace with `export {};` holds only what says `export`.
- `TestMembers.test_members_read`: Each kind of member of a namespace, and a function outside any.
- `TestMembers.test_nested_skipped`: A member's own fields are not members.
- `TestNames.test_kind_refused`: A class in the code is no interface in the text.
- `TestNames.test_member_code`: A member the code exports and the text lacks.
- `TestNames.test_member_text`: A member the text holds and the code lacks.
- `TestNames.test_names_passed`: Equal names pass, `function` and `const` being both a value.
- `TestNames.test_namespace_code`: A namespace the code holds and the text lacks.
- `TestNames.test_namespace_text`: A namespace the text holds and the code lacks.
- `TestNames.test_sides_passed`: Namespaces with one side by design pass.
- `TestStubs.test_absent_passed`: The programs with no stub and the test modules pass.
- `TestStubs.test_alias_refused`: An alias's value must agree.
- `TestStubs.test_assigned_passed`: A name a line assigns with no annotation states nothing.
- `TestStubs.test_attribute_annotated`: An annotation of an attribute must agree.
- `TestStubs.test_attribute_code`: An attribute the module assigns need not be in the stub.
- `TestStubs.test_attribute_text`: An attribute the stub names must be assigned.
- `TestStubs.test_bases_refused`: The bases of a class must agree.
- `TestStubs.test_class_refused`: A method and a class field are compared both ways.
- `TestStubs.test_default_passed`: Two default values are the same statement, as a stub writes `...`.
- `TestStubs.test_exports_passed`: A module's `__all__` is its public names, and a helper may stay out.
- `TestStubs.test_exports_refused`: A name of `__all__` the stub lacks fails.
- `TestStubs.test_function_code`: A public function the module holds and the stub lacks.
- `TestStubs.test_function_text`: A public function the stub holds and the module lacks.
- `TestStubs.test_module_alone`: A module with no stub.
- `TestStubs.test_opaque_passed`: A stub's `class Name: ...` leaves the class's members to the module.
- `TestStubs.test_signature_refused`: The name, annotation, return, default and decorator of a function.
- `TestStubs.test_stub_alone`: A stub with no module.

##### test_echo_loop

unittest, 11 cases, label smoke-test. Tests the echo main loop in forked children over pipes, with roots in `build/` whose settings are the checkout's with the gold's sizes and whose parameters are the run's with debug true, which a serving child sets as `bootstrap.py` does, and its error texts against the gold.

- `TestEcho.test_audit_note`: A page thread's `audit.note` is a note of the audit, nothing written.
- `TestEcho.test_browser_error`: The browser's `error` line is bailed out, then exit 1, unanswered.
- `TestEcho.test_browser_quiet`: Outside debug mode the browser's `error` is exit 1 with no TAP file.
- `TestEcho.test_echo_pair`: Two requests with blobs in memory each get their echo, then the end.
- `TestEcho.test_echo_streamed`: A blob over `overflow_bytes` streams through the cache and comes back.
- `TestEcho.test_end_partial`: The input ending inside a line: an `error` line, no id, full names.
- `TestEcho.test_reply_refused`: A line carrying `r` is refused before dispatch, with no id answered.
- `TestEcho.test_tap_line`: A `tap.line` push is appended as a line to its file, nothing written.
- `TestEcho.test_tap_unknown`: Outside debug mode a `tap.line` is a line of no handler.
- `TestEcho.test_type_unknown`: A type with no handler gets one `error` line with its id.
- `TestPrepare.test_prepare_bare`: The root gains only the empty cache directory, and nothing is returned.

##### test_engine_mcp

unittest, 10 cases, label smoke-test. Tests the handler of the `mcp` line in forked children, each registered with the real dispatcher on a real MCP server, so the server and the handler never reach another test.

- `TestExchange.test_error_response`: An error response is the reply of a `Failure` holding the exception.
- `TestExchange.test_request_pushed`: A request pushed with no wire id gets a reply without `r`.
- `TestExchange.test_session_opened`: Opening a session replies to `initialize` and `tools/list` only.
- `TestExchange.test_tool_raises`: A tool's exception is the `isError` reply of a `Failure` holding it.
- `TestPass.test_arguments_passed`: A tool gets the arguments of the call as they came, in their order.
- `TestPass.test_called_early`: Called before the registration the handler raises.
- `TestPass.test_failure_unanswered`: A kept failure with no response raises, as a `Failure` needs a reply.
- `TestPass.test_handlers_registered`: The handler is registered under `mcp` at version 0, a repeat refused.
- `TestPass.test_messages_answered`: Each message the server takes is answered, a notification by nothing.
- `TestPass.test_response_replied`: The response is the payload of the reply, and the wire id is separate.

##### test_engine_system

unittest, 26 cases, label smoke-test. Tests the handlers of `settings.put`, `source.put` and `system.restart` and the two tools of the same names, each in a forked child, so the root, debug mode and the handlers never reach another test.

- `TestRegister.test_called_early`: Called before the registration each handler raises.
- `TestRegister.test_handlers_registered`: Each handler is registered under its type at version 0, a repeat refused.
- `TestReplaced.test_option_replaced`: The file's option takes the place of each form of the old one, rest kept.
- `TestRestart.test_file_missing`: A file that does not exist raises.
- `TestRestart.test_name_invalid`: A name that is not plain raises, even where a file of it exists.
- `TestRestart.test_restart_gated`: With debug mode off the handler raises.
- `TestSettings.test_provider_object`: A nested provider of the type the decoder makes is kept.
- `TestSettings.test_settings_gated`: With debug mode off the handler raises and writes nothing.
- `TestSettings.test_settings_invalid`: Settings that fail the check raise and the old file stays as it was.
- `TestSettings.test_settings_replaced`: A changed value is in the file, and the file replaces the old one.
- `TestSettings.test_settings_written`: The file is the settings object written whole, and no file is left over.
- `TestSource.test_blob_missing`: A line with no blob raises and nothing is written.
- `TestSource.test_blob_streamed`: A blob the decoder streamed to the cache is moved into place.
- `TestSource.test_bytes_written`: A blob in memory is written as the file, and the reply is its `sha256`.
- `TestSource.test_file_replaced`: A second write under the same name replaces the file.
- `TestSource.test_name_invalid`: A name that is not plain raises and nothing is written.
- `TestSource.test_source_gated`: With debug mode off the handler raises and writes nothing.
- `TestSource.test_streamed_refused`: A streamed blob under a name that is not plain stays in the cache.
- `TestTools.test_permit_absent`: Neither tool is registered with a permit, so no client asks for one.
- `TestTools.test_restart_gated`: With debug mode off the restart tool raises, in a child it would replace.
- `TestTools.test_restart_refused`: A missing file or a missing argument raises, in a child it would replace.
- `TestTools.test_source_arguments`: Arguments that are missing or not text are refused with their code.
- `TestTools.test_source_gated`: With debug mode off the source tool raises and writes nothing.
- `TestTools.test_source_name`: A name that is not plain raises as any exception of a tool does.
- `TestTools.test_source_tool`: The source tool writes the text as the file and answers its `sha256`.
- `TestTools.test_tools_listed`: The tools listed are the server side of the API file, key for key.

##### test_main_loop

unittest, 51 cases, label smoke-test. Tests the main loop in forked children over pipes, with roots in `build/`.

- `TestAnalyst.test_arguments_object`: Every tool call's arguments are the text of a JSON object.
- `TestAnalyst.test_calls_form`: Every tool call is a `ScriptCall`: its three fields, each a string.
- `TestAnalyst.test_content_text`: A reply that calls tools has no text, and any other reply has text.
- `TestAnalyst.test_holds_read`: The nodes that read the tools' results are the gold's, with its texts.
- `TestAnalyst.test_inputs_held`: The table starts in its start node, and only input nodes hold inputs.
- `TestAnalyst.test_inputs_lead`: Results that hold the texts lead through the table's every call.
- `TestAnalyst.test_lacking_lead`: Results that lack a text end the input there, as after a refusal.
- `TestAnalyst.test_lacks_paired`: `after_lacks` stands wherever `after_holds` does, and only there.
- `TestAnalyst.test_next_known`: Every `next` names a node of the table.
- `TestAnalyst.test_otherwise_held`: Every node with replies answers any other input, as a person errs.
- `TestAnalyst.test_otherwise_lead`: Every input node's `otherwise` is one reply: no tools, on to `menu`.
- `TestAnalyst.test_tools_listed`: Every tool call names a browser tool of the tool list, with its prefix.
- `TestLoop.test_blob_recorded`: A line read with a blob is recorded with its blobs' count and sha256.
- `TestLoop.test_blob_streamed`: A blob over `overflow_bytes` streams to the cache, named by its digest.
- `TestLoop.test_browser_error`: Outside debug mode the browser's `error` ends the loop, nothing recorded.
- `TestLoop.test_browser_recorded`: In debug mode the browser's `error` is recorded as read, and bailed out.
- `TestLoop.test_databases_reopened`: A database a push made in one process is open in the next one.
- `TestLoop.test_debug_quiet`: Outside debug mode nothing is recorded as the loop serves.
- `TestLoop.test_end_partial`: The end of the input inside a line or inside a blob is an `error` line.
- `TestLoop.test_end_returns`: The end of the input between messages returns with nothing written.
- `TestLoop.test_failure_answered`: A `Failure` writes its reply, then the server's `error` line, no `r`.
- `TestLoop.test_failure_full`: In debug mode the server's `error` after a `Failure` is in full names.
- `TestLoop.test_failure_recorded`: In debug mode the audit holds the line read and the `error`, no message.
- `TestLoop.test_failure_unrecorded`: Outside debug mode a failure sends its `error` line, recording nothing.
- `TestLoop.test_fault_after`: A line before a fault in the same read is served, then the fault ends it.
- `TestLoop.test_fault_names`: An `error` line that answers no line is in full names in debug mode.
- `TestLoop.test_fault_recorded`: In debug mode the audit holds the `error` of a fault with no line.
- `TestLoop.test_fault_unrecorded`: Outside debug mode a fault of the input with no line records nothing.
- `TestLoop.test_file_copied`: A line's blob that is a cache file is copied to the output, whole.
- `TestLoop.test_line_bad`: Bytes that are no line get an `error` line with no id.
- `TestLoop.test_lines_recorded`: In debug mode the audit holds each line read, then the reply written.
- `TestLoop.test_own_unrecorded`: The audit's own lines, a note and a tail with its reply, are no entries.
- `TestLoop.test_put_get`: A value pushed is in the root's `_files`, byte for byte, unanswered.
- `TestLoop.test_reply_unknown`: A reply, to `tap.start` or to any other id, gets an `error` line, no id.
- `TestLoop.test_run_unprepared`: `loop_run` raises when `loop_prepare` has not run in the process.
- `TestLoop.test_stream_fault`: A fault between pushes answers the request with an `error`, no reply.
- `TestLoop.test_stream_recorded`: In debug mode each push is recorded as the loop draws it, then the reply.
- `TestLoop.test_stream_written`: A `Stream` writes its pushes in order, then its reply.
- `TestLoop.test_sync_served`: `db.sync` restores each database in name order, then names them.
- `TestLoop.test_tap_unknown`: Outside debug mode a `tap.line` is a line of no handler, its text unkept.
- `TestLoop.test_type_unknown`: An unknown type gets one `error` line with its id, and nothing after.
- `TestPrepare.test_document_absent`: A seed document that is gone raises, naming its file.
- `TestPrepare.test_image_absent`: An image that is gone raises as a document that is gone does.
- `TestPrepare.test_image_seeded`: The image's row holds the file's bytes, and the scene's header names it.
- `TestPrepare.test_metaverse_empty`: A metaverse file without `universe`, as a kill leaves it, is seeded.
- `TestPrepare.test_prepare_again`: A new process on the prepared root changes no row and seeds nothing.
- `TestPrepare.test_provider_kept`: A provider script in `_files` is kept, and a missing one seeded again.
- `TestPrepare.test_root_empty`: An empty root gets the databases, the settings and the seed.
- `TestPrepare.test_seed_invalid`: A seed document that is no JSON object is refused, naming its file.
- `TestPrepare.test_setting_changed`: A changed setting rewrites its row, in `_settings` only.
- `TestPrepare.test_world_ambiguous`: Insert and update refuse a second row naming a world, a rename passes.

##### test_mcp_stdio

unittest, 16 cases, label smoke-test. Tests the stdio loop in process on pipes, with a real `mcp.Server` that serves the tool a register function of the test adds to it.

- `TestErrors.test_line_blank`: A blank line is not JSON and raises.
- `TestErrors.test_line_malformed`: A line that is not JSON raises, after the responses before it are out.
- `TestErrors.test_line_object`: A line that is JSON but not an object raises.
- `TestErrors.test_number_overflow`: A number that overflows a double is refused by the decoder at read.
- `TestErrors.test_root_required`: Without `--root` the runner refuses, usage error on stderr, exit code 2.
- `TestLoop.test_failure_raised`: The exception of a tool is raised once its answer is out.
- `TestLoop.test_flush_each`: Responses are out as written, while the loop waits, notifications silent.
- `TestLoop.test_input_empty`: No input ends the loop with exit code 0 and no output.
- `TestLoop.test_line_unterminated`: A last line with no newline is still a message.
- `TestLoop.test_notification_silent`: A notification writes nothing.
- `TestLoop.test_session_replay`: A session goes to the one server line by line, a notification silent.
- `TestServe.test_program_run`: Run as a program, the file serves the root its command line names.
- `TestServe.test_root_served`: Each line is answered, the root's tools listed, end of input exits 0.
- `TestServe.test_settings_refused`: A settings file the reader refuses ends the runner with its error.
- `TestServe.test_streams_encoded`: The streams take the transport's encoding in place of the ones they had.
- `TestServe.test_switches_root`: The debug switch is the root's parameter, whatever the run's is.

##### test_bootstrap

unittest, 30 cases, label smoke-test. Tests the platform services in process. Its disabled tests are listed in section 5.

- `TestArguments.test_arguments_refused`: No root, an unknown role, option or extra word is refused by `argparse`.
- `TestArguments.test_option_repeated`: A repeated `--root` or `--main-loop` is refused after raw mode.
- `TestConsole.test_console_failed`: A sandbox denied a process is noted, one error line, exit 1, never raw.
- `TestConsole.test_console_loop`: The console role with `--main-loop` is refused, raw, before any shell.
- `TestConsole.test_console_outside`: A root outside `/home/`, which dash's sandbox hides, is refused first.
- `TestConsole.test_console_refused`: Outside debug mode nothing runs, nothing is written and the code is 1.
- `TestError.test_error_full`: Outside debug mode the error line is in full names, nothing recorded.
- `TestError.test_error_shape`: A missing settings file is one error line after raw mode, and exit 1.
- `TestFirst.test_first_full`: In debug mode `tap.start` has full names and no gold.
- `TestFirst.test_first_short`: No debug: short `tap.start`, and the stock loop answers.
- `TestFirst.test_provider_unread`: No provider is read: not scripted, no key and a garbled provider file.
- `TestHangup.test_hangup_ignored`: A hangup while the run is blocked in its error line's write ends nothing.
- `TestLock.test_lock_kept`: While the main loop runs the lock is held, and the run's end frees it.
- `TestLock.test_lock_released`: The lock closes at `exec`, so the probe the main loop becomes takes it.
- `TestMainLoop.test_debug_gate`: Outside debug mode `--main-loop` is refused before the file is loaded.
- `TestMainLoop.test_file_missing`: A named file that does not exist is refused before `tap.start`.
- `TestMainLoop.test_function_missing`: A file that lacks `loop_run` is refused before `tap.start`.
- `TestMainLoop.test_name_refused`: A name that is not a plain file name ending in `.py` is refused.
- `TestParameters.test_parameters_applied`: The parameters set the switches and their variables, not the parent's.
- `TestParameters.test_parameters_missing`: A root with no parameters file is refused, naming the file.
- `TestParameters.test_parameters_refused`: A parameters file with a key that names no switch is refused, unrecorded.
- `TestProgram.test_program_failed`: The code the run returns is the program's: a refused command line is 1.
- `TestProgram.test_program_served`: The words after the file's name reach the run, and exit 0 ends a serve.
- `TestRecord.test_first_quiet`: Outside debug mode a run that does not fail records nothing.
- `TestRecord.test_first_recorded`: In debug mode the audit holds `tap.start` and its reply.
- `TestReply.test_reply_accepted`: Short replies, in either field order, to a full `tap.start` are taken.
- `TestReply.test_reply_closed`: An input that ends before the reply is one error line, both recorded.
- `TestReply.test_reply_garbled`: A reply that is not JSON is refused by the decoder, never recorded.
- `TestReply.test_reply_streamed`: A reply with a blob over `overflow_bytes` is refused before its bytes.
- `TestReply.test_reply_wrong`: Each reply that is not the empty reply is refused, recorded as it came.

##### test_bootstrap_dash

unittest, 5 cases, label smoke-test. Tests the console role in debug mode, which runs dash in its bubblewrap sandbox.

- `TestConsole.test_console_binary`: A heredoc of binary bytes to `cat` comes back as the pty prints them.
- `TestConsole.test_console_level`: Dash runs at the level of the parameter verbose, and its verbose form.
- `TestConsole.test_console_scrubbed`: Dash starts in its own /tmp with only the kept variables, its code back.
- `TestConsole.test_console_signal`: A dash a signal ended gives its sandbox's code, 128 plus the signal.
- `TestConsole.test_console_terminated`: SIGTERM from outside to the sandbox gives 128 plus it, and is noted.

##### test_test_posix

unittest, 53 cases, label smoke-test. Tests of test_posix's check of the characters beyond ASCII and of its PowerShell comment lexer, on files in a scratch directory under build/ and on text.

- `TestAllowed.test_banner_passed`: The full block and the three shades of the banner pass in every file.
- `TestAuditMessage.test_module_exempt`: The same token in an exempt module passes.
- `TestAuditMessage.test_token_refused`: A token outside the exempt modules is refused at its line.
- `TestAuditProbe.test_probes_passed`: A token it refuses and a literal it passes leave it silent.
- `TestAuditProbe.test_token_found`: A probe that must pass but holds a token is named with that token.
- `TestAuditProbe.test_token_missed`: A probe that holds no token is named as one the audit misses.
- `TestBadBytes.test_bytes_refused`: A byte that is not `UTF-8` is refused, the decoder's error its cause.
- `TestByteOrder.test_column_after`: A refused character's column is counted after the mark.
- `TestByteOrder.test_mark_inside`: A mark after the start is refused at its line and column.
- `TestByteOrder.test_others_refused`: A Python or TypeScript file read as `utf-8` is refused at the mark.
- `TestByteOrder.test_powershell_marked`: A PowerShell file read as `utf-8-sig` passes the mark at its start.
- `TestByteOrder.test_powershell_plain`: A PowerShell file without the mark passes too.
- `TestCommentLines.test_lines_refused`: Comments on adjacent lines below the header are refused as one comment.
- `TestEscapeCheck.test_escape_extended`: A comment holding more than the escape is refused at its `-`.
- `TestEscapeCheck.test_escape_passed`: A `prettier-ignore` comment passes though it holds a `-`.
- `TestHeaderLimit.test_block_counted`: A block comment header is counted by the lines it spans.
- `TestHeaderLimit.test_doctype_uncounted`: A doctype line before a header is not one of its lines.
- `TestHeaderLimit.test_limit_passed`: A header of line comments at the limit passes.
- `TestHeaderLimit.test_limit_refused`: A header of line comments past the limit is refused at its first line.
- `TestHtmlLexer.test_script_comments`: The comments of a script element come in order with the page's own.
- `TestHtmlLexer.test_style_comments`: The comments of a style element are found past its strings.
- `TestHtmlLexer.test_tag_case`: An element's tags are found in either case.
- `TestHtmlLexer.test_tag_unclosed`: A script or style element with no end tag is refused at its start.
- `TestJavascriptLexer.test_block_comment`: A `/*` comment runs over its lines to its `*/`.
- `TestJavascriptLexer.test_braces_nested`: A brace pair inside a `${ }` span does not end the span.
- `TestJavascriptLexer.test_division_passed`: A slash after a word is a division, and opens nothing.
- `TestJavascriptLexer.test_line_comment`: A `//` comment runs to the end of its line or of the text.
- `TestJavascriptLexer.test_regex_skipped`: A regular expression hides a slash in its escapes and its class.
- `TestJavascriptLexer.test_strings_skipped`: Quoted strings hide a comment marker, past their escapes.
- `TestJavascriptLexer.test_template_spans`: A template hides comment markers, but not in its `${ }` spans.
- `TestJavascriptLexer.test_unterminated_refused`: Each unterminated literal, comment and span is refused.
- `TestLexerName.test_name_refused`: A name that no lexer has is refused.
- `TestPowershellCheck.test_block_refused`: A `<# #>` comment below the header is refused.
- `TestPowershellCheck.test_header_block`: A `<# #>` comment is allowed as the header.
- `TestPowershellCheck.test_marked_header`: A header of two lines is found past the mark.
- `TestPowershellLexer.test_block_comment`: A `<#` comment runs to its `#>`.
- `TestPowershellLexer.test_here_skipped`: Here strings hide a `#` to their closing line, an empty one too.
- `TestPowershellLexer.test_line_comment`: A `#` after a space or at the start of a line begins a line comment.
- `TestPowershellLexer.test_strings_skipped`: Single and double quoted strings hide a `#`, past their escapes.
- `TestPowershellLexer.test_subexpression_comment`: A comment inside the `$( )` of a double quoted string is found.
- `TestPowershellLexer.test_unterminated_refused`: Each unterminated string, subexpression and comment is refused.
- `TestPowershellLexer.test_word_hash`: A `#` inside a word or after a backtick begins no comment.
- `TestShellLexer.test_here_string`: A here string opens no here document, so the next line is code.
- `TestShellLexer.test_heredoc_skipped`: A here document hides a `#` to its closing line.
- `TestShellLexer.test_heredoc_stripped`: With `-` and a quoted word, tabs may come before the closing word.
- `TestShellLexer.test_heredocs_ordered`: Two here documents begun on a line close in order.
- `TestShellLexer.test_line_comment`: A `#` that starts a word begins a comment, one inside a word does not.
- `TestShellLexer.test_parens_nested`: A paren pair inside a `$( )` does not end it.
- `TestShellLexer.test_quoted_parts`: A double quoted string holds code in its `$( )` alone.
- `TestShellLexer.test_strings_skipped`: Quoted text and an escape hide a `#`.
- `TestShellLexer.test_unterminated_refused`: Each unterminated quote, substitution and here document is refused.
- `TestTypescriptPaths.test_paths_refused`: A top directory that holds no such file is refused.
- `TestTypescriptPaths.test_paths_sorted`: The `.ts` files of `ts/` come sorted, and no other file comes.

##### test_xsjs_serve

unittest, 14 cases, label smoke-test. Tests of xsjs_serve on roots in scratch directories under build/, with the ttyd the driver's bring up built. Its disabled tests are listed in section 5.

- `TestPaths.test_arguments_given`: The command line is the built ttyd, then the gold's on the port given.
- `TestPaths.test_root_default`: The default root is `root` under the start script's folder in home.
- `TestProgram.test_option_refused`: An option the program does not hold ends it before anything is built.
- `TestRoot.test_files_made`: The root holds the modules, the seed, the strings, the files, the page.
- `TestRoot.test_fresh_absent`: Fresh on a root that is not there yet makes it all the same.
- `TestRoot.test_fresh_removed`: Fresh removes the whole root first, what the making keeps included.
- `TestRoot.test_records_removed`: A second making removes an earlier run's records, a file and a directory.
- `TestRoot.test_rest_kept`: A second making replaces what it makes and keeps the rest of the root.
- `TestServer.test_log_copied`: ttyd's log reaches the descriptor given, up to its port's line and after.
- `TestServer.test_port_served`: ttyd serves the port its log names, alone in a session, until its stop.
- `TestServer.test_start_ended`: A ttyd that ends before it listens raises with its code, its log shown.
- `TestServer.test_ttyd_missing`: A ttyd not built is refused, naming where it should be.
- `TestServer.test_wait_ended`: The wait ends at ttyd's end, and the stop then raises with its code.
- `TestServer.test_wait_signal`: Either signal ends the wait, and ttyd, which never saw it blocked, stops.

##### test_guide_walk

unittest, 17 cases, label smoke-test. Tests guide_walk.table_build, by which a guide's table.json becomes the scripted table the port takes, on a scratch guide that each test writes in build/ from the gold's source and files, the core's files in `ecs` beside it, then on the three guides of python/guides/.

- `TestGuides.test_guides_built`: Each guide's table builds, its start one of its nodes.
- `TestScratch.test_arguments_text`: Each call's arguments become their compact JSON text.
- `TestScratch.test_both_refused`: A node that holds both a question and its own other reply is refused.
- `TestScratch.test_calls_refused`: An exit whose calls or resume calls are no list of calls is refused.
- `TestScratch.test_ecs_newline_refused`: A file of the core that does not end in a newline is refused.
- `TestScratch.test_ecs_replaced`: Each object of `$ecs` alone is its core file's text, less the newline.
- `TestScratch.test_exit_absent`: A table with no exit gains no reply and no node.
- `TestScratch.test_exit_copied`: Each node that asks calls its own copies of the exit's lists of calls.
- `TestScratch.test_exit_expanded`: The exit is a reply of the node that asks and three nodes of its own.
- `TestScratch.test_exit_old_refused`: An exit of the old form, a call in place of each list, is refused.
- `TestScratch.test_input_refused`: A node that asks and holds the exit's input or resume is refused.
- `TestScratch.test_member_refused`: An object of `$text` or `$ecs` that holds another member too is refused.
- `TestScratch.test_name_refused`: A node named as a node of an exit is refused where that exit is added.
- `TestScratch.test_neither_refused`: A node with replies and neither a question nor another reply is refused.
- `TestScratch.test_newline_refused`: A file of the guide that does not end in a newline is refused.
- `TestScratch.test_otherwise_built`: A node that asks takes `puzzled` then its question as its other reply.
- `TestScratch.test_text_replaced`: Each object of `$text` alone is its file's text, less the newline.

#### 3.1.2 Python integration suites, the pair test first

##### test_tap_pair

unittest, 12 cases, label smoke-test. Tests the TAP producer and consumer as a pair. Its fixtures are nested classes, run by both producers, which are no cases of their own.

- `TestPair.test_assertion_fails`: A failed assertion counts as one failure.
- `TestPair.test_class_setup`: A failed `setUpClass` counts as the oracle measures it.
- `TestPair.test_class_teardown`: A failed `tearDownClass` counts as the oracle measures it.
- `TestPair.test_error_raised`: An error counts as one failure.
- `TestPair.test_failure_expected`: An expected failure counts as passed, and its block passes.
- `TestPair.test_load_fails`: A module that fails to load counts as unittest's loader counts it.
- `TestPair.test_module_empty`: A module with no tests plans none and passes.
- `TestPair.test_module_setup`: A failed `setUpModule` counts as the oracle measures it, in a child.
- `TestPair.test_pass_counted`: A pass counts as passed.
- `TestPair.test_skips_counted`: A skip counts as skipped, without a reason and with one.
- `TestPair.test_subtests_fail`: A test counts as one failure however many of its subtests fail.
- `TestPair.test_success_unexpected`: An unexpected success counts as one failure.

##### test_integrate_dispatch

unittest, 6 cases, label smoke-test. Tests the dispatcher joined to the codec of `jslb`.

- `TestWire.test_blobs_echoed`: Blobs read go in the line, not payload, and reply blobs follow the reply.
- `TestWire.test_error_carried`: A raise passes through, its error line's cascade in name form, with `r`.
- `TestWire.test_id_float`: An id the decoder reads as a float is refused before any call.
- `TestWire.test_notification_none`: A notification reaches its handler and gets no reply.
- `TestWire.test_request_full`: A request in full names at a version gets its reply in full names.
- `TestWire.test_request_short`: A request in short names gets its reply in short names, with `r`.

##### test_integrate_settings

unittest, 5 cases, label smoke-test. Tests the settings joined to the codec of `jslb`.

- `TestCarried.test_list_damaged`: A list with an item of the wrong type in a nested object is refused.
- `TestCarried.test_settings_carried`: The checkout's settings pass the check as the decoder's objects.
- `TestCarried.test_synchronous_damaged`: A value of the wrong type at the top level is refused.
- `TestDoor.test_file_invalid`: A file that is not JSON raises the decoders' `jslb.text_not_json`.
- `TestDoor.test_number_overflow`: A number that overflows a double is refused at read, by the decoders.

##### test_integrate_vectors_make

unittest, 2 cases, label smoke-test. Tests vectors_make with its real callee, jslb.

- `TestVectors.test_encoded_same`: Success vectors, both kinds, are sidecar messages' jslb iff canonical.
- `TestVectors.test_renders_same`: Each vector's messages render with jslb as its sidecar's renders.

##### test_integrate_engine_db

unittest, 8 cases, label smoke-test. Tests `engine_db` with its callees.

- `TestRestore.test_full_names`: The lines in full names read back as the gold's, one per cache file.
- `TestRestore.test_lines_restored`: The lines carry the whole database: a restore from them gives it back.
- `TestServed.test_pushes_applied`: Each push in both name forms is applied and answered by nothing.
- `TestServed.test_request_refused`: A create with `i` is applied, then refused for want of a reply.
- `TestSync.test_forms_differ`: Debug on: the pushes are in full names, the reply in the request's.
- `TestSync.test_full_names`: In full names the lines carry every database whole, in name order.
- `TestSync.test_push_refused`: A sync that is not a request is refused, as a reply to a push is.
- `TestSync.test_short_names`: In short names the lines carry every database whole, in name order.

##### test_integrate_engine_doc

unittest, 2 cases, label smoke-test. Tests `engine_doc` with its callees.

- `TestServed.test_puts_applied`: Each put writes the next version of the body, answered by nothing.
- `TestServed.test_request_refused`: A put with `i` is applied, then refused for want of a reply.

##### test_integrate_engine_kv

unittest, 5 cases, label smoke-test. Tests `engine_kv` with its callees.

- `TestServed.test_delete_served`: A delete removes the row a put made, both answered by nothing.
- `TestServed.test_full_names`: Lines in full names are applied as ones in short names.
- `TestServed.test_image_put`: The image goes to the store under the header's key. Nothing answers.
- `TestServed.test_request_refused`: A put with `i` is applied, then refused for want of a reply.
- `TestServed.test_streamed_put`: A value the decoder streams to a file goes to the store whole.

##### test_integrate_engine_sql

unittest, 3 cases, label smoke-test. Tests `engine_sql` with its callees.

- `TestServed.test_full_names`: A line in full names is applied as one in short names.
- `TestServed.test_request_refused`: A run with `i` is applied, then refused for want of a reply.
- `TestServed.test_runs_applied`: Each run makes its table and row, the quoted text whole, unanswered.

##### test_integrate_engine_tap

unittest, 5 cases, label smoke-test. Tests engine_tap with its real callees in forked children, each on a scratch root in `build/`.

- `TestFailure.test_failure_taken`: The line's message in a bail out ends the TypeScript file.
- `TestServe.test_language_refused`: A language other than typescript is refused, and nothing is written.
- `TestServe.test_lines_served`: A run's lines, pushed, are appended to the file in order, unanswered.
- `TestServe.test_request_refused`: A `tap.line` request is appended, then refused for want of a reply.
- `TestServe.test_version_unknown`: The type is served at version 0 alone: version 1 has no handler.

##### test_integrate_engine_turn

unittest, 5 cases, label smoke-test. Tests `engine_turn` with its callees.

- `TestServed.test_full_names`: A line in full names is applied as one in short names.
- `TestServed.test_prompt_served`: A prompt line crosses the wire and comes before the turn that follows.
- `TestServed.test_request_refused`: An append with `i` is applied, then refused for want of a reply.
- `TestServed.test_text_wide`: Text beyond ASCII crosses the wire and is stored as raw characters.
- `TestServed.test_turns_served`: The player's message, a reply's call, the call's output, the answer.

##### test_integrate_mcp

unittest, 3 cases, label smoke-test. Tests the MCP server and client joined to `dispatch`, which writes the cascade of an exception.

- `TestCascade.test_cause_kept`: The exception a tool raised from another holds it under `cause`.
- `TestCascade.test_client_cascade`: A client joined to the server passes on the result with the cascade.
- `TestCascade.test_context_kept`: The exception a tool raised while another was handled holds it too.

##### test_integrate_page_build

unittest, 1 case, label smoke-test. Tests page_build.py with its project callees, vectors_make.py and jslb.py, whose suites have passed.

- `TestVectors.test_vectors_built`: The piece carries the vectors written anew, not a file left before.

##### test_integrate_tap_loop

unittest, 1 case, label smoke-test. Tests the TAP suite server joined to everything it calls into, in a forked child over pipes, with a root in `build/` whose settings are the checkout's and whose parameters are the run's with debug false, short names, which the child sets as `bootstrap.py` does.

- `TestRuns.test_runs_served`: Each run pushes its stream, then replies the driver's pass.

##### test_integrate_echo_loop

unittest, 2 cases, label smoke-test. Tests the echo main loop joined to everything it calls into, in forked children over pipes, with roots in `build/` whose settings are the checkout's with the gold's sizes.

- `TestSession.test_session_failed`: Echo, push, unhandled: echo out, `error` by id, push only in TAP.
- `TestSession.test_session_served`: Echo, push, fail: echoes out, pushes, bail in TAP, blob cached.

##### test_integrate_engine_mcp

unittest, 4 cases, label smoke-test. Tests engine_mcp with its real callees in forked children.

- `TestServe.test_failure_served`: A tool's exception is the `isError` reply of a `Failure`, its `r` set.
- `TestServe.test_push_refused`: A request pushed with no wire id is refused for the reply it gets.
- `TestServe.test_session_served`: Opening a session replies to `initialize` and `tools/list` only.
- `TestServe.test_tool_served`: A tool answers the arguments the decoder read, in their order.

##### test_integrate_engine_system

unittest, 5 cases, label smoke-test. Tests engine_system with its real callees in forked children, each on a scratch root in `build/`.

- `TestServe.test_debug_off`: Debug off: each write refused, and a streamed blob stays in the cache.
- `TestServe.test_restart_refused`: A restart to a missing file is refused, in a child it would replace.
- `TestServe.test_settings_served`: The settings the decoder read are written whole, the reply read back.
- `TestServe.test_source_memory`: A blob in memory is written as the main loop file.
- `TestServe.test_source_streamed`: A blob the decoder streamed is moved out of the cache into place.

##### test_integrate_main_loop

unittest, 10 cases, label smoke-test. Tests the main loop serving every engine it registers, each line type but `system.restart`, which execs, in forked children over pipes, with roots in `build/`.

- `TestEngines.test_audit_tail`: `audit.tail` gives the audit's newest entries, a line read among them.
- `TestEngines.test_debug_off`: With `debug` false, `source.put` gets an `error` line and writes nothing.
- `TestEngines.test_debug_served`: Debug on: `source.put` writes a loop, `settings.put` settings, answered.
- `TestEngines.test_mcp_tools`: The server's MCP server answers `initialize` and `tools/list` only.
- `TestEngines.test_pushes_applied`: Every kind of commit is applied as a push and answered by nothing.
- `TestEngines.test_session_unrecorded`: With `debug` false, a whole session leaves no record in the root.
- `TestEngines.test_sync_image`: `db.sync` carries the seeded image's row and the scene that names it.
- `TestEngines.test_sync_recorded`: A sync's lines are recorded in order, in full, with no blob's bytes.
- `TestEngines.test_sync_whole`: `db.sync` sends every database whole, each with its cache files after it.
- `TestEngines.test_tap_line`: A `tap.line` of the TypeScript stream is appended to its file, no answer.

##### test_integrate_mcp_stdio

unittest, 3 cases, label smoke-test. Tests the runner of the stdio transport, `stdio_serve`, which reads the root's settings and parameters and serves the tools of `engine_system` on a real `mcp.Server`, in forked children whose stdin is a pipe and stdout a file, on roots in build/ that hold the checkout's settings and the run's parameters with `debug` set.

- `TestServe.test_debug_refused`: Debug off: an error answer, a raise ends the run before line 2, no file.
- `TestServe.test_session_served`: Each line is answered, tools of the API file, and end of input exits 0.
- `TestServe.test_source_written`: Debug on: `source_put` writes the loop file, answering with its digest.

##### test_integrate_test_posix

unittest, 19 cases, label smoke-test. Tests test_posix.py with its project callees, category.py, page_build.py, reformat.py and switches.py, whose suites have passed.

- `TestAnthropicSwitch.test_driver_skipped`: Set by the test driver before its call, the switch does the same.
- `TestAnthropicSwitch.test_option_skipped`: Given to `test_posix.py`, the switch has it return, printing nothing.
- `TestDriverCounted.test_limit_counted`: The suite of the store's limit counts for the store module.
- `TestDriverCounted.test_modules_present`: Every suite of a `test-all` run counts for modules that exist.
- `TestDriverDisabled.test_disabled_left`: No run takes a disabled suite, and its module is left unchecked.
- `TestDriverDisabled.test_disabled_level`: A `test-disabled` run takes each disabled suite, and checks its module.
- `TestDriverDisabled.test_disabled_named`: `--module` runs a disabled suite, and its module is then checked.
- `TestDriverLevels.test_default_end`: With no option the run has no stream, and its rungs are of `smoke-test`.
- `TestDriverLevels.test_default_guides`: A run with no stream runs the guide tests alone.
- `TestDriverLevels.test_levels_raised`: Each level above end to end has a stream, the higher of two options won.
- `TestDriverLevels.test_normal_programs`: A run with a stream runs the wire, browser and demo tests first.
- `TestDriverLevels.test_programs_present`: Each end to end program is a file of the checkout's `python`.
- `TestDriverLevels.test_removed_refused`: The option the default level took the place of is gone.
- `TestDriverLevels.test_stream_raised`: An option of the stream raises the run to normal, not higher.
- `TestDriverSuites.test_formatters_left`: Under the switch, a `test-all` run takes no suite of a formatter.
- `TestDriverSuites.test_formatters_taken`: Without the switch, a `test-all` run takes them.
- `TestDriverSuites.test_module_refused`: Under the switch, `--module` refuses each suite of a formatter.
- `TestFormatterStep.test_normal_formatted`: A `test-all` run formats with no command and prints nothing.
- `TestFormatterStep.test_smoke_untouched`: A `smoke-test` run prints nothing and leaves the files alone.

##### test_integrate_bootstrap

unittest, 3 cases, label smoke-test. Tests the platform services with the stock main_loop.py serving every engine, in process. Its disabled tests are listed in section 5.

- `TestStock.test_failure_once`: A loop failure records one error line, and bootstrap adds nothing.
- `TestStock.test_page_failed`: A page error, recorded as read, ends the TAP file and run unanswered.
- `TestStock.test_tail_shared`: `audit.tail` reads bootstrap's records, then the main loop's, unrecorded.

##### test_integrate_xsjs_serve

unittest, 1 case, label smoke-test. Tests xsjs_serve.py as a program, as a person starts it, on a root in a scratch directory under build/.

- `TestProgram.test_token_fetched`: The program serves, ttyd gives its token, and SIGTERM stops them both.

#### 3.1.3 Python stdio suites

##### test_mcp_stdio_process

unittest, 3 cases, label smoke-test. Tests mcp_stdio.py as a process, started on pipes the way an external agent starts it, on a root in build/ that holds a copy of the checkout's settings.json and the run's parameters with debug true.

- `TestProcess.test_process_malformed`: A line that is not JSON exits with 1 and a traceback on stderr.
- `TestProcess.test_process_replay`: A session replays line for line, then closing stdin exits with 0.
- `TestProcess.test_process_wide`: Text outside ASCII comes in and goes out as `utf-8`, whatever the locale.

##### test_tap_tty

unittest, 17 cases, label smoke-test. Tests bootstrap.py run whole on a pty as ttyd runs it, unpatched, through tap_tty's EngineTty, with roots in build/ that hold no gold.

- `TestStall.test_stall_hangup`: The engine that never writes its first line ends by SIGHUP, unrecorded.
- `TestStock.test_failure_answered`: A handler's `Failure` writes its reply, then the server's error line.
- `TestStock.test_hangup_unread`: A hangup with a reply unread ends the engine by SIGHUP, no failure.
- `TestStock.test_lines_served`: Each line type but the debug ones, once, each push seen by the next.
- `TestStock.test_page_failed`: The page's error line ends its TAP stream and the engine, unanswered.
- `TestStock.test_page_quiet`: Outside debug mode the page's error line ends the engine, nothing kept.
- `TestStock.test_reply_refused`: A reply to the first line that is not the empty reply is refused.
- `TestStock.test_request_unknown`: A request of no handler is answered by an error line, then exit 1.
- `TestStock.test_restart_served`: The debug lines put the settings and a main loop file, then restart.
- `TestStock.test_start_full`: In debug mode the first line has full names and carries no gold.
- `TestStock.test_start_short`: Outside debug mode the first line has short names and no gold.
- `TestStock.test_stdio_beside`: `mcp_stdio.py` serves the same root while the engine runs on it.
- `TestSuites.test_bail_relayed`: A `smoke-test` run is failfast: its first failure bails out, one failure.
- `TestSuites.test_failures_miscounted`: Expecting one failure fewer or one more than the stream holds fails.
- `TestSuites.test_failures_relayed`: The failing suite relayed whole holds its failures, exactly expected.
- `TestSuites.test_suite_refused`: A suite the driver does not know is refused with no stream.
- `TestSuites.test_suites_relayed`: The gold's suites run on the server, their stream passing and whole.

#### 3.1.4 TypeScript group A unit blocks, in Node

##### test_tap_producer.ts

unittest, 33 cases, label smoke-test. Tests the TAP producer.

- `TestTracker.test_points_numbered`: Points are numbered, durations to one digit, and the last plan counts.
- `TestTracker.test_plan_first`: A plan set first is written at once, before the points.
- `TestTracker.test_diagnostics_blank`: A blank line of diagnostic text is still a diagnostic line.
- `TestTracker.test_line_refused`: Text that would break its line is refused with its diagnostics.
- `TestRunner.test_modules_pass`: Blocks plan first, parents follow, and the parent plan comes last.
- `TestRunner.test_module_fails`: Without failfast a failed module is graded and the stream goes on.
- `TestRunner.test_bail_ends`: A stream that bailed out takes no other module and writes no plan.
- `TestRunner.test_end_twice`: The stream ends once, and takes no module after its end.
- `TestRunner.test_stream_once`: The stream is set once, and a block before it is refused.
- `TestRunner.test_name_refused`: A module name that would break its lines is refused before any block.
- `TestBlocks.test_block_passes`: The plan comes at the start, points stream as added, then the parent.
- `TestBlocks.test_block_fails`: Without failfast a failed point fails the block and the stream goes on.
- `TestBlocks.test_block_failfast`: With failfast a failed point ends the stream before its planned points.
- `TestBlocks.test_block_open`: An open block takes no other block or module, and must end by its name.
- `TestBlocks.test_block_refused`: A block name that would break its lines is refused, and no block opens.
- `TestFailures.test_assertion_fails`: A failed assertion is a failing point with the assertion's text.
- `TestFailures.test_error_thrown`: An error thrown in a test is a failing point with the error's text.
- `TestFailures.test_setup_throws`: An error in `setUp` fails the test's point.
- `TestFailures.test_teardown_throws`: An error in `tearDown` fails the point of a test that passed.
- `TestFailures.test_outcomes_two`: A second outcome of one test adds its diagnostics to the same point.
- `TestFailures.test_failure_expected`: An expected failure is a `TODO` point that does not fail the block.
- `TestFailures.test_success_unexpected`: An unexpected success fails its point and says so.
- `TestFailures.test_skip_reason`: A skip is a passing point with its reason.
- `TestFailures.test_mixed_outcomes`: Without failfast every test runs and the failures fail the block.
- `TestFailures.test_failfast_bails`: With failfast the first failure ends the stream with a bail out line.
- `TestFailures.test_load_fails`: A module that does not load is one failing point with its stack.
- `TestFailures.test_load_failfast`: With failfast a module that does not load ends the stream.
- `TestExpectation.test_stated_lines`: Diagnostic lines not stated are dropped, stated ones kept in order.
- `TestExpectation.test_line_missing`: A stated line the run lacks leaves the streams different.
- `TestExpectation.test_run_unstated`: A run of diagnostics the expectation does not state is kept whole.
- `TestExpectation.test_failure_other`: A suite that fails another way does not match the stated failure.
- `TestReport.test_report_spans`: Failed points with their YAML blocks and diagnostics are wrapped.
- `TestReport.test_report_escape`: The text is escaped as HTML, inside a span and out of it.

##### test_unittest.ts

unittest, 16 cases, label smoke-test. Tests the unittest subset through its real result.

- `TestUnittest.test_outcome_lists`: Each kind of test is kept as Python keeps it.
- `TestUnittest.test_success_unkept`: A pass is kept by no list, and leaves the result successful.
- `TestUnittest.test_part_order`: `tearDown` runs after a test that passed and after one that failed.
- `TestUnittest.test_report_order`: A test starts before `setUp`, and a failure is kept before `tearDown`.
- `TestUnittest.test_loader_order`: The loader takes `TestCase` classes only, methods in definition order.
- `TestUnittest.test_expected_outcomes`: A test expected to fail keeps a throw as expected and a pass as not.
- `TestUnittest.test_expected_setup`: An error in `setUp` of a test expected to fail is an error.
- `TestUnittest.test_stack_header`: The stack of a failed assertion starts with its name and message.
- `TestUnittest.test_stop_flag`: A result that asks to stop before the first test runs nothing.
- `TestUnittest.test_failfast_stops`: With failfast a failure stops the run, and so does an unexpected pass.
- `TestUnittest.test_stack_missing`: A throw with no stack has no text to keep, and the result says so.
- `TestUnittest.test_missing_method`: A case bound to a method its class lacks is refused.
- `TestUnittest.test_assert_equal`: `assertEqual` compares arrays, bytes and plain objects by content.
- `TestUnittest.test_assert_in`: `assertIn` searches text, arrays by value and object keys.
- `TestUnittest.test_assert_raises`: `assertRaises` passes on its class, fails on no throw, passes others on.
- `TestUnittest.test_truth_asserts`: `assertTrue` and `assertFalse` follow JavaScript truth.

##### test_harness.ts

unittest, 6 cases, label smoke-test. Tests of harness.ts on the values the bring-up set.

- `TestValues.test_run_values`: The unit suites run only in debug mode, and only in the unit run.
- `TestValues.test_gold_built`: The gold is a copy of the built `test_gold`, not the object itself.
- `TestValues.test_nested_id`: A nested id reads the value under each of its keys.
- `TestValues.test_unknown_id`: An unknown id, or one through a value that is no object, names its file.
- `TestValues.test_set_twice`: A second `values_set` throws and the values stay as they were.
- `TestValues.test_values_frozen`: What the harness keeps is frozen, every object and array in it too.

##### test_ui_strings.ts

unittest, 2 cases, label smoke-test. Tests of the strings table module.

- `TestTableFrozen.test_table_frozen`: Both the table and the module object report frozen.
- `TestTableFrozen.test_table_write`: Adding a name to the table throws.

##### test_i18n.ts

unittest, 13 cases, label smoke-test. Tests of the strings function and its placeholder rule.

- `TestStringCall.test_missing_name`: A name that is not in the table throws, with or without arguments.
- `TestStringCall.test_inherited_name`: A name only the object prototype has is missing too.
- `TestStringCall.test_plain_text`: A text with no braces is returned as the table holds it.
- `TestStringCall.test_plain_extra`: An argument given to a text with no placeholder throws.
- `TestStringFormat.test_literal_braces`: Braces that are not a canonical index stay literal, as `{01}` does.
- `TestStringFormat.test_fill_indices`: The arguments fill the placeholders by index.
- `TestStringFormat.test_repeat_index`: An index may repeat and counts once.
- `TestStringFormat.test_gap_index`: A gap in the indices throws, at any argument count.
- `TestStringFormat.test_index_range`: An index at or past the argument count throws.
- `TestStringFormat.test_count_mismatch`: Fewer or more arguments than the placeholders throw.
- `TestStringFormat.test_no_placeholder`: A text with no placeholder and no arguments is returned as it is.
- `TestStringFormat.test_argument_literal`: The fill is one pass: braces and dollars in an argument stay as given.
- `TestStringFormat.test_number_argument`: A number is filled as its text.

##### test_switches.ts

unittest, 5 cases, label smoke-test. Tests of the switches module.

- `TestSwitchStore.test_set_read`: A value set is read back equal and frozen.
- `TestSwitchStore.test_set_twice`: A second set throws and keeps the first value.
- `TestSwitchStore.test_get_unset`: A read before the set throws.
- `TestSwitchStore.test_set_malformed`: Each value of another shape throws, naming it, and sets nothing.
- `TestThread.test_thread_read`: The three readers agree, and a second set throws.

##### test_utility.ts

unittest, 45 cases, label smoke-test. Tests of the shared routines in `utility.ts`.

- `TestDigest.test_empty_input`: No bytes at all still hash the one padding block.
- `TestDigest.test_short_text`: The standard three byte message.
- `TestDigest.test_padding_block`: The standard 448 bit message, whose padding spills into a second block.
- `TestDigest.test_two_chunks`: The standard 896 bit message, whose own bytes span two chunks.
- `TestDigest.test_million_bytes`: The standard message of a million letters a, many chunks.
- `TestDigest.test_view_offset`: Bytes that start inside a larger buffer hash as they would alone.
- `TestDigest.test_padding_vectors`: Inputs of 55, 56 and 64 bytes, whole and in pieces, give their digest.
- `TestHashStream.test_digest_midway`: A digest taken midway leaves the stream to go on to the whole digest.
- `TestHashStream.test_view_offset`: A view into a larger buffer is read from its offset, and not kept.
- `TestEncoding.test_empty_text`: No text gives no bytes.
- `TestEncoding.test_ascii_bytes`: ASCII is one byte each.
- `TestEncoding.test_two_bytes`: `U+00E9` takes two bytes.
- `TestEncoding.test_three_bytes`: `U+20AC` and `U+4E2D` take three bytes.
- `TestEncoding.test_four_bytes`: `U+1F600` takes four bytes.
- `TestEncoding.test_round_trip`: Text of every length survives encoding and decoding.
- `TestEncoding.test_byte_order`: A leading byte order mark is kept as the character `U+FEFF`.
- `TestEncoding.test_lone_surrogate`: A surrogate that is not half of a pair throws, wherever it stands.
- `TestEncoding.test_lone_byte`: A byte that no sequence can hold throws.
- `TestEncoding.test_bad_continuation`: A lead byte without a continuation byte after it throws.
- `TestEncoding.test_overlong_form`: An overlong form of a slash throws.
- `TestEncoding.test_surrogate_bytes`: The bytes of the surrogate `U+D800` throw.
- `TestEncoding.test_truncated_form`: A sequence cut short at the end throws.
- `TestEncoding.test_range_limit`: A code point beyond `U+10FFFF` throws.
- `TestDecoding.test_standard_vectors`: The test vectors of the base64 standard, with and without padding.
- `TestDecoding.test_high_bytes`: Bytes above 127 and the last two characters of the alphabet.
- `TestDecoding.test_bad_character`: A character outside the alphabet throws.
- `TestDecoding.test_bad_length`: A length that no padding can complete throws.
- `TestDecoding.test_missing_padding`: Text whose padding is missing throws.
- `TestDecoding.test_trailing_bits`: A last character whose unused bits are not zero throws.
- `TestDecoding.test_white_space`: White space anywhere throws.
- `TestJsonText.test_compact_output`: No whitespace is written outside strings, and inside them it is kept.
- `TestJsonText.test_key_order`: Integer like keys come first in ascending order, the rest as inserted.
- `TestJsonText.test_raw_characters`: Characters beyond ASCII are written as they are.
- `TestJsonText.test_escaped_controls`: Control characters are escaped.
- `TestJsonText.test_double_range`: Every finite double is written, those beyond 2 to the 53 too.
- `TestJsonText.test_no_text`: A value with no JSON text throws and does not give undefined.
- `TestFailure.test_wrap_cause`: The wrapper is an `Error` with the message and the very same cause.
- `TestFailure.test_wrap_value`: A cause that is not an `Error` is kept as it is.
- `TestFailure.test_fail_now`: The throw carries the message.
- `TestCauseAppend.test_no_cause`: An `Error` with no `cause` takes `first` as it, and is returned itself.
- `TestCauseAppend.test_chain`: In a chain of two, `first` goes under the innermost.
- `TestCauseAppend.test_value_thrown`: A thrown value that is no `Error` becomes one, its text the message.
- `TestCauseAppend.test_cause_value`: An innermost `cause` that is no `Error` becomes an `Error` of its text.
- `TestClock.test_clock_bounds`: The time is a whole number between two readings of the platform clock.
- `TestSurface.test_frozen_names`: The module is frozen and holds the ten names of its declaration.

##### test_jslb.ts

unittest, 38 cases, label smoke-test. Tests of jslb.ts that need no decoder.

- `TestBuild.test_header_defaults`: A header holds only its type when every field is at its default.
- `TestBuild.test_header_short`: Every field is set, in order, with short names.
- `TestBuild.test_header_full`: Every field is set, in order, with full names.
- `TestBuild.test_blob_bytes`: A blob of bytes is measured and keeps the same bytes object as `d`.
- `TestBuild.test_blob_reserved`: A field that `blob_make` sets cannot be given as a handler field.
- `TestBuild.test_line_numbering`: Blob headers are numbered from 1 and counted in a copy of the header.
- `TestBuild.test_line_empty`: A line with no blobs leaves the count out.
- `TestBuild.test_line_full`: A full header gives the blob headers full names for size and key.
- `TestBuild.test_line_counted`: A header that already counts blobs is refused.
- `TestBuild.test_payload_refused`: A payload key of decimal digits would read as a header, so is refused.
- `TestFields.test_field_short`: Either name form finds each field of a short header.
- `TestFields.test_field_full`: Either name form finds each field of full headers, blob headers too.
- `TestFields.test_field_defaults`: An absent field gives its default, or `undefined` when it has none.
- `TestFields.test_field_refused`: An absent required field throws, as does a name that is no field.
- `TestFields.test_field_forms`: A header holding both forms of a field throws.
- `TestFields.test_headers_probing`: Probing stops at the first missing integer key, strings included.
- `TestFields.test_payload_keys`: The payload is every key that is not an integer key, in order.
- `TestEncode.test_encode_empty`: A line with no blobs is its JSON text with no spaces and a CR.
- `TestEncode.test_encode_order`: Integer keys come first in ascending order, in nested objects too.
- `TestEncode.test_encode_keys`: Digit keys beyond the array indices are integer keys all the same.
- `TestEncode.test_encode_text`: Text is raw `UTF-8`, escaped as JSON does, with no CR but the last.
- `TestEncode.test_float_refused`: `NaN` and the infinities are refused.
- `TestEncode.test_value_refused`: A value that JSON has no text for is refused, not dropped or changed.
- `TestEncode.test_bytes_tagged`: Bytes in a value render as a tag of their size. The encoder refuses them.
- `TestEncode.test_text_refused`: Text holding half a surrogate pair is refused, in values and keys.
- `TestEncode.test_key_digits`: A payload key of digits is refused, a nested one is written as it is.
- `TestEncode.test_size_differs`: A blob whose `d` is missing or of another size is refused.
- `TestEncode.test_encode_checked`: The encoder refuses a line that the decoder would refuse.
- `TestRender.test_render_blobs`: The JSON text is followed by one tag per blob, numbered from 1.
- `TestRender.test_render_plain`: A line with no blobs renders as its JSON text alone.
- `TestJson.test_json_blobs`: The JSON text the encoder writes, its CR and blob bytes left off.
- `TestJson.test_json_bytes`: Bytes nested in a value become the marker of their size.
- `TestJsonDecode.test_values`: Any JSON value is returned, an array and a bare number too.
- `TestJsonDecode.test_numbers_read`: The tokens a line reads, read here the same.
- `TestJsonDecode.test_numbers_refused`: The tokens a line refuses, refused here the same.
- `TestJsonDecode.test_not_json`: A text that is not JSON is refused, the parse error its cause.
- `TestSurface.test_frozen_names`: The module is frozen and holds the names of its declaration.
- `TestSurface.test_error_name`: The error is named on its prototype, so its stack header shows it.

##### test_settings.ts

unittest, 13 cases, label smoke-test. Tests of the settings module.

- `TestValueStore.test_get_unset`: Reading an id before the settings are set throws.
- `TestValueStore.test_unknown_id`: An id that names no key throws, at any depth.
- `TestValueStore.test_nested_ids`: Top level and nested ids return their values.
- `TestValueStore.test_names_full`: Full names before the settings are set, then as debug mode says.
- `TestValueStore.test_frozen_write`: Outside debug mode the whole object is frozen and refuses a write.
- `TestValueStore.test_set_twice`: A second set throws and leaves the first settings in place.
- `TestValueStore.test_debug_mutable`: In debug mode the object is not frozen and shows a change at once.
- `TestValueStore.test_put_denied`: A put outside debug mode throws, sends nothing and changes nothing.
- `TestValueStore.test_put_unset`: A put before the settings are set throws.
- `TestValueStore.test_put_sent`: A put in debug mode changes the live value and sends all settings.
- `TestValueStore.test_put_unknown`: A put of an unknown id throws and sends nothing.
- `TestValueStore.test_sender_missing`: A put with no sender registered throws and changes nothing.
- `TestValueStore.test_sender_twice`: A second sender registration throws.

##### test_dispatch.ts

unittest, 41 cases, label smoke-test. Tests of the dispatcher.

- `TestHandlerRegistration.test_twice_throws`: A second registration of a pair throws and the first one stays.
- `TestHandlerRegistration.test_pairs_differ`: The same type at another version, and another type, register.
- `TestLineDispatch.test_handler_called`: Only the handler of the line's type and version is called.
- `TestLineDispatch.test_version_default`: A line with no version reaches the handler of version 0.
- `TestLineDispatch.test_line_whole`: The handler gets the line itself, with its blobs and payload in place.
- `TestLineDispatch.test_pair_unknown`: A type or a version that nothing registered throws.
- `TestLineDispatch.test_handler_throws`: An error from a handler propagates unchanged.
- `TestLineDispatch.test_request_reply`: A request gets the reply its handler returned, with `r` set to its `i`.
- `TestLineDispatch.test_full_request`: A full name request is answered in full names.
- `TestLineDispatch.test_reply_unset`: A reply without `r` gets it, spelled in the name form of its header.
- `TestLineDispatch.test_reply_overwritten`: A reply that names another request is changed to name this one.
- `TestLineDispatch.test_request_none`: A request whose handler returns nothing throws.
- `TestLineDispatch.test_notification_none`: A notification whose handler returns nothing returns nothing.
- `TestLineDispatch.test_notification_reply`: A notification whose handler returns a reply to no request throws.
- `TestLineDispatch.test_wake_reply`: A wake line has no id and may return the reply to an earlier request.
- `TestLineDispatch.test_reply_headerless`: A reply with no header throws, for a request and for a notification.
- `TestTaskSleep.test_sleep_fields`: The sleep holds the state, the ids and the type it was given.
- `TestTaskSleep.test_sleep_returned`: A sleep comes back unchanged, from a request and from a notification.
- `TestFailure.test_failure_fields`: The failure holds the reply and the error it was given.
- `TestFailure.test_request_failure`: The reply of a request's failure gets `r`, the failure comes back.
- `TestFailure.test_wake_failure`: The failure of a wake whose reply answers a request comes back as is.
- `TestFailure.test_notification_failure`: A failure of a line with no id throws, the failure's error its cause.
- `TestReplyMake.test_short_names`: A short name reply has `t` and `r` and nothing else of the request.
- `TestReplyMake.test_full_names`: A full name reply has `type` and `reply` and nothing else.
- `TestReplyMake.test_id_absent`: A reply to a notification has no `r`.
- `TestReplyMake.test_blobs_numbered`: Blobs are numbered from 1 and counted, apart from the payload.
- `TestErrorMake.test_request_error`: The error line of a request has `r`, the message and the stack.
- `TestErrorMake.test_full_error`: The error line of a full name request uses full names.
- `TestErrorMake.test_notification_error`: The error line of a notification has no `r`.
- `TestErrorMake.test_no_line`: The error line of no line has no `r`, in the form the settings pick.
- `TestErrorMake.test_stack_missing`: An error with no stack cannot be sent, so it throws.
- `TestErrorMake.test_cascade`: The error line carries the cascade under `cause`, the first innermost.
- `TestErrorMake.test_value_thrown`: A thrown value that is no `Error` is written as its text, no stack.
- `TestCauseMake.test_nested_errors`: An `Error` with two nested causes gives three entries, nested in order.
- `TestCauseMake.test_cause_value`: A `cause` that is no `Error` is written as its text with no stack.
- `TestCauseMake.test_value_thrown`: A thrown value that is no `Error` is written as its text with no stack.
- `TestCauseMake.test_stack_missing`: A nested `Error` with no stack cannot be sent, so it throws.
- `TestHeaderKinds.test_type_invalid`: A type that is not text throws in each call that reads it.
- `TestHeaderKinds.test_id_invalid`: An id that is not a number throws, before the handler is called.
- `TestIdNext.test_ids_count`: The ids of a port count up from 102, as 101 is the first line's.
- `TestIdNext.test_ports_separate`: Each port counts on its own, each from 102.

##### test_http.ts

unittest, 35 cases, label smoke-test. Tests of the HTTP port that need no network.

- `TestRequestTranslate.test_json_body`: A `json` field is serialized as the body, with no white space.
- `TestRequestTranslate.test_text_body`: A `body` field is sent as it is, white space and all.
- `TestRequestTranslate.test_json_wins`: When both fields are present the `json` field is the body.
- `TestRequestTranslate.test_json_null`: A `json` field of `null` is present, so the body is the text `null`.
- `TestRequestTranslate.test_json_unicode`: Text outside ASCII is written as it is and not as an escape.
- `TestRequestTranslate.test_body_absent`: A request with neither field has no body at all.
- `TestRequestTranslate.test_headers_kept`: The headers go on as given, names in the case they came in.
- `TestRequestTranslate.test_json_refused`: A `json` field that JSON cannot carry throws and sends nothing.
- `TestRequestTranslate.test_json_unchecked`: NaN and the infinities, which no decoder lets in, are sent as null.
- `TestRequestChecks.test_fields_least`: The smallest request is accepted.
- `TestRequestChecks.test_type_other`: A line of another type is refused.
- `TestRequestChecks.test_id_missing`: A request with no id is refused, as nothing could answer it.
- `TestRequestChecks.test_blobs_refused`: A request that carries a blob is refused.
- `TestRequestChecks.test_method_invalid`: A method other than GET or POST, in any form, is refused.
- `TestRequestChecks.test_url_invalid`: A url that is not text is refused.
- `TestRequestChecks.test_headers_invalid`: Headers that are not an object of text values are refused.
- `TestRequestChecks.test_body_invalid`: A `body` that is not text is refused, even beside a `json` field.
- `TestAnswerReply.test_json_answer`: A JSON response is a reply with `r` set and the parsed `json`.
- `TestAnswerReply.test_json_parameters`: The media type is read without its parameters and in any case.
- `TestAnswerReply.test_text_answer`: Any other body is `text`, even one that would parse as JSON.
- `TestAnswerReply.test_empty_answer`: A success with no body and no headers is an empty `text`.
- `TestAnswerReply.test_status_range`: Statuses 200 to 299 are replies and every other status is an error.
- `TestAnswerReply.test_status_error`: A failed status is an `error` line naming the url, status and body.
- `TestAnswerReply.test_json_malformed`: A body that is not JSON under a JSON content type is an `error` line.
- `TestAnswerReply.test_json_overflow`: A JSON body holding a number that overflows a double is refused too.
- `TestAnswerReply.test_reply_number`: The reply carries the id of its own request, and no id of its own.
- `TestAnswerReply.test_full_names`: A request in full names is answered in full names, error lines too.
- `TestFailureReply.test_timeout_text`: The timeout is an `error` line naming the url and the seconds.
- `TestFailureReply.test_timeout_fraction`: Fractions of a second are named as they are.
- `TestFailureReply.test_error_full`: The timeout's error line follows the name form of the request.
- `TestPortChecks.test_timeout_valid`: Timeouts above 0 that a timer can hold are accepted.
- `TestPortChecks.test_timeout_invalid`: Timeouts that are 0, negative or too long for a timer throw.
- `TestPortChecks.test_receiver_twice`: A second receiver throws.
- `TestPortChecks.test_post_unreceived`: A request posted before a receiver is set throws.
- `TestPortChecks.test_post_refused`: A line that fails a check throws from the post and nothing is received.

##### test_media.ts

unittest, 25 cases, label smoke-test. Tests of the media cache and port that need no image decoder and no network.

- `TestCacheBudget.test_budget_valid`: Budgets above 0 are accepted, whole bytes or not.
- `TestCacheBudget.test_budget_invalid`: Budgets that are 0 or negative throw.
- `TestRequestChecks.test_store_least`: The smallest store request is accepted and keeps its bytes.
- `TestRequestChecks.test_fetch_least`: The smallest fetch request is accepted and keeps its url.
- `TestRequestChecks.test_type_other`: A line of another type is refused.
- `TestRequestChecks.test_id_missing`: A request with no id is refused, as nothing could answer it.
- `TestRequestChecks.test_blobs_count`: A store needs exactly one blob and a fetch needs none.
- `TestRequestChecks.test_blob_handle`: A store whose blob is a cache handle and not bytes is refused.
- `TestRequestChecks.test_key_invalid`: A key that is missing, empty or not text is refused in both types.
- `TestRequestChecks.test_url_invalid`: A url that is missing, empty or not text is refused.
- `TestReplyLines.test_store_reply`: A store is answered with its key, size and hash and no blob.
- `TestReplyLines.test_fetch_reply`: A fetch is answered with the same payload and the bytes as blob 1.
- `TestReplyLines.test_reply_number`: The reply carries the id of its own request and no id of its own.
- `TestReplyLines.test_full_names`: A request in full names is answered in full names.
- `TestReplyLines.test_view_bytes`: The size and hash are those of the bytes in a view, not of its buffer.
- `TestFailureLines.test_timeout_text`: The timeout gives an error line naming the url, key and seconds.
- `TestFailureLines.test_timeout_fraction`: Fractions of a second are named as they are.
- `TestFailureLines.test_error_full`: The timeout's error line follows the name form of the request.
- `TestPortChecks.test_timeout_valid`: Timeouts above 0 that a timer can hold are accepted.
- `TestPortChecks.test_timeout_invalid`: Timeouts that are 0, negative or too long for a timer throw.
- `TestPortChecks.test_budget_invalid`: A budget that is 0 or negative throws from the port too.
- `TestPortChecks.test_receiver_twice`: A second receiver throws.
- `TestPortChecks.test_post_unreceived`: A request posted before a receiver is set throws.
- `TestPortChecks.test_post_refused`: A line that fails a check throws from the post and nothing is received.
- `TestPortChecks.test_image_absent`: A port that has kept nothing has no image under any key.

##### test_provider.ts

unittest, 21 cases, label smoke-test. Tests of the provider door to xAI's Responses API.

- `TestRequestBuild.test_model_whole`: A model request with every field writes them in the door's order.
- `TestRequestBuild.test_model_least`: A model request with no optional field writes the three it must.
- `TestRequestBuild.test_image_line`: An image request goes to the image path with its own body.
- `TestRequestBuild.test_key_carried`: The key given is the one the header carries.
- `TestModelResponse.test_output_kept`: The four fields are read and each item is kept as parsed, whole.
- `TestModelResponse.test_status_incomplete`: A reply cut short by a limit is read, its status kept.
- `TestModelResponse.test_output_least`: An output with no item, and a reasoning item with no content, are read.
- `TestModelResponse.test_full_names`: A reply in full names is read as one in short names.
- `TestModelResponse.test_type_refused`: An `error` line or a line of another type is refused by its type.
- `TestModelResponse.test_fields_invalid`: Each part missing or not valid is named, the first in the door's order.
- `TestOutputRead.test_calls_found`: The calls are found in order, as the very items of the output.
- `TestOutputRead.test_calls_none`: An output with no call has none.
- `TestOutputRead.test_parts_joined`: The parts of a message are joined in order by a line break.
- `TestOutputRead.test_messages_joined`: The messages are joined in order, a call between them skipped.
- `TestOutputRead.test_text_none`: An output that holds no message has no text, `null`.
- `TestOutputRead.test_parts_none`: A message with no part says the empty text, which is not `null`.
- `TestImageResponse.test_recorded_image`: A reply with a checkerboard PNG of 88 bytes as base64 is read whole.
- `TestImageResponse.test_url_kept`: An image given by url is read with its revised prompt.
- `TestImageResponse.test_fields_invalid`: Each part that is missing or not valid is named by its path.
- `TestToolsConvert.test_flat_tools`: Each tool keeps its name, text and schema, in order, and not `_meta`.
- `TestToolsConvert.test_empty_list`: No tools convert to no function tools.

##### test_provider_key.ts

unittest, 2 cases, label smoke-test. Tests of the provider key that `provider.key_set` keeps in memory, each test setting the key it reads.

- `TestProviderKey.test_key_replaced`: A second key replaces the first.
- `TestProviderKey.test_key_empty`: The empty key a scripted run may carry is kept as it is.

##### test_provider_key_unset.ts

unittest, 1 case, label smoke-test. The test of the provider key unset, a block of its own so that its realm starts with no key set.

- `TestProviderKey.test_key_unset`: With no key set in this realm, `key_get` refuses.

##### test_provider_script.ts

unittest, 74 cases, label smoke-test. Tests of the scripted provider, the fake of xAI's Responses API.

- `TestScriptWalk.test_turn_walk`: The castle turn, chained: three rounds of calls, then the subtitle.
- `TestScriptWalk.test_reply_line`: The reply comes inside the post, whole as the gold has it.
- `TestScriptWalk.test_full_names`: A request in full names is answered in full names.
- `TestScriptWalk.test_calls_numbered`: A reply that only calls has no message, and its calls are numbered.
- `TestScriptWalk.test_output_items`: A reply that speaks and calls holds its reasoning, message and call.
- `TestScriptWalk.test_echoes_kept`: The body echoes `tools` and `tool_choice` when given, and the model.
- `TestScriptWalk.test_stop_moves`: A reply without calls moves to its next node at once.
- `TestScriptWalk.test_place_shared`: The port keeps one place for every chain, so a new chain goes on there.
- `TestScriptIds.test_ids_repeated`: One request to two new ports is answered alike, ids included.
- `TestScriptIds.test_ids_differ`: Another context, or one context under another key, has another digest.
- `TestScriptChain.test_chain_context`: A chained request's context is its response's context, output and input.
- `TestScriptChain.test_restart_whole`: A restart of the whole context with no chain is answered as the chain.
- `TestScriptChain.test_due_seeded`: The calls due at a chained request's start are its response's calls.
- `TestScriptChain.test_first_undue`: A chain's first request has no call due, so an output answers none.
- `TestScriptChain.test_chain_foreign`: A response another port answered is not held by this one.
- `TestScriptChain.test_store_false`: With `store` false no chain follows, but the key's cache is kept.
- `TestScriptChain.test_store_true`: With `store` true the response is held, as with no `store`.
- `TestScriptChain.test_instructions_alone`: `instructions` is refused beside a chain only, and taken alone.
- `TestScriptUsage.test_usage_first`: A chain's first request counts its input and output, nothing cached.
- `TestScriptUsage.test_usage_chained`: A chained request counts the whole context, the key's last one cached.
- `TestScriptUsage.test_cache_keyed`: The cache is the key's: another key caches nothing of the first.
- `TestScriptFaults.test_start_unknown`: A script whose start names no node is refused when the port is made.
- `TestScriptFaults.test_next_unknown`: A reply that leads to no node is refused at the next request.
- `TestScriptFaults.test_after_unknown`: Results that lead to no node are refused when they come.
- `TestScriptFaults.test_input_invalid`: With no `otherwise`, a content that is not a string is refused.
- `TestScriptFaults.test_input_unknown`: With no `otherwise`, a text the node lacks is refused in normal form.
- `TestScriptFaults.test_results_unasked`: Tool results after a reply that called no tool are refused.
- `TestScriptFaults.test_results_pending`: A user message while tool results are pending is refused.
- `TestScriptFaults.test_results_unmatched`: Tool results whose call ids are not the calls of the reply are refused.
- `TestScriptFaults.test_after_missing`: Tool results that lead to a node with no reply after them are refused.
- `TestScriptFaults.test_role_unexpected`: A last item that is neither a user message nor a result is refused.
- `TestScriptFaults.test_receiver_rules`: A port with no receiver, or given a second one, refuses it.
- `TestScriptFaults.test_line_refused`: A line it cannot read is refused before the script chooses, in order.
- `TestScriptWords.test_case_matched`: Case and outer white space do not count, so each text takes its key.
- `TestScriptWords.test_punctuation_kept`: Punctuation and inner characters count, so a text that differs misses.
- `TestScriptWords.test_key_unnormal`: The first key not normal, in the table's order, refuses the port.
- `TestScriptOtherwise.test_otherwise_answers`: Every text `replies` lacks gets `otherwise`, the click's words included.
- `TestScriptOtherwise.test_otherwise_moves`: `otherwise` moves to its next node, where the choices then answer.
- `TestScriptOtherwise.test_replies_first`: An input the node holds takes its own reply, not `otherwise`.
- `TestScriptOtherwise.test_otherwise_calls`: An `otherwise` that calls tools moves on once their results are back.
- `TestScriptOtherwise.test_content_refused`: A content that is not a string is refused with `otherwise` in the node.
- `TestScriptAfter.test_holds_followed`: Results that each hold the text are followed by `after_tools`.
- `TestScriptAfter.test_lacks_followed`: One result of the reply that lacks the text gives `after_lacks`.
- `TestScriptAfter.test_lacks_moves`: `after_lacks` moves to its next node as `after_tools` does.
- `TestScriptAfter.test_lacks_calls`: The calls of `after_lacks` wait for their results, as any reply's do.
- `TestScriptAfter.test_after_unpaired`: A node with one of `after_holds` and `after_lacks` is a broken table.
- `TestScriptAfter.test_result_refused`: A tool result whose output is not text cannot be read for the text.
- `TestScriptQuote.test_quote_content`: A quote with `content` says the quoted text, a space, then `content`.
- `TestScriptQuote.test_quote_alone`: A quote with no `content` says the quoted text alone, as a message.
- `TestScriptQuote.test_quote_last`: The quote reads the last result, so an earlier one need not be JSON.
- `TestScriptQuote.test_quote_outcome`: `after_holds` picks the reply by the outcome, and either quotes the say.
- `TestScriptQuote.test_quote_unreached`: A reply to a user message that quotes is refused, `otherwise` too.
- `TestScriptQuote.test_quote_missing`: A result with no text at the path is refused, a bad decode its cause.
- `TestScriptQuote.test_quote_output`: A result whose output is not text is refused by its field.
- `TestRequestChecks.test_each_refused`: Each row of the gold breaks a good request, its first break named.
- `TestRequestChecks.test_choice_first`: The script chooses first, so its refusal comes before a bad field's.
- `TestRequestChecks.test_tools_bounded`: A request of 1000 tools is taken, and one of 1001 refused.
- `TestRequestChecks.test_tools_omitted`: In debug mode the omission's text is taken and echoed, a list refused.
- `TestRequestChecks.test_omission_refused`: Outside debug mode the omission's text is refused, as xAI would.
- `TestRequestChecks.test_tool_names`: A name of 64 letters, digits, `_` and `-` is taken, one of 65 refused.
- `TestRequestChecks.test_history_accepted`: A log of every kind of item, two calls answered in order, is taken.
- `TestRequestChecks.test_reasoning_lost`: A reply resent without its reasoning item is refused at its first item.
- `TestRequestChecks.test_due_end`: Calls still due at the end of the input are refused by the input.
- `TestImageReply.test_image_answer`: An image request is answered with the pattern as base64, and no move.
- `TestImageReply.test_image_count`: The pattern is given as many times as the request asks.
- `TestImageReply.test_image_refused`: An image request it cannot answer is refused by its field.
- `TestImagePattern.test_signature_recorded`: The PNG starts with the bytes the reference starts with.
- `TestImagePattern.test_chunks_recorded`: The chunks are a header, the data and an end, as the reference's are.
- `TestImagePattern.test_header_recorded`: The header chunk is the reference's byte for byte, its CRC included.
- `TestImagePattern.test_end_recorded`: The end chunk is the reference's byte for byte.
- `TestImagePattern.test_chunk_crcs`: The bitwise CRC matches each chunk of the reference, then each one made.
- `TestImagePattern.test_stored_blocks`: The data is a zlib stream of stored blocks that hold the rows.
- `TestImagePattern.test_adler_recorded`: The stream ends in the checksum the reference's stream of the rows does.
- `TestImagePattern.test_pattern_fresh`: Each call makes new bytes, equal to those of the call before.

##### test_wire.ts

unittest, 39 cases, label smoke-test. Tests of the wire module with no socket and no cache.

- `TestInputFrames.test_input_prefix`: A short line goes as one frame: the input kind, then its bytes.
- `TestInputFrames.test_chunk_limit`: A large line is cut into frames of at most the chunk, piece by piece.
- `TestInputFrames.test_line_order`: Lines queued one after another leave in order, no frame holding two.
- `TestInputFrames.test_empty_piece`: A blob of no bytes sends no frame.
- `TestInputFrames.test_line_limit`: A line of exactly `line_max` goes, and one byte more is refused.
- `TestInputFrames.test_blobs_limit`: Blobs of exactly `blob_max` go beside their line, one byte more not.
- `TestInputFrames.test_queue_limit`: Blobs that would pass `blob_max` with those held wait for blob frames.
- `TestInputFrames.test_queue_empty`: An empty queue has no frame to give.
- `TestInputFrames.test_chunk_invalid`: A chunk that cannot hold the kind and one byte is refused.
- `TestInputFrames.test_handle_unsent`: A blob held as a cache handle refuses the whole line, as none is sent.
- `TestConsolePort.test_output_relay`: The read takes a message before its relay moves the buffer away.
- `TestConsolePort.test_names_full`: The port's lines take full names exactly when the settings say debug.
- `TestConsolePort.test_close_read`: A read waiting when the socket closes is answered as timed out.
- `TestConsolePort.test_read_reopened`: After a close the port takes a new read, as a reopened console needs.
- `TestConsolePort.test_close_idle`: A close with no read waiting only reports its code.
- `TestConsolePort.test_close_unheard`: A close with no close receiver set is a fault, as nobody hears it.
- `TestConsolePort.test_type_refused`: A line of a type the console port does not take is refused.
- `TestConsolePort.test_id_missing`: An open or a read that is not a request with an id is refused.
- `TestConsolePort.test_read_invalid`: A read needs text to wait for and seconds from 0 that a timer holds.
- `TestConsolePort.test_input_unopened`: Input needs the socket, which only `console.open` makes.
- `TestConsoleRead.test_until_found`: A read answers with the output after it once `until` shows.
- `TestConsoleRead.test_output_before`: Output before the read is not part of it, so an old prompt is not one.
- `TestConsoleRead.test_until_split`: An `until` split over two messages is found.
- `TestConsoleRead.test_timer_expiry`: The timer ends a read with the output so far, and then none waits.
- `TestConsoleRead.test_timer_silent`: A read that times out with no output has empty text.
- `TestConsoleRead.test_read_twice`: A second read while one waits throws, and the first one stays.
- `TestConsoleRead.test_title_skipped`: Title and preferences are not output text.
- `TestConsoleRead.test_reads_consecutive`: Each read starts empty after the one before it ended.
- `TestConsoleRead.test_kind_refused`: An empty message, or one of a kind ttyd never sends, is a fault.
- `TestConsoleKeep.test_first_match`: A read ends at its first match, and the rest is kept for the next.
- `TestConsoleKeep.test_answered_start`: Kept output that already matches answers the read as it starts.
- `TestConsoleKeep.test_kept_expiry`: The timer ends a kept read with the kept text, which then is gone.
- `TestConsoleKeep.test_stop_dropped`: The stop drops the kept text, and a read then reads from its start.
- `TestConsoleKeep.test_keep_refused`: A stop with no keeping, and a second start, are faults.
- `TestConsoleKeep.test_kept_invalid`: Kept output is strict `UTF-8` though no read waits for it.
- `TestStrictText.test_character_split`: A character split over two messages is decoded whole.
- `TestStrictText.test_invalid_bytes`: Ignored output harms no read, as each read decodes from its own start.
- `TestStrictText.test_overlong_refused`: An overlong encoding of a slash is refused.
- `TestModuleSurface.test_frozen_names`: The module is frozen and holds its two ports and the parts they use.

##### test_queue.ts

unittest, 47 cases, label smoke-test. Tests of the task manager on real ports and a real far queue.

- `TestOwnerRouting.test_order_kept`: Lines from a port are dispatched one at a time in the order they came.
- `TestOwnerRouting.test_own_first`: A task posted to itself runs before an input that came during a task.
- `TestOwnerRouting.test_forward_unchanged`: A line another thread owns goes to that thread's queue unchanged.
- `TestOwnerRouting.test_forward_refused`: Forwarding a line the thread owns, or a request, throws.
- `TestOwnerRouting.test_owner_missing`: A type that no prefix of the owner table matches throws.
- `TestOwnerRouting.test_local_port`: A local port hands a post to its one receiver as the same object.
- `TestOwnerRouting.test_local_link`: Linked local ports hand a post to the receiver at the other end, once.
- `TestOwnerRouting.test_port_twice`: A second port to a thread throws, the thread's own port included.
- `TestOwnerRouting.test_forward_back`: A line whose owner is the port it came on throws and is not sent back.
- `TestOwnerRouting.test_thread_receiver`: A thread port takes one receiver, and a second one throws.
- `TestRequestReply.test_ids_shared`: One counter numbers the requests to every port, from 1, in its form.
- `TestRequestReply.test_request_answered`: A request is answered on its port by the line its handler returns.
- `TestRequestReply.test_wake_answers`: A wake answers the request that slept, on the port it came on.
- `TestRequestReply.test_error_line`: An error line from a port stops the queue with its message and stack.
- `TestRequestReply.test_error_cascade`: An error line's cascade is rebuilt as Errors under the queue's error.
- `TestRequestReply.test_reply_owed`: A wake must answer the request it owes, and only a request it owes.
- `TestRequestReply.test_header_kinds`: A type that is not text, or an id that is not a number, throws.
- `TestOwnerGiven.test_owner_override`: A given owner overrides the table, and the reply comes on its port.
- `TestOwnerGiven.test_owner_unconnected`: A given owner with no port throws as an owner from the table would.
- `TestOwnerGiven.test_owner_own`: A line posted to this thread runs here whatever owner the table names.
- `TestSleepWake.test_either_order`: Two replies wake the task once in either order, in submit order.
- `TestSleepWake.test_sleep_empty`: A sleep on no id wakes at once, after its handler returned.
- `TestSleepWake.test_wake_form`: A wake line is built in full names in debug mode, else in short names.
- `TestSleepWake.test_wait_rules`: A sleep names every request its handler submitted, each once.
- `TestSleepWake.test_submit_rules`: A submit outside a handler, or of a line with an id, throws.
- `TestSynchronousMode.test_run_twice`: The same inputs give the same posts and handler order twice.
- `TestSynchronousMode.test_handler_throws`: A handler that throws stops the queue, idle, and later inputs throw too.
- `TestSynchronousMode.test_step_waits`: Without synchronous mode a line from a port waits for a later step.
- `TestSynchronousMode.test_depth_counts`: The depth counts the lines held, the task running and the sleeping.
- `TestFailure.test_failure_posted`: The reply goes out, then the queue throws the error and stays stopped.
- `TestFailure.test_failure_submitted`: A failure after a submit posts the reply, then fails on the wait.
- `TestBlobTransfer.test_submit_detaches`: After a submit the caller's bytes are detached and the post holds them.
- `TestBlobTransfer.test_shared_buffer`: Blobs over one buffer move it once and keep their own views.
- `TestQueueLimit.test_limit_twice`: A second reader of the bound is refused.
- `TestQueueLimit.test_line_bytes`: A line counts the bytes its blobs hold in memory, a handle none.
- `TestQueueLimit.test_handle_unheld`: A held line whose blob streamed to a cache file passes the bound.
- `TestQueueLimit.test_line_measured`: A line counts the bytes of its blobs in memory, not its text.
- `TestQueueLimit.test_limit_exact`: Blobs filling the bound are held, then freed, one byte more is not.
- `TestQueueLimit.test_double_held`: Doubles past `2 ** 53`, which Python sends, are held and run.
- `TestQueueLimit.test_replies_held`: A reply's blobs stay held until its wake runs, and then they are free.
- `TestAudit.test_audit_lanes`: A line sent is recorded before it but to the server, one from a port too.
- `TestAudit.test_audit_held`: Records wait for the open, then go in order before any later one.
- `TestAudit.test_audit_sleep`: A sleep is noted by its ids and its wake's type, a run and a wake not.
- `TestAudit.test_audit_sleep_own`: A sleep on a wake under `audit.` is not noted, and wakes on this queue.
- `TestAudit.test_audit_own`: The audit's own lines are never recorded, sent or forwarded.
- `TestAudit.test_audit_masked`: A record masks the key of `http.request` and an answer's token, lines not.
- `TestAudit.test_audit_refused`: A second attach, an open unattached or twice, and an own audit throw.

##### test_substrate.ts

unittest, 6 cases, label smoke-test. Tests of substrate.ts that need no store and no cache.

- `TestRefs.test_split_forms`: Each form splits into its database, its key and its version.
- `TestRefs.test_refs_bad`: An empty ref, a missing key and a bad database name throw.
- `TestDocuments.test_round_trip`: Encoding moves refs into shared headers and decoding restores them.
- `TestDocuments.test_documents_bad`: Documents that would not round trip, or are malformed, throw.
- `TestDocuments.test_spaces_kept`: A string whose key holds a space, as Python counts space, stays text.
- `TestSurface.test_frozen_names`: The module is frozen and holds the names of its surface.

##### test_line_case.ts

own points, 3 cases, label smoke-test. Tests the line cases on the real ports of a real task manager.

- `cases_passing`: a run of line cases that pass writes the gold's passing stream and passes.
- `cases_graded`: a run whose cases fail by design, each a different way, writes the gold's graded stream and fails.
- `failfast_stops`: the graded cases again with failfast write the gold's failfast stream, stopping at the first failure.

##### test_mcp.ts

unittest, 31 cases, label smoke-test. Tests of the Model Context Protocol of the AI worker.

- `TestSurface.test_frozen_names`: The module and its constants are frozen and it exports its classes.
- `TestSurface.test_version_pinned`: The revision of the protocol is `2025-06-18`.
- `TestServerMethods.test_initialize_recorded`: `initialize` on the line and on stdio answers with the exact text.
- `TestServerMethods.test_ping_recorded`: `ping` answers an empty result.
- `TestServerMethods.test_list_recorded`: `tools/list` lists the tools in the order they were registered.
- `TestServerMethods.test_list_permit`: Only the permit tool carries its `_meta` through `tools/list`.
- `TestServerMethods.test_call_recorded`: `tools/call` runs the tool on its arguments and answers its result.
- `TestServerMethods.test_notification_none`: A notification, known or not, gets no answer.
- `TestServerMethods.test_arguments_absent`: A call with no arguments runs the tool on an empty object.
- `TestServerMethods.test_error_flag`: The error flag a tool sets reaches the result.
- `TestServerErrors.test_request_invalid`: A message that is not a valid request gets `-32600`.
- `TestServerErrors.test_method_unknown`: A method that is not served gets `-32601` naming it.
- `TestServerErrors.test_params_invalid`: `tools/call` params that are not a name and an object get `-32602`.
- `TestServerErrors.test_tool_unknown`: A call of a tool that is not registered gets `-32602` naming it.
- `TestServerErrors.test_tool_throw`: A throw in a tool answers an `isError` result holding its cascade.
- `TestServerErrors.test_tool_submitted`: A tool that submits, then throws: the answer, then the unawaited fault.
- `TestServerErrors.test_tool_twice`: A second tool of the same name is refused.
- `TestServerWakes.test_sleep_passed`: `message_handle` passes the sleep of the tool on as it is.
- `TestServerWakes.test_sleep_held`: `line_handle` holds the request line beside the state of the tool.
- `TestServerWakes.test_wake_answers`: The queue's wake answers the request in its name form.
- `TestServerWakes.test_wake_chain`: A wake may sleep again, and the last wake answers.
- `TestServerWakes.test_wake_throw`: A throw in a wake: its `isError` answer goes out, then the queue fails.
- `TestServerWakes.test_wake_unknown`: A sleep whose wake type the server did not register throws.
- `TestClientChecks.test_tools_unread`: The tools of a client cannot be had before they are read.
- `TestClientChecks.test_tools_invalid`: A `tools/list` result whose entry is not a tool is refused.
- `TestClientChecks.test_result_invalid`: A result whose content or error flag is not valid is refused.
- `TestClientChecks.test_reply_unknown`: A reply to a request of another client, or read twice, is refused.
- `TestClientChecks.test_reply_method`: A reply read as the answer of another method is refused.
- `TestClientSet.test_prefix_refused`: A prefix that is empty, holds the mark or is already added is refused.
- `TestClientSet.test_prefix_unknown`: A name with no mark or with a prefix of no client is refused.
- `TestClientSet.test_reply_stray`: A reply to a call of a client outside the set is refused.

##### test_wire_port.ts

unittest, 27 cases, label smoke-test. Tests of the wire port with no socket, on a real cache with no file.

- `TestWireMessages.test_first_line`: Title and preferences are kept and never decoded, then the first line.
- `TestWireMessages.test_preferences_overflow`: Preferences are read by the decoders' rules for bad numbers.
- `TestWireMessages.test_first_trailing`: Nothing may follow the first line before its reply, whole or in part.
- `TestWireMessages.test_first_split`: A first line split over two output messages arrives once it is whole.
- `TestWireMessages.test_start_missing`: A line other than `tap.start` or error before `tap.start` is a fault.
- `TestWireMessages.test_start_twice`: A second `tap.start`, which a restart of the server sends, is a fault.
- `TestWireMessages.test_post_early`: Nothing is posted before `tap.start`.
- `TestWireMessages.test_open_twice`: A port opens once: its first line receiver, which an open sets, is set.
- `TestWireMessages.test_kind_unknown`: An empty message, or one of a kind ttyd never sends, is a fault.
- `TestWireMessages.test_decoder_fault`: Output bytes the decoder refuses throw its fault.
- `TestWireMessages.test_fault_held`: The lines before a fault reach their receiver, then the fault throws.
- `TestWireMessages.test_receiver_missing`: A line with no receiver set is a fault.
- `TestWireMessages.test_receiver_twice`: Each receiver is set once.
- `TestWireMessages.test_scheme_unknown`: Only a page served over http or https has ttyd's sockets.
- `TestSettingsPhase.test_first_blob`: The first line is read with the first phase sizes, which allow no blob.
- `TestSettingsPhase.test_settings_sized`: The settings size the decoder only once the first line has come.
- `TestSettingsPhase.test_settings_unset`: The first line asks for no setting, and the first post after it does.
- `TestSettingsPhase.test_blobs_over`: Blobs over `blob_max` are refused before they are queued.
- `TestSettingsPhase.test_line_over`: A line over `line_max` is refused before it is queued.
- `TestSettingsPhase.test_socket_missing`: A line within the limits is queued, and sending it needs the socket.
- `TestSettingsPhase.test_restart_held`: A `system.restart` is sent, and a line posted after it is held.
- `TestCloseFault.test_close_silent`: A close with no error line is the fault, after its receiver hears it.
- `TestCloseFault.test_close_error`: An error line before the close leaves the fault to that line.
- `TestCloseFault.test_error_first`: An error line in place of the first, a refused lock, throws its message.
- `TestCloseFault.test_error_unpassed`: An error line before the first is not passed on, though one is awaited.
- `TestCloseFault.test_close_unheard`: A close with no receiver set is still the fault, naming its code.
- `TestCloseFault.test_close_partial`: A close in the middle of a message is a fault of its own.

#### 3.1.5 TypeScript group A integration, the TypeScript pair test first

##### test_tap_pair_ts

unittest, 6 cases, label smoke-test. Tests the TAP producer of TypeScript and the TAP consumer of Python as a pair. Its fixtures are the test methods of ts/test_tap_pair.ts, run by both producers, which are no cases of their own.

- `TestPair.test_answer_given`: The realm answered, sent only its stream and its runs, and exited 0.
- `TestPair.test_lines_parsed`: Every line of every run parses to a kind the consumer knows.
- `TestPair.test_points_named`: The realm's own block passes, with one point per run, named by it.
- `TestPair.test_stats_counted`: Each run's document is well formed, with the counts of the oracle.
- `TestPair.test_stream_read`: The stream reader takes every line of each run, and the stream ends.
- `TestPair.test_verdict_equal`: The consumer fails a run exactly when the runner's `module_run` does.

##### test_integrate_queue.ts

line cases, 9 cases, label smoke-test. The line cases of the task manager on real thread ports.

- `request_answered`: sends echo_one; expects echo_one_reply.
- `submit_blob`: sends relay_abc; expects relay_abc_reply.
- `replies_ordered`: sends pair_request; expects pair_reply.
- `forward_blob`: sends keep_abcd; expects kept_abcd.
- `halves_moved`: sends halves_abcd; expects halves_ab_cd.
- `order_kept`: sends echo_four, echo_five, echo_six; expects echo_four_reply, echo_five_reply, echo_six_reply.
- `note_silent`: sends note; expects nothing.
- `wake_ordered`: sends order_request, go; expects order_reply, after_seen.
- `audit_traced`: sends traced_abc; expects traced_reply, audit_seen.

##### test_integrate_mcp.ts

line cases, 6 cases, label smoke-test. The line cases of the Model Context Protocol between a real `mcp.Client` and a real `mcp.Server` on real queues.

- `handshake_read`: sends handshake; expects seen_initialize, seen_initialized, seen_list, handshake_reply.
- `results_read`: sends results; expects seen_source_put, seen_render, results_reply.
- `call_form`: sends form; expects console_call.
- `call_routed`: sends routed; expects seen_kv_get, routed_reply.
- `call_browser`: sends browser; expects browser_call.
- `tools_prefixed`: sends prefixed; expects seen_list_first, seen_list_second, prefixed_reply.

##### test_integrate_provider_script.ts

line cases, 9 cases, label smoke-test. The line cases of the scripted provider.

- `turn_tools`: sends turn_ask; expects turn_answer.
- `tools_image`: sends castle_ask; expects castle_answer.
- `image_answered`: sends image_ask; expects image_answer.
- `tools_scene`: sends imaged_ask; expects imaged_answer.
- `turn_subtitle`: sends entered_ask; expects entered_answer.
- `turn_next`: sends gatehouse_ask; expects gatehouse_answer.
- `images_two`: sends images_ask; expects images_answer.
- `turn_restart`: sends restart_ask; expects restart_answer.
- `names_short`: sends short_ask; expects short_answer.

#### 3.1.6 TypeScript group B unit blocks, in headless Chrome

##### test_error_overlay.ts

unittest, main thread, 9 cases, label smoke-test. Tests of the error overlay on the main thread.

- `TestOverlay.test_write_once`: The screen replaces the page, and the document is closed after it.
- `TestOverlay.test_first_only`: A second show leaves the first fault on screen.
- `TestOverlay.test_show_unstopped`: Showing a fault runs no stop function.
- `TestOverlay.test_stop_after`: The stop function runs after the screen with the thrown value, once.
- `TestOverlay.test_resource_thrown`: A resource that failed to load is a fault, an Error of its text.
- `TestOverlay.test_escaped_text`: The message and the stack sit in a `pre` as text, not as markup.
- `TestOverlay.test_reload_button`: A button follows the text and reloads the page when clicked.
- `TestStop.test_stop_twice`: A second stop function is refused.
- `TestSurface.test_frozen_names`: The module is frozen and holds its four routines and the screen class.

##### test_error_overlay_worker.ts

unittest, worker ai, 5 cases, label smoke-test. Tests of the error overlay in the AI worker.

- `TestReport.test_report_done`: The report gets the thrown value and `done`, which posts the cascade.
- `TestReport.test_posted_at_once`: With no report function the line is posted at once, the first only.
- `TestReport.test_fault_waiting`: A fault while the report waits posts at once, the first under its cause.
- `TestReport.test_report_thrown`: A report that throws is a fault met while it waits, posted at once.
- `TestReport.test_report_twice`: A second report function is refused.

##### test_overlay.ts

unittest, main thread, 19 cases, label smoke-test. Tests of the debug overlays, run on containers that are not in the page, and of the scrolling that keeps a shown overlay's end in view, run on a container of a fixed size put in the page and taken out after, or on one inside it that does not scroll, as `overlays` sits in `debug` on the engine page.

- `TestOverlay.test_no_elements`: Nothing is made before the first use of a tty.
- `TestOverlay.test_first_toggle`: The first toggle of a tty makes one shown `pre`, empty, of text only.
- `TestOverlay.test_text_shown`: A text shown replaces the last, as one text and no element.
- `TestOverlay.test_pre_reused`: Later texts and toggles of the same tty reuse its `pre`.
- `TestOverlay.test_text_escaped`: The text is shown as text, so markup in it makes no element.
- `TestOverlay.test_stays_detached`: Nothing is put in the page: the container and its `pre` stay detached.
- `TestToggle.test_toggle_twice`: A toggle shows a hidden `pre`, a second hides it, each saying which.
- `TestToggle.test_hide_empties`: A hide empties the `pre`, so the next show starts empty.
- `TestToggle.test_hidden_dropped`: A text that comes after the hide is dropped.
- `TestToggle.test_text_first`: A text before any toggle makes the `pre` hidden and keeps nothing.
- `TestSeparation.test_separate_pres`: Each tty has its own `pre`, made in the order of first use.
- `TestSeparation.test_toggles_independent`: A toggle shows or hides and empties only the `pre` of its own tty.
- `TestSeparation.test_objects_independent`: Two overlay objects on two containers share nothing.
- `TestScroll.test_text_scrolls`: Each text shown brings the overlay's end into view.
- `TestScroll.test_toggle_scrolls`: A show brings its `pre` into view below a tall one.
- `TestScroll.test_hidden_still`: A text dropped by a hidden overlay leaves the view where it is.
- `TestScroll.test_upper_overlay`: A text shown in the upper of two shown overlays brings it into view.
- `TestScroll.test_inner_container`: In a container that does not scroll, the element above it is scrolled.
- `TestSurface.test_frozen_names`: The module is frozen and holds the one class of its declaration.

##### test_substrate_limit.ts

unittest, worker ai, 2 cases, label smoke-test. Tests of substrate.ts's largest database, a block of group B in the AI worker, on the sqlite3.wasm module and OPFS pool the bring up sets as globals.

- `TestFull.test_full_refused`: The put past `blob_max` fails full, and the file, rows and limit hold.
- `TestFull.test_limit_refused`: Each statement that sets the limit is refused, and the limit holds.

##### test_substrate_store.ts

unittest, worker ai, 70 cases, label smoke-test. Tests of substrate.ts's cache and store, a block of group B in the AI worker, on the open OPFS files the bring up gives the block as `test_slots` and the sqlite3.wasm module and OPFS pool it sets as globals.

- `TestRefs.test_ref_database`: An internal ref needs a database and an external ref takes none.
- `TestDocuments.test_document_heads`: Each put writes the next version and moves the head, versions stay.
- `TestDocuments.test_version_exists`: A put whose next version is already a row throws and moves no head.
- `TestDocuments.test_nested_text`: A nested document is stored as the text the wire's encoder writes.
- `TestHash.test_digest_recorded`: Streamed values give their known digests.
- `TestHash.test_digest_lengths`: Every length around the block and padding bounds, in pieces of any size.
- `TestCache.test_sink_read`: A finished blob reads back by range, a copy of the bytes it was given.
- `TestCache.test_sink_partial`: A blob closed short of its size, after a decoder fault, is freed.
- `TestCache.test_cache_full`: A cache with no free file refuses a blob until a file is added.
- `TestCache.test_slots_found`: Files hold the value their first bytes name, others are free.
- `TestCache.test_names_bad`: A file whose first bytes name no `SHA-256`, or a name twice, throws.
- `TestCache.test_read_short`: A read the file gives short, the file cut under a finished blob, throws.
- `TestDatabases.test_tables_created`: A new database gets the substrate's tables and the schema row.
- `TestDatabases.test_tables_recorded`: Its tables are the statements of `API/sql/substrate.sql`, in order.
- `TestDatabases.test_tables_foreign`: A database file made elsewhere gets the tables when first opened.
- `TestDatabases.test_names_bad`: A name that is not a C identifier throws and makes no file.
- `TestDatabases.test_create_twice`: A second create, a second open, a missing file and a close all throw.
- `TestDatabases.test_create_failed`: A create that a full pool stops throws, leaves no file, and is redone.
- `TestDatabases.test_schema_partial`: A file with only some of the substrate's tables throws, kept as it is.
- `TestDatabases.test_schema_version`: A file whose schema row is not the substrate's version throws.
- `TestDatabases.test_database_busy`: Closing, dropping or restoring a database a transaction wrote throws.
- `TestDatabases.test_drop_files`: Dropping removes the file and the cache files no other database names.
- `TestValues.test_refs_both`: A value put by one ref form is read by the other, listed and deleted.
- `TestValues.test_overflow_boundary`: A value of exactly `overflow_bytes` stays in its row, one byte more not.
- `TestValues.test_cache_shared`: A cache file stays while any row of any database names its hash.
- `TestValues.test_handle_moved`: A blob the sink streamed moves into place, a small one is refused.
- `TestValues.test_file_lost`: A row whose cache file this store lacks stays, and only its read throws.
- `TestStored.test_stored_trip`: An encoded document is stored and read back as the same text.
- `TestStored.test_numbers_small`: Numbers below `1e-4` are stored as Python's `repr` writes them.
- `TestStored.test_version_wide`: A head past `2^53` moves to the exact next version, as in Python.
- `TestStored.test_values_refused`: Values JSON cannot carry, and bad ids and headers, throw.
- `TestTurns.test_turns_append`: Turns number from 1 in their scene, each an array of items as JSON.
- `TestTurns.test_turns_compact`: Compaction replaces turns 1 to `through` by one summary turn at 1.
- `TestPrompted.test_prompt_first`: A row `[message]` each, first, in order, and the turns count from 1.
- `TestPrompted.test_prompt_pushed`: One push carries its messages, and a second is refused, sending none.
- `TestPrompted.test_prompt_compacted`: Compaction neither counts it nor replaces it, by threshold or by call.
- `TestPrompted.test_prompt_restored`: The flag travels with the database in a whole sync.
- `TestCompaction.test_threshold_reached`: A `user` turn at the threshold compacts its scene first, sending none.
- `TestCompaction.test_compaction_rolled`: The compaction rolls back with the transaction of its `user` turn.
- `TestSql.test_sql_results`: Statements return columns, rows and changes, and only writes count.
- `TestSql.test_statements_refused`: Two statements in one, a parameter count that differs, an SQL error.
- `TestSql.test_trigger_name`: A trigger's name of a string is thrown as that string, SQLite's cause.
- `TestTransactions.test_transaction_whole`: Writes in one `transaction_run` commit together or roll back together.
- `TestTransactions.test_transaction_split`: A failure after one of two databases was written rolls both back.
- `TestTransactions.test_reopen`: Rows and values survive closing, reopening and a new store on the root.
- `TestSnapshot.test_snapshot_restore`: A restore brings back the rows of the snapshot and pushes nothing.
- `TestSnapshot.test_restore_foreign`: A file without the substrate's tables throws and the old one stays.
- `TestSnapshot.test_restore_left`: A restore file left by an earlier restore throws, and stays.
- `TestSnapshot.test_snapshots_apart`: Two snapshots of one database taken apart hold their own bytes.
- `TestSnapshot.test_value_held`: A cached value stays held through a snapshot and a restore of no file.
- `TestSnapshot.test_restore_files_lost`: A restore given one of two cache files reads all but the lost value.
- `TestSnapshot.test_restore_handle`: A restore takes the database and a file as handles of its own cache.
- `TestSnapshot.test_snapshot_missing_file`: A snapshot names only the cache files its store holds, throwing none.
- `TestView.test_view_vector`: The view of the operations' database is the vector's, as a JSON value.
- `TestView.test_view_lost`: A restore without the files of rows over `overflow_bytes` loses them.
- `TestView.test_document_lost`: A restore with no file loses a document's current version, which throws.
- `TestPush.test_databases_pushed`: A create and a drop each push the database's name at once.
- `TestPush.test_values_pushed`: A value in its row goes as a copy of its bytes, a delete by its ref.
- `TestPush.test_files_pushed`: A value over `overflow_bytes` goes as its file's bytes, never a handle.
- `TestPush.test_writes_pushed`: Documents, turns and statements that change something push payloads.
- `TestPush.test_transaction_pushed`: The pushes of one transaction follow its commit, in order, or none.
- `TestPush.test_threshold_pushed`: A `user` turn at the threshold compacts first and pushes only itself.
- `TestHandlers.test_types_registered`: Every type is registered at version 0.
- `TestHandlers.test_dump_pushed`: `audit.dump` pushes every database's view to the server, in name order.
- `TestHandlers.test_values_answered`: `kv.put` and `kv.get` answer with the known digest and the bytes.
- `TestHandlers.test_rows_answered`: `sql.run`, `kv.list` and `kv.delete` answer their results.
- `TestHandlers.test_documents_answered`: Documents and turns answer with their refs and numbers.
- `TestHandlers.test_databases_answered`: Databases are created and dropped by their lines.
- `TestHandlers.test_restore_answered`: A restore waits for its `db.file` lines, or runs at once with none.
- `TestHandlers.test_restore_refused`: A restore while one waits, or a file no restore waits for, throws.

##### test_jslb_decode.ts

unittest, worker ai, 40 cases, label smoke-test. Tests of the decoder of jslb.ts, a block of group B on a real `substrate.CacheFiles` over the open OPFS files the bring up gives the block as test_slots, cleared, which no other block uses.

- `TestEncode.test_encode_blobs`: Each blob's `d` follows the JSON as the same bytes object or handle.
- `TestEncode.test_double_range`: Doubles beyond `2 ** 53` are written as JSON writes them, and read back.
- `TestDecode.test_decode_line`: A line decodes to plain objects, and integer keys encode first again.
- `TestDecode.test_decode_keys`: Nested digit keys beyond the array indices encode as integer keys.
- `TestDecode.test_decode_blobs`: Blobs follow the CR, each `d` set to its bytes, empty ones too.
- `TestDecode.test_blob_empty`: A line whose blobs are all empty is complete at its CR.
- `TestDecode.test_decode_pieces`: Lines come back when their last byte arrives, several in one call.
- `TestDecode.test_integral_floats`: An integral float count or size reads as an integer, in either form.
- `TestDecode.test_fault_deferred`: Lines before a fault are returned and the next call throws the fault.
- `TestDecode.test_idle_states`: The decoder is idle between messages only, and never after a fault.
- `TestDecode.test_line_max`: A line of `line_max` bytes with its CR is read, one byte more is not.
- `TestDecode.test_line_early`: A line is refused once it passes `line_max`, before its CR arrives.
- `TestDecode.test_blob_max`: A blob of `blob_max` bytes is read, one more refused before buffering.
- `TestDecode.test_blobs_summed`: Blobs of `blob_max` in all pass with a longest line, one byte more not.
- `TestDecode.test_header_missing`: A line without header 0 is refused.
- `TestDecode.test_header_object`: A header that is not a JSON object is refused.
- `TestDecode.test_type_missing`: A line header without a type string is refused.
- `TestDecode.test_count_mismatch`: A blob count that differs from the blob headers is refused.
- `TestDecode.test_header_gap`: A gap in the blob headers is refused, a huge integer key too.
- `TestDecode.test_size_invalid`: A size that is not a non negative integer is refused.
- `TestDecode.test_payload_digits`: A payload key of decimal digits is refused.
- `TestDecode.test_forms_mixed`: Short and full names in one line are refused, across headers too.
- `TestDecode.test_line_field`: An unknown field in the line header is refused.
- `TestDecode.test_data_sent`: A blob header that carries `d` or `data` on the wire is refused.
- `TestDecode.test_text_invalid`: A line that is not strict `UTF-8` or not a JSON object is refused.
- `TestDecode.test_constant_refused`: The `NaN` and `Infinity` constants are refused as not JSON.
- `TestNumbers.test_integer_edges`: `2^53` either way reads as the integer, one past either is refused.
- `TestNumbers.test_size_integer`: A size past `2^53` is a refused integer before it is a bad size.
- `TestNumbers.test_integer_digits`: An integer of 17 digits or of 310 digits is refused.
- `TestNumbers.test_number_overflow`: A token whose double overflows to an infinity is refused.
- `TestNumbers.test_double_read`: A token with an exponent within the doubles reads as its double.
- `TestNumbers.test_digits_text`: Digits in a key or a string are no number, however many they are.
- `TestNumbers.test_number_first`: The first refused token in the text is the one reported.
- `TestNumbers.test_encoded_refused`: The encoder's digits for a double past `2^53` are refused at read.
- `TestStream.test_stream_sink`: A blob one byte over goes to the cache, `d` its handle, then `sha256`.
- `TestStream.test_stream_exact`: A blob of exactly `overflow_bytes` stays in memory, with no file.
- `TestStream.test_stream_bytes`: A streamed blob fed one byte at a time gives the same bytes and hash.
- `TestStream.test_sink_failure`: A cache with no free file ends the feed, and the decoder is unusable.
- `TestStream.test_close_failure`: A file closed under a streamed blob fails its append, then its close.
- `TestStream.test_hash_sent`: A sent `sha256` is replaced on a streamed blob, kept on one in memory.

##### test_console_view.ts

unittest, main thread, 62 cases, label smoke-test. Tests of the console view on the real xterm.js terminal, on a container above a band in a frame of a fixed size, put in the page by each test and taken out after it.

- `TestVisibility.test_made_hidden`: The view makes one hidden child and no terminal in it, and sends none.
- `TestVisibility.test_made_twice`: Two views on one queue can be made, as a view registers no handler.
- `TestVisibility.test_made_size`: The terminal is made 120 columns wide and 40 rows high.
- `TestVisibility.test_first_show`: The first show reveals the child, opens the terminal in it, focuses it.
- `TestVisibility.test_later_show`: Later shows reveal the child and focus again, and ask for nothing.
- `TestVisibility.test_hide_shown`: A hide hides the child and leaves the terminal in it.
- `TestVisibility.test_hide_idle`: A hide before any show leaves the terminal out of the page.
- `TestVisibility.test_toggle_twice`: A toggle shows a hidden view and the next toggle hides it again.
- `TestVisibility.test_toggle_open`: Showing an open console fits its rows and sends no resize to tty 0.
- `TestVisibility.test_open_wanted`: The view wants tty 0 when shown while idle, at first and after its end.
- `TestOpening.test_open_request`: A request gives the AI worker one `console.open`, and input stays off.
- `TestOpening.test_sleep_returned`: The request returns a sleep on the id it got that wakes with its type.
- `TestOpening.test_full_names`: Lines take the name form the settings pick, full exactly in debug mode.
- `TestOpening.test_open_twice`: A second request while opening or open is refused and gives nothing.
- `TestOpening.test_first_message`: The wake gives ttyd's first message, the one for an empty token.
- `TestOpening.test_first_token`: The first message carries the token of the reply.
- `TestOpening.test_first_size`: The first message has no kind byte and the size the terminal has.
- `TestOpening.test_reply_idle`: A wake before any request is refused and sends nothing.
- `TestOpening.test_reply_twice`: A second wake is refused and sends nothing more.
- `TestOpening.test_reply_type`: A reply of another type to the request is refused and sends nothing.
- `TestOpening.test_reply_id`: A wake with the reply to another request is refused, the right one not.
- `TestOpening.test_token_missing`: A reply without a token is refused and sends nothing.
- `TestInput.test_ascii_batch`: A batch of text is one line whose blob is a zero and the text.
- `TestInput.test_line_held`: Typed text is held until Enter submits it whole as one line.
- `TestInput.test_keys_pressed`: A key pressed joins the line, and Enter pressed submits it.
- `TestInput.test_two_bytes`: A character of two bytes is sent as its two `UTF-8` bytes.
- `TestInput.test_three_bytes`: A character of three bytes is sent as its three `UTF-8` bytes.
- `TestInput.test_four_bytes`: A character of four bytes, two `UTF-16` units, is sent as four bytes.
- `TestInput.test_mixed_batch`: A batch of mixed characters is one line with the bytes in order.
- `TestInput.test_control_dropped`: Control with a letter is dropped, and the line goes on.
- `TestInput.test_controls_dropped`: Every C0 control but Tab, Backspace and Enter, and every C1, is dropped.
- `TestInput.test_escapes_dropped`: Escape sequences, typed or of arrow keys, are dropped whole.
- `TestInput.test_tab_kept`: Tab joins the line as it is.
- `TestInput.test_backspace_edits`: Backspace removes the last character, and on an empty line nothing.
- `TestInput.test_enter_empty`: Enter on an empty line submits the carriage return alone.
- `TestInput.test_paste_cut`: A paste is cut at its carriage returns, its rest held.
- `TestInput.test_line_kept`: A line half typed before the AI's command is kept through it.
- `TestInput.test_input_idle`: Before any request the terminal takes no input, so nothing is sent.
- `TestInput.test_input_opening`: Before ttyd's first message the terminal takes no input either.
- `TestInput.test_input_held`: While the AI's command runs the terminal takes no keys: nothing is sent.
- `TestInput.test_input_freed`: Once the AI's command has ended the terminal takes keys again.
- `TestInput.test_freed_idle`: Freed while tty 0 is idle, the terminal still takes no keys.
- `TestInput.test_held_opening`: Held before tty 0 opens, the terminal takes no keys once it is open.
- `TestFit.test_rows_fitted`: A show fits the rows to the space above the band, so none is scrolled.
- `TestFit.test_fitted_first`: A fit while idle sends nothing, and the first message has the rows.
- `TestFit.test_space_changed`: A later show fits the rows again, to the space the frame has then.
- `TestFit.test_narrow_frame`: A scroll bar under wide columns is left out of the space.
- `TestFit.test_rows_least`: A band that leaves no room for one row leaves the terminal one row.
- `TestOutput.test_kind_unknown`: A kind byte that is not output, title or preferences is refused.
- `TestOutput.test_message_empty`: A message with no bytes has no kind and is refused.
- `TestClosing.test_close_request`: A request gives the AI worker one `console.close` and turns input off.
- `TestClosing.test_close_sleep`: The request returns a sleep on the id it got that wakes with its type.
- `TestClosing.test_close_reply`: The reply leaves the console closing, taking no input and no opening.
- `TestClosing.test_close_phase`: A close while idle, opening or closing is refused and gives nothing.
- `TestClosing.test_closed_early`: A wake of the close before any close is asked for is refused.
- `TestClosing.test_closed_checked`: A reply of another type or to another request is refused.
- `TestClosing.test_close_reopen`: The end after a close leaves the console idle, and it opens again.
- `TestExit.test_exit_open`: The end turns input off, so typing sends nothing more.
- `TestExit.test_exit_early`: An end before the console is open is refused.
- `TestExit.test_exit_twice`: A second end is refused, as the console is idle again.
- `TestExit.test_open_again`: A request after the end asks for tty 0 again and sends a first message.
- `TestSurface.test_frozen_names`: The module is frozen and holds the one class of its declaration.

##### test_media_cache.ts

unittest, main thread, 12 cases, label smoke-test. Tests of the order and accounting of the images the media cache keeps, on real decoded images.

- `TestCacheEviction.test_bytes_counted`: Each image counts as its width times height times 4 bytes.
- `TestCacheEviction.test_budget_exact`: A total exactly at the budget is within it, so nothing is evicted.
- `TestCacheEviction.test_oldest_evicted`: The oldest goes first, closed, and the total drops by its counted bytes.
- `TestCacheEviction.test_evict_least`: Eviction stops as soon as the total fits, so the younger images stay.
- `TestCacheEviction.test_evict_many`: One large image evicts every older image, oldest first.
- `TestCacheEviction.test_newest_alone`: The newest image is kept alone though it is over the budget.
- `TestCacheEviction.test_oversize_first`: An image over the budget is kept in an empty cache.
- `TestCacheEviction.test_oversize_evicted`: The next image evicts an oversize one, as the oldest image goes first.
- `TestCacheEviction.test_key_replaced`: A key kept again closes the old image and makes the new one newest.
- `TestCacheEviction.test_replace_evicts`: A replacement can evict, and the old image is not counted twice.
- `TestCacheEviction.test_lookup_order`: Looking an image up does not make it newer.
- `TestCacheEviction.test_get_missing`: A key that was never kept has no image.

##### test_script.ts

unittest, worker ai, 19 cases, label smoke-test. Tests of script.ts, a block of group B in the AI worker, on a real store.

- `TestRun.test_step_recorded`: The step script reads its row, runs its statement and returns.
- `TestRun.test_step_traced`: A traced run keeps the call of the store, with its time.
- `TestRun.test_trace_kept`: A trace keeps every call of the store, in order.
- `TestRun.test_trace_only`: Only a traced run traces the calls of the store.
- `TestRun.test_bytes_counted`: A trace shows the bytes an argument holds by their count.
- `TestRun.test_args_passed`: The arguments reach the script as they were given.
- `TestRun.test_engine_frozen`: The engine is frozen and holds the store and `i18n` alone.
- `TestRun.test_store_routine`: The store is frozen and holds the routine methods only, traced or not.
- `TestRun.test_store_machinery`: The store's machinery is not there: calling it is the engine's error.
- `TestRun.test_cached_script`: A script the store holds in its cache is read from the cache.
- `TestErrors.test_error_returned`: An `Error` the script throws comes back with its text and stack.
- `TestErrors.test_value_thrown`: A value that is no `Error` comes back as its text, with no stack.
- `TestErrors.test_syntax_returned`: A script that does not compile returns its `SyntaxError`.
- `TestErrors.test_trace_before`: The calls traced before the exception are kept.
- `TestErrors.test_value_uncarried`: A value JSON cannot carry is the run's exception, not the tool's.
- `TestErrors.test_value_unchecked`: NaN and the infinities are returned, as no decoder lets them in.
- `TestErrors.test_store_refused`: A call of the store that fails is the script's exception.
- `TestErrors.test_script_missing`: A name with no script throws the store's error.
- `TestSurface.test_frozen_names`: The module is frozen and holds only `script_run`.

##### test_worker_ai.ts

unittest, main thread, 20 cases, label smoke-test. Tests of the AI worker on the UI side, in a page load of its own, where no bring up has registered the types its relays register.

- `TestOwnerTables.test_routes`: The console's lines go here, to its port or to the UI, the rest out.
- `TestQueueMode.test_debug_only`: Read in debug mode, it is refused outside it.
- `TestRelays.test_console_closed`: The UI's close closes the console port once and is answered at once.
- `TestRelays.test_settings_sent`: A notice of new settings changes the live value, goes to the server.
- `TestRelays.test_tail_relayed`: The UI's `audit.tail` goes to the server, and its text comes back.
- `TestFaults.test_error_sent`: The cascade goes as one `error` line, its `cause` only when present.
- `TestFaults.test_fault_sent`: The UI's `fault` is sent on as that `error` line, then closes once.
- `TestWriter.test_lines_cut`: The AI's text goes one message per line a newline ends, in order.
- `TestWriter.test_rest_held`: The text after the last newline waits for the write that ends it.
- `TestWriter.test_view_passed`: Outside a turn the view's line goes as it came.
- `TestWriter.test_view_held`: A view's line inside the AI's turn waits until its idle, then goes.
- `TestWriter.test_turn_waits`: The AI's turn waits while the person's command runs, until the prompt.
- `TestWriter.test_view_own`: The person's line inside their own command goes while the AI waits.
- `TestWriter.test_prompt_split`: A prompt split across two messages of output still concludes tty 0.
- `TestWriter.test_open_unconcluded`: A tty 0 opened anew has shown no prompt, so the AI's turn waits.
- `TestWriter.test_read_waits`: A read in a waiting turn goes after the busy with the time it has left.
- `TestWriter.test_waiting_ended`: A turn the AI ends before it started sends nothing, then or later.
- `TestWriter.test_others_passed`: Reads and openings pass on as they came.
- `TestWriter.test_turn_refused`: A second busy within a turn, or an idle outside one, throws.
- `TestSurface.test_frozen_names`: The module is frozen and holds the names of its surface.

##### test_page.ts

unittest, main thread, 22 cases, label smoke-test. Tests of the UI thread on the test page's document.

- `TestOwnerTable.test_console_routes`: The console goes to the worker but for its output, end, show and turns.
- `TestOwnerTable.test_tap_route`: The table sends `tap.` lines to the worker.
- `TestWorkerLines.test_settings_taken`: The first line must be `settings.set`, which is taken whole.
- `TestWorkerLines.test_fault_read`: A message of the worker must be a fault line.
- `TestDomPort.test_text_submitted`: A submitted text is posted as `ui.input`, the input emptied and closed.
- `TestDomPort.test_click_mapped`: A click is posted as the point of the image's pixels it falls on.
- `TestDomPort.test_click_once`: A click closes the input at once, so that a second one is not taken.
- `TestDomPort.test_click_closed`: A click while the input is closed is not taken.
- `TestDomPort.test_control_key`: Control with a digit is posted and kept from the browser.
- `TestDomPort.test_overlay_key`: Control with 1 is posted as the audit's own line, with no payload.
- `TestDomPort.test_choice_answered`: A `dom.choice` shows its buttons and answers with the one clicked.
- `TestDomPort.test_post_refused`: Another type, a missing id and an unknown choice are refused.
- `TestDomPort.test_port_refused`: A second receiver and a container without the elements are refused.
- `TestHandlerChecks.test_image_missing`: A render of an image the media cache does not hold is a fault.
- `TestHandlerChecks.test_show_opening`: A console that is opening answers at once and is not asked for again.
- `TestHandlerChecks.test_dump_zero`: In debug mode the text 0 asks for the dumps first, then is said.
- `TestHandlerChecks.test_dump_other`: Another text, or 0 outside debug mode, is said alone.
- `TestHandlerChecks.test_tail_asked`: ctrl 1 asks for the audit's end as it shows, and not as it hides.
- `TestHandlerChecks.test_overlay_unrecorded`: ctrl 1 runs here, neither recorded nor forwarded, and ctrl 2 is recorded.
- `TestHandlerChecks.test_keys_gated`: Outside debug mode the keys toggle nothing and ask for nothing.
- `TestLayout.test_band_uncovered`: No picture or tall debug view covers the band: text, button, input.
- `TestSurface.test_module_frozen`: The module object is frozen.

##### test_tools_browser.ts

unittest, worker ai, 25 cases, label smoke-test. Tests of tools_browser.ts on real parts.

- `TestRegistry.test_tools_recorded`: The tools are those of `API/mcp/tools.json`, whole and in its order.
- `TestDatabases.test_sql_recorded`: `sql_run` runs the statements on the store and answers its results.
- `TestDatabases.test_create_drop`: `db_create` and `db_drop` add and remove a database.
- `TestValues.test_put_recorded`: `kv_put` writes the text's bytes and returns the row's digest.
- `TestValues.test_get_text`: `kv_get` reads a value as its text.
- `TestValues.test_get_cached`: `kv_get` reads a value held in the cache through its handle.
- `TestValues.test_get_refused`: `kv_get` of bytes that are not `UTF-8` throws.
- `TestValues.test_delete_empty`: `kv_delete` deletes the row and returns an empty object.
- `TestValues.test_file_lost`: The store's throw for a value whose cache file is lost passes through.
- `TestValues.test_list_keys`: `kv_list` returns the rows under the prefix.
- `TestDocuments.test_doc_recorded`: The arrival scene is put, read back as its stored document, and found.
- `TestScripts.test_run_recorded`: The step script reads its text, runs its statement, returns its value.
- `TestScripts.test_debug_traced`: `script_debug` returns the trace of the store's call with the value.
- `TestScripts.test_error_marked`: A script that throws gives a result marked as an error.
- `TestImages.test_image_recorded`: The castle turn's image is asked for, kept, sent to the UI, returned.
- `TestImages.test_image_fetched`: An image answered by url is downloaded by the UI and kept here.
- `TestRender.test_render_recorded`: An image the page does not hold reaches it from the store, then renders.
- `TestRender.test_render_cached`: An image a cache file holds goes as bytes in memory, never as a handle.
- `TestRender.test_render_lost`: A lost image fails as the store's `substrate.file_lost`, nothing sent.
- `TestRender.test_render_unknown`: An image with no row fails as `substrate.key_missing`, nothing sent.
- `TestRender.test_render_black`: A render with no image is black, as the boot's render is.
- `TestConsole.test_permit_denied`: A denial of each tool returns an error to the model, nothing sent on.
- `TestConsole.test_debug_off`: Outside debug mode each tool answers an error, the player asked nothing.
- `TestConsole.test_debug_continued`: The refusal fails nothing, so that the turn's next call is answered.
- `TestSurface.test_frozen_names`: The module is frozen and holds only `tools_register`.

##### test_agent.ts

unittest, worker ai, 28 cases, label smoke-test. Tests of the agent loop on real parts, on a real queue of thread `ai` in synchronous mode, which runs the turn, the client's `mcp` lines and the tools alike.

- `TestTurnRecorded.test_requests_recorded`: The first request holds the log, each later one the call outputs.
- `TestTurnRecorded.test_calls_recorded`: Each call reached its tool with its arguments, as the store now shows.
- `TestTurnRecorded.test_turns_stored`: The prompt at 0 as `[message]`, then each reply as sent, each output.
- `TestTurnRecorded.test_turns_pushed`: Each turn's row goes to the server as stored, the prompt as messages.
- `TestTurnRecorded.test_reply_recorded`: The turn ends with the reply to `ai.say`: the new scene, the subtitle.
- `TestTurnNext.test_scene_new`: The next turn is a new conversation, whose first request is whole.
- `TestTurnNext.test_universe_prompt`: The universe's prompt follows the analyst's once the scripts made one.
- `TestTurnShort.test_turn_short`: A reply with no calls ends the turn, in the request's name form.
- `TestTurnShort.test_click_turn`: A click is told to the model as text, and the reply ends the turn.
- `TestChain.test_turn_chained`: The next turn sends its user item alone, after the last response.
- `TestChain.test_results_chained`: Calls run before their reply is stored, their outputs go chained.
- `TestChain.test_rows_appended`: Rows a script appends between turns go in the chained request.
- `TestChain.test_threshold_restart`: A compaction at the threshold makes the next request a chain's first.
- `TestToolList.test_tools_omitted`: In debug mode a request holds the omission's text, not the tools.
- `TestToolList.test_tools_listed`: Outside debug mode a request lists every tool, flat, as xAI takes it.
- `TestPromptOnce.test_commit_once`: One commit before the first turn, and a chain's first alone sends it.
- `TestPromptOnce.test_prompt_kept`: A later turn stores no prompt and sends none, and an edit stays unread.
- `TestPromptOnce.test_compaction_kept`: A compaction between turns restarts the chain, the prompt sent once.
- `TestPrompt.test_prompt_analyst`: In the hyperposition the system prompt is the analyst's alone.
- `TestPrompt.test_prompt_universe`: The prompt of the universe of the current world follows the analyst's.
- `TestPrompt.test_prompt_absent`: A universe without a prompt adds none.
- `TestPrompt.test_prompt_head`: The head of the universe's prompt is read, not an older version.
- `TestPrompt.test_prompt_typed`: A prompt document of another type is read by its text all the same.
- `TestPrompt.test_prompt_reference`: A prompt text that is a reference string is read back as that text.
- `TestErrors.test_prompt_invalid`: A prompt text not a string throws, the universe's or the analyst's.
- `TestErrors.test_analyst_missing`: The store's error for a missing analyst's prompt reaches the caller.
- `TestSurface.test_frozen_names`: The module is frozen and holds the names of its surface.
- `TestSurface.test_types_registered`: The four line types are registered at version 0, in order.

##### test_boot.ts

unittest, main thread, 3 cases, label smoke-test. Tests of the bring up's entries.

- `TestBootEntries.test_modules_frozen`: The module is a frozen object.
- `TestBootEntries.test_entries_only`: The module holds the four entries and nothing else.
- `TestBootEntries.test_entries_shared`: The page's entry is the page module's own.

##### test_engine.ts

unittest, worker ai, 21 cases, label smoke-test. Tests of the worker's pieces of the engine in a fresh worker of the headless page, on a real queue of thread `ai` in synchronous mode.

- `TestEngineChain.test_server_lines`: The server's lane holds the handshake, then the sync, in that order.
- `TestEngineChain.test_tools_listed`: The agent lists the browser's tools, then the server's under `server`.
- `TestEngineChain.test_store_root`: The store sits under the root `/engine` of the pool it was given.
- `TestEngineChain.test_databases_restored`: The sync's wake finds every database of the seed restored.
- `TestEngineChain.test_file_restored`: A `db.file` line kept its value in the cache the start gave the store.
- `TestEngineChain.test_store_requests`: The UI thread's store requests reach the store, its handlers registered.
- `TestEngineChain.test_first_render`: The first render reaches the UI lane holding the seed's remark.
- `TestEngineChain.test_provider_key`: The scripted port needs a key, which the chain sets to the fixed text.
- `TestEngineChain.test_turn_ended`: The turn's tool renders on the UI lane, then the turn ends there.
- `TestEngineChain.test_turn_committed`: The turn's rows go to the server as commits.
- `TestEnginePieces.test_module_frozen`: The module is a frozen object holding its functions and nothing else.
- `TestEnginePieces.test_scripted_off`: A false `provider.scripted` throws before anything is built.
- `TestEnginePieces.test_sync_same`: A reply naming the store's databases passes.
- `TestEnginePieces.test_sync_differs`: A reply naming others throws, naming both lists.
- `TestEnginePieces.test_render_plain`: A scene with no image renders its subtitle alone.
- `TestEnginePieces.test_render_image`: A scene's image renders as the reference its document holds.
- `TestEnginePieces.test_media_line`: An image's line carries its bytes, read out of the store, under its ref.
- `TestEnginePieces.test_media_lost`: A row whose cache file is lost fails as the store says.
- `TestEnginePieces.test_media_unknown`: A key with no row fails as the store says.
- `TestEnginePieces.test_subtitle_missing`: A document with no subtitle is not a scene.
- `TestEnginePieces.test_image_invalid`: A document whose image is not text is not a scene.

##### test_engine_image.ts

unittest, worker ai, 4 cases, label smoke-test. Tests of a scene with an image, in a fresh worker of its own, since a realm takes one registration of the chain, on the bench of test_engine.ts.

- `TestImageRender.test_first_held`: The chain sends the bytes of the cache file, and no render follows yet.
- `TestImageRender.test_first_shown`: The answer to `media.store` brings the first render, naming the image.
- `TestImageRender.test_tool_held`: The tool sends the bytes of the cache file, and no render follows yet.
- `TestImageRender.test_tool_shown`: The answer to `media.store` brings the tool's render, then the turn ends.

##### test_engine_page.ts

line cases, main thread, 23 cases, label smoke-test. The line cases of the UI thread's program, `engine.page_run`, on the elements of the engine page, made here as the page's integration block makes them, under the ids the program finds.

- `refused`: sends refusal_1; expects refusal_1_reply.
- `closed`: sends band_2, image_3; expects band_2_reply, image_3_reply.
- `rendered`: sends render_4; expects render_4_reply.
- `rendered_read`: sends image_5, band_6; expects image_5_reply, band_6_reply.
- `typed`: sends submit_one; expects say_1.
- `typed_read`: sends band_7; expects band_7_reply.
- `typed_ended`: sends say_1_reply; expects nothing.
- `typed_shown`: sends band_8; expects band_8_reply.
- `permit_typed`: sends submit_three; expects say_2.
- `permit_asked`: sends ask_9; expects nothing.
- `permit_shown`: sends permit_10; expects permit_10_reply.
- `permit_chosen`: sends choose_accept; expects ask_9_reply.
- `permit_cleared`: sends permit_11; expects permit_11_reply.
- `permit_ended`: sends say_2_reply; expects nothing.
- `permit_read`: sends band_12; expects band_12_reply.
- `console_shown`: sends key_console; expects open_4.
- `console_shown_read`: sends band_13; expects band_13_reply.
- `console_hidden`: sends key_console; expects nothing.
- `console_hidden_read`: sends band_14; expects band_14_reply.
- `turn_typed`: sends submit_three; expects say_5.
- `turn_toggled`: sends key_console, key_console; expects nothing.
- `turn_read`: sends band_15; expects band_15_reply.
- `box_bound`: sends box_16; expects box_16_reply.

#### 3.1.7 TypeScript group B integration blocks

##### test_integrate_substrate.ts

line cases, worker ai, 15 cases, label smoke-test. The line cases of the store, a block of group B in the AI worker.

- `db_created`: sends create_alpha; expects create_alpha_push, create_alpha_reply.
- `row_put`: sends put_moat; expects put_moat_push, put_moat_reply.
- `row_got`: sends get_moat; expects get_moat_reply.
- `file_put`: sends put_bridge; expects put_bridge_push, put_bridge_reply.
- `file_got`: sends get_bridge; expects get_bridge_reply.
- `put_unchanged`: sends put_moat_again; expects put_moat_again_reply.
- `keys_listed`: sends list_alpha; expects list_alpha_reply.
- `document_put`: sends put_scroll; expects put_scroll_push, put_scroll_reply.
- `head_read`: sends head_scroll; expects head_scroll_reply.
- `turn_appended`: sends append_gate; expects append_gate_push, append_gate_reply.
- `rows_changed`: sends run_gate; expects run_gate_push, run_gate_reply.
- `rows_read`: sends read_gate; expects read_gate_reply.
- `value_deleted`: sends delete_moat; expects delete_moat_push, delete_moat_reply.
- `absent_deleted`: sends delete_absent; expects delete_absent_reply.
- `db_dropped`: sends drop_alpha; expects drop_alpha_push, drop_alpha_reply.

##### test_integrate_worker_ai.ts

line cases, worker ai, lanes, 3 cases, label smoke-test. The line cases of the AI worker's bring up.

- `started`: sends nothing; expects tap_start_reply.
- `settings_relayed`: sends settings_put_notice; expects settings_put_request.
- `fault_relayed`: sends fault_ui; expects error_relayed.

##### test_substrate_crash.ts

line cases, fresh workers, 2 cases, label smoke-test. The line cases of the store's crash, a block of the side `workers` of `test_headless`, with a fresh AI worker for each case.

- `put_held`: sends start_cleared; expects tap_start_reply, alpha_created, put_paused.
- `orphan_removed`: sends start_kept; expects tap_start_reply, orphan_checked.

##### test_integrate_page.ts

line cases, main thread, 22 cases, label smoke-test. The line cases of the UI thread's handlers on the page.

- `black`: sends render_1; expects render_1_reply.
- `black_read`: sends image_10, band_11; expects image_10_reply, band_11_reply.
- `stored`: sends store_2; expects store_2_reply.
- `painted`: sends render_3; expects render_3_reply.
- `painted_read`: sends image_12, band_13; expects image_12_reply, band_13_reply.
- `permit_asked`: sends permit_4; expects nothing.
- `permit_shown`: sends permit_14; expects permit_14_reply.
- `permit_chosen`: sends choose_always; expects permit_4_reply.
- `permit_cleared`: sends permit_15; expects permit_15_reply.
- `said`: sends submit_said; expects say_3.
- `said_read`: sends band_16; expects band_16_reply.
- `said_ended`: sends say_3_reply; expects nothing.
- `said_shown`: sends band_17; expects band_17_reply.
- `clicked`: sends click_pixel; expects click_4.
- `clicked_ended`: sends click_4_reply; expects nothing.
- `clicked_shown`: sends band_18; expects band_18_reply.
- `overlay_keyed`: sends key_2; expects nothing.
- `audit_keyed`: sends key_1; expects audit_tail_5.
- `audit_shown`: sends audit_tail_5_reply, overlays_19; expects overlays_19_reply.
- `audit_unkeyed`: sends key_1; expects nothing.
- `audit_hidden`: sends overlays_21; expects overlays_21_reply.
- `fetched`: sends fetch_20; expects fetch_20_reply.

##### test_integrate_tools_browser.ts

line cases, worker ai, 8 cases, label smoke-test. The line cases of the browser's tools.

- `tools_listed`: sends listed_request; expects listed_reply.
- `files_created`: sends files_request; expects files_pushed, files_reply.
- `world_created`: sends world_request; expects world_pushed, world_reply.
- `scene_put`: sends scene_request; expects scene_pushed, scene_reply.
- `scene_read`: sends read_request; expects read_reply.
- `region_made`: sends region_request; expects region_pushed, region_reply.
- `image_made`: sends image_request; expects image_pushed, image_reply.
- `keys_listed`: sends keys_request; expects keys_reply.

##### test_agent_faults.ts

line cases, fresh workers, 9 cases, label smoke-test. The line cases of the agent's faults, a block of the side `workers` of `test_headless`, with a fresh AI worker for each case, since each case fails the agent's queue, as fail loud intends, and a realm holds one agent.

- `arguments_unparsed`: sends start_cleared, say_unparsed; expects tap_start_reply, metaverse_created, universe_made, world_put, scene_put, prompt_put, worker_ready, prompted, said_unparsed, error_unparsed.
- `arguments_overflow`: sends start_cleared, say_overflow; expects tap_start_reply, metaverse_created, universe_made, world_put, scene_put, prompt_put, worker_ready, prompted, said_overflow, error_overflow.
- `arguments_array`: sends start_cleared, say_array; expects tap_start_reply, metaverse_created, universe_made, world_put, scene_put, prompt_put, worker_ready, prompted, said_array, error_array.
- `arguments_null`: sends start_cleared, say_null; expects tap_start_reply, metaverse_created, universe_made, world_put, scene_put, prompt_put, worker_ready, prompted, said_null, error_null.
- `arguments_number`: sends start_cleared, say_number; expects tap_start_reply, metaverse_created, universe_made, world_put, scene_put, prompt_put, worker_ready, prompted, said_number, error_number.
- `arguments_string`: sends start_cleared, say_string; expects tap_start_reply, metaverse_created, universe_made, world_put, scene_put, prompt_put, worker_ready, prompted, said_string, error_string.
- `reply_empty`: sends start_cleared, say_empty; expects tap_start_reply, metaverse_created, universe_made, world_put, scene_put, prompt_put, worker_ready, prompted, said_empty, error_empty.
- `tool_thrown`: sends start_cleared, say_thrown; expects tap_start_reply, metaverse_created, universe_made, world_put, scene_put, prompt_put, worker_ready, prompted, said_thrown, note_put, error_thrown.
- `content_unsupported`: sends start_cleared, say_picture; expects tap_start_reply, metaverse_created, universe_made, world_put, scene_put, prompt_put, worker_ready, prompted, said_picture, error_picture.

##### test_integrate_agent.ts

line cases, worker ai, 3 cases, label smoke-test. The line cases of the agent.

- `castle_built`: sends castle_ask; expects castle_answer.
- `next_answered`: sends next_ask; expects next_answer.
- `again_chained`: sends again_ask; expects again_answer.

#### 3.1.8 TypeScript group C integration blocks, behind ttyd

##### test_wire_end.ts

own points, main thread, 3 cases, label smoke-test. Tests of the wire port's end, group C, on the headless page that ttyd serves.

- `end_waits`: `wire_end` on an open socket: the line goes, `fn` runs at the server's close.
- `end_closed`: `wire_end` once the server has closed the socket: `fn` runs at once.
- `close_ended`: `wire_end` after `wire_close`: `fn` runs at once and nothing is sent.

##### test_worker_ai_console.ts

line cases, main thread, 2 cases, label smoke-test. The line cases of the AI worker's relays of the console, group C, on the UI side of the headless page that the block's own ttyd serves.

- `console_opened`: sends open_request; expects open_reply.
- `console_closed`: sends close_request; expects close_reply, exit.

##### test_integrate_engine.ts

line cases, engine worker, 10 cases, label smoke-test. The line cases of the engine's worker, group C, on the headless page of the block's own ttyd.

- `first_render`: sends nothing; expects first_store, first_render, wire_initialize, wire_initialize_reply, wire_initialized, wire_list, wire_list_reply, first_painted.
- `choice_1`: sends say_1; expects render_1, wire_prompt, wire_user_1, wire_asked_1, wire_stored, wire_result_1, wire_answer_1, wire_stored, say_1_reply.
- `choice_3`: sends say_3; expects permit_ask, console_show, console_busy, dash_reached, console_idle, render_output, wire_user_3, wire_asked_3, wire_stored, wire_result_3, wire_asked_output, wire_stored, wire_result_output, wire_answer_3, wire_stored, say_3_reply.
- `bad_number`: sends say_number; expects wire_otherwise, wire_stored, say_number_reply.
- `bad_word`: sends say_word; expects wire_otherwise, wire_stored, say_word_reply.
- `bad_empty`: sends say_empty; expects wire_otherwise, wire_stored, say_empty_reply.
- `bad_click`: sends click; expects wire_otherwise, wire_stored, click_reply.
- `choice_3_denied`: sends say_denied; expects permit_denied, wire_user_3, wire_asked_3, wire_stored, wire_denied, wire_lacks, wire_stored, say_denied_reply.
- `choice_1_again`: sends say_again; expects render_again, wire_user_1, wire_asked_1, wire_stored, wire_result_1, wire_answer_1, wire_stored, say_again_reply.
- `dumped`: sends dump, say_0; expects wire_dump_browser, wire_dump_server, wire_user_0, wire_answer_0, wire_stored, say_0_reply.

### 3.2 The checks of test_posix.py, without formatting

Run once the stream has passed, each over every whitelisted file, the first failure ending the run.

- `non-ASCII`: every file of python/reformat_whitelist.txt has a row of python/reformat_table.json, and is read in its row's encoding with no non-ASCII character outside _NON_ASCII_ALLOWED
- `comment rules`: every whitelisted file's header stops within 20 lines, and every comment below it is one line, no `<# #>` comment, and holds only letters, digits, white space and _ENGLISH_PUNCT outside Doxygen `code` spans, unless it is a formatter escape
- `audit probe`: the synchronization audit refuses each of its _AUDIT_REFUSED samples and passes each of its _AUDIT_PASSED samples
- `synchronization audit`: no ts/*.ts file outside _SYNCHRONIZATION_MODULES uses await, `.then(`, `new Promise`, Atomics or SharedArrayBuffer outside its comments and literals
- `linters`: `ruff check` passes on the whitelisted .py and .pyi files, the one row of python/reformat_table.json with a linter
- `API compile`: page_build.api_check: tsc compiles ts/tsconfig.api.json, every file of API/ts as one project
- `API TypeScript match`: api_match.typescript_match: every member the API text of API/ts declares is in the code and every member the code exports is in the text, each pair assignable both ways
- `API Python match`: api_match.python_match: each stub of API/python agrees with its module's public functions, classes, signatures and bases
- `API handler match`: api_match.handlers_match: each handler a python/engine_*.py module registers takes exactly the fields of its payload in API/ts/lines.d.ts
- `API gold match`: api_match.gold_match: the gold of test_tools_browser and test_substrate_store agrees with API/mcp/tools.json and API/sql/substrate.sql

### 3.3 test_wire.py, smoke-test rungs

The page is built first, then three roots run in one browser, each a ttyd of its own and one TAP stream of the page, one point per rung, read from `<root>/tap/typescript.tap`.

- `page built`: build/test_wire.html is built from the test template, its sha256 shown.
- `echo: ttyd`: ttyd starts on the echo root.
- `echo: page`: the page opens on that ttyd.
- `echo: first`: `tap.start` in full names, id 101, its settings and gold, reaches the page.
- `echo: echo`: an `echo` line comes back equal, with no blob and the payload sent.
- `echo: extensions`: a socket of its own sends nothing, so no program starts, and its `extensions` is empty.
- `echo: control`: one blob of the gold's control_bytes, 1 MiB, is echoed whole.
- `echo: repeat`: one blob of 8256 bytes is echoed.
- `echo: repeated`: the same 8257 byte frame again, which ended a ttyd that offered compression, is echoed.
- `echo: stream end`: the stream ends passing, one point per rung.
- `echo: ttyd killed`: ttyd is killed, and its end and that of the program it ran are checked.
- `stock: ttyd`: ttyd starts on the stock root.
- `stock: page`: the page opens on that ttyd.
- `stock: first`: `tap.start` reaches the page from the stock server.
- `stock: mcp`: `initialize`, then `notifications/initialized` and a tool call of the server's MCP.
- `stock: sync`: `db.sync` brings the gold's four databases, each one's db.restore then its db.file lines, in name order.
- `stock: commits`: each push line the gold lists goes to the server in order.
- `stock: audit`: a record and a note of the rung's own, then audit.tail holds the record laid out and the note under it.
- `stock: console`: tty 0 opens, `exit` is typed at the prompt, and its end comes.
- `stock: lines`: a subshell's numbers come every one in order, then the prompt.
- `stock: unknown`: its point and the parent lines, then an unknown push ends the server.
- `stock: stream end`: the stream ends passing, one point per rung.
- `stock: server end`: the server wrote the unknown push's error line and exited with code 1 as ttyd logged, was reaped, and its databases hold every commit of the commits rung, the dropped database gone.
- `restart: ttyd`: ttyd starts on the restart root.
- `restart: page`: the page opens on that ttyd.
- `restart: first`: `tap.start` reaches the page from the server.
- `restart: restart`: `source.put` of the main loop and its digest, then `system.restart`, held until the driver releases it.
- `restart: stream end`: the stream ends passing, one point per rung.
- `restart: server end`: the server execed in place under its pid, recorded the page's refusal `wire.start_twice` and wrote its error line, exited with code 1, was reaped, and the page's fault screen shows the refusal.

### 3.4 test_browser.py, smoke-test rungs

Only the suites root is smoke-test: the ttyd page's bring up over TAP.

- `ttyd for the root suites`: ttyd serves the suites root's ttyd page.
- `stage 0: typescript suites`, root suites: Runs the suites on the page, keeping document 1 when document 2 starts.
- `stage 0: typescript suites in order`, root suites: The worker's modules, then the UI's, in order, the first document whole.
- `stage 8: fresh root`, root suites: A root the test put no provider script in holds the seed's script.
- `leaving the root suites`: the page leaves the root, and its ttyd stops.

### 3.5 test_demo.py, smoke-test rungs

The engine page on a debug root, then the plain rung on a root outside debug mode, each typed with no click after choice 1.

- `served`, the debug root: The page builds, the root is made, ttyd answers and the first render shows.
- `choice 1`, the debug root: Clicks the box, and typing 1 ends with the analyst's first text in the band.
- `choice 3`, the debug root: Typing 3 asks the permit, and Accept runs the command in dash in view.
- `bad input`, the debug root: Each input the table does not hold, `7`, `word` and an empty line, is answered, and a choice then still is.
- `prompt kept`, the debug root: After a load the prompt is not stored again, and goes once with the log.
- `dump`, the debug root: Typing 0 ends with its answer, and the audit holds both sides' dumps.
- `audit`, the debug root: The audit holds the gold's table, no line of its own and notes of sleeps.
- `left`, the debug root: Leaving the page ends the server and ttyd stops, `--debug` keeping the audit.
- `plain`, the plain root: A root outside debug mode serves two turns and ends up holding no record.

### 3.6 Then the guide tests

Section 2, whole, in the same order.

## 4 `--test-all`

Adds what is labelled test-all and not disabled, the formatters and the type checker, and the line count, which test_posix.sh turns on by passing `--coverage` with this option. The run has no deadline of its own. Each item says where it runs among those of section 3.

### 4.1 The TAP stream, test-all suites and blocks

#### test_reformat_formatters

unittest, 4 cases, label test-all. Tests reformat's check and formatting with the real formatters of reformat_table.json, ruff, shfmt and prettier, and its type checker, pyright, which refuses a Python file of a type error once it is formatted. Runs in the Python unit suites, after test_reformat.

- `TestCheck.test_check_commands`: A check starts each Linux row's checker on its files, rewriting none.
- `TestCheck.test_check_formatted`: The TypeScript row's checker passes a formatted file as it is.
- `TestFormat.test_format_commands`: A formatting starts each Linux row's formatter on its files.
- `TestFormat.test_types_refused`: A type error fails after formatting, its report raised, nothing printed.

#### test_local_http_delay

unittest, 2 cases, label test-all. Tests the delayed answers of the local HTTP server, on the server and the script of test_local_http, the tests that wait out a delay of that script, so that this suite runs in a test-all run only. Runs in the Python unit suites, after test_local_http.

- `TestDelay.test_delay_threaded`: A delayed answer is due after its delay, another answered meanwhile.
- `TestDelay.test_paths_answered`: Each delayed path answers GET and POST with its status and body.

#### test_devtools_powershell

unittest, 11 cases, label test-all. Tests devtools_windows.py and the parts of devtools.py that need a browser, on Chrome or Edge on Windows through a relay in powershell.exe, as WSL cannot reach Windows' 127.0.0.1. A later suite from 2026-10-30, run by no option, until the request of 2026-11-12 labelled it test-all. It counts no module's lines; see section 6.2.2. Runs in the Python unit suites, after test_verbose, 84 s, 62 s of it test_open_timeout's wait.

- `TestClose.test_close_target`: Closing the page closes its target, and no more calls to it work.
- `TestConsole.test_console_followed`: A console message reaches every follower as its text.
- `TestOpen.test_open_error`: Any other navigation error fails at once.
- `TestOpen.test_open_refused`: A refused navigation is sent again until one loads.
- `TestOpen.test_open_timeout`: A navigation refused until its timer ends fails, naming the address.
- `TestRelay.test_relay_unfound`: A PATH that holds no PowerShell fails loud, starting nothing.
- `TestStart.test_call_session`: Page methods carry the page's session, browser and target ones do not.
- `TestStart.test_port_written`: The port file's address serves DevTools, and the page evaluates.
- `TestTrace.test_trace_end`: Ending a trace returns every event sent until it completed.
- `TestTrace.test_trace_start`: A trace starts afresh, holding none of the loads of the one before.
- `TestWorker.test_worker_pause`: The worker is attached from the page, its debugger enabled and paused.

#### test_test_posix_formatters

unittest, 3 cases, label test-all. Tests the formatter step of test_posix.py with the real formatters of reformat_table.json, ruff among them, and the whole program. Runs in the Python unit suites, after test_test_posix.

- `TestFormatterStep.test_normal_formatted`: A `test-all` run formats the file and prints nothing.
- `TestProgramRun.test_files_checked`: With no option it checks, lints and compiles the API, printing nothing.
- `TestProgramRun.test_switch_skipped`: With no program to start, the switch of the cloud environment returns.

#### test_failing_block

unittest, 2 cases, label test-all. Tests the driver's count of a TypeScript realm's failing tests, running test_all.py as a program with `--stream --module failing_block.ts` and `--failures` of the gold's count, so that each run passes with nothing on stderr and its stream holds the gold's counts. Runs in group A's integration phase, after test_tap_pair_ts.

- `TestBlock.test_bail_counted`: A `smoke-test` run bails out at the first failure, which it expects.
- `TestBlock.test_failures_counted`: A `test-all` run expecting the block's failures passes, counts kept.

#### failing_block.ts

unittest, 6 cases. Fails by design, so that `--failures` is checked to count a Node realm's failures right: test_failing_block runs it twice, whole in a test-all run, 6 planned, 2 passed, 3 failed and 1 skipped, and failfast in a smoke-test run, which bails out at test_failed. It is run by no suite before the request of 2026-11-12, and is listed apart from the phases, so only `--module` runs it.

- `TestOutcomes.test_passed`: Passes.
- `TestOutcomes.test_failed`: Fails an assertion.
- `TestOutcomes.test_errored`: Throws an error that is no assertion.
- `TestOutcomes.test_skipped`: Is skipped.
- `TestOutcomes.test_expected_failed`: Fails as it is expected to, which counts as no failure.
- `TestOutcomes.test_unexpected_passed`: Passes though it is expected to fail, which counts as a failure.

#### failing_suite

unittest, 7 cases. Fails by design. Its cases are no test cases of their own: test_tap_loop, test_integrate_tap_loop and test_tap_tty, of section 3.1, run it through `--module` and check the failures they expect, so it runs first at `--test-normal` as their fixture, and so at this level too.

- `TestOutcomes.test_errored`: Raises an error that is no assertion.
- `TestOutcomes.test_expected_failed`: Fails as it is expected to, which counts as no failure.
- `TestOutcomes.test_failed`: Fails an assertion.
- `TestOutcomes.test_passed`: Passes.
- `TestOutcomes.test_skipped`: Is skipped.
- `TestOutcomes.test_subtests_failed`: Fails two subtests and passes one, which counts as one failure.
- `TestOutcomes.test_unexpected_passed`: Passes though it is expected to fail, which counts as a failure.

#### test_integrate_http.ts

line cases, 11 cases, label test-all. The line cases of the HTTP port. Runs in group A's integration blocks, in Node, after test_integrate_queue.ts.

- `json_answered`: sends json_request; expects json_reply.
- `json_parameters`: sends charset_request; expects charset_reply.
- `text_answered`: sends text_request; expects text_reply.
- `empty_answered`: sends empty_request; expects empty_reply.
- `status_failed`: sends missing_request; expects missing_error.
- `json_malformed`: sends malformed_request; expects malformed_error.
- `json_overflow`: sends overflow_request; expects overflow_error.
- `full_names`: sends full_request; expects full_reply.
- `full_error`: sends full_missing_request; expects full_missing_error.
- `fetch_refused`: sends closed_request; expects closed_error.
- `timeout_expired`: sends slow_request; expects slow_error.

#### test_integrate_media.ts

line cases, main thread, 7 cases, label test-all. The line cases of the media port on the page. Runs in group B's integration blocks, in headless Chrome, after test_integrate_substrate.ts.

- `store_kept`: sends store_request; expects store_reply.
- `store_undecodable`: sends broken_request; expects broken_error.
- `fetch_kept`: sends fetch_request; expects fetch_reply.
- `status_failed`: sends missing_request; expects missing_error.
- `fetch_refused`: sends closed_request; expects closed_error.
- `timeout_expired`: sends slow_request; expects slow_error.
- `fetch_undecodable`: sends text_request; expects text_error.

#### test_integrate_wire.ts

line cases, main thread, 4 cases, label test-all. The line cases of the console port over the whole console connection, a block of group C on the headless page that the block's own ttyd serves, through `bootstrap.py`'s console role and dash on ttyd's pty. Runs in group C's blocks, behind ttyd, after test_wire_end.ts.

- `console_opened`: sends console_open; expects console_open_reply.
- `first_sent`: sends first_message; expects nothing.
- `binary_echoed`: sends heredoc_command, heredoc_row_01, heredoc_row_02, heredoc_row_03, heredoc_row_04, heredoc_row_05, heredoc_row_06, heredoc_row_07, heredoc_row_08, heredoc_row_09, heredoc_row_10, heredoc_row_11, heredoc_row_12, heredoc_row_13, heredoc_row_14, heredoc_row_15, heredoc_row_16, heredoc_row_17, heredoc_end; expects heredoc_output.
- `console_closed`: sends console_close; expects console_exit.

#### test_integrate_xsjs_screenshot

unittest, 2 cases, label test-all. Tests xsjs_screenshot.py as a program, as a person starts it, on the Linux browser of devtools.py, named by --browser so that the run is the same on WSL and off it. Runs in the last phase, the whole page suite, after test_integrate_engine.ts.

- `TestProgram.test_browser_refused`: A browser outside the list fails the run, and no picture is saved.
- `TestProgram.test_page_saved`: The page passes, its PNG is saved, and nothing is left in `build/`.

### 4.2 The line count

By `--coverage`, line_coverage.py counts the lines run from before any project module loads. After the passing block of the last suite that counts for a module, the run fails at that module's first line never run. One check per module, in the order they run. A module is not checked when a disabled suite the run lacks counts for it, or when a suite that counts for it had a skipped test: api_match.py, bootstrap.py, devtools.py, page_build.py, ttyd_build.py, xsjs_serve.py.

- `python/tap_consumer.py`: every code line ran, checked after test_tap_consumer.
- `python/tap_producer.py`: every code line ran, checked after test_tap_producer.
- `python/internationalization.py`: every code line ran, checked after test_internationalization.
- `python/reformat.py`: every code line ran, checked after test_reformat_formatters.
- `python/harness.py`: every code line ran, checked after test_test.
- `python/category.py`: every code line ran, checked after test_test.
- `python/audit.py`: every code line ran, checked after test_audit.
- `python/audit_read.py`: every code line ran, checked after test_audit_read.
- `python/switches.py`: every code line ran, checked after test_switches.
- `python/third_party_fetch.py`: every code line ran, checked after test_third_party_fetch.
- `python/local_http.py`: every code line ran, checked after test_local_http_delay.
- `python/stall_loop.py`: every code line ran, checked after test_stall_loop.
- `python/vectors_make.py`: every code line ran, checked after test_vectors_make.
- `python/substrate.py`: every code line ran, checked after test_substrate_limit.
- `python/verbose.py`: every code line ran, checked after test_verbose.
- `python/dispatch.py`: every code line ran, checked after test_dispatch.
- `python/settings.py`: every code line ran, checked after test_settings.
- `python/engine_audit.py`: every code line ran, checked after test_engine_audit.
- `python/engine_db.py`: every code line ran, checked after test_engine_db.
- `python/engine_doc.py`: every code line ran, checked after test_engine_doc.
- `python/engine_kv.py`: every code line ran, checked after test_engine_kv.
- `python/engine_sql.py`: every code line ran, checked after test_engine_sql.
- `python/engine_tap.py`: every code line ran, checked after test_engine_tap.
- `python/engine_turn.py`: every code line ran, checked after test_engine_turn.
- `python/jslb.py`: every code line ran, checked after test_jslb_vectors.
- `python/mcp.py`: every code line ran, checked after test_mcp.
- `python/tap_loop.py`: every code line ran, checked after test_tap_loop.
- `python/echo_loop.py`: every code line ran, checked after test_echo_loop.
- `python/engine_mcp.py`: every code line ran, checked after test_engine_mcp.
- `python/engine_system.py`: every code line ran, checked after test_engine_system.
- `python/main_loop.py`: every code line ran, checked after test_main_loop.
- `python/mcp_stdio.py`: every code line ran, checked after test_mcp_stdio.
- `python/test_posix.py`: every code line ran, checked after test_test_posix_formatters.

### 4.3 The checks of test_posix.py, formatting

- `formatters`: the whitelisted files of each linux row of python/reformat_table.json pass its formatter: prettier for .html, .js and .ts, ruff format for .py and .pyi, shfmt for .sh; runs after the synchronization audit and before the linters.
- `type checker`: `pyright --project python/pyproject.toml`, strict, passes on the .py and .pyi files, after every formatter.

### 4.4 test_wire.py, test-all rungs

- `echo: fit`: one blob of the setting blob_max is echoed, and ttyd's resident size is read. Runs after `echo: repeated`.

### 4.5 test_browser.py, test-all rungs

After the smoke-test rungs of the suites root, in this order.

- `stage 8: long tasks`, root suites: The long tasks the UI thread ran since the observer started.
- `stage 5: traced synchronous load found`, root suites: A synchronous GET on the UI thread is found in a trace, as its control.
- `stage 5: no synchronous load on the UI thread`, root suites: The page's bring up and suites make no synchronous load on the UI thread.
- `ttyd for the root faults`: ttyd serves the faults root's ttyd page.
- `stage 0: thrown error`, root faults: An error thrown after load replaces the page and reaches the server.
- `stage 0: first fault only`, root faults: A second fault leaves the first one alone on the screen.
- `stage 0: reload`, root faults: The fault screen's Reload loads the page again and both streams end.
- `stage 0: rejection`, root faults: A rejected promise nothing handles reaches the fault screen and the server.
- `stage 0: failing script`, root faults: A resource that fails to load reaches the capture handler and the server.
- `stage 0: failing image`, root faults: A resource that fails to load reaches the capture handler and the server.
- `stage 0: failing link`, root faults: A resource that fails to load reaches the capture handler and the server.
- `stage 0: failing with neither address`, root faults: A resource that fails to load reaches the capture handler and the server.
- `stage 0: failing object`, root faults: A resource that fails to load reaches the capture handler and the server.
- `stage 0: failing SVG image`, root faults: An SVG image whose only address is `xlink:href` faults naming no address.
- `leaving the root faults`: the page leaves the root, and its ttyd stops.
- `stage 5: stub reachable`: The stub HTTP server's own page loads, which proves the browser reaches it first.
- `ttyd for the root probe`: ttyd serves the probe root's headless page.
- `stage 5: wire first line`, root probe: The wire port's first line, `tap.start`, with no gold, and the page's gold.
- `stage 5: blob_max plus one refused`, root probe: The page's wire port refuses to post a blob one byte over `blob_max`.
- `stage 5: wire_close`, root probe: `wire_close` ends the server and reports no close.
- `stage 5: error line then close`, root probe: An `error` line and the server's end are reported as a close with an error.
- `stage 5: http post`, root probe: The POST carries its exact body and headers and gets its JSON back.
- `stage 5: http preflight`, root probe: The cross origin POST was preceded by its CORS preflight.
- `stage 5: http stalled body`, root probe: A body that stalls after its head is a timeout `error` line.
- `stage 5: http one line per request`, root probe: After a timeout the port gives no second line, though the answer comes late.
- `stage 5: http out of order`, root probe: Replies arriving in reverse order each answer their own request.
- `stage 5: http get with a body`, root probe: A GET with a body is refused by the browser, an `error` line.
- `stage 5: http port in a worker`, root probe: The HTTP port works inside a worker made from the bundle.
- `stage 5: queue two replies`, root probe: A task sleeping on two requests wakes with both, in submit order.
- `stage 5: http throwing receiver`, root probe: A receiver that throws reaches the fault screen as a rejection.
- `stage 5: close without error line`, root probe: A server that ends with no `error` line is a fault naming the close code.
- `stage 5: queue handler throws`, root probe: A handler that throws reaches the fault screen.
- `stage 7: console open, close, exit, open`, root probe: A console port opens again after this side closed it and after `exit`.
- `stage 7: console closed before open`, root probe: A console socket that closes before it opens is the port's fault.
- `leaving the root probe`: the page leaves the root, and its ttyd stops.
- `ttyd for the root credential`: ttyd serves the credential root's headless page.
- `stage 7: token with a credential`, root credential: A ttyd that asks a credential gives its token to a page that sends it.
- `leaving the root credential`: the page leaves the root, and its ttyd stops.
- `ttyd for the root release`: ttyd serves the release root's ttyd page.
- `stage 7: console role refused`, root release: The console role is refused outside debug mode.
- `leaving the root release`: the page leaves the root, and its ttyd stops.

### 4.6 test_demo.py, test-all rungs

- `reload`, the debug root: A second load at once comes up on the files the first load's worker held. Runs after `served`.
- `choice 2`, the debug root: Typing 2 ends with its text, and the server's database holds the note. Runs after `bad input`.
- `console`, the debug root: ctrl 0 hides and shows the view, a command runs in it, ctrl 0 hides it again. Runs after `choice 2`.
- `overlay`, the debug root: ctrl 1 shows the audit's end with the last turn, then hides and empties it. Runs after `console`.
- `tools served`, the tools root: A root whose table calls every tool serves, and its first render shows. Runs after `plain`.
- `tools data`, the tools root: Typing 1 runs every data tool, and the picture they render shows. Runs after `tools served`.
- `tools console`, the tools root: Typing 2 runs every console tool, each permit answered by a click. Runs after `tools data`.
- `tools again`, the tools root: Each tool again: 3 past the turns that compact, 4 compacting them first. Runs after `tools console`.
- `tools dump`, the tools root: Typing 0 dumps both sides, the server holding the turns the browser dropped. Runs after `tools again`.
- `tools record`, the tools root: The audit shows the prompt once per chain, every tool's result and commit. Runs after `tools dump`.
- `tools restart`, the tools root: Typing 5 restarts the server in place, which the page refuses by its fault. Runs after `tools record`.

## 5 `--test-disabled`

Adds every disabled suite, test, root and rung, each with no time limit but its own. test_posix.sh passes no `--coverage` with this option, so the line count of section 4.2 does not run; see section 6.1.

### 5.1 The TAP stream, disabled suites and tests

#### test_devtools_chrome

unittest, 25 cases, label smoke-test. Tests the parts of devtools.py that need the Linux browser, a later suite of devtools on /usr/local/bin/chrome-headless-shell, which the maintainer approved for the test driver on 2026-10-30. Runs in the Python unit suites, after test_verbose. Disabled, 15 s: 25 tests that each start a Chrome of their own, 0.2 s at least, and one that waits out the 5 s a Chrome has to exit.

- `TestBinding.test_binding_called`: Each call comes back with its payload, in order, before the reply.
- `TestBinding.test_binding_loaded`: A page loaded after the binding is added calls it as it loads.
- `TestClose.test_attach_pages`: With no page left an attach makes one, and with one it takes that one.
- `TestClose.test_close_target`: Closing the page closes its target, and no more calls to it work.
- `TestConsole.test_console_followed`: A console message reaches the follower as its text.
- `TestEvaluate.test_evaluate_blank`: The first page is about:blank, and evaluates.
- `TestEvaluate.test_evaluate_large`: A value longer than any pipe's buffer comes back whole.
- `TestEvaluate.test_evaluate_thrown`: An exception the page throws fails loud with its message.
- `TestEvaluate.test_evaluate_unserializable`: A value JSON can't hold fails loud, naming the value.
- `TestEvaluate.test_method_unknown`: A method DevTools doesn't have fails loud, naming the method.
- `TestExit.test_exit_crashed`: A crash ends the call under way, its signal the code, and only there.
- `TestExit.test_exit_read`: Closing the browser ends a wait with its exit, code 0.
- `TestExit.test_exit_write`: A call after the exit fails the same way, as its message can't go.
- `TestLifecycle.test_load_events`: A load the page starts itself shows under a loader of its own.
- `TestNavigate.test_navigate_data`: A data: URL loads, and its page evaluates.
- `TestNavigate.test_navigate_refused`: A port bound but not listening refuses, and the navigation fails at once.
- `TestProfile.test_exit_stopped`: A browser that ignores the end of its pipe is killed, failing the end.
- `TestProfile.test_exit_unseen`: A browser killed while no call waits fails the Browser's end.
- `TestProfile.test_profile_removed`: The profile is a directory under build/ that goes when the browser does.
- `TestProfile.test_start_refused`: An exec the kernel refuses ends the start, leaving no pipe or profile.
- `TestRetried.test_navigate_retried`: A refused navigation is sent again until the server listens.
- `TestScreenshot.test_screenshot_size`: The PNG has the window's width and height in its header.
- `TestTrace.test_trace_end`: Ending a trace returns every event sent until it completed.
- `TestTrace.test_trace_start`: A trace starts afresh, holding none of the loads of the one before.
- `TestWorker.test_worker_pause`: A worker that posts while it runs posts nothing once it is paused.

#### test_page_build_tsc

unittest, 7 cases, label smoke-test. Tests page_build.py with the real tsc, a split suite of page_build that reads the SQLite wasm and xterm.js archives the driver fetches before its first block. Runs in the Python unit suites, after test_page_build_node. Disabled, 9 s: three full compiles of the bundle, 2.2 s each, and two small ones, 0.8 s each.

- `TestBuild.test_archives_named`: Each page holds the members of the gold's two archives.
- `TestBuild.test_bundle_test`: Each page holds the bundle of the test config, the table in place.
- `TestBuild.test_command_printed`: The template and the name build that page, and the child prints its hex.
- `TestBuild.test_page_copied`: A copy with other gold is the page filled with that gold instead.
- `TestBuild.test_templates_filled`: Each page is its template filled from the same pieces, read here.
- `TestCheck.test_project_passed`: A project that compiles passes and writes nothing.
- `TestCheck.test_project_refused`: A type error in a `.d.ts` file raises, tsc's output in the cause.

#### test_ttyd_build, disabled tests

Run inside test_ttyd_build, in its place in the stream, where a lower option shows each as a SKIP point.

- `TestInputs.test_inputs_changed`: Other patches build again, the same are kept, a removed ttyd is built. Disabled, builds ttyd from source three times, 4.5 s.

#### test_api_match, disabled tests

Run inside test_api_match, in its place in the stream, where a lower option shows each as a SKIP point.

- `TestCheckout.test_checkout_passed`: A checkout whose text and code agree passes, its old intermediates gone. Disabled, two real compiler runs each, 1.6 s to 1.9 s.
- `TestCheckout.test_handler_refused`: A handler that differs from its payload stops the whole match. Disabled, two real compiler runs each, 1.6 s to 1.9 s.
- `TestCheckout.test_stub_refused`: A stub that differs from its module stops the whole match. Disabled, two real compiler runs each, 1.6 s to 1.9 s.
- `TestCheckout.test_text_broken`: A fault of the text itself keeps tsc's own failure. Disabled, two real compiler runs each, 1.6 s to 1.9 s.
- `TestCheckout.test_types_refused`: A type the text and the code disagree on fails the compile, each named. Disabled, two real compiler runs each, 1.6 s to 1.9 s.

#### test_bootstrap, disabled tests

Run inside test_bootstrap, in its place in the stream, where a lower option shows each as a SKIP point.

- `TestLock.test_lock_hangup`: A hangup during the wait ends the run by SIGHUP, as elsewhere. Disabled, holds the lock 0.25 s, the suite then over 1 s.
- `TestLock.test_lock_refused`: A lock held past the wait is one error line, its cause the last refusal. Disabled, waits out the 5 s lock wait of bootstrap.py.
- `TestLock.test_lock_waited`: A lock freed within the wait is taken, and the first line then comes. Disabled, holds the lock 0.25 s, the suite then over 1 s.

#### test_xsjs_serve, disabled tests

Run inside test_xsjs_serve, in its place in the stream, where a lower option shows each as a SKIP point.

- `TestProgram.test_program_served`: It builds the page, makes the root, serves on stdout, stops at SIGINT. Disabled, the program whole, with a full compile, 2.3 s.
- `TestServer.test_stop_killed`: A ttyd deaf to SIGTERM is killed past the wait, with a shell's code. Disabled, waits out the 5 s a ttyd has to stop.

#### test_xsjs_serve_death

unittest, 3 cases, label test-all. Tests that ttyd dies with xsjs_serve, on the forked program of test_xsjs_serve and a root in a scratch directory under build/, with the ttyd the driver's bring up built. Runs in the Python unit suites, after test_xsjs_serve. Disabled, 8 s: three tests that each run the serve program whole, with a full compile, 2.2 s.

- `TestParentDeath.test_death_hangup`: The program installs no hangup handler, so SIGHUP ends it as abruptly.
- `TestParentDeath.test_death_killed`: SIGKILL runs no line of the program, and ttyd ends all the same.
- `TestParentDeath.test_death_reader`: A reader of stdout that leaves ends the program at the next log line.

#### test_integrate_bootstrap, disabled tests

Run inside test_integrate_bootstrap, in its place in the stream, where a lower option shows each as a SKIP point.

- `TestDriverHangup.test_hangup_restored`: A driver started with the hangup ignored still passes the suite. Disabled, runs all of test_bootstrap again, 0.8 s.

#### test_jslb_decode_vectors.ts

unittest, worker ai, 2 cases, label smoke-test. The vectors of build/vectors, which the test page carries as test_vectors, each read with the limits its sidecar names, whole, by single bytes and split at every offset, a streamed blob's digest the one its sidecar holds, on the helpers of test_jslb_decode. Runs in group B's unit blocks, in headless Chrome, after test_jslb_decode.ts. Disabled, 7.1 s: decodes each vector at every split.

- `TestVectors.test_vectors_success`: Each success vector, and the bytes it encodes to, decode to its sidecar.
- `TestVectors.test_vectors_error`: Each error vector gives its lines, then its fault, however it is fed.

#### test_integrate_console_view.ts

line cases, main thread, 55 cases, label smoke-test. The line cases of the console view on the page, every part real, on a queue of the UI thread whose lane to the AI worker is the test's end. Runs in group B's integration blocks, in headless Chrome, after test_integrate_worker_ai.ts. Disabled, 6.6 s: 26 of its 55 cases wait a fixed 0.2 s or 0.5 s for the terminal to draw.

- `shown_idle`: sends show_6; expects open_1.
- `opened`: sends open_1_reply; expects input_first, show_6_reply.
- `shown_open`: sends show_7; expects show_7_reply.
- `typed`: sends type_ls; expects input_typed.
- `output_fed`: sends output_prompt, output_hi; expects nothing.
- `output_read`: sends rows_20; expects rows_20_reply.
- `ignored`: sends title, preferences, rows_21; expects rows_21_reply.
- `split_fed`: sends split_head, split_tail; expects nothing.
- `split_read`: sends rows_22; expects rows_22_reply.
- `invalid_fed`: sends invalid; expects nothing.
- `invalid_read`: sends rows_23; expects rows_23_reply.
- `bare_read`: sends bare, rows_24; expects rows_24_reply.
- `key_hidden`: sends key_0; expects nothing.
- `hidden_read`: sends shown_25; expects shown_25_reply.
- `hidden_fed`: sends output_kept; expects nothing.
- `shown_again`: sends show_8; expects show_8_reply.
- `shown_drawn`: sends nothing; expects nothing.
- `kept_read`: sends rows_26; expects rows_26_reply.
- `close_asked`: sends close_ask; expects close_2.
- `close_answered`: sends close_2_reply; expects nothing.
- `exited`: sends exit; expects nothing.
- `key_idle`: sends key_0; expects nothing.
- `idle_read`: sends shown_27; expects shown_27_reply.
- `key_reopen`: sends key_0; expects open_3.
- `key_opened`: sends open_3_reply; expects input_first.
- `echo_typed`: sends type_ab; expects nothing.
- `echo_read`: sends rows_28; expects rows_28_reply.
- `echo_output_fed`: sends output_after; expects nothing.
- `echo_output_read`: sends rows_29; expects rows_29_reply.
- `echo_busy`: sends busy; expects nothing.
- `echo_busy_read`: sends rows_30; expects rows_30_reply.
- `echo_idle`: sends idle; expects nothing.
- `echo_idle_read`: sends rows_31; expects rows_31_reply.
- `echo_backspace`: sends type_backspace; expects nothing.
- `echo_backspace_read`: sends rows_32; expects rows_32_reply.
- `echo_submitted`: sends type_c_enter; expects input_ac.
- `echo_submitted_drawn`: sends nothing; expects nothing.
- `echo_erased_read`: sends rows_33; expects rows_33_reply.
- `wrap_filled`: sends output_fill; expects nothing.
- `wrap_typed`: sends type_wide; expects nothing.
- `wrap_read`: sends rows_34; expects rows_34_reply.
- `wrap_busy`: sends busy; expects nothing.
- `wrap_busy_read`: sends rows_35; expects rows_35_reply.
- `wrap_idle`: sends idle; expects nothing.
- `wrap_submitted`: sends type_enter; expects input_wide.
- `saved_fed`: sends output_saved; expects nothing.
- `saved_typed`: sends type_cd; expects nothing.
- `saved_restored`: sends output_restored; expects nothing.
- `saved_read`: sends rows_36; expects rows_36_reply.
- `pending_fed`: sends output_pending; expects nothing.
- `pending_returned`: sends output_return; expects nothing.
- `pending_read`: sends spans_37; expects spans_37_reply.
- `wide_fed`: sends output_wide; expects nothing.
- `wide_returned`: sends output_return; expects nothing.
- `wide_read`: sends rows_38; expects rows_38_reply.

#### test_tools_browser_console.ts

line cases, worker ai, 19 cases, label smoke-test. The line cases of the browser's console tools, group C, in a fresh worker of the headless page that the block's own ttyd serves, its parts real down to dash on ttyd's tty 0. Runs in group C's blocks, behind ttyd, after test_worker_ai_console.ts. Disabled, 6.6 s: 0.6 s of real commands in dash, and five cases that wait out a timeout of 0.5 s to 2 s.

- `opened`: sends open_request; expects open_reply.
- `recorded`: sends first_input, recorded_request; expects recorded_ask, recorded_show, console_busy, console_idle, recorded_reply.
- `counted`: sends counted_request; expects counted_ask, counted_show, console_busy, console_idle, counted_reply.
- `always`: sends always_request; expects always_ask, always_show, console_busy, console_idle, always_reply.
- `allowed`: sends allowed_request; expects allowed_show, console_busy, console_idle, allowed_reply.
- `prompted_write`: sends prompted_write_request; expects prompted_write_ask, prompted_write_show, console_busy, prompted_write_reply.
- `prompted_wait`: sends prompted_wait_request; expects prompted_wait_ask, prompted_wait_show, prompted_wait_reply.
- `prompted_answer`: sends prompted_answer_request; expects prompted_answer_show, prompted_answer_reply.
- `prompted_done`: sends prompted_done_request; expects prompted_done_show, console_idle, prompted_done_reply.
- `partial_first`: sends partial_first_request; expects partial_first_show, console_busy, partial_first_reply.
- `partial_held`: sends partial_held_request; expects partial_held_show, partial_held_reply.
- `partial_rest`: sends partial_rest_request; expects partial_rest_show, partial_rest_reply.
- `partial_done`: sends partial_done_request; expects partial_done_show, console_idle, partial_done_reply.
- `view_write`: sends view_write_request; expects view_write_show, console_busy, view_write_reply.
- `view_answer`: sends view_input, view_answer_request; expects view_answer_show, view_answer_reply.
- `view_done`: sends view_done_request; expects view_done_show, console_idle, view_done_reply, view_released.
- `sleep_wait`: sends sleep_input, sleep_wait_request; expects sleep_wait_show, console_busy, console_idle, sleep_wait_reply.
- `expired`: sends expired_request; expects expired_show, console_busy, console_idle, expired_reply.
- `wait_expired`: sends wait_expired_request; expects wait_expired_show, wait_expired_reply.

#### test_console_open.ts

line cases, main thread, 11 cases, label smoke-test. The line cases of the console view's open path, group C, on the UI side of the headless page that the block's own ttyd serves, through dash on tty 0, every part real. Runs in group C's blocks, behind ttyd, after test_tools_browser_console.ts. Disabled, 4.3 s: four cases wait a fixed 0.2 s to 2 s for dash's output to draw.

- `hidden_idle`: sends phase_1; expects phase_1_reply.
- `shown_opened`: sends show_2; expects show_2_reply.
- `open_read`: sends phase_3; expects phase_3_reply.
- `prompt_drawn`: sends nothing; expects nothing.
- `prompt_read`: sends rows_4; expects rows_4_reply.
- `echo_typed`: sends type_size; expects nothing.
- `echo_read`: sends rows_5; expects rows_5_reply.
- `size_run`: sends type_enter; expects nothing.
- `size_read`: sends rows_6; expects rows_6_reply.
- `closed`: sends close_ask; expects nothing.
- `idle_read`: sends phase_7; expects phase_7_reply.

### 5.2 test_browser.py, disabled roots and rungs

- `stage 5: wire token timer`, root probe: The wire port's wait for a token from a stopped ttyd runs out. Runs after `stage 7: console open, close, exit, open`. Disabled, waits out the 120 s token wait of wire.ts.
- `stage 5: wire open timer`, root probe: The wire port's wait for a socket that never opens runs out. Runs after `stage 5: wire token timer`. Disabled, waits out the 120 s open wait of wire.ts.
- `ttyd for the root echo`: ttyd serves the echo root's headless page.
- `stage 5: wire drain poll`, root echo: Echoes posted while ttyd is stopped wait on the port's poll, then all come. Disabled, 0.8 s to send 10 MiB of echoes through ttyd and back, before the 5 s it holds ttyd stopped.
- `stage 5: wire drain timer`, root echo: A socket that takes no bytes for the drain wait faults the port. Disabled, waits out the 120 s drain wait of wire.ts.
- `leaving the root echo`: the page leaves the root, and its ttyd stops.
- `ttyd for the root stalled`: ttyd serves the stalled root's ttyd page.
- `stage 5: wire first line timer`, root stalled: A server that never writes the first line runs out the worker's wait. Disabled, waits out the 120 s first line wait of wire.ts.
- `leaving the root stalled`: the page leaves the root, and its ttyd stops.
- `stage 5: release runs nothing`, root release: Outside debug mode the page gets its settings and runs nothing. Runs first in the root release. Disabled, 0.8 s to load the page and its settings, before the 5 s window in which nothing may happen.
- `ttyd for the root locked`: ttyd serves the locked root's ttyd page.
- `stage 5: error before the first line`, root locked: An `error` line before the first line shows the server's message and stack. Disabled, waits out the 5 s lock wait of bootstrap.py.
- `leaving the root locked`: the page leaves the root, and its ttyd stops.

## 6 Requirements not yet satisfied

The first request of 2026-11-12 asked for a bullet per test case of every level, broken up by the option that enables it and listed in the order the cases run, and stated two requirements of the levels themselves: each option enables more and disables nothing, and every case runs with a single option unless it is disabled. The second request of 2026-11-12 moved the cases no option ran, a later suite, a block and a suite that fail by design, under `--test-all`, so the second requirement holds. The first still has the gap below, which has a cause written in the code, but the maintainer has not confirmed that the cause still stands, so it is class B: unsatisfied with cause but without confirmation.

- Each option enables more and disables nothing: holds for the four level options but for the line count, 6.1.
- Every case runs with a single option unless it is disabled: holds.

### 6.1 `--test-disabled` drops the line count

test_posix.sh passes `--coverage` with `--test-all` alone, so the 33 module checks of section 4.2 run at `--test-all` and not at `--test-disabled`; its header says so: "--test-disabled raises it to everything disabled too, with no count". The recorded reason is that the modules only a disabled suite checks, page_build.py among them, would pass or fail by whether the compile stamps in build/ are cold, as a warm stamp leaves page_build.bundle_compile's lines unrun.

6.1.1 Question: should `--test-disabled` also count lines, so that it holds everything `--test-all` runs? The answer decides whether the six modules section 4.2 leaves unchecked, api_match.py, bootstrap.py, devtools.py, page_build.py, ttyd_build.py and xsjs_serve.py, get a line count at any level.

[ ] A. Keep it as it is: `--test-disabled` counts no lines, and this plan names the line count as the one thing `--test-all` runs that `--test-disabled` does not.

[ ] B. Count lines at `--test-disabled` too: test_posix.sh passes `--coverage` with either option, and the compile lines a warm stamp skips are reached by a test that compiles in a scratch build directory. The cost is a change to test_posix.sh and page_build's tests, and a full `--test-disabled` run to prove the six modules complete.

### 6.2 Decisions, reported so that overturning them is cheap

6.2.1 "Each flag" is read as the four level options of test_posix.sh. The switch `--anthropic`, for Anthropic's cloud container, removes the suites test_reformat_formatters and test_test_posix_formatters and every check of test_posix.py, as the rule for the cloud environment requires that it run no formatting or checking; this plan keeps it.

6.2.2 test_devtools_powershell counts no module's lines: its row of `_COUNTED` in test_all.py is empty, so devtools_windows.py stays out of the line count of section 4.2, as it was while the suite was later. Measured under the suite, the count would fail `--test-all` at the module's first line never run. A browser search that finds none, and three early returns of a relay closed that never opened, could be reached by a test; five failures, a browser that exits before serving DevTools, a Windows with no TEMP folder, a process that outlives its stop, a profile that cannot be removed for a reason but a busy file, and a relay that exits with an error, each need a Windows that fails.

6.2.2.1 Question: should the Windows relay's lines be counted at `--test-all`? The answer decides whether devtools_windows.py joins the 33 modules section 4.2 checks.

[ ] A. Keep it uncounted, as decided on 2026-11-12, the module's failures proved by no test.

[ ] B. Count it: add a test of a browser search over an environment holding no browser and one closing a relay never opened, and mark the five failures a working Windows cannot reach `# pragma: no cover`, the mark that today exempts only internal errors. The cost is two tests and five marks, and a full `--test-all` run to prove the module complete.

6.2.3 Under the switch `--verbose` the console runs `dash -v`, which echoes each command twice, and test_tools_browser_console.ts fails; the maintainer chose on 2026-11-05 to leave the console tool as it is. The block is disabled, so only `--test-disabled --verbose` meets it. `--debug` changes what the programs copy and print, and no case.

6.2.4 The deadline of 180 s binds the run with no option and with `--test-normal`, and no run of `--test-all` or `--test-disabled`, which could not fit in it. It is a limit of the smoke-test label and no test case, so this plan does not count its absence as a check removed.
