import pygame
import random
import os
import sys

# Initialize
pygame.init()

# Screen
WIDTH, HEIGHT = 1200, 450
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Dino Game")

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (83, 83, 83)
LIGHT_GRAY = (200, 200, 200)
DARK_BG = (40, 44, 52)
NIGHT_OBSTACLE = (144, 238, 144)
NIGHT_GROUND = (100, 100, 120)
CLOUD_COLOR = (240, 240, 240)
DARK_CLOUD = (80, 85, 100)

# Clock
clock = pygame.time.Clock()
FPS = 60

# High score file
HIGHSCORE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "highscore.txt")


def get_font(size, bold=False, chinese=False):
    if chinese:
        for name in ["microsoftyahei", "simhei", "simsun", "nsimsun", "fangsong"]:
            try:
                return pygame.font.SysFont(name, size, bold=bold)
            except:
                continue
    return pygame.font.SysFont("consolas", size, bold=bold)


def load_highscore():
    try:
        with open(HIGHSCORE_FILE, "r") as f:
            return int(f.read().strip())
    except (FileNotFoundError, ValueError):
        return 0


def save_highscore(score):
    with open(HIGHSCORE_FILE, "w") as f:
        f.write(str(score))


class Particle:
    def __init__(self, x, y, color=(255, 255, 255)):
        self.x = x
        self.y = y
        self.vx = random.uniform(-3, 3)
        self.vy = random.uniform(-4, 1)
        self.life = random.randint(10, 25)
        self.size = random.randint(3, 6)
        self.color = color

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.15
        self.life -= 1

    def draw(self, surface):
        if self.life > 0:
            alpha = max(0, min(255, self.life * 12))
            s = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
            s.fill((*self.color, alpha))
            surface.blit(s, (int(self.x), int(self.y)))

    def alive(self):
        return self.life > 0


class RingParticle:
    """Expanding ring effect for double jump."""
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.radius = 10
        self.max_radius = 40
        self.alpha = 255
        self.life = 8
        self.max_life = 8

    def update(self):
        progress = 1.0 - (self.life / self.max_life)
        self.radius = 10 + (self.max_radius - 10) * progress
        self.alpha = int(255 * (1.0 - progress))
        self.life -= 1

    def draw(self, surface):
        if self.life > 0:
            r = int(self.radius)
            size = r * 2 + 4
            s = pygame.Surface((size, size), pygame.SRCALPHA)
            pygame.draw.circle(s, (255, 255, 255, self.alpha), (r + 2, r + 2), r, 2)
            surface.blit(s, (int(self.x - r - 2), int(self.y - r - 2)))

    def alive(self):
        return self.life > 0


class Inventory:
    """10-slot inventory bar at bottom center."""
    SLOTS = 10
    SLOT_SIZE = 30

    def __init__(self):
        self.slots = [None] * self.SLOTS
        self.selected = 0
        self.full_flash = 0
        self.use_flash = 0

    def add(self, item_type):
        for i in range(self.SLOTS):
            if self.slots[i] and self.slots[i]["type"] == item_type:
                self.slots[i]["count"] += 1
                return True
        for i in range(self.SLOTS):
            if self.slots[i] is None:
                self.slots[i] = {"type": item_type, "count": 1}
                if self.selected is None or self.slots[self.selected] is None:
                    self.selected = i
                return True
        self.full_flash = int(1.0 * FPS)
        return False

    def use_selected(self):
        if self.selected is not None and self.slots[self.selected]:
            slot = self.slots[self.selected]
            slot["count"] -= 1
            item_type = slot["type"]
            if slot["count"] <= 0:
                self.slots[self.selected] = None
                self._auto_select()
            return item_type
        return None

    def get_selected_type(self):
        if self.selected is not None and self.slots[self.selected]:
            return self.slots[self.selected]["type"]
        return None

    def select_left(self):
        for i in range(self.SLOTS):
            idx = (self.selected - 1 - i) % self.SLOTS
            if self.slots[idx]:
                self.selected = idx
                return

    def select_right(self):
        for i in range(self.SLOTS):
            idx = (self.selected + 1 + i) % self.SLOTS
            if self.slots[idx]:
                self.selected = idx
                return

    def _auto_select(self):
        for i in range(self.SLOTS):
            if self.slots[i]:
                self.selected = i
                return

    def add_visual(self, item_type):
        """Add a display-only item (no usable count) in the first empty slot."""
        for i in range(self.SLOTS):
            if self.slots[i] is None:
                self.slots[i] = {"type": item_type, "count": 0, "visual": True}
                return

    def remove_visual(self, item_type):
        """Remove all visual-only items of the given type."""
        for i in range(self.SLOTS):
            if self.slots[i] and self.slots[i].get("visual") and self.slots[i]["type"] == item_type:
                self.slots[i] = None
        self._auto_select()

    def update(self):
        if self.full_flash > 0:
            self.full_flash -= 1
        if self.use_flash > 0:
            self.use_flash -= 1

    def draw(self, surface, night):
        total_w = self.SLOTS * self.SLOT_SIZE
        start_x = (WIDTH - total_w) // 2
        y = HEIGHT - self.SLOT_SIZE - 5

        small_font = pygame.font.SysFont("consolas", 10, bold=True)
        name_font = pygame.font.SysFont("consolas", 11, bold=True)
        num_font = pygame.font.SysFont("consolas", 9, bold=True)

        TYPE_NAMES = {
            "ammo": "AMMO", "shield": "SHIELD", "clock": "CLOCK",
            "shrink": "SHRINK", "rocket": "ROCKET"
        }

        for i in range(self.SLOTS):
            x = start_x + i * self.SLOT_SIZE
            is_sel = (i == self.selected)

            if is_sel:
                # Enlarged selected slot
                pad = 3
                sel_rect = (x - pad, y - pad, self.SLOT_SIZE + pad * 2, self.SLOT_SIZE + pad * 2)
                pygame.draw.rect(surface, (255, 255, 0), sel_rect, 3)
                # Flash white feedback
                if self.use_flash > 0 and (self.use_flash // 3) % 2 == 0:
                    flash_surf = pygame.Surface((self.SLOT_SIZE + pad * 2, self.SLOT_SIZE + pad * 2), pygame.SRCALPHA)
                    flash_surf.fill((255, 255, 255, 80))
                    surface.blit(flash_surf, (x - pad, y - pad))
            else:
                pygame.draw.rect(surface, (150, 150, 150), (x, y, self.SLOT_SIZE, self.SLOT_SIZE), 1)

            # Number hint in top-left corner
            num_text = num_font.render(str(i + 1), True, (180, 180, 180))
            surface.blit(num_text, (x + 1, y + 1))

            if self.slots[i]:
                slot = self.slots[i]
                cx, cy = x + self.SLOT_SIZE // 2, y + self.SLOT_SIZE // 2
                if slot["type"] == "ammo":
                    pygame.draw.rect(surface, (255, 215, 0), (cx - 6, cy - 2, 12, 4))
                    pygame.draw.polygon(surface, (255, 215, 0), [
                        (cx + 6, cy - 2), (cx + 9, cy), (cx + 6, cy + 2)
                    ])
                elif slot["type"] == "shield":
                    pygame.draw.circle(surface, (100, 200, 255), (cx, cy), 8)
                    t = small_font.render("S", True, WHITE)
                    surface.blit(t, (cx - t.get_width() // 2, cy - t.get_height() // 2))
                elif slot["type"] == "clock":
                    pygame.draw.circle(surface, (0, 0, 139), (cx, cy), 8)
                    pygame.draw.circle(surface, (255, 215, 0), (cx, cy), 8, 1)
                    pygame.draw.line(surface, (255, 215, 0), (cx, cy), (cx, cy - 5), 1)
                elif slot["type"] == "shrink":
                    pygame.draw.rect(surface, (128, 0, 128), (cx - 3, cy - 4, 6, 9))
                    pygame.draw.rect(surface, (100, 0, 100), (cx - 2, cy - 6, 4, 3))
                elif slot["type"] == "rocket":
                    pygame.draw.rect(surface, (220, 20, 60), (cx - 5, cy - 1, 10, 5))
                    pygame.draw.rect(surface, (220, 20, 60), (cx - 5, cy - 4, 3, 4))
                    pygame.draw.rect(surface, (255, 140, 0), (cx - 4, cy + 4, 2, 3))

                if slot["count"] > 1:
                    badge = small_font.render(str(slot["count"]), True, WHITE)
                    surface.blit(badge, (x + self.SLOT_SIZE - badge.get_width() - 1, y + 1))

        # Selected item name below slots
        if self.selected is not None and self.slots[self.selected]:
            item_type = self.slots[self.selected]["type"]
            name = TYPE_NAMES.get(item_type, item_type.upper())
            name_surf = name_font.render(name, True, (255, 255, 0))
            name_x = start_x + self.selected * self.SLOT_SIZE + self.SLOT_SIZE // 2 - name_surf.get_width() // 2
            surface.blit(name_surf, (name_x, y + self.SLOT_SIZE + 2))

        if self.full_flash > 0:
            blink = (self.full_flash // 6) % 2
            if blink:
                warn = pygame.font.SysFont("consolas", 16, bold=True).render("FULL", True, (220, 20, 60))
                surface.blit(warn, (start_x + total_w + 10, y + 6))

    def reset(self):
        self.slots = [None] * self.SLOTS
        self.selected = 0
        self.full_flash = 0
        self.use_flash = 0


class Dino:
    def __init__(self):
        self.x = 80
        self.stand_h = 50
        self.duck_h = 25
        self.w = 40
        self.h = self.stand_h
        self.y = HEIGHT - 100 - self.h
        self.vel_y = 0
        self.jumping = False
        self.ducking = False
        self.gravity = 0.8
        self.jump_power = -14
        self.double_jump_power = -14
        self.ground_y = HEIGHT - 100 - self.stand_h

        # Double jump / Glide state
        self.jump_count = 0
        self.gliding = False
        self.glide_timer = 0
        self.glide_max_time = 3 * FPS  # 3 seconds
        self.glide_gravity = 0.8 / 5  # ~1/5 normal gravity
        self.glide_speed_boost = 2
        self.particles = []
        self.ring_particles = []
        self.dust_particles = []
        self.dust_timer = 0
        self.flicker_timer = 0
        self.run_frame = 0
        self.double_jump_cooldown = 0

    def jump(self, reverse=False):
        if self.ducking:
            return
        if reverse:
            if not self.jumping:
                self.vel_y = -self.jump_power
                self.jumping = True
                self.jump_count = 1
                self.gliding = False
            elif self.jump_count == 1:
                self.vel_y = -self.double_jump_power
                self.jump_count = 2
                self.double_jump_cooldown = 12
                self.ring_particles.append(RingParticle(
                    self.x + self.w // 2, self.y + self.h // 2
                ))
        else:
            if not self.jumping:
                self.vel_y = self.jump_power
                self.jumping = True
                self.jump_count = 1
                self.gliding = False
                # Takeoff dust burst
                for _ in range(random.randint(4, 6)):
                    dp = Particle(
                        self.x + self.w // 2 + random.randint(-10, 10),
                        self.y + self.h + random.randint(-3, 3),
                        color=(150, 150, 150)
                    )
                    dp.vx = random.uniform(-3, 1)
                    dp.vy = random.uniform(-1, 2)
                    dp.life = random.randint(10, 15)
                    dp.size = random.randint(3, 6)
                    self.dust_particles.append(dp)
            elif self.jump_count == 1:
                self.vel_y = self.double_jump_power
                self.jump_count = 2
                self.double_jump_cooldown = 12
                self.ring_particles.append(RingParticle(
                    self.x + self.w // 2, self.y + self.h // 2
                ))
            for _ in range(8):
                self.particles.append(Particle(
                    self.x + self.w // 2 + random.randint(-10, 10),
                    self.y + self.h // 2 + random.randint(-10, 10)
                ))

    def start_glide(self):
        if self.jump_count == 2 and self.jumping and not self.gliding:
            self.gliding = True
            self.glide_timer = 0
            for _ in range(12):
                self.particles.append(Particle(
                    self.x + self.w // 2 + random.randint(-15, 15),
                    self.y + self.h // 2 + random.randint(-10, 10)
                ))

    def release_glide(self):
        if self.gliding:
            self.gliding = False

    def duck(self, active):
        self.ducking = active
        if active and not self.jumping:
            self.h = self.duck_h
            self.y = HEIGHT - 100 - self.h

    def update(self, gravity_reversed=False):
        self.double_jump_cooldown = max(0, self.double_jump_cooldown - 1)
        g = -self.gravity if gravity_reversed else self.gravity
        if gravity_reversed:
            land_y = 10  # ceiling landing position
        else:
            land_y = self.ground_y

        if self.jumping:
            if self.gliding:
                self.vel_y += self.glide_gravity * (-1 if gravity_reversed else 1)
                if abs(self.vel_y) > 2:
                    self.vel_y = 2 * (-1 if gravity_reversed else 1)
                self.y += self.vel_y
                self.glide_timer += 1
                self.flicker_timer += 1
                if self.glide_timer % 3 == 0:
                    sp = Particle(
                        self.x + self.w // 2 + random.randint(-5, 5),
                        self.y + self.h + random.randint(0, 5),
                        color=(255, 255, 255)
                    )
                    sp.vx = random.uniform(-1, 1)
                    sp.vy = random.uniform(0, 2)
                    sp.life = random.randint(20, 30)
                    sp.size = random.randint(1, 2)
                    self.particles.append(sp)
                if self.glide_timer >= self.glide_max_time:
                    self.gliding = False
            else:
                self.vel_y += g
                self.y += self.vel_y

            if gravity_reversed:
                if self.y <= land_y:
                    self.y = land_y
                    self.vel_y = 0
                    self.jumping = False
                    self.jump_count = 0
                    self.gliding = False
                    self.glide_timer = 0
            else:
                if self.y >= land_y:
                    self.y = land_y
                    self.vel_y = 0
                    self.jumping = False
                    self.jump_count = 0
                    self.gliding = False
                    self.glide_timer = 0

        if not self.jumping and not self.ducking:
            self.h = self.stand_h
            self.y = land_y
            self.run_frame += 1
            # Running dust
            self.dust_timer += 1
            if self.dust_timer % 5 == 0:
                for _ in range(random.randint(1, 2)):
                    dp = Particle(
                        self.x + random.randint(-5, 0),
                        self.y + self.h + random.randint(-3, 0),
                        color=(150, 150, 150)
                    )
                    dp.vx = random.uniform(-3, -1)
                    dp.vy = random.uniform(-1, 1)
                    dp.life = random.randint(10, 15)
                    dp.size = random.randint(2, 4)
                    self.dust_particles.append(dp)

        for p in self.particles:
            p.update()
        self.particles = [p for p in self.particles if p.alive()]
        for rp in self.ring_particles:
            rp.update()
        self.ring_particles = [rp for rp in self.ring_particles if rp.alive()]
        for dp in self.dust_particles:
            dp.update()
        self.dust_particles = [dp for dp in self.dust_particles if dp.alive()]

    def draw(self, surface, night, offset_x=0, offset_y=0):
        WHITE_SUIT = (255, 255, 255)
        HAT_BAND = (0, 0, 139)
        SKIN = (255, 220, 177)
        HAIR_BLACK = (20, 20, 20)
        GOLD = (255, 215, 0)
        LENS_BLUE = (173, 216, 230)
        TIE_RED = (220, 20, 60)
        SHOE_BLACK = (0, 0, 0)
        SHIRT_GRAY = (220, 220, 220)

        bx, by = self.x + offset_x, self.y + offset_y
        w = self.w
        h = self.h

        phase = self.run_frame % 20
        if phase < 10:
            leg_swing = int(5 * (phase / 5.0 - 1)) if phase > 5 else int(5 * (phase / 5.0))
        else:
            leg_swing = int(5 * ((phase - 10) / 5.0 - 1)) if (phase - 10) > 5 else int(5 * ((phase - 10) / 5.0))

        def draw_monocle(cx, cy, r=4):
            pygame.draw.circle(surface, GOLD, (cx, cy), r, 1)
            pygame.draw.circle(surface, LENS_BLUE, (cx, cy), r - 2)
            hl = pygame.Surface((2, 2), pygame.SRCALPHA)
            hl.fill((255, 255, 255, 200))
            surface.blit(hl, (cx - 1, cy - 2))

        def draw_face(fx, fy):
            pygame.draw.rect(surface, SKIN, (fx, fy, 14, 12))
            pygame.draw.rect(surface, SKIN, (fx + 13, fy + 6, 3, 3))
            pygame.draw.rect(surface, SKIN, (fx - 1, fy + 4, 3, 4))
            pygame.draw.rect(surface, HAIR_BLACK, (fx - 1, fy - 1, 15, 3))
            pygame.draw.rect(surface, HAIR_BLACK, (fx - 2, fy + 1, 3, 5))
            draw_monocle(fx + 12, fy + 7, 4)
            pygame.draw.arc(surface, SHOE_BLACK, (fx + 6, fy + 8, 6, 4), 3.14, 6.28, 1)

        def draw_hat(hx, hy):
            pygame.draw.rect(surface, WHITE_SUIT, (hx, hy, 14, 14))
            pygame.draw.rect(surface, WHITE_SUIT, (hx - 4, hy + 13, 22, 3))
            pygame.draw.rect(surface, HAT_BAND, (hx, hy + 11, 14, 2))

        def draw_tie(tx, ty):
            pygame.draw.rect(surface, TIE_RED, (tx, ty, 3, 8))
            pygame.draw.rect(surface, TIE_RED, (tx - 1, ty, 5, 3))

        def draw_gloves(gx1, gy1, gx2, gy2):
            pygame.draw.rect(surface, WHITE_SUIT, (gx1, gy1, 4, 4))
            pygame.draw.rect(surface, WHITE_SUIT, (gx2, gy2, 4, 4))

        if self.gliding:
            flicker = 220 + int(35 * abs((self.flicker_timer % 10) - 5) / 5)
            wing_c = (flicker, flicker, flicker)
            pygame.draw.polygon(surface, wing_c, [
                (bx - 2, by + 10), (bx - 40, by + 2),
                (bx - 45, by + 22), (bx - 10, by + 30),
                (bx - 2, by + 26),
            ])
            pygame.draw.rect(surface, WHITE_SUIT, (bx + 4, by + 16, w - 8, 12))
            draw_tie(bx + 10, by + 16)
            draw_face(bx + 6, by + 4)
            draw_hat(bx + 5, by - 12)
            draw_gloves(bx + w - 2, by + 20, bx + w + 2, by + 26)
            pygame.draw.rect(surface, WHITE_SUIT, (bx + 2, by + 28, 4, 8))
            pygame.draw.rect(surface, WHITE_SUIT, (bx + 8, by + 28, 4, 8))
            pygame.draw.rect(surface, SHOE_BLACK, (bx, by + 36, 5, 3))
            pygame.draw.rect(surface, SHOE_BLACK, (bx + 6, by + 36, 5, 3))

        elif self.ducking:
            pygame.draw.polygon(surface, WHITE_SUIT, [
                (bx - 2, by + 4), (bx + 22, by + 12),
                (bx + 28, by + 6), (bx - 2, by - 2),
            ])
            pygame.draw.rect(surface, WHITE_SUIT, (bx + 4, by + 2, w - 8, h - 4))
            draw_tie(bx + 10, by + 2)
            pygame.draw.rect(surface, SKIN, (bx + 8, by - 6, 12, 10))
            pygame.draw.rect(surface, SKIN, (bx + 20, by - 3, 2, 3))
            pygame.draw.rect(surface, HAIR_BLACK, (bx + 7, by - 8, 13, 3))
            pygame.draw.rect(surface, HAIR_BLACK, (bx + 6, by - 6, 3, 4))
            draw_monocle(bx + 19, by - 2, 3)
            draw_hat(bx + 6, by - 20)
            draw_gloves(bx + 2, by + 8, bx + w - 4, by + 8)
            pygame.draw.rect(surface, WHITE_SUIT, (bx + 8, by + h, 4, 5))
            pygame.draw.rect(surface, WHITE_SUIT, (bx + 16, by + h, 4, 5))
            pygame.draw.rect(surface, SHOE_BLACK, (bx + 7, by + h + 5, 5, 3))
            pygame.draw.rect(surface, SHOE_BLACK, (bx + 15, by + h + 5, 5, 3))

        else:
            if self.jumping:
                if self.jump_count >= 2:
                    cape_phase = (self.run_frame % 10)
                    cape_up = 6 if cape_phase < 5 else 2
                    pygame.draw.polygon(surface, WHITE_SUIT, [
                        (bx - 2, by + 14), (bx - 22, by + 8 - cape_up),
                        (bx - 28, by + 18 - cape_up), (bx - 16, by + 30),
                        (bx - 2, by + h - 6),
                    ])
                    pygame.draw.polygon(surface, WHITE_SUIT, [
                        (bx - 2, by + 18), (bx - 32, by + 12 - cape_up),
                        (bx - 36, by + 26 - cape_up), (bx - 2, by + h - 2),
                    ])
                else:
                    pygame.draw.polygon(surface, WHITE_SUIT, [
                        (bx - 2, by + 14), (bx - 16, by + 6),
                        (bx - 22, by + 18), (bx - 2, by + h - 6),
                    ])
            else:
                wave = int(4 * ((self.run_frame % 20) / 10.0 - 1))
                cape_y_off = wave
                pygame.draw.polygon(surface, WHITE_SUIT, [
                    (bx - 2, by + 14), (bx - 18, by + 8 + cape_y_off),
                    (bx - 24, by + 22 + cape_y_off), (bx - 14, by + 34),
                    (bx - 2, by + h - 4),
                ])
                pygame.draw.polygon(surface, WHITE_SUIT, [
                    (bx - 2, by + 20), (bx - 14, by + 16 + cape_y_off),
                    (bx - 18, by + 28 + cape_y_off), (bx - 2, by + h - 2),
                ])

            pygame.draw.rect(surface, WHITE_SUIT, (bx + 4, by + 16, w - 10, h - 16))
            pygame.draw.rect(surface, SHIRT_GRAY, (bx + 2, by + 16, 4, 6))
            draw_tie(bx + 12, by + 17)

            if self.jumping:
                arm_y = by + 18
                pygame.draw.rect(surface, WHITE_SUIT, (bx + w - 4, arm_y - 4, 4, 8))
                pygame.draw.rect(surface, WHITE_SUIT, (bx - 2, arm_y, 4, 8))
                draw_gloves(bx + w - 4, arm_y - 8, bx - 2, arm_y + 8)
            else:
                arm_swing = leg_swing
                pygame.draw.rect(surface, WHITE_SUIT, (bx + w - 2, by + 18 + arm_swing, 4, 10))
                pygame.draw.rect(surface, WHITE_SUIT, (bx - 2, by + 22 - arm_swing, 4, 10))
                draw_gloves(bx + w - 2, by + 28 + arm_swing, bx - 2, by + 32 - arm_swing)

            draw_face(bx + 8, by + 4)
            draw_hat(bx + 7, by - 12)

            if self.jumping and self.jump_count >= 2:
                pygame.draw.rect(surface, WHITE_SUIT, (bx + 8, by + h, 4, 7))
                pygame.draw.rect(surface, WHITE_SUIT, (bx + 8 + 4, by + h + 5, 4, 4))
                pygame.draw.rect(surface, WHITE_SUIT, (bx + 18, by + h, 4, 7))
                pygame.draw.rect(surface, WHITE_SUIT, (bx + 18 + 4, by + h + 5, 4, 4))
                pygame.draw.rect(surface, SHOE_BLACK, (bx + 11, by + h + 9, 5, 3))
                pygame.draw.rect(surface, SHOE_BLACK, (bx + 21, by + h + 9, 5, 3))
            elif self.jumping:
                pygame.draw.rect(surface, WHITE_SUIT, (bx + 8, by + h, 4, 8))
                pygame.draw.rect(surface, WHITE_SUIT, (bx + 18, by + h, 4, 8))
                pygame.draw.rect(surface, SHOE_BLACK, (bx + 7, by + h + 8, 5, 3))
                pygame.draw.rect(surface, SHOE_BLACK, (bx + 17, by + h + 8, 5, 3))
            else:
                front_x = bx + 16 + leg_swing
                pygame.draw.rect(surface, WHITE_SUIT, (front_x, by + h, 4, 8))
                pygame.draw.rect(surface, WHITE_SUIT, (front_x + 2, by + h + 6, 4, 4))
                pygame.draw.rect(surface, SHOE_BLACK, (front_x + 1, by + h + 10, 5, 3))
                back_x = bx + 8 - leg_swing
                pygame.draw.rect(surface, WHITE_SUIT, (back_x, by + h, 4, 8))
                pygame.draw.rect(surface, WHITE_SUIT, (back_x - 2, by + h + 6, 4, 4))
                pygame.draw.rect(surface, SHOE_BLACK, (back_x - 3, by + h + 10, 5, 3))

        for p in self.particles:
            p.draw(surface)
        for rp in self.ring_particles:
            rp.draw(surface)
        for dp in self.dust_particles:
            dp.draw(surface)

    def get_rect(self):
        if self.gliding:
            glide_h = int(self.h * 0.6)
            glide_w = self.w + 20
            glide_x = self.x - 10
            glide_y = self.y + (self.h - glide_h)
            return pygame.Rect(glide_x, glide_y, glide_w, glide_h)
        return pygame.Rect(self.x, self.y, self.w, self.h)


class Spike:
    HEIGHTS = [25, 35, 45]

    def __init__(self, speed):
        self.w = 20
        self.h = random.choice(self.HEIGHTS)
        self.x = WIDTH + random.randint(0, 50)
        self.y = HEIGHT - 100
        self.speed = speed

    def update(self):
        self.x -= self.speed

    def draw(self, surface, night):
        color = NIGHT_OBSTACLE if night else (60, 60, 60)
        tip = (self.x + 10, self.y - self.h)
        left = (self.x, self.y)
        right = (self.x + 20, self.y)
        pygame.draw.polygon(surface, color, [tip, left, right])
        # Highlight edge
        hl = (100, 100, 100) if not night else (180, 255, 180)
        pygame.draw.line(surface, hl, left, tip, 1)

    def off_screen(self):
        return self.x + self.w < 0

    def get_rect(self):
        return pygame.Rect(self.x, self.y - self.h, self.w, self.h)


class BulletWarning:
    def __init__(self, target_y, speed, warning_sec=2.5):
        self.target_y = target_y
        self.speed = speed
        self.timer = int(warning_sec * FPS)
        self.spawned = False
        self.total_time = self.timer

    def update(self):
        self.timer -= 1
        if self.timer <= 0:
            self.spawned = True

    def draw(self, surface):
        blink_cycle = self.timer % 18
        alpha = 200 if blink_cycle < 9 else 60
        dash_len = 8
        gap = 6
        progress = 1.0 - (self.timer / self.total_time)
        line_end = int(WIDTH - 10 - progress * (WIDTH - 100))
        line_start = WIDTH - 10
        # Bounding box: from line_end to line_start, y from target_y-9 to target_y+9
        surf_x = max(0, line_end - 2)
        surf_y = max(0, self.target_y - 10)
        surf_w = min(WIDTH - surf_x, line_start - surf_x + 4)
        surf_h = 20
        dash_surf = pygame.Surface((surf_w, surf_h), pygame.SRCALPHA)
        x = line_start
        while x > line_end:
            seg_len = min(dash_len, x - line_end)
            if seg_len <= 0:
                break
            pygame.draw.rect(dash_surf, (220, 20, 60, alpha),
                             (x - seg_len - surf_x, self.target_y - 1 - surf_y, seg_len, 3))
            x -= dash_len + gap
        ax = line_end - surf_x
        ay = self.target_y - surf_y
        pygame.draw.polygon(dash_surf, (220, 20, 60, alpha), [
            (ax, ay), (ax + 12, ay - 8), (ax + 12, ay + 8)
        ])
        surface.blit(dash_surf, (surf_x, surf_y))

    def done(self):
        return self.spawned


class Bullet:
    def __init__(self, speed, y, score=0):
        self.w = 8
        self.h = 4
        self.x = WIDTH + 10
        self.y = y
        self.base_speed = speed
        self.bonus = min(score // 100, 8)

    def update(self):
        self.speed = self.base_speed + 4 + self.bonus
        self.x -= self.speed

    def draw(self, surface, night):
        trail_colors = [
            (255, 215, 0, 180),
            (255, 215, 0, 120),
            (255, 215, 0, 60),
        ]
        for i, color in enumerate(trail_colors):
            tx = self.x + self.w + i * 5
            tw = 4 - i
            trail_surf = pygame.Surface((tw, self.h), pygame.SRCALPHA)
            trail_surf.fill(color)
            surface.blit(trail_surf, (tx, self.y))
        pygame.draw.rect(surface, (220, 20, 60), (self.x, self.y, self.w, self.h))

    def off_screen(self):
        return self.x + self.w < 0

    def get_rect(self):
        return pygame.Rect(self.x, self.y, self.w, self.h)


class HomingMissile:
    """Red homing missile that tracks dino Y position."""
    def __init__(self, speed, dino_y):
        self.w = 10
        self.h = 10
        self.x = WIDTH + 10
        self.y = random.randint(50, HEIGHT - 120)
        self.speed = speed * 0.6
        self.target_y = dino_y
        self.trail = []

    def update(self):
        self.x -= self.speed
        dy = self.target_y - self.y
        if abs(dy) > 1:
            self.y += dy * 0.01
        self.trail.append((self.x + self.w, self.y + self.h // 2))
        if len(self.trail) > 8:
            self.trail.pop(0)

    def draw(self, surface, night):
        # Trail
        for i, (tx, ty) in enumerate(self.trail):
            alpha = 180 - i * 20
            if alpha > 0:
                s = pygame.Surface((4, 4), pygame.SRCALPHA)
                s.fill((255, 140, 0, alpha))
                surface.blit(s, (int(tx), int(ty - 2)))
        # Body
        pygame.draw.circle(surface, (220, 20, 60), (int(self.x + 5), int(self.y + 5)), 5)
        pygame.draw.circle(surface, (255, 80, 80), (int(self.x + 4), int(self.y + 4)), 2)

    def off_screen(self):
        return self.x + self.w < 0

    def get_rect(self):
        return pygame.Rect(self.x, self.y, self.w, self.h)


class GravityZone:
    """Purple zone that reverses jump direction."""
    def __init__(self, speed):
        self.w = 100
        self.h = 120
        self.x = WIDTH + 10
        self.y = HEIGHT - 100 - 120
        self.speed = speed * 0.5
        self.timer = 8 * FPS
        self.alpha = 30
        # Pre-generate fixed star positions (relative to zone)
        self.stars = [(random.randint(4, self.w - 4), random.randint(4, self.h - 4))
                      for _ in range(random.randint(8, 12))]

    def update(self):
        self.x -= self.speed
        self.timer -= 1

    def draw(self, surface, night):
        s = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        s.fill((128, 0, 128, self.alpha))
        surface.blit(s, (int(self.x), int(self.y)))
        # Stars flicker at fixed positions
        for rx, ry in self.stars:
            if random.random() < 0.6:
                bright = random.randint(150, 255)
                pygame.draw.circle(surface, (bright, bright, bright), (int(self.x) + rx, int(self.y) + ry), 1)
        # Border (3px thick)
        pygame.draw.rect(surface, (180, 0, 180, 80), (int(self.x), int(self.y), self.w, self.h), 3)
        # Arrow hint at top
        cx = int(self.x) + self.w // 2
        ty = int(self.y) + 6
        arrow_font = pygame.font.SysFont("consolas", 16, bold=True)
        arrow_text = arrow_font.render("↑↓", True, (255, 255, 255))
        surface.blit(arrow_text, (cx - arrow_text.get_width() // 2, ty))

    def off_screen(self):
        return self.x + self.w < 0

    def expired(self):
        return self.timer <= 0

    def get_rect(self):
        return pygame.Rect(self.x, self.y, self.w, self.h)


class Cloud:
    def __init__(self):
        self.x = WIDTH + random.randint(0, 200)
        self.y = random.randint(20, 80)
        self.w = 60 + random.randint(0, 40)
        self.h = 20 + random.randint(0, 10)
        self.speed = 0.5 + random.random() * 0.5

    def update(self):
        self.x -= self.speed

    def draw(self, surface, night):
        color = DARK_CLOUD if night else CLOUD_COLOR
        pygame.draw.ellipse(surface, color, (self.x, self.y, self.w, self.h))
        pygame.draw.ellipse(surface, color, (self.x + 10, self.y - 8, self.w * 0.6, self.h))
        pygame.draw.ellipse(surface, color, (self.x + self.w * 0.3, self.y - 5, self.w * 0.5, self.h))

    def off_screen(self):
        return self.x + self.w < -20


class ShieldItem:
    def __init__(self):
        self.x = WIDTH + random.randint(0, 100)
        self.base_y = HEIGHT - 100 - random.randint(40, 130)
        self.y = self.base_y
        self.w = 12
        self.h = 12
        self.speed = 0.7
        self.frame = random.randint(0, 60)
        self.collected = False

    def update(self):
        self.x -= self.speed
        self.frame += 1
        self.y = self.base_y + int(3 * ((self.frame % 60) / 30.0 - 1))

    def draw(self, surface, night):
        cx, cy = int(self.x + self.w // 2), int(self.y + self.h // 2)
        pygame.draw.circle(surface, (100, 200, 255), (cx, cy), 7)
        font = pygame.font.SysFont("consolas", 10, bold=True)
        text = font.render("S", True, WHITE)
        surface.blit(text, (cx - text.get_width() // 2, cy - text.get_height() // 2))

    def off_screen(self):
        return self.x + self.w < 0

    def get_rect(self):
        return pygame.Rect(self.x, self.y, self.w, self.h)


class AmmoItem:
    def __init__(self):
        self.x = WIDTH + random.randint(0, 100)
        self.base_y = HEIGHT - 100 - random.randint(40, 130)
        self.y = self.base_y
        self.w = 8
        self.h = 4
        self.speed = 0.7
        self.frame = random.randint(0, 60)
        self.collected = False

    def update(self):
        self.x -= self.speed
        self.frame += 1
        self.y = self.base_y + int(2 * ((self.frame % 60) / 30.0 - 1))

    def draw(self, surface, night):
        pygame.draw.rect(surface, (255, 215, 0), (self.x, self.y, self.w, self.h))
        pygame.draw.polygon(surface, (255, 215, 0), [
            (self.x + self.w, self.y),
            (self.x + self.w + 3, self.y + self.h // 2),
            (self.x + self.w, self.y + self.h),
        ])
        pygame.draw.rect(surface, (255, 240, 150), (self.x + 1, self.y, 3, 2))

    def off_screen(self):
        return self.x + self.w < 0

    def get_rect(self):
        return pygame.Rect(self.x, self.y, self.w + 3, self.h)


class ClockItem:
    def __init__(self):
        self.x = WIDTH + random.randint(0, 100)
        self.base_y = HEIGHT - 100 - random.randint(40, 130)
        self.y = self.base_y
        self.w = 15
        self.h = 15
        self.speed = 0.7
        self.frame = random.randint(0, 60)
        self.collected = False

    def update(self):
        self.x -= self.speed
        self.frame += 1
        self.y = self.base_y + int(3 * ((self.frame % 60) / 30.0 - 1))

    def draw(self, surface, night):
        cx, cy = int(self.x + self.w // 2), int(self.y + self.h // 2)
        pygame.draw.circle(surface, (0, 0, 139), (cx, cy), 7)
        pygame.draw.circle(surface, (255, 215, 0), (cx, cy), 7, 1)
        angle = (self.frame % 60) / 60.0 * 6.28
        hx = int(cx + 4 * 0.7)
        hy = int(cy - 4 * 0.7)
        pygame.draw.line(surface, (255, 215, 0), (cx, cy), (hx, hy), 1)

    def off_screen(self):
        return self.x + self.w < 0

    def get_rect(self):
        return pygame.Rect(self.x, self.y, self.w, self.h)


class ShrinkPotionItem:
    def __init__(self):
        self.x = WIDTH + random.randint(0, 100)
        self.base_y = HEIGHT - 100 - random.randint(40, 130)
        self.y = self.base_y
        self.w = 10
        self.h = 14
        self.speed = 0.7
        self.frame = random.randint(0, 60)
        self.collected = False

    def update(self):
        self.x -= self.speed
        self.frame += 1
        self.y = self.base_y + int(3 * ((self.frame % 60) / 30.0 - 1))

    def draw(self, surface, night):
        cx, cy = int(self.x + self.w // 2), int(self.y + self.h // 2)
        pygame.draw.rect(surface, (128, 0, 128), (cx - 4, cy - 3, 8, 10))
        pygame.draw.rect(surface, (180, 80, 220), (cx - 2, cy - 1, 4, 6))
        pygame.draw.rect(surface, (100, 0, 100), (cx - 3, cy - 5, 6, 3))
        if self.frame % 20 < 10:
            pygame.draw.circle(surface, (200, 100, 255), (cx + 3, cy - 7), 2)

    def off_screen(self):
        return self.x + self.w < 0

    def get_rect(self):
        return pygame.Rect(self.x, self.y, self.w, self.h)


class RocketBootsItem:
    def __init__(self):
        self.x = WIDTH + random.randint(0, 100)
        self.base_y = HEIGHT - 100 - random.randint(40, 130)
        self.y = self.base_y
        self.w = 12
        self.h = 10
        self.speed = 0.7
        self.frame = random.randint(0, 60)
        self.collected = False

    def update(self):
        self.x -= self.speed
        self.frame += 1
        self.y = self.base_y + int(3 * ((self.frame % 60) / 30.0 - 1))

    def draw(self, surface, night):
        cx, cy = int(self.x + self.w // 2), int(self.y + self.h // 2)
        pygame.draw.rect(surface, (220, 20, 60), (cx - 6, cy - 2, 12, 6))
        pygame.draw.rect(surface, (220, 20, 60), (cx - 6, cy - 5, 4, 4))
        if self.frame % 6 < 3:
            pygame.draw.rect(surface, (255, 140, 0), (cx - 5, cy + 4, 3, 4))
            pygame.draw.rect(surface, (255, 200, 0), (cx - 4, cy + 4, 2, 3))

    def off_screen(self):
        return self.x + self.w < 0

    def get_rect(self):
        return pygame.Rect(self.x, self.y, self.w, self.h)


class HeartKeyItem:
    def __init__(self):
        self.x = WIDTH + random.randint(0, 100)
        self.base_y = HEIGHT - 100 - random.randint(40, 130)
        self.y = self.base_y
        self.w = 15
        self.h = 15
        self.speed = 0.7
        self.frame = random.randint(0, 60)
        self.collected = False

    def update(self):
        self.x -= self.speed
        self.frame += 1
        self.y = self.base_y + int(3 * ((self.frame % 60) / 30.0 - 1))

    def draw(self, surface, night):
        cx, cy = int(self.x + self.w // 2), int(self.y + self.h // 2)
        pygame.draw.circle(surface, (255, 105, 180), (cx - 3, cy - 2), 3)
        pygame.draw.circle(surface, (255, 105, 180), (cx + 3, cy - 2), 3)
        pygame.draw.polygon(surface, (255, 105, 180), [
            (cx - 6, cy - 1), (cx + 6, cy - 1), (cx, cy + 5)
        ])
        pygame.draw.rect(surface, (255, 215, 0), (cx - 1, cy + 4, 2, 5))
        pygame.draw.rect(surface, (255, 215, 0), (cx - 1, cy + 7, 4, 2))
        if self.frame % 20 < 10:
            spark = pygame.Surface((3, 3), pygame.SRCALPHA)
            spark.fill((255, 255, 200, 200))
            surface.blit(spark, (cx + 5, cy - 6))

    def off_screen(self):
        return self.x + self.w < 0

    def get_rect(self):
        return pygame.Rect(self.x, self.y, self.w, self.h)


class PokerCard:
    SUITS = ["spade", "heart", "club", "diamond"]

    def __init__(self, x, y, speed):
        self.w = 20
        self.h = 30
        self.x = x
        self.y = y
        self.speed = speed + 8
        self.suit = random.choice(self.SUITS)

    def update(self):
        self.x += self.speed

    def draw(self, surface, night):
        pygame.draw.rect(surface, (255, 255, 255), (self.x, self.y, self.w, self.h))
        pygame.draw.rect(surface, (220, 20, 60), (self.x, self.y, self.w, self.h), 2)
        cx, cy = self.x + self.w // 2, self.y + self.h // 2
        suit_color = (220, 20, 60)
        if self.suit == "spade":
            pygame.draw.polygon(surface, suit_color, [
                (cx, cy - 6), (cx - 5, cy + 1), (cx + 5, cy + 1)
            ])
            pygame.draw.rect(surface, suit_color, (cx - 1, cy + 1, 2, 4))
        elif self.suit == "heart":
            pygame.draw.polygon(surface, suit_color, [
                (cx, cy + 5), (cx - 5, cy - 2), (cx + 5, cy - 2)
            ])
            pygame.draw.circle(surface, suit_color, (cx - 3, cy - 3), 3)
            pygame.draw.circle(surface, suit_color, (cx + 3, cy - 3), 3)
        elif self.suit == "club":
            pygame.draw.circle(surface, suit_color, (cx, cy - 4), 3)
            pygame.draw.circle(surface, suit_color, (cx - 4, cy + 1), 3)
            pygame.draw.circle(surface, suit_color, (cx + 4, cy + 1), 3)
            pygame.draw.rect(surface, suit_color, (cx - 1, cy + 1, 2, 4))
        elif self.suit == "diamond":
            pygame.draw.polygon(surface, suit_color, [
                (cx, cy - 6), (cx + 5, cy), (cx, cy + 6), (cx - 5, cy)
            ])

    def off_screen(self):
        return self.x > WIDTH + 20

    def get_rect(self):
        return pygame.Rect(self.x, self.y, self.w, self.h)


class Game:
    # Item round-robin order
    ITEM_CYCLE = ["ammo", "shield", "clock", "shrink", "rocket"]

    def __init__(self):
        self.dino = Dino()
        self.obstacles = []
        self.warnings = []
        self.items = []
        self.gravity_zones = []
        self.clouds = [Cloud() for _ in range(3)]
        self.poker_cards = []
        self.explosion_particles = []
        self.score = 0
        self.highscore = load_highscore()
        self.base_speed = 5
        self.speed = self.base_speed
        self.max_speed = 15
        self.speed_timer = 0
        self.item_drought_timer = 0
        self.total_time = 0
        self.game_over = False
        self.spawn_timer = 0
        self.night = False
        self.night_timer = 0
        self.day_night_interval = 30 * FPS
        self.transitioning = False
        self.transition_alpha = 0
        self.transition_target_night = False
        self.transition_duration = int(0.5 * FPS)

        # Parallax background layers
        self._generate_bg_layers()
        self.parallax_offset = 0.0

        # Ground pebbles
        self.pebbles = []
        for _ in range(80):
            self.pebbles.append([random.randint(0, WIDTH), random.randint(2, 18)])

        self.inventory = Inventory()
        # Shield three-phase state
        self.shield_active = False
        self.invisible = False
        self.invisible_timer = 0
        self.cooldown = False
        self.cooldown_timer = 0
        self.cd_flash = 0
        # Phase system (6 phases)
        self.phase = 1
        self.phase_timer = 0
        self.phase_transition_msg = ""
        self.phase_transition_timer = 0
        # Difficulty bonuses
        self.diff_bullet_speed_bonus = 0
        self.diff_homing_speed_mult = 1.0
        self.diff_max_obstacles = 3
        # Item round-robin
        self.item_cycle_idx = 0
        self.item_spawn_timer = 3 * FPS
        self.heart_item_timer = 15 * FPS
        # Dino original dimensions (for rocket scale restore)
        self.dino_orig_w = 40
        self.dino_orig_stand_h = 50
        self.dino_orig_duck_h = 25
        # Passive
        self.heart_keys = 0
        # Active effects
        self.time_stop = False
        self.time_stop_timer = 0
        self.shrunk = False
        self.shrink_timer_active = 0
        self.rocket_active = False
        self.rocket_timer_active = 0
        self.rocket_particles = []
        # Gravity state
        self.gravity_reversed = False
        self.gravity_zone_active = False
        # Newbie revival
        self.death_count = 0
        self.reviving = False
        self.revive_timer = 0
        self.revive_text_timer = 0
        self.revive_invisible = False

        self.font = pygame.font.SysFont("consolas", 20, bold=True)
        self.big_font = pygame.font.SysFont("consolas", 36, bold=True)
        self.big_font_cn = get_font(36, bold=True, chinese=True)

    def _generate_bg_layers(self):
        # Mountain points (jagged peaks, far parallax)
        self.mountain_points = []
        x = 0
        while x < WIDTH + 200:
            h = random.randint(40, 100)
            self.mountain_points.append((x, h))
            x += random.randint(40, 80)
        # Building silhouettes (rectangles, mid parallax)
        self.buildings = []
        x = 0
        while x < WIDTH + 200:
            w = random.randint(30, 70)
            h = random.randint(30, 80)
            self.buildings.append([x, w, h])
            x += w + random.randint(10, 40)

    def spawn_obstacle(self, speed):
        if self.phase == 1:
            return
        if self.phase == 2:
            # Spikes only, height 25 (lowest)
            s = Spike(speed)
            s.h = 25
            self.obstacles.append(s)
        elif self.phase == 3:
            # Spikes + bullets (3s warning)
            if random.random() < 0.5:
                self.obstacles.append(Spike(speed))
            else:
                bullet_y = HEIGHT - 100 - random.randint(10, 120)
                self.warnings.append(BulletWarning(bullet_y, speed, warning_sec=3.0))
        elif self.phase == 4:
            # Spikes + bullets (2.5s) + homing
            r = random.random()
            if r < 0.4:
                self.obstacles.append(Spike(speed))
            elif r < 0.7:
                bullet_y = HEIGHT - 100 - random.randint(10, 120)
                self.warnings.append(BulletWarning(bullet_y, speed))
            else:
                self.obstacles.append(HomingMissile(speed, self.dino.y))
        elif self.phase == 5:
            # Spikes + bullets + homing + gravity (3s)
            r = random.random()
            if r < 0.35:
                self.obstacles.append(Spike(speed))
            elif r < 0.6:
                bullet_y = HEIGHT - 100 - random.randint(10, 120)
                self.warnings.append(BulletWarning(bullet_y, speed))
            elif r < 0.8:
                self.obstacles.append(HomingMissile(speed, self.dino.y))
            else:
                gz = GravityZone(speed)
                self.gravity_zones.append(gz)
        else:
            # Phase 6+: all obstacles (spikes + bullets + homing + gravity)
            r = random.random()
            if r < 0.25:
                self.obstacles.append(Spike(speed))
            elif r < 0.5:
                bullet_y = HEIGHT - 100 - random.randint(10, 120)
                self.warnings.append(BulletWarning(bullet_y, speed))
            elif r < 0.75:
                self.obstacles.append(HomingMissile(speed, self.dino.y))
            else:
                gz = GravityZone(speed)
                self.gravity_zones.append(gz)

    def reset(self):
        self.dino = Dino()
        self.obstacles = []
        self.warnings = []
        self.items = []
        self.gravity_zones = []
        self.poker_cards = []
        self.explosion_particles = []
        self.score = 0
        self.speed = self.base_speed
        self.speed_timer = 0
        self.item_drought_timer = 0
        self.total_time = 0
        self.game_over = False
        self.spawn_timer = 0
        self.night = False
        self.night_timer = 0
        self.transitioning = False
        self.transition_alpha = 0
        self._generate_bg_layers()
        self.parallax_offset = 0.0
        self.pebbles = []
        for _ in range(80):
            self.pebbles.append([random.randint(0, WIDTH), random.randint(2, 18)])
        self.inventory.reset()
        self.shield_active = False
        self.invisible = False
        self.invisible_timer = 0
        self.cooldown = False
        self.cooldown_timer = 0
        self.cd_flash = 0
        self.phase = 1
        self.phase_timer = 0
        self.phase_transition_msg = ""
        self.phase_transition_timer = 0
        self.diff_bullet_speed_bonus = 0
        self.diff_homing_speed_mult = 1.0
        self.diff_max_obstacles = 3
        self.item_cycle_idx = 0
        self.item_spawn_timer = 3 * FPS
        self.heart_item_timer = 15 * FPS
        self.heart_keys = 0
        self.time_stop = False
        self.time_stop_timer = 0
        self.shrunk = False
        self.shrink_timer_active = 0
        self.rocket_active = False
        self.rocket_timer_active = 0
        self.rocket_particles = []
        self.gravity_reversed = False
        self.gravity_zone_active = False
        self.death_count = 0
        self.reviving = False
        self.revive_timer = 0
        self.revive_text_timer = 0
        self.revive_invisible = False

    def fire_poker_card(self):
        if len(self.poker_cards) < 3:
            dino = self.dino
            card_x = dino.x + dino.w
            card_y = dino.y + dino.h // 2 - 15
            self.poker_cards.append(PokerCard(card_x, card_y, self.speed))

    def handle_input(self):
        if self.reviving:
            return
        keys = pygame.key.get_pressed()
        self.dino.duck(keys[pygame.K_DOWN])

        if self.dino.jump_count == 2 and self.dino.jumping and self.dino.double_jump_cooldown == 0:
            if keys[pygame.K_SPACE] or keys[pygame.K_UP]:
                if not self.dino.gliding:
                    self.dino.start_glide()
            else:
                self.dino.release_glide()
        elif not (keys[pygame.K_SPACE] or keys[pygame.K_UP]):
            self.dino.release_glide()

    def update(self):
        if self.game_over:
            return

        # --- Always update: visual elements, timers, particles ---
        self.total_time += 1
        self.parallax_offset += self.speed

        # Phase tracking (6 phases)
        self.phase_timer += 1
        phase_sec = self.phase_timer / FPS
        PHASE_TIMES = {1: 15, 2: 40, 3: 80, 4: 140, 5: 220}
        PHASE_NAMES_CN = {
            2: "尖刺", 3: "子弹", 4: "导弹",
            5: "重力", 6: "地狱"
        }
        if self.phase < 6:
            threshold = PHASE_TIMES.get(self.phase)
            if threshold and phase_sec >= threshold:
                self.phase += 1
                cn = PHASE_NAMES_CN.get(self.phase, "")
                self.phase_transition_msg = f"准备！{cn}阶段来袭"
                self.phase_transition_timer = 3 * FPS
                self.spawn_timer = -3 * FPS

        if self.phase_transition_timer > 0:
            self.phase_transition_timer -= 1

        # Night timer + transition (always runs)
        self.night_timer += 1
        if self.night_timer >= self.day_night_interval:
            self.night_timer = 0
            self.transitioning = True
            self.transition_alpha = 0
            self.transition_target_night = not self.night

        if self.transitioning:
            self.transition_alpha += 255 / self.transition_duration
            if self.transition_alpha >= 255:
                self.night = self.transition_target_night
                self.transitioning = False
                self.transition_alpha = 0

        # Explosion particles (always update)
        for p in self.explosion_particles:
            p.update()
        self.explosion_particles = [p for p in self.explosion_particles if p.alive()]

        # Clouds (always update)
        for c in self.clouds:
            c.update()
        self.clouds = [c for c in self.clouds if not c.off_screen()]
        while len(self.clouds) < 3:
            self.clouds.append(Cloud())

        # Rocket particles (always update)
        for p in self.rocket_particles:
            p.update()
        self.rocket_particles = [p for p in self.rocket_particles if p.alive()]

        # Inventory (always update)
        self.inventory.update()

        # Revival text timer (runs independently of reviving state)
        if self.revive_text_timer > 0:
            self.revive_text_timer -= 1

        # --- Revival: skip core game logic, keep visuals running ---
        if self.reviving:
            self.revive_timer -= 1
            if self.revive_timer <= 0:
                self.reviving = False
            return

        # --- Core game logic (skipped during revival) ---
        self.score += 1

        # Difficulty scaling
        elapsed = self.total_time / FPS
        self.diff_bullet_speed_bonus = self.score // 200
        self.diff_homing_speed_mult = 1.0 + (self.score // 300) * 0.1
        self.diff_max_obstacles = min(3 + self.phase, 6)

        # Speed growth curve (very slow)
        if elapsed < 60:
            target_speed = 5
        elif elapsed < 180:
            target_speed = 5 + int((elapsed - 60) // 30)
        elif elapsed < 360:
            target_speed = 8 + int((elapsed - 180) // 60)
        else:
            target_speed = 11 + int((elapsed - 360) // 90)
        target_speed = min(target_speed, self.max_speed)
        if self.speed < target_speed:
            self.speed = target_speed

        # Rocket speed boost
        effective_speed = self.speed * 2 if self.rocket_active else self.speed

        # Obstacle spawning (per-phase intervals)
        self.spawn_timer += 1
        PHASE_INTERVALS = {1: 9999, 2: 120, 3: 100, 4: 90, 5: 80, 6: 80}
        interval = PHASE_INTERVALS.get(self.phase, 80)
        if self.phase == 6:
            # Phase 6: interval decreases over time, floor 50
            extra_sec = max(0, elapsed - 220)
            interval = max(50, 80 - int(extra_sec // 60) * 5)
        if self.spawn_timer >= interval:
            self.spawn_timer = 0
            if len(self.obstacles) < self.diff_max_obstacles:
                self.spawn_obstacle(effective_speed)

        if not self.time_stop:
            for w in self.warnings:
                w.update()
                if w.done():
                    b = Bullet(effective_speed, w.target_y, self.score)
                    b.bonus += self.diff_bullet_speed_bonus
                    self.obstacles.append(b)
            self.warnings = [w for w in self.warnings if not w.done()]

        self.dino.update(gravity_reversed=self.gravity_reversed)

        # Item spawning (round-robin)
        self.item_spawn_timer -= 1
        if self.item_spawn_timer <= 0:
            item_type = self.ITEM_CYCLE[self.item_cycle_idx % len(self.ITEM_CYCLE)]
            self.item_cycle_idx += 1
            TYPE_MAP = {
                "ammo": AmmoItem, "shield": ShieldItem, "clock": ClockItem,
                "shrink": ShrinkPotionItem, "rocket": RocketBootsItem
            }
            cls = TYPE_MAP.get(item_type)
            if cls and sum(1 for i in self.items if isinstance(i, cls)) < 1:
                self.items.append(cls())
            next_type = self.ITEM_CYCLE[self.item_cycle_idx % len(self.ITEM_CYCLE)]
            self.item_spawn_timer = (3 * FPS) if next_type == "ammo" else (4 * FPS)
        # Heart key (independent timer, every 15s)
        self.heart_item_timer -= 1
        if self.heart_item_timer <= 0:
            if sum(1 for i in self.items if isinstance(i, HeartKeyItem)) < 1:
                self.items.append(HeartKeyItem())
            self.heart_item_timer = 15 * FPS

        # Item drought safeguard (Bug3: only reset on shield/heart key)
        self.item_drought_timer += 1
        if self.item_drought_timer >= 15 * FPS:
            if not self.shield_active and self.heart_keys <= 0:
                if random.random() < 0.5:
                    self.items.append(ShieldItem())
                else:
                    self.items.append(HeartKeyItem())
                self.item_drought_timer = 0

        for item in self.items:
            item.speed = self.speed * 0.5
            item.update()
        self.items = [i for i in self.items if not i.off_screen() and not i.collected]

        # Item collision
        PICKUP_COLORS = {
            AmmoItem: (255, 215, 0),
            ShieldItem: (100, 200, 255),
            ClockItem: (0, 0, 139),
            ShrinkPotionItem: (128, 0, 128),
            RocketBootsItem: (220, 20, 60),
            HeartKeyItem: (255, 105, 180),
        }
        dino_rect = self.dino.get_rect()
        for item in self.items:
            if dino_rect.colliderect(item.get_rect()):
                collected = False
                if isinstance(item, AmmoItem):
                    if self.inventory.add("ammo"):
                        item.collected = True
                        collected = True
                elif isinstance(item, ShieldItem):
                    if not self.cooldown and not self.shield_active:
                        item.collected = True
                        self.shield_active = True
                        self.inventory.add_visual("shield")
                        collected = True
                elif isinstance(item, ClockItem):
                    if self.inventory.add("clock"):
                        item.collected = True
                        collected = True
                elif isinstance(item, ShrinkPotionItem):
                    if self.inventory.add("shrink"):
                        item.collected = True
                        collected = True
                elif isinstance(item, RocketBootsItem):
                    if self.inventory.add("rocket"):
                        item.collected = True
                        collected = True
                elif isinstance(item, HeartKeyItem):
                    item.collected = True
                    self.heart_keys += 1
                    collected = True
                if collected:
                    # Bug3: only reset drought on shield/heart key
                    if isinstance(item, (ShieldItem, HeartKeyItem)):
                        self.item_drought_timer = 0
                    color = PICKUP_COLORS.get(type(item), (255, 255, 255))
                    cx = item.x + item.w // 2
                    cy = item.y + item.h // 2
                    for _ in range(6):
                        gp = Particle(cx, cy, color=color)
                        gp.vx = random.uniform(-2, 2)
                        gp.vy = random.uniform(-4, -1)
                        gp.life = random.randint(15, 25)
                        self.explosion_particles.append(gp)

        # Gravity zone updates
        if not self.time_stop:
            for gz in self.gravity_zones:
                gz.update()
            self.gravity_zones = [gz for gz in self.gravity_zones if not gz.off_screen() and not gz.expired()]
        # Check if dino is in gravity zone (state-based to prevent edge jitter)
        was_in_gravity = self.gravity_zone_active
        dino_rect = self.dino.get_rect()
        self.gravity_zone_active = False
        for gz in self.gravity_zones:
            if dino_rect.colliderect(gz.get_rect()):
                self.gravity_zone_active = True
                break

        # Just entered gravity zone
        if self.gravity_zone_active and not was_in_gravity:
            if not self.dino.jumping:
                self.dino.vel_y = -5
                self.dino.jumping = True
                self.dino.jump_count = 1

        # Just left gravity zone
        if not self.gravity_zone_active and was_in_gravity:
            self.dino.vel_y = 5
            self.dino.jumping = True
            self.dino.jump_count = 1

        self.gravity_reversed = self.gravity_zone_active

        # Homing missile tracking update
        for obs in self.obstacles:
            if isinstance(obs, HomingMissile):
                obs.target_y = self.dino.y

        # Glide speed boost
        if self.dino.gliding:
            for obs in self.obstacles:
                obs.x -= self.dino.glide_speed_boost
        # Rocket speed boost
        rocket_speed_extra = 0
        if self.rocket_active:
            rocket_speed_extra = self.speed
        # Time stop freezes obstacles
        if not self.time_stop:
            for obs in self.obstacles:
                if isinstance(obs, Bullet):
                    obs.base_speed = self.speed
                elif isinstance(obs, HomingMissile):
                    obs.speed = (self.speed + rocket_speed_extra) * 0.6 * self.diff_homing_speed_mult
                else:
                    obs.speed = self.speed + rocket_speed_extra
                obs.update()
            self.obstacles = [o for o in self.obstacles if not o.off_screen()]
        # Rocket destroys spikes and bullets on contact
        if self.rocket_active:
            dino_rect = self.dino.get_rect()
            to_remove = []
            for obs in self.obstacles:
                if isinstance(obs, Spike) and dino_rect.colliderect(obs.get_rect()):
                    to_remove.append(obs)
                    for _ in range(8):
                        self.explosion_particles.append(Particle(
                            int(obs.x + 10), int(obs.y - obs.h // 2)
                        ))
                elif isinstance(obs, Bullet) and dino_rect.colliderect(obs.get_rect()):
                    to_remove.append(obs)
                    for _ in range(6):
                        self.explosion_particles.append(Particle(
                            int(obs.x + obs.w // 2), int(obs.y + obs.h // 2)
                        ))
            self.obstacles = [o for o in self.obstacles if o not in to_remove]

        # Update poker cards
        for card in self.poker_cards:
            card.speed = self.speed + 8
            card.update()
        self.poker_cards = [c for c in self.poker_cards if not c.off_screen()]

        # Poker card vs bullet collision
        cards_to_remove = []
        bullets_to_remove = []
        for card in self.poker_cards:
            card_rect = card.get_rect()
            for obs in self.obstacles:
                if isinstance(obs, Bullet) and card_rect.colliderect(obs.get_rect()):
                    cx = int(obs.x + obs.w // 2)
                    cy = int(obs.y + obs.h // 2)
                    for _ in range(10):
                        self.explosion_particles.append(Particle(cx, cy))
                    cards_to_remove.append(card)
                    bullets_to_remove.append(obs)
                    break
        self.poker_cards = [c for c in self.poker_cards if c not in cards_to_remove]
        self.obstacles = [o for o in self.obstacles if o not in bullets_to_remove]

        # Collision
        if not self.invisible:
            dino_rect = self.dino.get_rect()
            for obs in self.obstacles:
                hit = dino_rect.colliderect(obs.get_rect())
                if hit:
                    if self.shield_active:
                        self.shield_active = False
                        self.inventory.remove_visual("shield")
                        self.invisible = True
                        self.invisible_timer = 5 * FPS
                        self.obstacles.remove(obs)
                        break
                    else:
                        if self.heart_keys > 0:
                            self.heart_keys -= 1
                            self.obstacles.remove(obs)
                            self.invisible = True
                            self.invisible_timer = 3 * FPS
                            break
                        # Newbie revival: first 2 deaths get a free heart key
                        if self.death_count < 2:
                            self.death_count += 1
                            self.heart_keys = max(self.heart_keys, 1)
                            self.heart_keys -= 1
                            self.reviving = True
                            self.revive_timer = int(1.5 * FPS)
                            self.revive_text_timer = 2 * FPS
                            # Gold burst particles
                            cx = self.dino.x + self.dino.w // 2
                            cy = self.dino.y + self.dino.h // 2
                            for _ in range(20):
                                gp = Particle(cx, cy, color=(255, 215, 0))
                                gp.vx = random.uniform(-5, 5)
                                gp.vy = random.uniform(-5, 5)
                                gp.life = random.randint(25, 40)
                                self.explosion_particles.append(gp)
                            self.obstacles.clear()
                            self.warnings.clear()
                            self.gravity_zones.clear()
                            self.dino = Dino()
                            self.gravity_reversed = False
                            self.gravity_zone_active = False
                            self.spawn_timer = -3 * FPS
                            self.invisible = True
                            self.invisible_timer = 2 * FPS
                            self.revive_invisible = True
                            break
                        self.game_over = True
                        if self.score > self.highscore:
                            self.highscore = self.score
                            save_highscore(self.highscore)
                        break

        # Invisible timer
        if self.invisible:
            self.invisible_timer -= 1
            if self.invisible_timer <= 0:
                self.invisible = False
                self.revive_invisible = False
                self.cooldown = True
                self.cooldown_timer = 5 * FPS

        # Cooldown timer
        if self.cooldown:
            self.cooldown_timer -= 1
            if self.cooldown_timer <= 0:
                self.cooldown = False

        if self.cd_flash > 0:
            self.cd_flash -= 1

        # Active effect timers
        if self.time_stop:
            self.time_stop_timer -= 1
            if self.time_stop_timer <= 0:
                self.time_stop = False
        if self.shrunk:
            self.shrink_timer_active -= 1
            if self.shrink_timer_active <= 0:
                self.shrunk = False
                self.dino.w = 40
                self.dino.stand_h = 50
                self.dino.duck_h = 25
                self.dino.ground_y = HEIGHT - 100 - self.dino.stand_h
                if not self.dino.jumping:
                    self.dino.h = self.dino.stand_h
                    self.dino.y = self.dino.ground_y
        if self.rocket_active:
            self.rocket_timer_active -= 1
            # Bigger flame particles
            if self.rocket_timer_active % 2 == 0:
                for _ in range(2):
                    p = Particle(
                        self.dino.x + random.randint(-8, 8),
                        self.dino.y + self.dino.h + random.randint(-5, 5)
                    )
                    p.size = random.randint(5, 10)
                    p.vy = random.uniform(1, 4)
                    self.rocket_particles.append(p)
            # Gold aura particles
            if self.rocket_timer_active % 3 == 0:
                gp = Particle(
                    self.dino.x + random.randint(-15, self.dino.w + 15),
                    self.dino.y + random.randint(-10, self.dino.h + 10),
                    color=(255, 215, 0)
                )
                gp.vx = random.uniform(-1, 1)
                gp.vy = random.uniform(-2, 0)
                gp.size = random.randint(2, 4)
                self.rocket_particles.append(gp)
            if self.rocket_timer_active <= 0:
                self.rocket_active = False
                # Restore dino size
                self.dino.w = self.dino_orig_w
                self.dino.stand_h = self.dino_orig_stand_h
                self.dino.duck_h = self.dino_orig_duck_h
                self.dino.ground_y = HEIGHT - 100 - self.dino.stand_h
                if not self.dino.jumping:
                    self.dino.h = self.dino.stand_h
                    self.dino.y = self.dino.ground_y

    def draw(self, paused=False):
        # Background
        if self.transitioning:
            t = self.transition_alpha / 255
            if self.transition_target_night:
                bg_r = int(200 + (DARK_BG[0] - 200) * t)
                bg_g = int(200 + (DARK_BG[1] - 200) * t)
                bg_b = int(200 + (DARK_BG[2] - 200) * t)
            else:
                bg_r = int(DARK_BG[0] + (200 - DARK_BG[0]) * t)
                bg_g = int(DARK_BG[1] + (200 - DARK_BG[1]) * t)
                bg_b = int(DARK_BG[2] + (200 - DARK_BG[2]) * t)
            screen.fill((bg_r, bg_g, bg_b))
        else:
            screen.fill(DARK_BG if self.night else LIGHT_GRAY)

        # --- Background parallax layers ---
        bg_color = DARK_BG if self.night else LIGHT_GRAY

        # Mountains (far parallax, 0.2x speed)
        mtn_base_y = HEIGHT - 100
        mtn_color = (60, 65, 75) if self.night else (160, 165, 175)
        mtn_offset = int(self.parallax_offset * 0.2) % (WIDTH + 200)
        mtn_pts = []
        for px, ph in self.mountain_points:
            sx = px - mtn_offset
            while sx < -100:
                sx += WIDTH + 200
            while sx > WIDTH + 100:
                sx -= WIDTH + 200
            mtn_pts.append((int(sx), mtn_base_y - ph))
        mtn_pts.sort(key=lambda p: p[0])
        pts = [(0, mtn_base_y)] + mtn_pts + [(WIDTH, mtn_base_y)]
        if len(pts) >= 3:
            pygame.draw.polygon(screen, mtn_color, pts)

        # Buildings (mid parallax, 0.5x speed)
        bld_base_y = HEIGHT - 100
        bld_color = (50, 55, 65) if self.night else (140, 145, 155)
        bld_offset = int(self.parallax_offset * 0.5) % (WIDTH + 200)
        for bx, bw, bh in self.buildings:
            sx = bx - bld_offset
            while sx < -100:
                sx += WIDTH + 200
            while sx > WIDTH + 100:
                sx -= WIDTH + 200
            pygame.draw.rect(screen, bld_color, (int(sx), bld_base_y - bh, bw, bh))

        # Ground runway (20px high)
        ground_color = NIGHT_GROUND if self.night else GRAY
        ground_y = HEIGHT - 100
        pygame.draw.rect(screen, ground_color, (0, ground_y, WIDTH, 20))
        # Ground top edge highlight
        edge_color = tuple(min(255, c + 30) for c in ground_color)
        pygame.draw.line(screen, edge_color, (0, ground_y), (WIDTH, ground_y), 2)
        # Pebbles
        pebble_color = tuple(min(255, c + 50) for c in ground_color)
        ground_speed = int(self.speed)
        for peb in self.pebbles:
            peb[0] -= ground_speed
            if peb[0] < 0:
                peb[0] = WIDTH + random.randint(0, 20)
                peb[1] = random.randint(2, 18)
            pygame.draw.circle(screen, pebble_color, (int(peb[0]), ground_y + peb[1]), random.choice([1, 1, 2]))

        for c in self.clouds:
            c.draw(screen, self.night)

        for gz in self.gravity_zones:
            gz.draw(screen, self.night)

        for w in self.warnings:
            w.draw(screen)

        for obs in self.obstacles:
            obs.draw(screen, self.night)

        for item in self.items:
            item.draw(screen, self.night)

        for card in self.poker_cards:
            card.draw(screen, self.night)

        for p in self.explosion_particles:
            p.draw(screen)

        # Draw dino (invisible: blue tint overlay covering full dino)
        if self.reviving:
            self.dino.draw(screen, self.night)
            dino_rect = self.dino.get_rect()
            ox = dino_rect.x - 50
            oy = dino_rect.y - 20
            ow = dino_rect.width + 80
            oh = dino_rect.height + 40
            pulse = int(100 + 60 * abs((self.revive_timer % 20) - 10) / 10.0)
            overlay = pygame.Surface((ow, oh), pygame.SRCALPHA)
            overlay.fill((255, 215, 0, pulse))
            screen.blit(overlay, (ox, oy))
            border = pygame.Surface((ow + 4, oh + 4), pygame.SRCALPHA)
            pygame.draw.rect(border, (255, 235, 80, min(255, pulse + 50)), (0, 0, ow + 4, oh + 4), 3)
            screen.blit(border, (ox - 2, oy - 2))
        elif self.invisible:
            self.dino.draw(screen, self.night)
            dino_rect = self.dino.get_rect()
            ox = dino_rect.x - 50
            oy = dino_rect.y - 20
            ow = dino_rect.width + 80
            oh = dino_rect.height + 40
            pulse = int(100 + 60 * abs((self.invisible_timer % 20) - 10) / 10.0)
            overlay = pygame.Surface((ow, oh), pygame.SRCALPHA)
            border = pygame.Surface((ow + 4, oh + 4), pygame.SRCALPHA)
            if self.revive_invisible:
                # Gold theme (continuation of revival)
                overlay.fill((255, 215, 0, pulse))
                pygame.draw.rect(border, (255, 235, 80, min(255, pulse + 50)), (0, 0, ow + 4, oh + 4), 3)
            else:
                # Blue theme (normal invisible)
                overlay.fill((80, 170, 255, pulse))
                pygame.draw.rect(border, (120, 210, 255, min(255, pulse + 50)), (0, 0, ow + 4, oh + 4), 3)
            screen.blit(overlay, (ox, oy))
            screen.blit(border, (ox - 2, oy - 2))
        else:
            self.dino.draw(screen, self.night)

        # Shield effect ring
        if self.shield_active:
            dino_rect = self.dino.get_rect()
            shield_cx = dino_rect.centerx
            shield_cy = dino_rect.centery
            shield_surf = pygame.Surface((60, 60), pygame.SRCALPHA)
            pygame.draw.circle(shield_surf, (100, 180, 255, 60), (30, 30), 30)
            pygame.draw.circle(shield_surf, (100, 180, 255, 120), (30, 30), 30, 2)
            screen.blit(shield_surf, (shield_cx - 30, shield_cy - 30))

        # Score
        score_text = self.font.render(f"Score: {self.score}  Best: {self.highscore}", True,
                                       WHITE if self.night else BLACK)
        screen.blit(score_text, (WIDTH - score_text.get_width() - 20, 15))

        # Speed
        speed_text = self.font.render(f"Speed: {self.speed}", True,
                                       WHITE if self.night else BLACK)
        screen.blit(speed_text, (20, 15))

        # Day/night
        dn_text = self.font.render("NIGHT" if self.night else "DAY", True,
                                    WHITE if self.night else BLACK)
        screen.blit(dn_text, (WIDTH // 2 - dn_text.get_width() // 2, 15))

        # Phase indicator
        PHASE_COLORS = {
            1: (80, 200, 80), 2: (255, 220, 50), 3: (255, 180, 50),
            4: (255, 100, 50), 5: (200, 50, 200), 6: (255, 0, 0)
        }
        PHASE_NAMES = {
            1: "TUTORIAL", 2: "SPIKES", 3: "BULLETS",
            4: "HOMING", 5: "GRAVITY", 6: "HELL MODE"
        }
        pcolor = PHASE_COLORS.get(self.phase, (255, 255, 255))
        pname = PHASE_NAMES.get(self.phase, "")
        if self.phase == 6:
            if (self.phase_timer // 15) % 2:
                phase_text = self.font.render(pname, True, pcolor)
                screen.blit(phase_text, (WIDTH // 2 - phase_text.get_width() // 2, 35))
        else:
            phase_text = self.font.render(pname, True, pcolor)
            screen.blit(phase_text, (WIDTH // 2 - phase_text.get_width() // 2, 35))

        # Tutorial hint
        if self.phase == 1:
            hint_font = get_font(20, bold=True, chinese=True)
            hint = hint_font.render("按↑跳跃", True, (120, 120, 120))
            screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, HEIGHT - 130))

        # Phase transition message
        if self.phase_transition_timer > 0:
            msg_surf = self.big_font_cn.render(self.phase_transition_msg, True, (255, 255, 100))
            bg_w = msg_surf.get_width() + 30
            bg_h = msg_surf.get_height() + 16
            bg_x = WIDTH // 2 - bg_w // 2
            bg_y = HEIGHT // 2 - 80
            bg = pygame.Surface((bg_w, bg_h), pygame.SRCALPHA)
            bg.fill((0, 0, 0, 180))
            screen.blit(bg, (bg_x, bg_y))
            screen.blit(msg_surf, (WIDTH // 2 - msg_surf.get_width() // 2, bg_y + 8))

        # State indicator
        if self.dino.gliding:
            state_str = "GLIDE"
            state_color = (100, 200, 255)
        elif self.dino.jump_count == 2:
            state_str = "DOUBLE"
            state_color = (255, 255, 100)
        elif self.dino.jumping:
            state_str = "JUMP"
            state_color = (200, 200, 200)
        else:
            state_str = ""
        if state_str:
            state_text = self.font.render(state_str, True, state_color)
            screen.blit(state_text, (WIDTH - state_text.get_width() - 20, 40))

        # Status display area (stacked top-right)
        status_y = 55
        small_font = pygame.font.SysFont("consolas", 14, bold=True)
        # Heart key count
        if self.heart_keys > 0:
            hk_text = small_font.render(f"♥ x{self.heart_keys}", True, (255, 105, 180))
            screen.blit(hk_text, (WIDTH - hk_text.get_width() - 20, status_y))
            status_y += 18
        # Shield phase
        if self.shield_active:
            t = small_font.render("SHIELD", True, (100, 180, 255))
            screen.blit(t, (WIDTH - t.get_width() - 20, status_y))
            status_y += 18
        elif self.invisible:
            blink = (self.invisible_timer // 8) % 2
            if blink:
                sec = self.invisible_timer / FPS
                t = small_font.render(f"INVISIBLE {sec:.1f}", True, (255, 255, 255))
                screen.blit(t, (WIDTH - t.get_width() - 20, status_y))
            status_y += 18
        elif self.cooldown:
            sec = self.cooldown_timer / FPS
            t = small_font.render(f"CD {sec:.1f}", True, (160, 160, 160))
            screen.blit(t, (WIDTH - t.get_width() - 20, status_y))
            status_y += 18
        # Time stop
        if self.time_stop:
            sec = self.time_stop_timer / FPS
            t = small_font.render(f"TIME STOP {sec:.1f}", True, (80, 140, 255))
            screen.blit(t, (WIDTH - t.get_width() - 20, status_y))
            status_y += 18
        # Shrink
        if self.shrunk:
            sec = self.shrink_timer_active / FPS
            t = small_font.render(f"SMALL {sec:.1f}", True, (180, 80, 220))
            screen.blit(t, (WIDTH - t.get_width() - 20, status_y))
            status_y += 18
        # Rocket
        if self.rocket_active:
            sec = self.rocket_timer_active / FPS
            t = small_font.render(f"ROCKET {sec:.1f}", True, (255, 60, 60))
            screen.blit(t, (WIDTH - t.get_width() - 20, status_y))
            # Gold border around text
            pygame.draw.rect(screen, (255, 215, 0),
                             (WIDTH - t.get_width() - 22, status_y - 2, t.get_width() + 4, t.get_height() + 4), 1)
            status_y += 18
        # Gravity reversed indicator
        if self.gravity_reversed:
            t = small_font.render("REVERSE!", True, (180, 0, 255))
            screen.blit(t, (WIDTH // 2 - t.get_width() // 2, HEIGHT // 2 - 30))

        # Rocket flame particles
        for p in self.rocket_particles:
            p.draw(screen)

        # CD中 flash
        if self.cd_flash > 0:
            flash_alpha = min(255, self.cd_flash * 6)
            cd_flash_surf = self.big_font_cn.render("CD中", True, (220, 60, 60))
            flash_bg = pygame.Surface((cd_flash_surf.get_width() + 20, cd_flash_surf.get_height() + 10), pygame.SRCALPHA)
            flash_bg.fill((255, 255, 255, flash_alpha))
            screen.blit(flash_bg, (WIDTH // 2 - flash_bg.get_width() // 2, HEIGHT // 2 - 60))
            screen.blit(cd_flash_surf, (WIDTH // 2 - cd_flash_surf.get_width() // 2, HEIGHT // 2 - 55))

        # Inventory bar
        self.inventory.draw(screen, self.night)

        # Revival message
        if self.revive_text_timer > 0:
            revive_font = get_font(48, bold=True, chinese=True)
            # Gold text with black outline
            revive_text = revive_font.render("复活！继续加油！", True, (255, 215, 0))
            outline_text = revive_font.render("复活！继续加油！", True, (0, 0, 0))
            bg_w = revive_text.get_width() + 40
            bg_h = revive_text.get_height() + 20
            bg_x = WIDTH // 2 - bg_w // 2
            bg_y = HEIGHT // 2 - bg_h // 2
            bg = pygame.Surface((bg_w, bg_h), pygame.SRCALPHA)
            bg.fill((0, 0, 0, 180))
            screen.blit(bg, (bg_x, bg_y))
            tx = WIDTH // 2 - revive_text.get_width() // 2
            ty = HEIGHT // 2 - revive_text.get_height() // 2
            for dx, dy in [(-2, 0), (2, 0), (0, -2), (0, 2)]:
                screen.blit(outline_text, (tx + dx, ty + dy))
            screen.blit(revive_text, (tx, ty))

        # Game over
        if self.game_over:
            go_text = self.big_font.render("GAME OVER", True, WHITE if self.night else BLACK)
            screen.blit(go_text, (WIDTH // 2 - go_text.get_width() // 2, HEIGHT // 2 - 40))
            hint = self.font.render("Press R to restart", True, WHITE if self.night else GRAY)
            screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, HEIGHT // 2 + 10))

        if not paused:
            pygame.display.flip()


def title_screen():
    """Show title screen until any key is pressed."""
    highscore = load_highscore()
    title_font = get_font(48, bold=True, chinese=True)
    hs_font = get_font(28, bold=True, chinese=True)
    hint_font = get_font(22, bold=True, chinese=True)

    # Static background mountains and buildings
    mtn_points = []
    x = 0
    while x < WIDTH + 200:
        h = random.randint(40, 100)
        mtn_points.append((x, h))
        x += random.randint(40, 80)
    buildings = []
    x = 0
    while x < WIDTH + 200:
        w = random.randint(30, 70)
        h = random.randint(30, 80)
        buildings.append([x, w, h])
        x += w + random.randint(10, 40)

    blink_timer = 0
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                return

        screen.fill(DARK_BG)

        # Mountains
        mtn_base_y = HEIGHT - 100
        mtn_color = (60, 65, 75)
        pts = [(0, mtn_base_y)]
        for px, ph in mtn_points:
            pts.append((px, mtn_base_y - ph))
        pts.append((WIDTH, mtn_base_y))
        if len(pts) >= 3:
            pygame.draw.polygon(screen, mtn_color, pts)

        # Buildings
        bld_color = (50, 55, 65)
        for bx, bw, bh in buildings:
            pygame.draw.rect(screen, bld_color, (bx, mtn_base_y - bh, bw, bh))

        # Ground
        pygame.draw.rect(screen, NIGHT_GROUND, (0, HEIGHT - 100, WIDTH, 20))
        edge_color = tuple(min(255, c + 30) for c in NIGHT_GROUND)
        pygame.draw.line(screen, edge_color, (0, HEIGHT - 100), (WIDTH, HEIGHT - 100), 2)

        # Title
        title_text = title_font.render("怪盗基德：无尽奔跑", True, (255, 215, 0))
        screen.blit(title_text, (WIDTH // 2 - title_text.get_width() // 2, 80))

        # High score
        hs_text = hs_font.render(f"最高分：{highscore}", True, (200, 200, 200))
        screen.blit(hs_text, (WIDTH // 2 - hs_text.get_width() // 2, 160))

        # Blink hint
        blink_timer += 1
        if (blink_timer // 40) % 2 == 0:
            hint_text = hint_font.render("按任意键开始", True, (180, 180, 180))
            screen.blit(hint_text, (WIDTH // 2 - hint_text.get_width() // 2, 230))

        pygame.display.flip()
        clock.tick(FPS)


def main():
    title_screen()
    game = Game()

    paused = False
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_p:
                    if not game.game_over:
                        paused = not paused
                    continue
                if paused:
                    continue
                if event.key == pygame.K_SPACE or event.key == pygame.K_UP:
                    if not game.game_over:
                        game.dino.jump(reverse=game.gravity_reversed)
                if event.key == pygame.K_r:
                    if game.game_over:
                        game.reset()
                        paused = False
                if event.key == pygame.K_ESCAPE:
                    running = False
                # Inventory: left/right to select
                if event.key == pygame.K_LEFT:
                    game.inventory.select_left()
                if event.key == pygame.K_RIGHT:
                    game.inventory.select_right()
                # Enter: use selected item
                if event.key == pygame.K_RETURN:
                    if not game.game_over:
                        item_type = game.inventory.get_selected_type()
                        if item_type == "ammo":
                            game.inventory.use_selected()
                            game.inventory.use_flash = 15
                            game.fire_poker_card()
                        elif item_type == "clock":
                            game.inventory.use_selected()
                            game.inventory.use_flash = 15
                            game.time_stop = True
                            game.time_stop_timer = 2 * FPS
                        elif item_type == "shrink":
                            game.inventory.use_selected()
                            game.inventory.use_flash = 15
                            game.shrunk = True
                            game.shrink_timer_active = 5 * FPS
                            game.dino.w = 20
                            game.dino.stand_h = 25
                            game.dino.duck_h = 12
                            game.dino.ground_y = HEIGHT - 100 - game.dino.stand_h
                            if not game.dino.jumping:
                                game.dino.h = game.dino.stand_h
                                game.dino.y = game.dino.ground_y
                        elif item_type == "rocket":
                            game.inventory.use_selected()
                            game.inventory.use_flash = 15
                            game.rocket_active = True
                            game.rocket_timer_active = 3 * FPS
                            # Scale up dino 120%
                            game.dino.w = int(game.dino_orig_w * 1.2)
                            game.dino.stand_h = int(game.dino_orig_stand_h * 1.2)
                            game.dino.duck_h = int(game.dino_orig_duck_h * 1.2)
                            game.dino.ground_y = HEIGHT - 100 - game.dino.stand_h
                            if not game.dino.jumping:
                                game.dino.h = game.dino.stand_h
                                game.dino.y = game.dino.ground_y

        if not paused:
            game.handle_input()
            game.update()
        game.draw(paused=paused)

        # Pause overlay (drawn after game.draw which skips flip when paused)
        if paused:
            pause_font = get_font(36, bold=True, chinese=True)
            pause_text = pause_font.render("暂停中 - 按P继续", True, (255, 255, 255))
            bg_w = pause_text.get_width() + 40
            bg_h = pause_text.get_height() + 20
            bg_x = WIDTH // 2 - bg_w // 2
            bg_y = HEIGHT // 2 - bg_h // 2
            bg = pygame.Surface((bg_w, bg_h), pygame.SRCALPHA)
            bg.fill((0, 0, 0, 180))
            screen.blit(bg, (bg_x, bg_y))
            screen.blit(pause_text, (WIDTH // 2 - pause_text.get_width() // 2, HEIGHT // 2 - pause_text.get_height() // 2))
            pygame.display.flip()

        clock.tick(FPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
