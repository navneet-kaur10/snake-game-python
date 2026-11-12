import math
import random
import sys
import pygame

CELL, COLS, ROWS, HUD = 32, 22, 17, 72
W, H = COLS * CELL, ROWS * CELL + HUD
FPS = 60

BG_TOP, BG_BOT = (12, 14, 34), (34, 14, 60)
HEAD_C, TAIL_C = (130, 255, 200), (50, 130, 255)
FOOD_C = (255, 85, 120)
TEXT_C, DIM_C = (235, 240, 255), (150, 160, 205)

DIRS = {
    pygame.K_UP: (0, -1), pygame.K_w: (0, -1),
    pygame.K_DOWN: (0, 1), pygame.K_s: (0, 1),
    pygame.K_LEFT: (-1, 0), pygame.K_a: (-1, 0),
    pygame.K_RIGHT: (1, 0), pygame.K_d: (1, 0),
}


# ---------------------------------------------------------------- helpers
def lerp(a, b, t):
    return a + (b - a) * t


def mix(c1, c2, t):
    return tuple(int(lerp(a, b, t)) for a, b in zip(c1, c2))


def glow_sprite(radius, color, strength=110):
    """Soft radial glow on a transparent surface."""
    s = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
    for r in range(radius, 0, -1):
        a = int(strength * (1 - r / radius) ** 2)
        pygame.draw.circle(s, (*color, a), (radius, radius), r)
    return s


def make_font(size):
    return pygame.font.SysFont("segoeui,helveticaneue,trebuchetms,arial", size, bold=True)


# ---------------------------------------------------------------- game
class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Neon Snake")
        self.screen = pygame.display.set_mode((W, H))
        self.canvas = pygame.Surface((W, H))
        self.clock = pygame.time.Clock()

        self.f_big, self.f_mid, self.f_small = make_font(64), make_font(30), make_font(18)

        self.glow_food = glow_sprite(52, FOOD_C, 150)
        self.glow_snake = glow_sprite(32, (70, 255, 190), 60)
        self.build_background()

        self.bokeh = []
        for _ in range(24):
            r = random.randint(8, 26)
            col = random.choice([(90, 120, 255), (160, 90, 255), (60, 220, 200)])
            self.bokeh.append({
                "x": random.uniform(0, W), "y": random.uniform(0, H), "r": r,
                "vx": random.uniform(-8, 8), "vy": random.uniform(-16, -4),
                "sprite": glow_sprite(r, col, 70),
            })

        self.best = 0
        self.time = 0.0
        self.reset()
        self.state = "start"

    # ------------------------------------------------------------ setup
    def build_background(self):
        self.bg = pygame.Surface((W, H))
        for y in range(H):
            pygame.draw.line(self.bg, mix(BG_TOP, BG_BOT, y / H), (0, y), (W, y))

        self.board = pygame.Surface((W, H - HUD), pygame.SRCALPHA)
        for cy in range(ROWS):
            for cx in range(COLS):
                col = (24, 28, 70, 150) if (cx + cy) % 2 else (34, 38, 86, 150)
                pygame.draw.rect(self.board, col, (cx * CELL, cy * CELL, CELL, CELL))
        pygame.draw.line(self.board, (110, 255, 210, 200), (0, 0), (W, 0), 2)

    def reset(self):
        cx, cy = COLS // 2, ROWS // 2
        self.snake = [(cx - i, cy) for i in range(4)]
        self.prev = list(self.snake)
        self.dir = (1, 0)
        self.queue = []
        self.score = 0
        self.acc = 0.0
        self.particles = []
        self.popups = []
        self.shake = 0.0
        self.food = self.spawn_food()
        self.food_age = 0.0

    def spawn_food(self):
        free = [(x, y) for x in range(COLS) for y in range(ROWS) if (x, y) not in self.snake]
        return random.choice(free)

    @property
    def step_ms(self):
        return max(60, 135 - self.score * 3)

    # ------------------------------------------------------------ logic
    def handle_event(self, e):
        if e.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        if e.type != pygame.KEYDOWN:
            return
        if e.key == pygame.K_ESCAPE:
            pygame.quit()
            sys.exit()

        if self.state in ("start", "over") and e.key in (pygame.K_SPACE, pygame.K_RETURN):
            self.reset()
            self.state = "play"
        elif self.state == "play":
            if e.key == pygame.K_p:
                self.state = "paused"
            elif e.key in DIRS:
                d = DIRS[e.key]
                last = self.queue[-1] if self.queue else self.dir
                if d != last and d != (-last[0], -last[1]) and len(self.queue) < 2:
                    self.queue.append(d)
        elif self.state == "paused" and e.key in (pygame.K_p, pygame.K_SPACE):
            self.state = "play"

    def burst(self, cell, colors, count=22, speed=(60, 230)):
        cx = cell[0] * CELL + CELL / 2
        cy = HUD + cell[1] * CELL + CELL / 2
        for _ in range(count):
            a = random.uniform(0, math.tau)
            v = random.uniform(*speed)
            life = random.uniform(0.4, 0.9)
            self.particles.append([cx, cy, math.cos(a) * v, math.sin(a) * v,
                                   life, life, random.choice(colors), random.uniform(2, 5)])

    def tick(self):
        if self.queue:
            self.dir = self.queue.pop(0)
        hx, hy = self.snake[0]
        new = (hx + self.dir[0], hy + self.dir[1])
        grow = new == self.food
        body = self.snake if grow else self.snake[:-1]

        if not (0 <= new[0] < COLS and 0 <= new[1] < ROWS) or new in body:
            self.state = "over"
            self.prev = list(self.snake)
            self.shake = 0.4
            self.best = max(self.best, self.score)
            self.burst(self.snake[0], [(255, 90, 90), (255, 255, 255), (255, 170, 80)], 40, (80, 300))
            return

        self.prev = list(self.snake)
        self.snake.insert(0, new)
        if grow:
            self.score += 1
            self.burst(new, [FOOD_C, (255, 255, 255), HEAD_C])
            self.popups.append([new[0] * CELL + CELL / 2, HUD + new[1] * CELL, 0.0])
            self.food = self.spawn_food()
            self.food_age = 0.0
        else:
            self.snake.pop()

    def update(self, dt):
        self.time += dt
        self.food_age += dt
        self.shake = max(0.0, self.shake - dt)

        if self.state == "play":
            self.acc += dt * 1000
            while self.acc >= self.step_ms and self.state == "play":
                self.acc -= self.step_ms
                self.tick()

        for p in self.particles:
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[2] *= 0.97
            p[3] *= 0.97
            p[4] -= dt
        self.particles = [p for p in self.particles if p[4] > 0]

        for pop in self.popups:
            pop[2] += dt
        self.popups = [p for p in self.popups if p[2] < 0.9]

        for b in self.bokeh:
            b["x"] = (b["x"] + b["vx"] * dt) % W
            b["y"] = (b["y"] + b["vy"] * dt) % H

    # ------------------------------------------------------------ drawing
    def text(self, surf, s, font, color, pos, anchor="center", alpha=255):
        img = font.render(s, True, color)
        sh = font.render(s, True, (0, 0, 0))
        img.set_alpha(alpha)
        sh.set_alpha(int(110 * alpha / 255))
        rect = img.get_rect(**{anchor: pos})
        surf.blit(sh, rect.move(2, 3))
        surf.blit(img, rect)

    def draw_food(self):
        fx, fy = self.food
        cx = fx * CELL + CELL / 2
        cy = HUD + fy * CELL + CELL / 2
        s = min(1.0, self.food_age / 0.3)
        s = 1 - (1 - s) ** 3
        pulse = 1 + 0.07 * math.sin(self.time * 6)
        r = CELL * 0.33 * s * pulse

        g = self.glow_food
        self.canvas.blit(g, (cx - g.get_width() / 2, cy - g.get_height() / 2))
        pygame.draw.circle(self.canvas, FOOD_C, (cx, cy), r)
        pygame.draw.circle(self.canvas, mix(FOOD_C, (255, 255, 255), 0.55),
                           (cx - r * 0.35, cy - r * 0.35), max(1, r * 0.3))
        pygame.draw.line(self.canvas, (110, 70, 40), (cx, cy - r * 0.8), (cx + 2, cy - r * 1.35), 3)
        pygame.draw.ellipse(self.canvas, (110, 240, 130),
                            (cx + 2, cy - r * 1.5, r * 0.9, r * 0.5))

    def draw_snake(self):
        t = min(1.0, self.acc / self.step_ms) if self.state in ("play", "paused") else 1.0
        pts = []
        for i, seg in enumerate(self.snake):
            a = self.prev[i] if i < len(self.prev) else seg
            pts.append((lerp(a[0], seg[0], t) * CELL + CELL / 2,
                        HUD + lerp(a[1], seg[1], t) * CELL + CELL / 2))
        n = len(pts)
        dead = self.state == "over"
        flash = 0.5 + 0.5 * math.sin(self.time * 14) if dead else 0

        gs = self.glow_snake
        for p in pts:
            self.canvas.blit(gs, (p[0] - gs.get_width() / 2, p[1] - gs.get_height() / 2))

        cols, rads = [], []
        for i in range(n):
            k = i / max(1, n - 1)
            c = mix(HEAD_C, TAIL_C, k)
            if dead:
                c = mix(c, (255, 70, 70), 0.35 + 0.4 * flash)
            cols.append(c)
            rads.append(CELL * (0.47 - 0.17 * k))

        for i in range(n - 1, -1, -1):
            if i < n - 1:
                pygame.draw.line(self.canvas, cols[i], pts[i], pts[i + 1], int(rads[i] * 2))
            pygame.draw.circle(self.canvas, cols[i], pts[i], rads[i])
        for i in range(n - 1, -1, -1):
            r = rads[i]
            pygame.draw.circle(self.canvas, mix(cols[i], (255, 255, 255), 0.4),
                               (pts[i][0] - r * 0.22, pts[i][1] - r * 0.28), max(1, r * 0.42))

        # head details
        hx, hy = pts[0]
        fx, fy = self.dir
        px, py = -fy, fx
        r = rads[0]

        if not dead and math.sin(self.time * 7) > 0.55:  # flicking tongue
            bx, by = hx + fx * r, hy + fy * r
            tx, ty = hx + fx * (r + CELL * 0.32), hy + fy * (r + CELL * 0.32)
            pygame.draw.line(self.canvas, (255, 80, 110), (bx, by), (tx, ty), 3)
            for s in (-1, 1):
                pygame.draw.line(self.canvas, (255, 80, 110), (tx, ty),
                                 (tx + fx * 6 + px * s * 6, ty + fy * 6 + py * s * 6), 2)

        for s in (-1, 1):
            ex = hx + fx * CELL * 0.12 + px * s * CELL * 0.2
            ey = hy + fy * CELL * 0.12 + py * s * CELL * 0.2
            pygame.draw.circle(self.canvas, (255, 255, 255), (ex, ey), CELL * 0.15)
            pygame.draw.circle(self.canvas, (15, 20, 40),
                               (ex + fx * CELL * 0.05, ey + fy * CELL * 0.05), CELL * 0.08)

    def draw_particles(self):
        for x, y, _, _, life, maxlife, col, size in self.particles:
            k = life / maxlife
            pygame.draw.circle(self.canvas, mix((20, 20, 50), col, k), (x, y), max(1, size * k))

    def draw_popups(self):
        for x, y, age in self.popups:
            k = age / 0.9
            self.text(self.canvas, "+1", self.f_mid, (255, 235, 140),
                      (x, y - k * 40), alpha=int(255 * (1 - k)))

    def draw_hud(self):
        panel = pygame.Surface((W - 24, HUD - 24), pygame.SRCALPHA)
        pygame.draw.rect(panel, (255, 255, 255, 22), panel.get_rect(), border_radius=14)
        self.canvas.blit(panel, (12, 12))
        mid = HUD // 2
        self.text(self.canvas, f"SCORE  {self.score}", self.f_mid, TEXT_C, (32, mid), "midleft")
        self.text(self.canvas, f"BEST  {self.best}", self.f_mid, DIM_C, (W - 32, mid), "midright")
        title = mix(HEAD_C, TAIL_C, 0.5 + 0.5 * math.sin(self.time * 2))
        self.text(self.canvas, "NEON SNAKE", self.f_small, title, (W // 2, mid))

    def draw_overlay(self):
        if self.state == "play":
            return
        veil = pygame.Surface((W, H), pygame.SRCALPHA)
        veil.fill((8, 10, 24, 170))
        self.canvas.blit(veil, (0, 0))
        cx, cy = W // 2, H // 2
        pulse = int(170 + 85 * math.sin(self.time * 4))

        if self.state == "start":
            self.text(self.canvas, "NEON SNAKE", self.f_big, HEAD_C, (cx, cy - 50))
            self.text(self.canvas, "Press SPACE to start", self.f_mid, TEXT_C, (cx, cy + 20), alpha=pulse)
            self.text(self.canvas, "Arrows / WASD to steer   -   P to pause",
                      self.f_small, DIM_C, (cx, cy + 66))
        elif self.state == "over":
            self.text(self.canvas, "GAME OVER", self.f_big, (255, 100, 110), (cx, cy - 60))
            self.text(self.canvas, f"Score {self.score}    Best {self.best}",
                      self.f_mid, TEXT_C, (cx, cy + 2))
            self.text(self.canvas, "Press SPACE to play again", self.f_mid, HEAD_C,
                      (cx, cy + 56), alpha=pulse)
        elif self.state == "paused":
            self.text(self.canvas, "PAUSED", self.f_big, TEXT_C, (cx, cy - 10))
            self.text(self.canvas, "Press P to resume", self.f_small, DIM_C, (cx, cy + 40))

    def draw(self):
        self.canvas.blit(self.bg, (0, 0))
        for b in self.bokeh:
            self.canvas.blit(b["sprite"], (b["x"] - b["r"], b["y"] - b["r"]))
        self.canvas.blit(self.board, (0, HUD))

        self.draw_food()
        self.draw_particles()
        self.draw_snake()
        self.draw_popups()
        self.draw_hud()
        self.draw_overlay()

        mag = self.shake / 0.4 * 10
        off = (random.uniform(-mag, mag), random.uniform(-mag, mag)) if mag else (0, 0)
        self.screen.fill((0, 0, 0))
        self.screen.blit(self.canvas, off)
        pygame.display.flip()

    # ------------------------------------------------------------ main loop
    def run(self):
        while True:
            dt = min(self.clock.tick(FPS) / 1000, 0.05)
            for e in pygame.event.get():
                self.handle_event(e)
            self.update(dt)
            self.draw()


if __name__ == "__main__":
    Game().run()