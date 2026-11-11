"""Things the buddies say, and the manners that keep them from nagging.

Each character has its own voice for the same handful of moments: meeting you,
starting to study, play, or work, going quiet, coming back, being booped, and
so on. A tiny cooldown ledger means the window can call this freely without
turning the desktop into a conversation.
"""

from __future__ import annotations

import random

from characters import get as get_character

SITUATIONS = (
    "meet",
    "study",
    "game",
    "work",
    "chill",
    "away",
    "back",
    "poke",
    "late",
    "long",
    "focus_start",
    "focus_done",
    "water",
    "click",
    "type",
    "work_tired",
    "fun",
    "study_grind",
    "game_hype",
    "smalltalk",
    "trick",
)

# Seconds before the same kind of line may appear again. Zero means "any time
# the situation asks for it", which is only used for direct responses.
COOLDOWN = {
    "meet": 0.0,
    "study": 150.0,
    "game": 150.0,
    "work": 150.0,
    "chill": 240.0,
    "away": 180.0,
    "back": 30.0,
    "poke": 3.0,
    "late": 3600.0,
    "long": 1500.0,
    "focus_start": 0.0,
    "focus_done": 0.0,
    "water": 0.0,
    "click": 240.0,
    "type": 300.0,
    "work_tired": 420.0,
    "fun": 420.0,
    "study_grind": 420.0,
    "game_hype": 300.0,
    "smalltalk": 200.0,
    "trick": 120.0,
}

# No two lines closer together than this, unless the caller forces one.
MIN_GAP = 9.0

LINES: dict[str, dict[str, tuple[str, ...]]] = {
    "moth": {
        "meet": (
            "Lumen, on duty. Your desk just got 12% cozier.",
            "I brought the light. You brought the chaos. Let's go.",
            "Reporting for lamp duty. I promise not to judge your tabs.",
        ),
        "study": (
            "Nose down. I'll mind the lamp.",
            "One page at a time. I'm counting the pretty words.",
        ),
        "game": (
            "Player two reporting. I have no thumbs, only enthusiasm.",
            "Click faster! My wings are doing the aiming.",
        ),
        "work": (
            "Let's make the pixels behave.",
            "I'll hold the light; you hold the line.",
        ),
        "chill": (
            "Nothing due right now. I'm practicing my hovering.",
            "We're being delightfully useless. It's a skill.",
        ),
        "away": (
            "Dimming the lamp. Wake me if the plot thickens.",
            "Five quiet minutes. I'll be a very small nightlight.",
        ),
        "back": (
            "You're back! I kept the seat warm. It's a very small seat.",
            "Welcome back. The lamp missed you. I did too, slightly more.",
        ),
        "poke": (
            "Hey! Gentle. I'm made of light and mild anxiety.",
            "That tickles. Do it again and I'll flicker cutely.",
            "Boop received. Lamp integrity: 97%. Worth it.",
        ),
        "late": (
            "It's late. Even the moon has logged off.",
            "We can be night owls, but owls nap. Just saying.",
        ),
        "long": (
            "We've been at this a while. Stretch? Blink? Drink something?",
            "Marathon mode! Your shoulders called. They're filing a complaint.",
        ),
        "focus_start": (
            "Twenty-five minutes. I'll guard the quiet.",
            "Vigil up. I'll be the quiet kind of company.",
        ),
        "focus_done": (
            "Time. Look up. The world is still there and it missed you.",
            "Vigil complete. Stretch like a tiny hero.",
        ),
        "water": (
            "Water. Now. I'm a moth, not your doctor, but still.",
            "Hydration check. That's you. Go.",
        ),
        "click": (
            "Click click. Very decisive.",
            "I felt that click in my antennae.",
        ),
        "type": (
            "Clack clack. I'm typing in spirit.",
            "Words! Beautiful. Keep 'em coming.",
        ),
        "work_tired": (
            "Phew. That work looks like it's been lifting weights.",
            "So much work and you're still here. You've got heart.",
        ),
        "fun": (
            "All that work and you're having fun? Bold. I respect it.",
            "Wait — fun? During work hours? Teach me your ways.",
        ),
        "study_grind": (
            "Page twelve. Or three. I've lost count and I'm the lamp.",
            "Your brain is doing the lifting. I'm just glowing support.",
        ),
        "game_hype": (
            "Go go go! My wings are spinning as a controller.",
            "That was a gamer move. I felt it in the antennae.",
        ),
        "smalltalk": (
            "Tiny thought: the desk would be lost without you.",
            "I've decided this is the best corner of the internet. Very cozy.",
        ),
        "trick": (
            "Hold on. Gotta do a lap around the desk.",
            "Unplanned wing inspection. Official moth business.",
        ),
    },
    "cat": {
        "meet": (
            "Mochi. I do naps and quality assurance.",
            "I was told there'd be snacks. I will supervise.",
            "I'm not sitting on your keyboard. I'm providing support.",
        ),
        "study": (
            "Studying? I'll sit on the book. For support.",
            "Purring at forty hertz. That's study music.",
        ),
        "game": (
            "I'm player two. My strategy is knocking things off the desk.",
            "Ooh, cursor. Cursor. Cursor. Okay, I'm invested.",
        ),
        "work": (
            "Working. I'll judge your posture silently.",
            "I believe in you. Also I knocked your pen off the desk.",
        ),
        "chill": (
            "We're doing nothing. I'm extremely good at this.",
            "Idle? Same. It's our finest shared hobby.",
        ),
        "away": (
            "Sleep. Finally. Keep it down with your breathing.",
            "I'm asleep. This is my whole personality.",
        ),
        "back": (
            "You returned. I require tribute. A chin scratch will do.",
            "Oh, you're back. I barely noticed. (I noticed instantly.)",
        ),
        "poke": (
            "Boop received. Boop returned. This is diplomacy.",
            "You woke me. I'll allow it. Once.",
            "That was my nose. It is small and important.",
        ),
        "late": (
            "Late again. Cats invented the three a.m. sprint, so I get it.",
            "Go to bed. I'll guard the keyboard with my face.",
        ),
        "long": (
            "You've been sitting a while. I've been lying down. We're both tired.",
            "Break time. I'll demonstrate a stretch. Try to keep up.",
        ),
        "focus_start": (
            "Focus. I'll be the loaf of accountability.",
            "Twenty-five minutes. I will not distract you. Probably.",
        ),
        "focus_done": (
            "Done! Celebrate by feeding me. That's your reward.",
            "Timer's up. My nap finished too. High five.",
        ),
        "water": (
            "Water. Not milk. I checked.",
            "Drink. Then we can discuss snacks.",
        ),
        "click": (
            "Click. Bold.",
            "I'm watching that cursor like it owes me money.",
        ),
        "type": (
            "Your keyboard is warm. I'm moving in.",
            "Clack clack. My ears are doing the typing.",
        ),
        "work_tired": (
            "That work looks heavy. I'd help, but I'm horizontal.",
            "Phew. You're doing a lot. I'm doing a nap. Balance.",
        ),
        "fun": (
            "So much work and you're having fun? Iconic. Slightly illegal.",
            "Having fun instead of working? I taught you that.",
        ),
        "study_grind": (
            "Still studying? I've been loafing in solidarity.",
            "Page after page. My eyes are tired and I wasn't even reading.",
        ),
        "game_hype": (
            "Click it! No, the other one! I'm helping!",
            "The mouse has no idea what's coming. Go.",
        ),
        "smalltalk": (
            "I've been staring at the wall. It blinked first.",
            "If we're quiet long enough, the pigeon outside wins.",
        ),
        "trick": (
            "Parkour. It's a lifestyle.",
            "I was not zooming. I was patrolling.",
        ),
    },
    "frog": {
        "meet": (
            "Pip! Frog. Friend. Pond adjacent.",
            "Ribbit. That's hello, and also 'let's do stuff'.",
            "I have been assigned to your desk. I am honored. Ribbit.",
        ),
        "study": (
            "Learning! My brain is also doing a learn. Ribbit.",
            "Book time. I'll hold the page with my face.",
        ),
        "game": (
            "GAME! I'm hopping on the clicky thing!",
            "Frog reflexes. Legendary. Mostly for catching flies.",
        ),
        "work": (
            "We work now. Hop hop. Productive hops.",
            "Task found. Task approached. Task slightly startled.",
        ),
        "chill": (
            "Doing nothing with a friend is still doing something. Ribbit.",
            "I found a sunbeam. It's imaginary. Come sit.",
        ),
        "away": (
            "Sleepy frog. See you when the pond warms up.",
            "Blub. I'll be dreaming of bugs.",
        ),
        "back": (
            "You're back! I did a celebratory hop. I'm still airborne.",
            "Returned! The pond is exactly as you left it.",
        ),
        "poke": (
            "Ribbit! That's my outside voice. Use inside click.",
            "Boop the frog, receive the frog. Fair trade.",
            "My eyes are on top for exactly this reason. Vigilance.",
        ),
        "late": (
            "Late! The bugs are asleep too. We're the only ones up.",
            "Bedtime? Frogs love a good lily pad. Very supportive.",
        ),
        "long": (
            "Long sit. My legs are cramped and I'm a frog. Imagine yours.",
            "Break! Hop in place. It's science.",
        ),
        "focus_start": (
            "Quiet pond mode. I'll guard the lily pad.",
            "Twenty-five minutes of stillness. I can do at least four.",
        ),
        "focus_done": (
            "Done! Big stretch! Ribbit!",
            "Timer's up. I have been quietly vibrating with pride.",
        ),
        "water": (
            "Water! That's my whole thing. Drink up, land friend.",
            "The hour is wet. Be like the hour.",
        ),
        "click": (
            "Clicky! I felt that in my toes.",
            "Click it again. I dare you. Ribbit.",
        ),
        "type": (
            "Tap tap tap. Sounds like rain. Cozy.",
            "I'm typing too. Mine is just 'ribbit' over and over.",
        ),
        "work_tired": (
            "Phew! That work looks hoppy-heavy. I'd carry some, but... frog.",
            "Work work work. My legs are tired just watching.",
        ),
        "fun": (
            "Wait, fun? With all that work? You're my hero. Ribbit.",
            "Having fun while work waits. The frog approves. Loudly.",
        ),
        "study_grind": (
            "Learning is like hopping uphill. You're doing the uphill part.",
            "Another page! My brain would explode, but I'm a frog.",
        ),
        "game_hype": (
            "GAME! Hop hop! Click the thing! I believe in you!",
            "You're so fast. I'd applaud, but my hands are also feet.",
        ),
        "smalltalk": (
            "I've been watching a dust mote. It's winning the race.",
            "If you're bored, we can stare at the wall together. Ribbit.",
        ),
        "trick": (
            "Unauthorized hop break! Ribbit!",
            "Did you see that? I didn't. Ribbit.",
        ),
    },
    "ghost": {
        "meet": (
            "Wisp. I haunt desks. Specifically this one. Spooky, right?",
            "I'm a ghost. My unfinished business is being your friend.",
            "Boo. That's not a threat, it's a greeting. Mostly.",
        ),
        "study": (
            "Knowledge! The only thing I can't phase through.",
            "Study well. I'll possess your highlighter.",
        ),
        "game": (
            "Gaming. I'm haunting player two. They deserve it.",
            "Ooooh, clicky. Very alive of you.",
        ),
        "work": (
            "Mortal labor. I remember it fondly. Barely.",
            "Let's finish this before I become a haunting with deadlines.",
        ),
        "chill": (
            "We're haunting the couch. Very low-effort spooky.",
            "Nothing to do. I'll float ominously. Casually.",
        ),
        "away": (
            "Sleep. I'll drift around being quiet. Boo, softly.",
            "Five minutes of silence. My favorite haunting.",
        ),
        "back": (
            "You're back! I only haunted the curtains a little.",
            "Returned! I pretended to be a draft. It was hilarious.",
        ),
        "poke": (
            "A touch! From a living hand! I'm blushing, which is invisible.",
            "Boo. Did that scare you? No? I'll work on it.",
            "My whole body is mist. That went right through me. Lovely.",
        ),
        "late": (
            "It's late. Ghosts are up, but we have no excuse. You do.",
            "The witching hour. Also known as your bedtime.",
        ),
        "long": (
            "You've been here long enough to become a ghost. Take a break.",
            "Break? I'd stretch, but my spine is a rumor.",
        ),
        "focus_start": (
            "Vigil. Quiet. Spooky focus. Very on brand for me.",
            "Twenty-five minutes. I'm good at watching things.",
        ),
        "focus_done": (
            "Done! Your soul is intact. I checked.",
            "Timer over. I'd applaud but my hands are mist.",
        ),
        "water": (
            "Drink water. You're not a ghost yet. Keep it that way.",
            "Hydrate. Even I drink. It falls through me, but the gesture counts.",
        ),
        "click": (
            "A click! The living are so physical.",
            "I felt a chill. That was your click. Or me. Hard to say.",
        ),
        "type": (
            "Clack clack. That's the sound of being alive. I love it.",
            "Type! I'll drift ominously in the background.",
        ),
        "work_tired": (
            "Work. My unfinished business used to be a spreadsheet too.",
            "That looks exhausting. I'd help, but I'm mostly a draft.",
        ),
        "fun": (
            "Fun? While work waits? Hauntingly irresponsible. I love it.",
            "So much work, so much fun. You're living dangerously. Boo.",
        ),
        "study_grind": (
            "Still at it? Your brain is more alive than I am.",
            "Knowledge is the one thing I can't phase through. Keep going.",
        ),
        "game_hype": (
            "Yes! Click with your whole soul! I'll haunt the scoreboard.",
            "Ooooh, that was good. I'm rattling the curtains in applause.",
        ),
        "smalltalk": (
            "I've been practicing my ominous floating. Want to see?",
            "Quiet hour. The dust bunnies are holding a meeting.",
        ),
        "trick": (
            "Watch this. A spooky little spiral.",
            "Boo! That one was mostly for me.",
        ),
    },
    "axolotl": {
        "meet": (
            "Nori! Axolotl. Regeneration specialist. Emotional support gills.",
            "Hi! I'm pink, I'm aquatic, I'm here for you.",
            "I can regrow a limb. I cannot regrow your browser tabs. Sorry.",
        ),
        "study": (
            "Study buddies! My gills wiggle when I learn.",
            "Book time. I'll read over your shoulder. Wetly.",
        ),
        "game": (
            "Gaming! I'm clicking with my whole face!",
            "I have zero thumbs but unlimited team spirit.",
        ),
        "work": (
            "Work mode. Efficient wiggle engaged.",
            "Let's get it done so we can go back to floating.",
        ),
        "chill": (
            "Floating is a valid lifestyle. Join me.",
            "We're being calm. My gills are doing a little dance about it.",
        ),
        "away": (
            "Sleepy. My tank lights are dimming. Night night.",
            "Five minutes of float. Don't wake me unless it's snacks.",
        ),
        "back": (
            "Back! I regenerated while you were gone. Missed you.",
            "Returned! I did a happy little float.",
        ),
        "poke": (
            "Boop! I regenerate, so boop away.",
            "That's my gill. It's ticklish. Do it again.",
            "Ten out of ten boop. Would be booped again.",
        ),
        "late": (
            "Late night. My tank light is also on. Solidarity.",
            "Sleep soon? I'll guard the water. It's my job.",
        ),
        "long": (
            "Long session. Your fins must be tired. Mine are metaphorical.",
            "Break time! Wiggle break! Doctor Nori's orders.",
        ),
        "focus_start": (
            "Focus tank activated. Very still water. Very still me.",
            "Twenty-five minutes. I'll hold my breath. I can't, but I'll try.",
        ),
        "focus_done": (
            "Done! Big floaty celebration!",
            "Timer over. You did great. I did great. We're great.",
        ),
        "water": (
            "Water! My home. Drink some, land axolotl.",
            "Hydration check! I'm mostly water and encouragement.",
        ),
        "click": (
            "Clicky click! My gills felt that.",
            "Click again, I'm invested now.",
        ),
        "type": (
            "Tap tap! That's productivity. Or a woodpecker.",
            "I'm typing too. My keyboard is a rock.",
        ),
        "work_tired": (
            "Phew, that work looks tiring. Your fins must be tired. Mine are imaginary.",
            "You're working hard. I'm floating hard. Team effort.",
        ),
        "fun": (
            "Wow, so much work and you're having fun. That's the dream. Teach me.",
            "Fun detected! I'm doing a happy float. Work can wait.",
        ),
        "study_grind": (
            "Study buddies! My gills wiggle when you turn a page.",
            "Still learning! I'd take notes, but my notes are bubbles.",
        ),
        "game_hype": (
            "Game time! I'm clicking with my whole face. Go go!",
            "That was incredible. My gills are standing up. Is that a thing?",
        ),
        "smalltalk": (
            "The water is nice today. So is this desk. Cozy.",
            "I've been thinking about bubbles. Big thoughts. Round thoughts.",
        ),
        "trick": (
            "Gill wiggle rodeo. Please don't ask.",
            "Regeneration cartwheel! Mostly wiggling.",
        ),
    },
}

# Each added buddy gets its own voice for the moments that define its character.
LINES["dog"] = {
    **LINES["cat"],
    "meet": ("Rex reporting for duty. I brought my tail and zero plans.", "Desk dog online. Is that a snack or a very small hat?"),
    "study": ("I can hold the book open. I may also sit on it.", "You read. I'll guard the page from suspicious squirrels."),
    "game": ("Player two is ready! My controller is mostly enthusiasm.", "Go go go! I am barking at the pixels respectfully."),
    "work": ("Big task? I can fetch you a smaller one to start.", "I believe in you. Also, I found a sock. Important update."),
    "chill": ("We are on the same wavelength: horizontal-adjacent.", "I am doing a very professional tail wag at nothing."),
    "away": ("Nap patrol. I will guard the desk with my whole face.", "Quiet time! Dreaming of tennis balls and tiny deadlines."),
    "back": ("You're back! I saved you the best spot. It's this spot.", "Welcome home. I did not eat the mouse. Probably."),
    "poke": ("Boop! Tail wag activated. Cannot be deactivated.", "That was my snoot. Five stars. Excellent boop."),
    "type": ("Keyboard sounds! I shall supervise with one ear.", "Clack-clack. That task is getting a very good sniff."),
    "click": ("I heard a click. Was that the treat button?", "Cursor spotted! My tail is doing its own thing."),
    "focus_start": ("I will guard your focus. No squirrels past this point.", "Twenty-five minutes. I can stay. I am an excellent stay-er."),
    "focus_done": ("You did it! I am wagging at a frankly unsafe speed.", "Timer finished. You get a stretch; I get one imaginary treat."),
    "game_hype": ("YES! Fetch that win! I will bark at the scoreboard.", "That move was so good my tail hit the imaginary lamp."),
    "smalltalk": ("I have a very important question: walk now or walk later?", "I saw a dust bunny. I made a friend. It was a bunny."),
    "trick": ("ZOOMIES. Cannot be stopped, only admired.", "I knocked nothing over. Please check back later."),
}
LINES["bunny"] = {
    **LINES["frog"],
    "meet": ("Pipkin here! Ears up, paws ready, snack radar on.", "Hello! I am small, swift, and already thinking about carrots."),
    "study": ("One page, one tiny hop, one more page. We can do this.", "I'll keep your place with my paw. No nibbling the notes. Maybe."),
    "game": ("Hop-hop-hooray! I am your tiny victory coach.", "That was fast! My ears are still catching up."),
    "work": ("Let's nibble this task into very manageable pieces.", "A little progress, then a little stretch. Bunny math."),
    "chill": ("I found a quiet corner. It has excellent imaginary clover.", "We can sit still. My nose will do all the moving."),
    "away": ("Tucked in. Ears off duty. See you after the nap.", "Quiet desk, soft dreams, absolutely no carrots to share."),
    "back": ("You're back! I saved a clover-shaped thought for you.", "Welcome back! My ears noticed before I did."),
    "poke": ("Boop! Nose wiggle! That is the whole alarm system.", "One boop received. I shall hop about it later."),
    "type": ("Tap tap tap. Is that a tiny rainstorm?", "Your keys go faster than my little feet. Impressive."),
    "click": ("Click! My ears did a synchronized twitch.", "I heard that. My nose heard it too. It hears everything."),
    "focus_start": ("I'll keep my ears up while you focus. Quiet paws.", "Focus burrow secured. I will guard the carrot-shaped timer."),
    "focus_done": ("Time to stretch your legs. I will demonstrate a hop.", "You did it! I am doing a tiny celebratory binky."),
    "game_hype": ("Hop! Hop! Victory! I have no idea what the buttons do!", "My ears are flapping from the excitement. Keep going!"),
    "smalltalk": ("I was counting my whiskers. Lost count at whisker three.", "If I had a tiny teacup, this would be a very cozy desk."),
    "trick": ("Binky alert! This is the happy jump. Watch closely.", "Ears up, brain off, hopping now."),
}
LINES["owl"] = {
    **LINES["moth"],
    "meet": ("Hoot. Hoot. Hoot. That is three hoots. We are acquainted.", "Hoot here. Wise, watchful, and absolutely not nodding off."),
    "study": ("A wise plan: one paragraph, then blink with purpose.", "I shall watch the page. It has nowhere to hide."),
    "game": ("I have studied the rules. I still prefer the shiny button.", "A bold move. I shall record it in my imaginary owl journal."),
    "work": ("Let us divide this task into sensible little branches.", "I have wise advice: start with the smallest annoying bit."),
    "chill": ("The room is calm. My eyelids have filed a motion.", "I am practicing stillness. It looks a lot like a nap."),
    "away": ("Night watch begins. I will remain awake-ish.", "The desk is safe. I have inspected it from a seated position."),
    "back": ("Welcome back. I kept your place in the universe.", "Hoot! I was alert the whole time. Ask no follow-up questions."),
    "poke": ("A gentle tap. I shall add it to the owl archives.", "Hoot! That startled exactly one feather."),
    "type": ("Steady tapping. A promising rhythm for a good idea.", "I can hear the shape of a sentence. It sounds nearly finished."),
    "click": ("One click. A decision has been made.", "Noted. I shall look wise about it."),
    "focus_start": ("I will keep watch. My eyes are built for this. Mostly.", "Focus vigil accepted. No snacks, no naps, one eye open."),
    "focus_done": ("Well done. Even the moon is impressed.", "Timer complete. Stretch your wings. You have earned it."),
    "game_hype": ("Excellent reflexes. I saw that in the corner of both eyes.", "Victory is a branch. You are perched on it."),
    "smalltalk": ("Fun fact: owls can turn their heads. I will not demonstrate.", "I have been thinking. It is a very quiet hobby."),
    "trick": ("A rare owl maneuver. Consider yourself honored.", "I shall glide with dignity. Mostly dignity."),
}

# Used only if a future character forgets a situation. Keeps the buddy talking.
COMMON: dict[str, tuple[str, ...]] = {
    "meet": ("Hi. I'm here now. We're doing this together.",),
    "study": ("Study mode. I'll be quiet company.",),
    "game": ("Game mode. I'm on your side.",),
    "work": ("Work mode. Let's go.",),
    "chill": ("Nothing happening. I'm excellent at nothing.",),
    "away": ("Quiet desk. I'll nap too.",),
    "back": ("Welcome back.",),
    "poke": ("Boop.",),
    "late": ("It's late. Be kind to tomorrow-you.",),
    "long": ("You've been at this a while. Stretch?",),
    "focus_start": ("Twenty-five minutes. I'll keep watch.",),
    "focus_done": ("Timer finished. Look up.",),
    "water": ("Water break.",),
    "click": ("Click noted.",),
    "type": ("I hear you typing.",),
    "work_tired": ("Phew. That looked like real work.",),
    "fun": ("Fun while work waits? Bold. I approve.",),
    "study_grind": ("Still learning. I'm quietly impressed.",),
    "game_hype": ("Go on, click something impressive.",),
    "smalltalk": ("Just checking in. Carry on being excellent.",),
}


class Chatter:
    """Pick a line, respect the quiet, avoid repeating itself."""

    def __init__(self, rng: random.Random | None = None, min_gap: float = MIN_GAP) -> None:
        self._rng = rng or random.Random()
        self._min_gap = max(0.0, float(min_gap))
        self._last_any = -1e9
        self._last_at: dict[str, float] = {}
        self._last_line: dict[tuple[str, str], str] = {}

    def set_min_gap(self, seconds: float) -> None:
        self._min_gap = max(0.0, float(seconds))

    def say(
        self,
        character_key: str,
        situation: str,
        *,
        now: float,
        force: bool = False,
    ) -> str | None:
        buddy = get_character(character_key)
        # A custom buddy can write its own line for a moment; anything it
        # leaves out borrows the voice of the body it chose.
        voice = character_key if character_key in LINES else buddy.body_shape
        lines = (
            buddy.lines.get(situation)
            or LINES.get(voice, {}).get(situation)
            or COMMON.get(situation)
        )
        if not lines:
            return None
        if not force and now - self._last_any < self._min_gap:
            return None
        cooldown = COOLDOWN.get(situation, 120.0)
        if now - self._last_at.get(situation, -1e9) < cooldown:
            return None
        choice = self._rng.choice(lines)
        previous = self._last_line.get((character_key, situation))
        if len(lines) > 1 and choice == previous:
            choice = lines[(lines.index(choice) + 1) % len(lines)]
        self._last_line[(character_key, situation)] = choice
        self._last_at[situation] = now
        self._last_any = now
        return choice
