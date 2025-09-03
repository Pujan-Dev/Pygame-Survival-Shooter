import pygame
import sys
import time
import random
import math

pygame.init()

# === Display / Core ===
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
screen_width, screen_height = screen.get_size()
pygame.display.set_caption("Pygame – Roguelite Survival")
clock = pygame.time.Clock()

# === Fonts ===
font = pygame.font.SysFont(None, 56)
mid_font = pygame.font.SysFont(None, 40)
small_font = pygame.font.SysFont(None, 28)

# === Game states ===
START, PLAYING, POWERUP_PICK, GAME_OVER = (
    "start",
    "playing",
    "powerup_pick",
    "game_over",
)
state = START


# === Helpers ===
def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def draw_text_center(text, fnt, color, y, shadow=True):
    render = fnt.render(text, True, color)
    rect = render.get_rect(center=(screen_width // 2, y))
    if shadow:
        sh = fnt.render(text, True, (0, 0, 0))
        sh_rect = sh.get_rect(center=(screen_width // 2 + 2, y + 2))
        screen.blit(sh, sh_rect)
    screen.blit(render, rect)


def draw_bar(x, y, w, h, pct, fg=(50, 205, 50), bg=(70, 70, 70), border=(20, 20, 20)):
    pygame.draw.rect(screen, border, (x - 2, y - 2, w + 4, h + 4), border_radius=6)
    pygame.draw.rect(screen, bg, (x, y, w, h), border_radius=4)
    fw = int(w * clamp(pct, 0, 1))
    pygame.draw.rect(screen, fg, (x, y, fw, h), border_radius=4)


def angle_to(a, b):
    return math.atan2(b[1] - a[1], b[0] - a[0])


def dist(a, b):
    return math.hypot(b[0] - a[0], b[1] - a[1])


def rand_spawn_away_from(px, py, margin=120):
    # Spawn at edges, away from player
    side = random.choice(["top", "bottom", "left", "right"])
    if side == "top":
        x = random.randint(60, screen_width - 60)
        y = -40
    elif side == "bottom":
        x = random.randint(60, screen_width - 60)
        y = screen_height + 40
    elif side == "left":
        x = -40
        y = random.randint(60, screen_height - 60)
    else:
        x = screen_width + 40
        y = random.randint(60, screen_height - 60)
    # small nudge to avoid immediate overlap if player near edge
    if dist((x, y), (px, py)) < margin:
        x += margin * (1 if x < px else -1)
        y += margin * (1 if y < py else -1)
    return x, y


# === Core Entities ===
class Bullet:
    def __init__(self, x, y, tx, ty, speed, dmg, pierce=0):
        self.x = x
        self.y = y
        ang = angle_to((x, y), (tx, ty))
        self.vx = math.cos(ang) * speed
        self.vy = math.sin(ang) * speed
        self.r = 5
        self.color = (255, 230, 90)
        self.dmg = dmg
        self.pierce = (
            pierce  # how many enemies it can pass through after dealing damage
        )
        self.alive = True

    def update(self):
        self.x += self.vx
        self.y += self.vy
        # offscreen kill
        if (
            self.x < -50
            or self.x > screen_width + 50
            or self.y < -50
            or self.y > screen_height + 50
        ):
            self.alive = False

    def draw(self, surface):
        pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), self.r)


class Player:
    def __init__(self):
        self.w = 50
        self.h = 50
        self.x = screen_width // 2
        self.y = screen_height // 2
        self.rect = pygame.Rect(self.x, self.y, self.w, self.h)
        self.color = (0, 160, 255)

        # Stats (upgradeable)
        self.max_hp = 100
        self.hp = self.max_hp
        self.move_speed = 6
        self.fr = 0.25  # fire rate seconds per shot
        self.bullet_speed = 15
        self.bullet_damage = 20
        self.bullet_pierce = 0
        self.i_frames = 0.8  # seconds of invulnerability after hit
        self.last_shot = 0.0
        self.last_hit_time = -10.0
        self.knockback_resist = 0.0

        # Minor juice
        self.flash_time = 0.0  # for damage flash

    def handle_keys(self):
        keys = pygame.key.get_pressed()
        dx = dy = 0
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            dx -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            dx += 1
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            dy -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            dy += 1
        if dx or dy:
            inv = (dx * dx + dy * dy) ** 0.5
            dx /= inv
            dy /= inv
        self.x += dx * self.move_speed
        self.y += dy * self.move_speed
        self.x = clamp(self.x, 0, screen_width - self.w)
        self.y = clamp(self.y, 0, screen_height - self.h)
        self.rect.topleft = (int(self.x), int(self.y))

    def can_shoot(self, now):
        return (now - self.last_shot) >= self.fr

    def shoot(self, bullets, mx, my, now):
        self.last_shot = now
        bullets.append(
            Bullet(
                self.x + self.w / 2,
                self.y + self.h / 2,
                mx,
                my,
                self.bullet_speed,
                self.bullet_damage,
                self.bullet_pierce,
            )
        )

    def take_damage(self, dmg, now, src_pos=None, kb=6):
        if now - self.last_hit_time < self.i_frames:
            return
        self.last_hit_time = now
        self.hp -= dmg
        self.flash_time = now
        # Knockback if source known
        if src_pos is not None and kb > 0:
            ang = angle_to(src_pos, (self.x, self.y))
            mag = kb * (1 - self.knockback_resist)
            self.x += math.cos(ang) * mag
            self.y += math.sin(ang) * mag
            self.x = clamp(self.x, 0, screen_width - self.w)
            self.y = clamp(self.y, 0, screen_height - self.h)
            self.rect.topleft = (int(self.x), int(self.y))

    def draw(self, surface, now):
        # brief red flash when hit
        if now - self.flash_time < 0.12:
            c = (255, 80, 80)
        else:
            c = self.color
        pygame.draw.rect(surface, c, self.rect, border_radius=8)


class Enemy:
    # type: 'basic' | 'fast' | 'tank'
    def __init__(self, kind, px, py, wave):
        self.kind = kind
        if kind == "basic":
            self.size = 42
            self.speed = 2.2 + 0.05 * wave
            self.hp = 30 + 4 * wave
            self.damage = 10
        elif kind == "fast":
            self.size = 34
            self.speed = 3.6 + 0.06 * wave
            self.hp = 22 + 3 * wave
            self.damage = 8
        else:  # tank
            self.size = 56
            self.speed = 1.5 + 0.04 * wave
            self.hp = 65 + 6 * wave
            self.damage = 15
        self.x, self.y = rand_spawn_away_from(px, py)
        self.rect = pygame.Rect(self.x, self.y, self.size, self.size)
        self.color = (255, 70, 70) if kind != "tank" else (220, 120, 60)
        self.alive = True

    def update(self, player: Player):
        ang = angle_to((self.x, self.y), (player.x, player.y))
        self.x += math.cos(ang) * self.speed
        self.y += math.sin(ang) * self.speed
        self.rect.topleft = (int(self.x), int(self.y))

    def draw(self, surface):
        pygame.draw.rect(surface, self.color, self.rect, border_radius=6)

    def hit(self, dmg):
        self.hp -= dmg
        if self.hp <= 0:
            self.alive = False


# === Powerups ===
ALL_POWERUPS = [
    ("Glass Cannon", "Bullet dmg +40%, HP -15%", "dmg_up_hp_down"),
    ("Adrenaline", "Move speed +20%", "speed_up"),
    ("Trigger Finger", "Fire rate +25%", "firerate_up"),
    ("Splinter Rounds", "Bullets pierce +1", "pierce_up"),
    ("Magnum Rounds", "Bullet dmg +25%", "dmg_up"),
    ("Hot Load", "Bullet speed +20%", "bspeed_up"),
    ("Hardened", "Max HP +20%, i-frames +0.1s", "hp_up_iframe"),
    ("Steadfast", "Knockback taken -50%", "kb_resist"),
    ("Second Wind", "Heal 30 HP (over-heal to +10)", "heal_now"),
    ("Vampiric Rounds", "On kill: heal 2 HP", "lifesteal"),
]


def apply_powerup(player: Player, tag: str, meta):
    if tag == "dmg_up_hp_down":
        player.bullet_damage = int(player.bullet_damage * 1.4)
        player.max_hp = max(40, int(player.max_hp * 0.85))
        player.hp = min(player.hp, player.max_hp)
    elif tag == "speed_up":
        player.move_speed *= 1.2
    elif tag == "firerate_up":
        player.fr *= 0.75
    elif tag == "pierce_up":
        player.bullet_pierce += 1
    elif tag == "dmg_up":
        player.bullet_damage = int(player.bullet_damage * 1.25)
    elif tag == "bspeed_up":
        player.bullet_speed *= 1.2
    elif tag == "hp_up_iframe":
        player.max_hp = int(player.max_hp * 1.2)
        player.hp = min(player.max_hp, player.hp + 20)
        player.i_frames += 0.1
    elif tag == "kb_resist":
        player.knockback_resist = clamp(player.knockback_resist + 0.5, 0, 0.9)
    elif tag == "heal_now":
        player.hp = min(player.max_hp + 10, player.hp + 30)
    elif tag == "lifesteal":
        meta["lifesteal"] = True


# === Game control ===
def start_screen():
    screen.fill((25, 25, 30))
    draw_text_center("ROGUELITE SURVIVAL", font, (255, 255, 255), screen_height // 3)
    draw_text_center(
        "WASD / Arrows to move · Mouse Left to shoot",
        mid_font,
        (210, 210, 210),
        screen_height // 2 - 30,
    )
    draw_text_center(
        "Survive waves, pick 1 of 3 powerups between waves",
        small_font,
        (200, 200, 200),
        screen_height // 2 + 10,
    )
    draw_text_center(
        "Press any key to start · ESC to quit",
        small_font,
        (200, 200, 200),
        screen_height // 2 + 60,
    )
    pygame.display.flip()


def game_over_screen(score, wave):
    screen.fill((30, 20, 20))
    draw_text_center("GAME OVER", font, (255, 120, 120), screen_height // 3)
    draw_text_center(
        f"Score: {int(score)}  ·  Wave Reached: {wave}",
        mid_font,
        (240, 240, 240),
        screen_height // 2,
    )
    draw_text_center(
        "Press R to Restart  ·  Q or ESC to Quit",
        small_font,
        (220, 220, 220),
        screen_height // 2 + 60,
    )
    pygame.display.flip()


def draw_hud(player: Player, wave, time_left, enemies_left, score):
    # Top-left info
    timer_text = small_font.render(
        f"Wave {wave}  |  Time: {int(time_left)}s  |  Enemies: {enemies_left}",
        True,
        (255, 255, 255),
    )
    screen.blit(timer_text, (14, 12))
    # Score
    stext = small_font.render(f"Score: {int(score)}", True, (255, 255, 255))
    screen.blit(stext, (14, 40))
    # HP bar
    draw_bar(14, 70, 260, 18, player.hp / player.max_hp)
    hptext = small_font.render(
        f"HP: {int(player.hp)}/{player.max_hp}", True, (255, 255, 255)
    )
    screen.blit(hptext, (18, 68 - 22))


def roll_powerups():
    # 3 distinct random options
    return random.sample(ALL_POWERUPS, 3)


def draw_powerup_pick(options):
    screen.fill((20, 26, 30))
    draw_text_center("Choose a Powerup", font, (255, 255, 255), 120)
    y = 230
    for i, (name, desc, tag) in enumerate(options, start=1):
        # Card
        x = screen_width // 2 - 420 + (i - 1) * 420
        card = pygame.Rect(x - 160, y - 60, 320, 180)
        pygame.draw.rect(screen, (40, 45, 55), card, border_radius=12)
        pygame.draw.rect(screen, (90, 95, 120), card, width=2, border_radius=12)
        tname = mid_font.render(f"{i}. {name}", True, (255, 255, 255))
        tdesc = small_font.render(desc, True, (220, 220, 230))
        screen.blit(tname, (card.x + 18, card.y + 18))
        screen.blit(tdesc, (card.x + 18, card.y + 64))
    draw_text_center("Press 1 / 2 / 3", small_font, (220, 220, 220), y + 180)
    pygame.display.flip()


# === Initialize run ===
running = True
player = Player()
bullets = []
enemies = []
meta = {"lifesteal": False}  # global toggles from powerups

# Wave system: spawn-once, no mid-wave spawns, either timer hits 0 or all enemies die -> powerup pick
wave = 0
wave_time_total = 18
wave_time_left = wave_time_total
options = []
score = 0
last_time = time.time()


def spawn_wave(wave, player):
    count = 4 + wave * 2
    mix = []
    for _ in range(count):
        kind = random.choices(
            population=["basic", "fast", "tank"],
            weights=[60, 28 + wave * 2, 12 + max(0, wave - 2) * 3],
            k=1,
        )[0]
        mix.append(kind)
    spawned = []
    for k in mix:
        e = Enemy(k, player.x, player.y, wave)
        spawned.append(e)
    return spawned


def start_game():
    global player, bullets, enemies, wave, wave_time_left, score, last_time, meta
    player = Player()
    bullets = []
    enemies = []
    meta = {"lifesteal": False}
    wave = 1
    wave_time_left = wave_time_total
    enemies[:] = spawn_wave(wave, player)
    score = 0
    last_time = time.time()


# === Main Loop ===
while running:
    now = time.time()
    dt = now - last_time
    last_time = now

    if state == START:
        start_screen()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                else:
                    start_game()
                    state = PLAYING

    elif state == PLAYING:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_q):
                    running = False
                if event.key == pygame.K_r:
                    start_game()
                    continue
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = pygame.mouse.get_pos()
                if player.can_shoot(now):
                    player.shoot(bullets, mx, my, now)

        # Inputs + shooting hold
        player.handle_keys()
        if pygame.mouse.get_pressed()[0]:
            mx, my = pygame.mouse.get_pos()
            if player.can_shoot(now):
                player.shoot(bullets, mx, my, now)

        # Update bullets
        for b in bullets:
            b.update()
        bullets = [b for b in bullets if b.alive]

        # Update enemies
        for e in enemies:
            e.update(player)

        # Collisions: bullets -> enemies
        for b in bullets:
            if not b.alive:
                continue
            br = pygame.Rect(int(b.x - 4), int(b.y - 4), 8, 8)
            hit_any = False
            for e in enemies:
                if e.alive and e.rect.colliderect(br):
                    e.hit(b.dmg)
                    hit_any = True
                    if not e.alive and meta.get("lifesteal"):
                        player.hp = min(player.max_hp, player.hp + 2)
                    if b.pierce > 0:
                        b.pierce -= 1
                    else:
                        b.alive = False
                        break
            # allow bullet to continue if still alive (due to pierce)

        # Collisions: enemies -> player
        for e in enemies:
            if e.alive and e.rect.colliderect(player.rect):
                player.take_damage(e.damage, now, (e.x, e.y), kb=7)

        # Cleanup dead enemies
        enemies = [e for e in enemies if e.alive]

        # Wave timer and score
        wave_time_left -= dt
        score += dt * (1 + 0.1 * wave)  # tiny scaling

        # End wave conditions: either timer ends OR all enemies dead
        if wave_time_left <= 0 or len(enemies) == 0:
            # Go to powerup pick
            options = roll_powerups()
            state = POWERUP_PICK

        # Death check
        if player.hp <= 0:
            state = GAME_OVER

        # Draw
        screen.fill((28, 28, 32))
        player.draw(screen, now)
        for e in enemies:
            e.draw(screen)
        for b in bullets:
            b.draw(screen)

        draw_hud(player, wave, max(0, wave_time_left), len(enemies), score)

        pygame.display.flip()
        clock.tick(60)

    elif state == POWERUP_PICK:
        # Freeze world; spawn next wave only after pick
        draw_powerup_pick(options)
        picked = None
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_q):
                    running = False
                elif event.key == pygame.K_1:
                    picked = 0
                elif event.key == pygame.K_2:
                    picked = 1
                elif event.key == pygame.K_3:
                    picked = 2
        if picked is not None:
            name, desc, tag = options[picked]
            apply_powerup(player, tag, meta)
            # Next wave
            wave += 1
            wave_time_left = wave_time_total + min(
                10, wave * 1.2
            )  # slowly longer waves
            enemies = spawn_wave(wave, player)  # spawn ONCE, no mid-wave spawns
            state = PLAYING

    elif state == GAME_OVER:
        game_over_screen(score, wave)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_q):
                    running = False
                elif event.key == pygame.K_r:
                    start_game()
                    state = PLAYING

pygame.quit()
sys.exit()
