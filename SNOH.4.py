import math
import random
import pygame

pygame.init()

WIDTH, HEIGHT = 900, 700
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("MAJA GAME")
clock = pygame.time.Clock()

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

font = pygame.font.Font(None, 40)
big_font = pygame.font.Font(None, 70)
small_font = pygame.font.Font(None, 30)
pixel_font = pygame.font.Font(None, 16)  # tiny font, scaled up for the pixel look
# comic-style font for the speech bubble (falls back to a normal font if missing)
comic_font = pygame.font.SysFont("comicsansms,comic sans ms,arial", 44, bold=True)


def load_image(filename, size, fallback_color):
    """Load and scale a sprite. If the file is missing, use a plain
    colored square so the game still runs."""
    try:
        img = pygame.image.load(filename).convert_alpha()
    except (FileNotFoundError, pygame.error):
        print("Couldn't find", filename)
        img = pygame.Surface(size)
        img.fill(fallback_color)
        return img
    return pygame.transform.scale(img, size)


# --- images ---------------------------------------------------------

snow_bg = load_image("snow day.jpeg", (WIDTH, HEIGHT), (200, 220, 255))
snow_sky = load_image("snow sky.jpeg", (WIDTH, HEIGHT), (170, 200, 240))
fire_bg = load_image("fire sky.jpeg", (WIDTH, HEIGHT), (120, 30, 10))
boss_bg = load_image("fire boss.jpeg", (WIDTH, HEIGHT), (90, 10, 0))

PLAYER_SIZE = (100, 100)
male_img = load_image("snowman.png", PLAYER_SIZE, (230, 230, 255))
female_img = load_image("snowwoman.png", PLAYER_SIZE, (255, 200, 230))
player_img = male_img

snowball_img = load_image("snowball.png", (24, 24), WHITE)

# Two enemy types. Change the numbers here to tune the difficulty.
enemy_types = [
    {"image": load_image("firedude.png", (80, 80), (255, 100, 0)),
     "health": 1, "speed": 3, "points": 1},
    {"image": load_image("firedude2.png", (110, 110), (255, 160, 0)),
     "health": 2, "speed": 2, "points": 2},
]

# The boss is firedude2 blown up to just under half the screen
BOSS_SIZE = (330, 330)
boss_img = load_image("firedude2.png", BOSS_SIZE, (255, 160, 0))

# fireball the boss shoots (drawn with circles so no extra image is needed)
fireball_img = pygame.Surface((30, 30), pygame.SRCALPHA)
pygame.draw.circle(fireball_img, (255, 90, 0), (15, 15), 15)
pygame.draw.circle(fireball_img, (255, 220, 0), (15, 15), 8)


# --- levels ---------------------------------------------------------
# goal = points needed to finish the level
# bonus = extra speed added to every enemy in that level
# heavy = % chance that an enemy is the tougher firedude2 (2 hits to kill)
# After the last level the boss fight starts.
LEVELS = [
    {"goal": 30, "bonus": 1, "heavy": 40},
    {"goal": 35, "bonus": 2, "heavy": 55},
]

# --- boss settings --------------------------------------------------
BOSS_HEALTH = 50
BOSS_STOP_X = WIDTH - BOSS_SIZE[0] - 20   # where the boss stops after entering
BOSS_SPEED = 3                            # up/down speed
BOSS_RAGE_SPEED = 5                       # up/down speed at 25% health or less
BOSS_SHOOT_DELAY = 75                     # frames between fireballs
BOSS_RAGE_SHOOT_DELAY = 40                # frames between fireballs at 25% health or less
BOSS_RAGE_HEALTH = BOSS_HEALTH // 4       # rage starts at this much health (12)
FIREBALL_SPEED = 7
MINION_BONUS = 1                          # how much faster the boss's little helpers are

# --- shooting -------------------------------------------------------
SHOOT_COOLDOWN = 300   # milliseconds between snowballs (0.3 seconds)

# --- playtesting ----------------------------------------------------
# Press | (or the backslash key) to skip: level -> next level, last level -> boss,
# boss -> ending. Set this to False when you're done testing.
DEV_KEYS = True


# --- pixel 3D text --------------------------------------------------

def pixel_text(text, color, shadow, scale, depth):
    """Render chunky pixel text with a stacked shadow behind it for the 3D look."""
    front = pixel_font.render(text, False, color).convert_alpha()
    back = pixel_font.render(text, False, shadow).convert_alpha()
    w, h = front.get_size()
    front = pygame.transform.scale(front, (w * scale, h * scale))
    back = pygame.transform.scale(back, (w * scale, h * scale))

    surf = pygame.Surface((w * scale + depth, h * scale + depth), pygame.SRCALPHA)
    for i in range(depth, 0, -1):
        surf.blit(back, (i, i))
    surf.blit(front, (0, 0))
    return surf


def pixel_line(segments, scale=2, depth=4):
    """A line made of (text, color, shadow) pieces, so one word can have its own color."""
    parts = [pixel_text(t, c, s, scale, depth) for t, c, s in segments]
    width = sum(p.get_width() - depth for p in parts) + depth
    line = pygame.Surface((width, parts[0].get_height()), pygame.SRCALPHA)
    x = 0
    for p in parts:
        line.blit(p, (x, 0))
        x += p.get_width() - depth
    return line


YELLOW = (255, 220, 0)
YELLOW_DARK = (160, 100, 0)
RED = (235, 40, 40)
RED_SHADOW = (90, 0, 0)
DARK_RED = (130, 0, 0)
DARK_RED_SHADOW = (30, 0, 0)
GRAY_SHADOW = (90, 90, 90)
BLUE_SHADOW = (20, 40, 90)

# build all the story text once so we don't re-render it every frame
title_intro = [
    pixel_line([("You lived in a peaceful", WHITE, BLUE_SHADOW)]),
    pixel_line([("village called", WHITE, BLUE_SHADOW)]),
]
title_letters = [pixel_text(c, YELLOW, YELLOW_DARK, 6, 6) for c in "SNOWLANDIA"]

attack_lines = [
    pixel_line([("One Terrible Night,", RED, RED_SHADOW)]),
    pixel_line([("The Furies entered your village", RED, RED_SHADOW)]),
    pixel_line([("and ", RED, RED_SHADOW),
                ("destroyed", DARK_RED, DARK_RED_SHADOW),
                (" it.", RED, RED_SHADOW)]),
]

hidden_lines = [
    pixel_line([("You were hidden by your family,", WHITE, GRAY_SHADOW)]),
    pixel_line([("and after the chaos was finished,", WHITE, GRAY_SHADOW)]),
    pixel_line([("You emerge out...", WHITE, GRAY_SHADOW)]),
]

# text for the cutscene after each level
congrats_letters = [pixel_text(c, YELLOW, YELLOW_DARK, 6, 6) for c in "Congrats"]
levelup_lines = [
    pixel_line([("on defeating the boss,", WHITE, BLUE_SHADOW)]),
    pixel_line([("Keep moving forward", WHITE, BLUE_SHADOW)]),
]

# game over screen text
gameover_text = pixel_text("GAME OVER", RED, RED_SHADOW, 10, 8)
restart_text = pixel_line([("Press R to play again", WHITE, GRAY_SHADOW)])

# the ending text needs the player's name, so it is built after the boss dies
ending_line = None
ending_big = pixel_text("Was It Worth it?", WHITE, GRAY_SHADOW, 6, 6)

# the comic speech bubble text
bubble_text = comic_font.render("I am Inevitable", True, BLACK)

# frames = how long the scene lasts (60 frames = 1 second)
scenes = [
    {"kind": "title", "frames": 300},
    {"kind": "attack", "frames": 360},
    {"kind": "hidden", "frames": 330},
    {"kind": "emerge", "frames": 300,
     "text": "You realise that your village, your family and everyone you knew were no more."},
    {"kind": "emerge", "frames": 420,
     "text": "You seeked to avenge the fallen. You wanted the people who had "
             "destroyed everything you loved and knew dead."},
    # text is filled in once the player has picked a character
    {"kind": "emerge", "frames": 300, "text": ""},
]

LEVELUP_FRAMES = 270
ENDING_FRAMES = 480
INEVITABLE_FRAMES = 270


# --- game state -----------------------------------------------------

# start -> gender -> dialogue -> story -> game -> levelup -> ... -> boss
#       -> ending -> inevitable -> gameover      (death can happen in game or boss)
state = "start"

player_name = ""
gender = ""

PLAYER_START = (50, (HEIGHT - PLAYER_SIZE[1]) // 2)
player = pygame.Rect(*PLAYER_START, *PLAYER_SIZE)
player_speed = 5

bullets = []
bullet_speed = 7
last_shot = 0   # time (ms) of the last snowball, for the cooldown

score = 0
high_score = 0
level = 0                 # index into LEVELS
death_return = "game"     # where "R" sends you after dying: "game" or "boss"

# boss fight stuff
boss = {}
fireballs = []
minions = []

# menu boxes are placed from the screen size, so they stay centered
start_box = pygame.Rect(0, 0, 500, 100)
start_box.center = (WIDTH // 2, HEIGHT // 2)

gender_box = pygame.Rect(0, 0, 440, 180)
gender_box.center = (WIDTH // 2, HEIGHT // 2)
male_button = pygame.Rect(0, 0, 120, 50)
male_button.center = (gender_box.centerx - 100, gender_box.centery + 40)
female_button = pygame.Rect(0, 0, 120, 50)
female_button.center = (gender_box.centerx + 100, gender_box.centery + 40)

dialogue_box = pygame.Rect(50, HEIGHT - 200, WIDTH - 100, 150)
story_box = pygame.Rect(40, HEIGHT - 190, WIDTH - 80, 150)

dialogues = []
dialogue_index = 0
shown_text = ""
text_timer = 0
text_speed = 2  # higher = slower typing

story_index = 0
story_timer = 0
cut_timer = 0   # timer for the level-up, ending, bubble and game over screens
game_fade = 0   # counts down after a cutscene so the game fades in

FADE_FRAMES = 30


def spawn_enemy(x=WIDTH, bonus=None, heavy=None):
    """Make a new enemy. Speed and chance of a tough one depend on the level
    unless a bonus / heavy chance is given."""
    if bonus is None:
        bonus = LEVELS[level]["bonus"]
    if heavy is None:
        heavy = LEVELS[level]["heavy"]
    kind = random.choices(enemy_types, weights=[100 - heavy, heavy])[0]
    size = kind["image"].get_size()
    rect = pygame.Rect(x, random.randint(0, HEIGHT - size[1]), *size)
    return {"rect": rect, "image": kind["image"], "health": kind["health"],
            "speed": kind["speed"] + bonus, "points": kind["points"]}


enemy = spawn_enemy()


def reset_game():
    """Restart the current level from 0 points."""
    global enemy, score
    score = 0
    player.topleft = PLAYER_START
    bullets.clear()
    enemy = spawn_enemy()


def init_boss():
    """Set up a fresh boss fight."""
    boss["rect"] = pygame.Rect(WIDTH, (HEIGHT - BOSS_SIZE[1]) // 2, *BOSS_SIZE)
    boss["health"] = BOSS_HEALTH
    boss["dir"] = 1
    boss["entered"] = False
    boss["shoot_timer"] = 90
    boss["minion_timer"] = random.randint(300, 480)
    fireballs.clear()
    minions.clear()
    bullets.clear()
    player.topleft = PLAYER_START


def full_restart():
    """Back to level 1 after the game over screen."""
    global level, state, game_fade
    level = 0
    reset_game()
    game_fade = FADE_FRAMES
    state = "game"


def finish_levelup():
    """Called when the level cutscene ends: next level, or the boss after level 3."""
    global level, state, game_fade
    if level < len(LEVELS) - 1:
        level += 1
        reset_game()
        state = "game"
    else:
        init_boss()
        state = "boss"
    game_fade = FADE_FRAMES


def skip_level():
    """Playtesting shortcut (the | key)."""
    if state in ("game", "levelup"):
        finish_levelup()   # next level, or the boss after the last level
    elif state == "boss":
        start_ending()


def start_ending():
    """The boss just died: build the ending text with the player's name."""
    global ending_line, state, cut_timer
    ending_line = pixel_line([
        ("You finally killed the Head of the Furies, ", WHITE, GRAY_SHADOW),
        (player_name, YELLOW, YELLOW_DARK),
        (".", WHITE, GRAY_SHADOW),
    ])
    fireballs.clear()
    minions.clear()
    bullets.clear()
    cut_timer = 0
    state = "ending"


def draw_text(text, fnt, color, x, y):
    screen.blit(fnt.render(text, True, color), (x, y))


def draw_text_center(text, fnt, color, cx, cy):
    surf = fnt.render(text, True, color)
    screen.blit(surf, surf.get_rect(center=(cx, cy)))


def draw_centered(surf, y, dx=0, dy=0):
    screen.blit(surf, ((WIDTH - surf.get_width()) // 2 + dx, y + dy))


def draw_faded(surf, y, alpha):
    """Draw a centered surface at a given opacity (0-255)."""
    copy = surf.copy()
    copy.set_alpha(max(0, min(255, int(alpha))))
    draw_centered(copy, y)


def draw_bouncing(letters, t, y):
    """Letters that bounce, each one a little later than the one before it."""
    total = sum(l.get_width() - 6 for l in letters) + 6
    x = (WIDTH - total) // 2
    for i, letter in enumerate(letters):
        bounce = math.sin(t * 0.12 + i * 0.6) * 14
        screen.blit(letter, (x, y + bounce))
        x += letter.get_width() - 6


def wrap_text(text, fnt, max_width):
    lines, current = [], ""
    for word in text.split():
        test = (current + " " + word).strip()
        if fnt.size(test)[0] <= max_width:
            current = test
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def fade_overlay(alpha):
    if alpha <= 0:
        return
    cover = pygame.Surface((WIDTH, HEIGHT))
    cover.set_alpha(min(255, int(alpha)))
    screen.blit(cover, (0, 0))  # surface is black by default


def scene_fade(t, frames):
    """Fade in at the start and out at the end of a scene."""
    if t < FADE_FRAMES:
        fade_overlay(255 * (1 - t / FADE_FRAMES))
    elif t > frames - FADE_FRAMES:
        fade_overlay(255 * (1 - (frames - t) / FADE_FRAMES))


def next_scene():
    global story_index, story_timer, state, game_fade
    story_index += 1
    story_timer = 0
    if story_index >= len(scenes):
        game_fade = FADE_FRAMES
        state = "game"


def draw_story():
    scene = scenes[story_index]
    kind = scene["kind"]
    t = story_timer

    if kind == "title":
        screen.blit(snow_bg, (0, 0))   # swapped: the village scene uses the snow day
        for i, line in enumerate(title_intro):
            draw_centered(line, HEIGHT // 2 - 170 + i * 40)
        draw_bouncing(title_letters, t, HEIGHT // 2 - 60)

    elif kind == "attack":
        screen.blit(snow_sky, (0, 0))  # swapped: the attack scene uses the snow sky

        # a few Furies sneak in from the right
        crowd = [(enemy_types[0]["image"], 0, HEIGHT - 300),
                 (enemy_types[1]["image"], 150, HEIGHT - 380),
                 (enemy_types[0]["image"], 300, HEIGHT - 230)]
        for img, offset, y in crowd:
            screen.blit(img, (WIDTH + offset - t * 1.5, y))

        # darker strip behind the text so it's readable
        band = pygame.Surface((WIDTH, 170), pygame.SRCALPHA)
        band.fill((0, 0, 0, 130))
        screen.blit(band, (0, 40))

        for i, line in enumerate(attack_lines):
            shake_x = random.randint(-3, 3)
            shake_y = random.randint(-3, 3)
            draw_centered(line, 65 + i * 40, shake_x, shake_y)

    elif kind == "hidden":
        screen.fill(BLACK)
        for i, line in enumerate(hidden_lines):
            if t > i * 80:  # lines show up one after another
                draw_centered(line, HEIGHT // 2 - 100 + i * 60)

    elif kind == "emerge":
        screen.blit(fire_bg, (0, 0))
        screen.blit(player_img, ((WIDTH - PLAYER_SIZE[0]) // 2,
                                 (HEIGHT - PLAYER_SIZE[1]) // 2))

        pygame.draw.rect(screen, BLACK, story_box)
        pygame.draw.rect(screen, WHITE, story_box, 2)
        typed = scene["text"][:t // 2]
        # wrap the full text so words don't jump lines while typing
        full_lines = wrap_text(scene["text"], small_font, story_box.width - 30)
        count = 0
        for i, line in enumerate(full_lines):
            part = typed[count:count + len(line)]
            count += len(line) + 1
            draw_text(part, small_font, WHITE, story_box.x + 15, story_box.y + 20 + i * 32)

    scene_fade(t, scene["frames"])


def draw_levelup():
    """'Congrats' cutscene shown after every level."""
    t = cut_timer
    screen.fill(BLACK)
    draw_bouncing(congrats_letters, t, HEIGHT // 2 - 120)
    for i, line in enumerate(levelup_lines):
        draw_centered(line, HEIGHT // 2 + 10 + i * 50)
    scene_fade(t, LEVELUP_FRAMES)


def draw_ending():
    """Text after the boss dies. The big line fades in a bit after the first one."""
    t = cut_timer
    screen.fill(BLACK)
    draw_faded(ending_line, HEIGHT // 2 - 130, t * 255 / 60)
    if t > 120:
        draw_faded(ending_big, HEIGHT // 2 - 30, (t - 120) * 255 / 90)
    if t > ENDING_FRAMES - FADE_FRAMES:
        fade_overlay(255 * (1 - (ENDING_FRAMES - t) / FADE_FRAMES))


def draw_inevitable():
    """The hero stands there and says the line in a comic speech bubble."""
    t = cut_timer
    screen.blit(fire_bg, (0, 0))
    hero_x = (WIDTH - PLAYER_SIZE[0]) // 2
    hero_y = (HEIGHT - PLAYER_SIZE[1]) // 2
    screen.blit(player_img, (hero_x, hero_y))

    if t > 40:
        tw, th = bubble_text.get_size()
        bubble = pygame.Rect(0, 0, tw + 90, th + 70)
        bubble.center = (WIDTH // 2, hero_y - 130)
        cx = bubble.centerx
        tip_y = hero_y - 8

        # black outline pieces first, then the white fill on top of them
        pygame.draw.polygon(screen, BLACK, [(cx - 24, bubble.bottom - 10),
                                            (cx + 30, bubble.bottom - 10),
                                            (cx + 6, tip_y)])
        pygame.draw.ellipse(screen, BLACK, bubble)
        pygame.draw.ellipse(screen, WHITE, bubble.inflate(-10, -10))
        pygame.draw.polygon(screen, WHITE, [(cx - 16, bubble.bottom - 14),
                                            (cx + 22, bubble.bottom - 14),
                                            (cx + 5, tip_y - 10)])
        screen.blit(bubble_text, bubble_text.get_rect(center=bubble.center))

    scene_fade(t, INEVITABLE_FRAMES)


def draw_gameover():
    t = cut_timer
    screen.fill(BLACK)
    wobble = math.sin(t * 0.08) * 6
    draw_centered(gameover_text, HEIGHT // 2 - 100, 0, wobble)
    if t > 60 and (t // 30) % 2 == 0:   # blinking prompt
        draw_centered(restart_text, HEIGHT // 2 + 60)
    if t < FADE_FRAMES:
        fade_overlay(255 * (1 - t / FADE_FRAMES))


def move_player():
    keys = pygame.key.get_pressed()
    if keys[pygame.K_UP] and player.top > 0:
        player.y -= player_speed
    if keys[pygame.K_DOWN] and player.bottom < HEIGHT:
        player.y += player_speed


def move_bullets():
    """Move snowballs and drop the ones that left the screen."""
    global bullets
    for ball in bullets:
        ball.x += bullet_speed
    bullets = [b for b in bullets if b.left < WIDTH]


# --- main loop ------------------------------------------------------

running = True
while running:
    clock.tick(60)

    # pick the background (the story and cutscenes draw their own)
    if state in ("start", "gender", "dialogue"):
        screen.blit(snow_bg, (0, 0))
    elif state == "boss" or (state == "death" and death_return == "boss"):
        screen.blit(boss_bg, (0, 0))
    else:
        screen.blit(fire_bg, (0, 0))

    # --- events ---
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        # playtesting: | (or backslash) skips the current level
        elif (DEV_KEYS and event.type == pygame.KEYDOWN
              and state in ("game", "levelup", "boss")
              and (event.unicode == "|" or event.key == pygame.K_BACKSLASH)):
            skip_level()

        elif state == "start" and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN and player_name:
                state = "gender"
            elif event.key == pygame.K_BACKSPACE:
                player_name = player_name[:-1]
            elif len(player_name) < 12 and event.unicode.isprintable():
                player_name += event.unicode

        elif state == "gender" and event.type == pygame.MOUSEBUTTONDOWN:
            if male_button.collidepoint(event.pos):
                gender, player_img = "Male", male_img
            elif female_button.collidepoint(event.pos):
                gender, player_img = "Female", female_img

            if gender:
                dialogues = [
                    f"Welcome, {player_name}.",
                    "This world is not what it used to be...",
                ]
                dialogue_index = 0
                shown_text = ""
                text_timer = 0
                state = "dialogue"

        elif state == "dialogue" and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                dialogue_index += 1
                shown_text = ""
                text_timer = 0
                if dialogue_index >= len(dialogues):
                    scenes[-1]["text"] = f"You are a {gender.lower()} snow warrior."
                    story_index = 0
                    story_timer = 0
                    state = "story"

        elif state == "story" and event.type == pygame.KEYDOWN:
            # space finishes the typing first, then skips to the next scene
            if event.key == pygame.K_SPACE:
                scene = scenes[story_index]
                if "text" in scene and story_timer // 2 < len(scene["text"]):
                    story_timer = len(scene["text"]) * 2
                else:
                    next_scene()

        elif state in ("game", "boss") and event.type == pygame.KEYDOWN:
            now = pygame.time.get_ticks()
            if event.key == pygame.K_SPACE and now - last_shot >= SHOOT_COOLDOWN:
                last_shot = now
                ball = snowball_img.get_rect(midleft=player.midright)
                bullets.append(ball)

        elif state == "levelup" and event.type == pygame.KEYDOWN:
            # only skippable after a moment, so shooting spam doesn't skip it
            if event.key == pygame.K_SPACE and cut_timer > 60:
                finish_levelup()

        elif state == "death" and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r:
                if death_return == "boss":
                    init_boss()
                    state = "boss"
                else:
                    reset_game()
                    state = "game"

        elif state == "gameover" and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r and cut_timer > 60:
                full_restart()

    # --- start screen ---
    if state == "start":
        pygame.draw.rect(screen, BLACK, start_box)
        draw_text("Enter Name: " + player_name, font, WHITE,
                  start_box.x + 40, start_box.centery - 12)

    # --- gender screen ---
    elif state == "gender":
        pygame.draw.rect(screen, BLACK, gender_box)
        draw_text_center("Choose your character", font, WHITE,
                        gender_box.centerx, gender_box.y + 40)
        pygame.draw.rect(screen, (0, 0, 180), male_button)
        pygame.draw.rect(screen, (180, 0, 100), female_button)
        draw_text_center("Male", font, WHITE, *male_button.center)
        draw_text_center("Female", font, WHITE, *female_button.center)

    # --- dialogue ---
    elif state == "dialogue":
        # type out one more letter every few frames
        text_timer += 1
        if text_timer % text_speed == 0:
            full_text = dialogues[dialogue_index]
            shown_text = full_text[:len(shown_text) + 1]

        pygame.draw.rect(screen, BLACK, dialogue_box)
        pygame.draw.rect(screen, WHITE, dialogue_box, 2)
        draw_text(shown_text, font, WHITE, dialogue_box.x + 20, dialogue_box.centery - 12)

    # --- story intro ---
    elif state == "story":
        draw_story()
        story_timer += 1
        if story_timer >= scenes[story_index]["frames"]:
            next_scene()

    # --- gameplay (levels 1-3) ---
    elif state == "game":
        move_player()
        move_bullets()

        # move the enemy
        enemy["rect"].x -= enemy["speed"]

        # the hitboxes are a bit smaller than the sprites so hits feel fair
        player_hitbox = player.inflate(-20, -20)
        enemy_hitbox = enemy["rect"].inflate(-20, -20)

        if enemy["rect"].right < 0 or player_hitbox.colliderect(enemy_hitbox):
            death_return = "game"
            state = "death"

        # snowballs hitting the enemy
        for ball in bullets[:]:
            if ball.colliderect(enemy_hitbox):
                bullets.remove(ball)
                enemy["health"] -= 1

                if enemy["health"] <= 0:
                    score += enemy["points"]
                    high_score = max(high_score, score)
                    enemy = spawn_enemy()
                    break

        # draw everything
        screen.blit(player_img, player)
        screen.blit(enemy["image"], enemy["rect"])
        for ball in bullets:
            screen.blit(snowball_img, ball)

        goal = LEVELS[level]["goal"]
        level_text = font.render(f"Level {level + 1}", True, WHITE)
        score_text = font.render(f"Score: {score}/{goal}", True, WHITE)
        high_text = font.render(f"High Score: {high_score}", True, WHITE)
        screen.blit(level_text, (10, 10))
        screen.blit(score_text, (WIDTH - score_text.get_width() - 10, 10))
        screen.blit(high_text, (WIDTH - high_text.get_width() - 10, 50))

        # level finished?
        if state == "game" and score >= goal:
            bullets.clear()
            cut_timer = 0
            state = "levelup"

    # --- level complete cutscene ---
    elif state == "levelup":
        draw_levelup()
        cut_timer += 1
        if cut_timer >= LEVELUP_FRAMES:
            finish_levelup()

    # --- boss fight ---
    elif state == "boss":
        move_player()
        move_bullets()

        b = boss["rect"]
        if not boss["entered"]:
            # slide in from the right
            b.x -= 3
            if b.x <= BOSS_STOP_X:
                b.x = BOSS_STOP_X
                boss["entered"] = True
        else:
            # below 25% health he gets angry: faster movement and fireballs
            raging = boss["health"] <= BOSS_RAGE_HEALTH

            # move up and down
            b.y += boss["dir"] * (BOSS_RAGE_SPEED if raging else BOSS_SPEED)
            if b.top <= 0:
                b.top = 0
                boss["dir"] = 1
            elif b.bottom >= HEIGHT:
                b.bottom = HEIGHT
                boss["dir"] = -1

            # shoot a fireball at the player
            boss["shoot_timer"] -= 1
            if boss["shoot_timer"] <= 0:
                boss["shoot_timer"] = BOSS_RAGE_SHOOT_DELAY if raging else BOSS_SHOOT_DELAY
                sx, sy = b.left + 30, b.centery
                dx, dy = player.centerx - sx, player.centery - sy
                dist = math.hypot(dx, dy) or 1
                fireballs.append({"x": sx, "y": sy,
                                  "vx": dx / dist * FIREBALL_SPEED,
                                  "vy": dy / dist * FIREBALL_SPEED})

            # every now and then he calls in a normal enemy (much rarer than in the levels)
            boss["minion_timer"] -= 1
            if boss["minion_timer"] <= 0:
                boss["minion_timer"] = random.randint(300, 480)
                minions.append(spawn_enemy(b.left, MINION_BONUS, 30))

        player_hitbox = player.inflate(-20, -20)
        boss_hitbox = b.inflate(-80, -80)
        hit_player = False

        # fireballs
        for f in fireballs[:]:
            f["x"] += f["vx"]
            f["y"] += f["vy"]
            f_rect = fireball_img.get_rect(center=(f["x"], f["y"]))
            if f_rect.inflate(-10, -10).colliderect(player_hitbox):
                hit_player = True
            if f_rect.right < -40 or f_rect.top > HEIGHT + 40 or f_rect.bottom < -40:
                fireballs.remove(f)

        # the little enemies
        for m in minions[:]:
            m["rect"].x -= m["speed"]
            if m["rect"].right < 0:
                minions.remove(m)   # in the boss fight they just disappear
            elif m["rect"].inflate(-20, -20).colliderect(player_hitbox):
                hit_player = True

        # snowballs hit minions first, then the boss
        for ball in bullets[:]:
            hit = False
            for m in minions[:]:
                if ball.colliderect(m["rect"].inflate(-20, -20)):
                    m["health"] -= 1
                    if m["health"] <= 0:
                        minions.remove(m)
                    hit = True
                    break
            if not hit and ball.colliderect(boss_hitbox):
                boss["health"] -= 1
                hit = True
            if hit:
                bullets.remove(ball)

        if hit_player:
            death_return = "boss"
            state = "death"

        # draw everything
        screen.blit(player_img, player)
        for m in minions:
            screen.blit(m["image"], m["rect"])
        screen.blit(boss_img, b)
        for f in fireballs:
            screen.blit(fireball_img, fireball_img.get_rect(center=(f["x"], f["y"])))
        for ball in bullets:
            screen.blit(snowball_img, ball)

        # boss health bar
        bar = pygame.Rect(WIDTH // 2 - 200, 15, 400, 22)
        pygame.draw.rect(screen, (60, 0, 0), bar)
        fill = bar.copy()
        fill.width = int(bar.width * max(0, boss["health"]) / BOSS_HEALTH)
        pygame.draw.rect(screen, (230, 40, 40), fill)
        pygame.draw.rect(screen, WHITE, bar, 2)
        draw_text_center("HEAD OF THE FURIES", small_font, WHITE, WIDTH // 2, 52)

        if state == "boss" and boss["health"] <= 0:
            start_ending()

    # --- ending text ---
    elif state == "ending":
        draw_ending()
        cut_timer += 1
        if cut_timer >= ENDING_FRAMES:
            cut_timer = 0
            state = "inevitable"

    # --- "I am Inevitable" ---
    elif state == "inevitable":
        draw_inevitable()
        cut_timer += 1
        if cut_timer >= INEVITABLE_FRAMES:
            cut_timer = 0
            state = "gameover"

    # --- game over ---
    elif state == "gameover":
        draw_gameover()
        cut_timer += 1

    # --- death screen ---
    elif state == "death":
        draw_text_center("YOU DIED", big_font, (255, 0, 0), WIDTH // 2, HEIGHT // 2 - 30)
        draw_text_center("Press R to Restart", font, WHITE, WIDTH // 2, HEIGHT // 2 + 40)

    # fade the game in after a cutscene ends
    if game_fade > 0:
        fade_overlay(255 * game_fade / FADE_FRAMES)
        game_fade -= 1

    pygame.display.update()

pygame.quit()
