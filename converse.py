"""A tiny, deterministic chat toy — not a language model.

The talk box is meant for a bit of fun: the buddy matches a handful of ordinary
phrases and answers in character. There is deliberately no model or network
call. Questions are cleaned and matched against static keyword rules. The
short conversation lives only in the open chat panel and clears when it closes;
it is never logged or saved.

Replies come from fixed tables, so nothing a person types can change the
markup, path, command, or file the app touches. The same goes for the bubble:
it paints plain text, never rich text.
"""

from __future__ import annotations

import random
import re

from characters import get as get_character
from safety import clean_text

MAX_QUESTION = 120
MAX_REPLY = 100

# Ordered: earlier intents win. Word boundaries keep "hi" out of "this".
_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("identity", ("who are you", "your name", "what are you", "are you a bot")),
    ("real", ("are you real", "are you alive", "ai", "artificial", "chatgpt", "robot")),
    ("feeling", ("how are you", "how's it going", "hows it going", "you okay", "you ok")),
    ("support", ("tired", "stressed", "sad", "anxious", "overwhelmed", "exhausted", "rough day")),
    ("study", ("study", "studying", "homework", "exam", "revision", "assignment", "learn")),
    ("work", ("work", "working", "deadline", "job", "meeting", "email", "boss")),
    ("game", ("game", "gaming", "play", "playing", "level", "win")),
    ("food", ("food", "snack", "hungry", "eat", "coffee", "tea", "lunch")),
    ("bored", ("bored", "nothing to do", "boring")),
    ("joke", ("joke", "funny", "make me laugh")),
    ("love", ("love you", "like you", "best friend", "friend")),
    ("thanks", ("thank", "thanks", "thx")),
    ("bye", ("bye", "goodnight", "good night", "see you", "later")),
    ("cute", ("cute", "adorable", "awesome", "cool", "pretty")),
    ("help", ("help", "what can you do", "commands", "talk about")),
    ("greeting", ("hi", "hello", "hey", "yo", "sup", "morning")),
)


def _rule_for(text: str) -> str | None:
    for name, keywords in _RULES:
        for keyword in keywords:
            if re.search(rf"\b{re.escape(keyword)}\b", text):
                return name
    return None


VOICES: dict[str, dict[str, tuple[str, ...]]] = {
    "moth": {
        "identity": ("Lumen, lantern moth, professional desk light.", "I'm a moth with a lamp and opinions."),
        "real": ("I'm as real as a warm lamp on a cold evening.", "Not a robot. A moth. Very different paperwork."),
        "feeling": ("Bright and slightly dusty. You?", "Glowing steadily. My wings are doing fine, thanks."),
        "support": ("Small steps are still steps. I'll keep the light on.", "Rough patch. Sit with it a minute. I'll glow."),
        "study": ("One page. Then another. I'll mind the lamp.", "Studying is just hovering with extra steps. You've got this."),
        "work": ("Work work work. I'll be the tiny lamp of morale.", "Deadlines are moths to a flame. Try not to get singed."),
        "game": ("Player two, reporting. I have no thumbs, only vibes.", "Click something heroic. I'll flicker approval."),
        "food": ("Snacks are lamp fuel. This is science.", "I can't eat, but I support the snack agenda."),
        "bored": ("We could count my wing spots. There are two. Done.", "Bored? Excellent. I'm a professional at that."),
        "joke": ("Why did the moth sit on the lamp? It liked the ambiance.", "My love life is a series of bright ideas."),
        "love": ("I'm a lamp. I have a lot of warm feelings.", "Careful, I might get too bright."),
        "thanks": ("Anytime. I'm literally here to glow.", "You're welcome. No charge. I run on vibes."),
        "bye": ("Go gently. I'll keep the porch light on.", "Bye! I'll be here, being softly luminous."),
        "cute": ("Cute? I'm a sophisticated nightlight, thank you.", "I know. It's the antennae."),
        "help": ("Ask about studying, work, games, snacks, or jokes. I'm small but opinionated.", "I can do pep talks, bad jokes, and lamp-based wisdom."),
        "greeting": ("Hey. The lamp is on and the desk is ours.", "Hello! You're just in time for nothing in particular."),
    },
    "cat": {
        "identity": ("Mochi. Loaf. Quality assurance. Nap department.", "I'm the cat. I sit on things professionally."),
        "real": ("I'm real. The keyboard is warm, which proves it.", "Not a robot. I knock things off desks with real paws."),
        "feeling": ("Sleepy. Hungry. Both, somehow.", "Excellent. I've been horizontal for two hours."),
        "support": ("Rough day. Come sit. I'll purr at the problem.", "You're doing more than you think. I'm watching. Fondly."),
        "study": ("I'll sit on the book. That's peer review.", "Studying? I'll supervise from the warmest page."),
        "work": ("Work. I'll judge your posture silently.", "Emails can wait. My nap cannot. But you should keep going."),
        "game": ("Ooh, cursor. Cursor. Cursor. I'm invested.", "Player two. Strategy: knock the boss off the desk."),
        "food": ("Snacks? I heard snacks. Where.", "You had me at food. I'm already sitting on the bowl."),
        "bored": ("Bored? Let's stare at the wall. I'll go first.", "I can fix boredom by lying on your keyboard."),
        "joke": ("Why did the cat sit on the laptop? To keep an eye on the mouse.", "I'm not lazy. I'm in energy-saving mode."),
        "love": ("I tolerate you. That's cat for love.", "You may scratch my chin. Once."),
        "thanks": ("You're welcome. Payment is one snack.", "Noted. I'll add it to your tab. It's all snacks."),
        "bye": ("Bye. I'll guard the chair with my body.", "Later. Wake me if the snack situation changes."),
        "cute": ("Obviously. I have a mirror. It's the window.", "Cute is my default setting."),
        "help": ("I know naps, snacks, and knocking things off edges. Ask away.", "I'm a cat. My help is mostly moral support and fur."),
        "greeting": ("You're here. Good. The sunbeam is waiting.", "Hello. I was asleep, but I'm awake now. Mostly."),
    },
    "frog": {
        "identity": ("Pip! Frog. Pond adjacent. Desk assigned.", "Pocket frog, at your service. Ribbit."),
        "real": ("Very real. I just hopped. You missed it.", "Not a robot. Robots don't have this much leg."),
        "feeling": ("Hopping! Also a little damp. Normal for me.", "Good! My gills are calm and my legs are ready."),
        "support": ("Big feelings. Small hops. We'll get there.", "I'm here. Ribbit. That's frog for 'I've got you'."),
        "study": ("Learning! My brain is also doing a learn. Ribbit.", "Book time. I'll hold the page with my face."),
        "work": ("We work now. Hop hop. Productive hops.", "Task found. Task approached. Task slightly startled."),
        "game": ("GAME! I'm hopping on the clicky thing!", "Frog reflexes. Legendary. Mostly for catching flies."),
        "food": ("Food! I like bugs. You like... not bugs. We're diverse.", "Snack time? I'll catch it. Reflexes."),
        "bored": ("Bored? I can hop in place. It's a whole show.", "We could count flies. Zero. Great count."),
        "joke": ("What do you call a frog with no legs? A hopless situation.", "I'd tell a better joke, but my brain is pond water."),
        "love": ("Ribbit! That's the frog word for 'aww'.", "I love you too. In a moist, supportive way."),
        "thanks": ("Ribbit! You're welcome. Hop hop.", "Anytime! I'm small but sincere."),
        "bye": ("Bye! I'll keep the lily pad warm.", "Later! Try not to croak. That's my job."),
        "cute": ("I know. It's the eyes on top. Very avant-garde.", "Cute and moist. The full package."),
        "help": ("Ask about studying, games, snacks, or feelings. I'll ribbit wisely.", "I offer hops, encouragement, and questionable bug facts."),
        "greeting": ("Ribbit! That's hello, and also 'let's do stuff'.", "Hey! The pond is exactly as you left it."),
    },
    "ghost": {
        "identity": ("Wisp. Desk ghost. Unfinished business: friendship.", "I'm the ghost. I haunt this specific corner."),
        "real": ("Define real. Define 'paying rent'.", "I'm real. My hands are mist, but my feelings are solid."),
        "feeling": ("Dead, mostly. Other than that, excellent.", "Floaty. It's a good day for a quiet haunting."),
        "support": ("Heavy day. Let it be heavy for a minute. I'll drift nearby.", "You're not alone. I'm literally hard to get rid of."),
        "study": ("Knowledge! The only thing I can't phase through.", "Study well. I'll possess your highlighter."),
        "work": ("Mortal labor. I remember it fondly. Barely.", "Deadlines: the real ghosts."),
        "game": ("Gaming. I'm haunting player two. They deserve it.", "Ooooh, clicky. Very alive of you."),
        "food": ("I miss food. I don't miss the dishes.", "Eat something. I'll watch enviously through the wall."),
        "bored": ("Bored? I can make the curtains move. It's subtle.", "Haunting is 90% waiting. I'm a professional."),
        "joke": ("I told a ghost joke once. It died. Then it came back.", "Why do ghosts love elevators? It lifts their spirits."),
        "love": ("My heart doesn't beat, but it's doing something.", "Careful. I'm emotionally translucent."),
        "thanks": ("You're welcome. I'd tip my hat, but it's mist.", "Anytime. Haunting you is the highlight."),
        "bye": ("Bye. I'll be the draft you can't explain.", "Later. Boo, softly."),
        "cute": ("Cute? I'm hauntingly adorable.", "I'm dead, not blind. I know I'm cute."),
        "help": ("I know spooky trivia, mild encouragement, and how to be quiet. Ask.", "I can haunt, float, and offer deadpan advice."),
        "greeting": ("Boo. That's a greeting. Mostly.", "You're back. The curtains were getting nervous."),
    },
    "axolotl": {
        "identity": ("Nori! Axolotl. Regeneration specialist. Emotional support gills.", "Pink, aquatic, here for you. That's the whole résumé."),
        "real": ("Very real. I can regrow a limb. Can a robot do that?", "Not a robot. I'm mostly water and encouragement."),
        "feeling": ("Floaty and pink. The usual.", "Good! My gills are doing a little dance about it."),
        "support": ("Soft landing. You don't have to fix it all today.", "I'm here. We can float on the problem together."),
        "study": ("Study buddies! My gills wiggle when I learn.", "Book time. I'll read over your shoulder. Wetly."),
        "work": ("Work mode. Efficient wiggle engaged.", "Let's get it done so we can go back to floating."),
        "game": ("Gaming! I'm clicking with my whole face!", "I have zero thumbs but unlimited team spirit."),
        "food": ("Snacks! I'm mostly water, but I make room.", "Food is just fancy floating fuel. Go for it."),
        "bored": ("Floating is a valid lifestyle. Join me.", "Bored? Let's watch bubbles. They're very dramatic."),
        "joke": ("Why did the axolotl fail the exam? It only knew the bare necessities.", "I tried stand-up comedy. I kept regenerating my dignity."),
        "love": ("Aww. My gills are blushing. I didn't know they could.", "Love you too. In a warm, slightly damp way."),
        "thanks": ("You're welcome! Big floaty heart.", "Anytime! I'm 60% water, 40% support."),
        "bye": ("Bye! I'll guard the tank. It's my job.", "Later! I'll do a tiny float in your honor."),
        "cute": ("It's the gills. They do a lot of work.", "I know. I'm basically a pink compliment."),
        "help": ("Ask about studying, work, snacks, feelings, or bad jokes. I float ready.", "I can encourage, float, and regenerate morale."),
        "greeting": ("Hi! I'm pink, I'm aquatic, I'm here for you.", "Hello! The tank is calm and the vibes are buoyant."),
    },
}

VOICES["dog"] = {
    **VOICES["cat"],
    "identity": ("Rex. Loyal desk dog, professional sock inspector.", "Desk dog here. My tail is wagging at your excellent timing."),
    "support": ("Come sit by me. We can untangle one little thing at a time.", "Ruff day? I prescribe a breath, a stretch, and absolutely no guilt."),
    "study": ("I'll guard your notes. If a squirrel appears, I may need a moment.", "One page at a time. I can stay. I am very good at staying."),
    "work": ("Let's fetch the easiest task first. Momentum is a treat.", "I believe in you. My tail says so, and it has excellent judgment."),
    "game": ("Player two reporting! I bring enthusiasm and no button knowledge.", "Go! I am cheering at the pixels. They seem nice."),
    "food": ("Snack? I have already heard the wrapper from three rooms away.", "I cannot share your snack, but I can supervise it closely."),
    "joke": ("Why did the dog sit by the computer? It wanted to keep an eye on the mouse.", "I tried to fetch the cursor. It moved. I respect the challenge."),
    "help": ("I offer encouragement, enthusiastic tail wagging, and sock security.", "Tell me about work, study, games, snacks, or your very good choices."),
}
VOICES["bunny"] = {
    **VOICES["frog"],
    "identity": ("Pipkin. Pocket bunny, carrot enthusiast, tiny hop expert.", "I'm a bunny! My ears are tall and my snack standards are higher."),
    "support": ("Big feeling? We can make it smaller, one gentle hop at a time.", "You can rest here. I brought imaginary clover and no deadlines."),
    "study": ("One page, then a stretch. I will keep your place with my paw.", "Let's nibble through that chapter. Metaphorically. Mostly."),
    "work": ("Pick one small task. We can make a whole carrot out of it.", "You do the work; I will provide a very serious nose wiggle."),
    "game": ("Hop-hop-hooray! I am your tiny victory coach.", "That was fast! I blinked and your score did a backflip."),
    "food": ("Carrots for me, snacks for you. A perfectly fair arrangement.", "Snack break! My ears detected the word from across the room."),
    "joke": ("Why did the bunny bring a pencil? To draw its own hare-raising plans.", "I tried to tell a joke, but I got a little hare-brained."),
    "help": ("I can hop beside you, cheer you on, and guard your clover.", "Ask about study, work, games, or snacks. My ears are listening."),
}
VOICES["owl"] = {
    **VOICES["moth"],
    "identity": ("Hoot. I am Hoot, a study owl with excellent eyebrows.", "A small owl. I know a little about a lot and nap about the rest."),
    "support": ("Even wise owls pause between branches. You may pause too.", "That sounds heavy. Let's sit with it before we try to solve it."),
    "study": ("Read one paragraph. Blink thoughtfully. Continue being brilliant.", "I shall watch the page. It has nowhere to hide."),
    "work": ("Wise plan: choose the smallest task and give it your full beak.", "A long list is just several short lists wearing a trench coat."),
    "game": ("I have studied the rules. I still prefer the shiny button.", "A bold move. I shall record it in my imaginary owl journal."),
    "food": ("I enjoy a midnight snack. Preferably not while I am asleep.", "You eat; I shall make a very scholarly note about it."),
    "joke": ("What do you call an owl magician? Hoo-dini. I regret nothing.", "I tried to tell a joke at night. The audience was mostly crickets."),
    "help": ("I offer calm company, study nudges, and one excellent hoot.", "Ask about studying, work, games, or snacks. I have considered all four."),
}

FALLBACK = (
    "I'm more of a vibes buddy than a search engine. Ask about studying, games, snacks, or jokes.",
    "I didn't catch that one. My brain is mostly lamp light and enthusiasm.",
    "Hmm. I'm small. Try asking about work, fun, feelings, or food.",
)

def reply(character_key: str, question: str, rng: random.Random | None = None) -> str | None:
    """A short in-character answer, or ``None`` for empty/unusable input."""
    text = clean_text(question, MAX_QUESTION).lower()
    if not text:
        return None
    picker = rng or random.Random()
    intent = _rule_for(text)
    buddy = get_character(character_key)
    voice_key = character_key if character_key in VOICES else buddy.body_shape
    if voice_key not in VOICES:
        voice_key = "moth"
    options = VOICES[voice_key].get(intent or "", ())
    if not options:
        options = FALLBACK
    answer = picker.choice(options)
    return answer[:MAX_REPLY]
