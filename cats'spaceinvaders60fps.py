# ============================================================
#   CAT'S SPACE INVADERS  --  one file, no external assets
#   Python 3.14 + pygame  |  60 FPS  |  built-in beeps & boops
#   Y = start      N = quit
#   MENU: start game / help / exit / about / settings
# ============================================================
import sys
import random
from array import array

import pygame

# ------------------------------------------------------------
#  SETUP
# ------------------------------------------------------------
W, H = 800, 600
FPS = 60                          # default; changeable in settings

pygame.mixer.pre_init(22050, -16, 1, 512)
pygame.init()
AUDIO = True
if pygame.mixer.get_init() is None:
    try:
        pygame.mixer.init(22050, -16, 1, 512)
    except pygame.error:
        AUDIO = False

screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("cat's py. space invaders port 0.1")
clock = pygame.time.Clock()

font_big = pygame.font.SysFont("consolas,couriernew,monospace", 56, bold=True)
font_med = pygame.font.SysFont("consolas,couriernew,monospace", 28, bold=True)
font_sml = pygame.font.SysFont("consolas,couriernew,monospace", 20, bold=True)

# ------------------------------------------------------------
#  COLORS
# ------------------------------------------------------------
BLACK   = (0, 0, 0)
WHITE   = (240, 240, 240)
GREEN   = (100, 255, 140)
CYAN    = (90, 230, 255)
YELLOW  = (250, 220, 80)
RED     = (255, 90, 100)
PINK    = (255, 120, 200)
GREY    = (120, 120, 140)
DKGREY  = (60, 60, 75)

# ------------------------------------------------------------
#  NES-STYLE SQUARE WAVE SOUND ENGINE  (no files needed)
# ------------------------------------------------------------
SR = 22050
SOUND_ENABLED = True              # toggled from Settings


def _tone(freq, ms, vol=0.22, duty=0.5, sweep=0.0):
    """Build a raw 16-bit mono square-wave Sound."""
    n = max(1, int(SR * ms / 1000))
    buf = array('h', [0]) * n
    phase = 0.0
    for i in range(n):
        f = freq + sweep * (i / n)
        if f < 20.0:
            f = 20.0
        phase = (phase + f / SR) % 1.0
        s = vol if phase < duty else -vol
        env = 1.0 - (i / n) ** 1.5          # decay envelope
        buf[i] = int(s * env * 32767)
    if sys.byteorder == 'big':
        buf.byteswap()
    return pygame.mixer.Sound(buffer=buf.tobytes())


SND = {}
if AUDIO:
    try:
        SND = {
            'shoot': _tone(1000,  70, 0.16, 0.50, -700),
            'kill':  _tone( 260, 110, 0.20, 0.25, -180),
            'hit':   _tone( 140, 420, 0.28, 0.50,  -90),
            'over':  _tone( 200, 800, 0.26, 0.50, -160),
            'start': _tone( 330, 140, 0.18, 0.50,  500),
            'wave':  _tone( 520, 200, 0.18, 0.50,  300),
            'step':  [_tone(f, 60, 0.14, 0.5) for f in (120, 106, 94, 84)],
            'blip':  _tone( 760,  40, 0.12, 0.50, 0),
        }
    except Exception:
        SND = {}


def play(name, idx=0):
    if not SOUND_ENABLED or not SND:
        return
    s = SND.get(name)
    if s is None:
        return
    if isinstance(s, list):
        s = s[idx % len(s)]
    s.play()


# ------------------------------------------------------------
#  SPRITES  (tiny bitmaps -> pre-rendered surfaces)
# ------------------------------------------------------------
INVADER_A = [                       # top row - 30 pts
    "00111100",
    "01111110",
    "11111111",
    "11011011",
    "11111111",
    "00100100",
    "01011010",
    "10100101",
]
INVADER_B = [                       # middle rows - 20 pts
    "00011000",
    "00111100",
    "01111110",
    "11011011",
    "11111111",
    "00100100",
    "00100100",
    "01000010",
]
INVADER_C = [                       # bottom rows - 10 pts
    "00111100",
    "01111110",
    "11111111",
    "11100111",
    "11111111",
    "00011000",
    "00111100",
    "01100110",
]
PLAYER_SHIP = [
    "00000100000",
    "00001110000",
    "00001110000",
    "01111111110",
    "11111111111",
    "11111111111",
    "11111111111",
]


def make_sprite(pattern, scale, color):
    w = len(pattern[0]) * scale
    h = len(pattern) * scale
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    for r, row in enumerate(pattern):
        for c, ch in enumerate(row):
            if ch == '1':
                surf.fill(color, (c * scale, r * scale, scale, scale))
    return surf


INV_SPRITES = [
    make_sprite(INVADER_A, 3, PINK),
    make_sprite(INVADER_B, 3, CYAN),
    make_sprite(INVADER_C, 3, GREEN),
]
PLAYER_IMG = make_sprite(PLAYER_SHIP, 3, GREEN)
PLAYER_MINI = make_sprite(PLAYER_SHIP, 2, GREEN)

# ------------------------------------------------------------
#  LAYOUT CONSTANTS
# ------------------------------------------------------------
INV_W = INV_H = 24
GAP_X, GAP_Y = 18, 14
COLS, ROWS = 11, 5

GRID_W = COLS * (INV_W + GAP_X) - GAP_X
GRID_LEFT = (W - GRID_W) // 2
GRID_TOP = 90

PLAYER_W, PLAYER_H = 33, 21
PLAYER_SPEED = 6

CELL = 6
BUNKER_PAT = [
    "001111111100",
    "011111111110",
    "111111111111",
    "111111111111",
    "111111111111",
    "111100001111",
    "111000000111",
    "110000000011",
]
BUNKER_W = len(BUNKER_PAT[0]) * CELL
BUNKER_H = len(BUNKER_PAT) * CELL
BUNKER_Y = H - 150
_slot = (W - 4 * BUNKER_W) / 5
BUNKER_XS = [int(_slot + i * (BUNKER_W + _slot)) for i in range(4)]


def text(surf, s, font, color, x, y, center=True):
    img = font.render(s, True, color)
    r = img.get_rect()
    if center:
        r.centerx = x
    else:
        r.x = x
    r.y = y
    surf.blit(img, r)


# ------------------------------------------------------------
#  ENTITIES
# ------------------------------------------------------------
class Invader:
    __slots__ = ("x", "y", "row", "col", "kind", "alive")

    def __init__(self, x, y, row, col, kind):
        self.x = float(x)
        self.y = float(y)
        self.row = row
        self.col = col
        self.kind = kind
        self.alive = True


# ------------------------------------------------------------
#  GAME
# ------------------------------------------------------------
class Game:
    # ---- menu definition (top -> bottom) ----
    MENU_ITEMS = ["start game", "help", "exit", "about", "settings"]
    FPS_CHOICES = [30, 60, 120]

    def __init__(self):
        self.state = "menu"           # menu | play | gameover | help | about | settings
        self.best = 0
        self.stars = [(random.randrange(W), random.randrange(H),
                       random.choice((40, 60, 90, 130, 180))) for _ in range(70)]

        # ---- menu cursor ----
        self.menu_idx = 0

        # ---- settings ----
        self.fps_target = FPS
        self.fps_idx = self.FPS_CHOICES.index(FPS) if FPS in self.FPS_CHOICES else 1

        # ---- settings submenu cursor ----
        self.settings_idx = 0
        self.SETTINGS_ITEMS = ["sound", "fps", "back"]

        self.new_game()

    # ---------- setup ----------
    def new_game(self):
        self.score = 0
        self.lives = 3
        self.wave = 1
        self.px = W // 2 - PLAYER_W // 2
        self.py = H - 70
        self.player_bullet = None
        self.enemy_bullets = []
        self.dir = 1
        self.fire_timer = 70
        self.snd_accum = 0.0
        self.step_i = 0
        self.build_bunkers()
        self.spawn_wave()

    def spawn_wave(self):
        drop = min(60, (self.wave - 1) * 20)
        self.invaders = []
        for r in range(ROWS):
            for c in range(COLS):
                kind = 0 if r == 0 else (1 if r < 3 else 2)
                x = GRID_LEFT + c * (INV_W + GAP_X)
                y = GRID_TOP + r * (INV_H + GAP_Y) + drop
                self.invaders.append(Invader(x, y, r, c, kind))
        self.dir = 1
        self.enemy_bullets.clear()
        self.player_bullet = None
        self.fire_timer = 70
        self.snd_accum = 0.0

    def build_bunkers(self):
        self.cells = []
        for bx in BUNKER_XS:
            for r, row in enumerate(BUNKER_PAT):
                for c, ch in enumerate(row):
                    if ch == '1':
                        self.cells.append(
                            pygame.Rect(bx + c * CELL, BUNKER_Y + r * CELL, CELL, CELL))

    def player_rect(self):
        return pygame.Rect(int(self.px), self.py, PLAYER_W, PLAYER_H)

    # ---------- helpers ----------
    def carve(self, rect):
        hit = False
        for c in self.cells:
            if c.colliderect(rect):
                hit = True
                break
        if not hit:
            return False
        cx, cy = rect.center
        self.cells = [c for c in self.cells
                      if (c.centerx - cx) ** 2 + (c.centery - cy) ** 2 > 121]
        return True

    def lose_life(self, instant=False):
        play('hit')
        self.lives -= 1
        self.enemy_bullets.clear()
        self.player_bullet = None
        if instant:
            self.lives = 0
        if self.lives <= 0:
            self.lives = 0
            self.state = "gameover"
            self.best = max(self.best, self.score)
            play('over')

    # ---------- update ----------
    def update(self):
        if self.state != "play":
            return

        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.px -= PLAYER_SPEED
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.px += PLAYER_SPEED
        self.px = max(16, min(W - 16 - PLAYER_W, self.px))

        # ----- invaders -----
        alive = [i for i in self.invaders if i.alive]
        if not alive:
            self.score += 100 * self.wave
            self.wave += 1
            play('wave')
            self.spawn_wave()
            self.build_bunkers()
            return

        speed = 0.45 + 2.8 * (1.0 - len(alive) / float(COLS * ROWS))
        minx = min(i.x for i in alive)
        maxx = max(i.x for i in alive) + INV_W
        dx = speed * self.dir

        if maxx + dx > W - 16 or minx + dx < 16:
            self.dir *= -1
            for i in alive:
                i.y += 20
        else:
            for i in alive:
                i.x += dx
            self.snd_accum += speed
            if self.snd_accum >= 16:
                self.snd_accum = 0.0
                play('step', self.step_i)
                self.step_i += 1

        for i in alive:
            if i.y + INV_H >= self.py:
                self.lose_life(instant=True)
                return

        # ----- invaders shoot -----
        self.fire_timer -= 1
        if self.fire_timer <= 0 and len(self.enemy_bullets) < 3:
            lo = max(16, 60 - self.wave * 4)
            hi = max(lo + 10, 110 - self.wave * 8)
            self.fire_timer = random.randint(lo, hi)
            s = random.choice(alive)
            self.enemy_bullets.append(
                pygame.Rect(int(s.x + INV_W // 2 - 2), int(s.y + INV_H), 4, 12))

        # ----- player bullet -----
        if self.player_bullet:
            self.player_bullet.y -= 10
            if self.player_bullet.bottom < 0:
                self.player_bullet = None

        if self.player_bullet:
            pb = self.player_bullet
            for i in self.invaders:
                if i.alive and pb.colliderect(
                        pygame.Rect(int(i.x), int(i.y), INV_W, INV_H)):
                    i.alive = False
                    self.score += (30, 20, 10)[i.kind]
                    play('kill')
                    self.player_bullet = None
                    break
            else:
                if self.player_bullet and self.carve(self.player_bullet):
                    self.player_bullet = None

        # ----- enemy bullets -----
        prect = self.player_rect()
        for b in self.enemy_bullets[:]:
            b.y += 5
            if b.top > H:
                self.enemy_bullets.remove(b)
                continue
            if self.carve(b):
                self.enemy_bullets.remove(b)
                continue
            if b.colliderect(prect):
                self.enemy_bullets.remove(b)
                self.lose_life()
                if self.state != "play":
                    return

    # ---------- menu actions ----------
    def menu_select(self):
        choice = self.MENU_ITEMS[self.menu_idx]
        play('blip')
        if choice == "start game":
            self.new_game()
            self.state = "play"
            play('start')
        elif choice == "help":
            self.state = "help"
        elif choice == "exit":
            return "quit"
        elif choice == "about":
            self.state = "about"
        elif choice == "settings":
            self.settings_idx = 0
            self.state = "settings"
        return None

    def settings_select(self):
        item = self.SETTINGS_ITEMS[self.settings_idx]
        if item == "sound":
            global SOUND_ENABLED
            SOUND_ENABLED = not SOUND_ENABLED
            play('blip')
        elif item == "fps":
            self.fps_idx = (self.fps_idx + 1) % len(self.FPS_CHOICES)
            self.fps_target = self.FPS_CHOICES[self.fps_idx]
            play('blip')
        elif item == "back":
            self.state = "menu"
            play('blip')

    def settings_adjust(self, d):
        item = self.SETTINGS_ITEMS[self.settings_idx]
        if item == "sound":
            global SOUND_ENABLED
            SOUND_ENABLED = not SOUND_ENABLED
            play('blip')
        elif item == "fps":
            self.fps_idx = (self.fps_idx + d) % len(self.FPS_CHOICES)
            self.fps_target = self.FPS_CHOICES[self.fps_idx]
            play('blip')

    # ---------- draw ----------
    def draw(self):
        screen.fill(BLACK)

        for (sx, sy, sb) in self.stars:
            screen.fill((sb, sb, sb), (sx, sy, 2, 2))

        for c in self.cells:
            screen.fill(GREEN, c)

        for i in self.invaders:
            if i.alive:
                screen.blit(INV_SPRITES[i.kind], (int(i.x), int(i.y)))

        if self.state in ("play", "gameover"):
            screen.blit(PLAYER_IMG, (int(self.px), self.py))

        if self.player_bullet:
            screen.fill(WHITE, self.player_bullet)
        for b in self.enemy_bullets:
            screen.fill(RED, b)

        # HUD (only during play / gameover)
        if self.state in ("play", "gameover"):
            text(screen, "SCORE %05d" % self.score, font_sml, WHITE, 20, 16, center=False)
            text(screen, "WAVE %d" % self.wave, font_sml, CYAN, W // 2, 16)
            for k in range(self.lives):
                screen.blit(PLAYER_MINI, (W - 26 - k * 28, 18))

        if self.state == "menu":
            self.draw_menu()
        elif self.state == "help":
            self.draw_help()
        elif self.state == "about":
            self.draw_about()
        elif self.state == "settings":
            self.draw_settings()
        elif self.state == "gameover":
            self.draw_gameover()

    def _overlay(self, alpha=190):
        ov = pygame.Surface((W, H), pygame.SRCALPHA)
        ov.fill((0, 0, 0, alpha))
        screen.blit(ov, (0, 0))

    # ---- file-browser / terminal main menu ----
    def draw_menu(self):
        self._overlay(200)

        # header — program title
        text(screen, "cat's py. space invaders port 0.1", font_med, GREEN, W // 2, 90)
        # separator line
        pygame.draw.line(screen, DKGREY, (W // 2 - 200, 158), (W // 2 + 200, 158), 2)

        # menu items with a ">" cursor
        top = 200
        line_h = 42
        for k, item in enumerate(self.MENU_ITEMS):
            y = top + k * line_h
            selected = (k == self.menu_idx)
            cursor = ">" if selected else " "
            color = YELLOW if selected else GREY
            label = "%s %s" % (cursor, item)
            text(screen, label, font_med, color, W // 2, y)

        # status footer
        files_state = "off"
        text(screen, "files = %s" % files_state,
             font_sml, DKGREY, W // 2 - 120, 470)
        text(screen, "%d fps" % self.fps_target,
             font_sml, DKGREY, W // 2 + 120, 470)

        # shortcuts + best
        text(screen, "[ up/down  move ]   [ enter  select ]   [ y  start ]   [ n  quit ]",
             font_sml, DKGREY, W // 2, 520)
        if self.best:
            text(screen, "BEST  %d" % self.best, font_sml, WHITE, W // 2, 560)

    # ---- help ----
    def draw_help(self):
        self._overlay(215)
        text(screen, "help", font_big, CYAN, W // 2, 70)
        pygame.draw.line(screen, DKGREY, (W // 2 - 200, 130), (W // 2 + 200, 130), 2)

        lines = [
            ("arrows / a-d", "move ship"),
            ("space", "fire"),
            ("y", "start game"),
            ("n / esc", "quit"),
            ("p", "pause (during play)"),
            ("", ""),
            ("enemy rows", "30 / 20 / 10 pts"),
            ("clear a wave", "bonus 100 x wave"),
            ("bunkers", "destructible cover"),
            ("", ""),
            ("goal", "survive. score. repeat."),
        ]
        y = 165
        for k, v in lines:
            if k:
                text(screen, k, font_sml, YELLOW, W // 2 - 190, y, center=False)
                text(screen, v, font_sml, WHITE, W // 2 - 10, y, center=False)
            y += 30

        text(screen, "press any key to return", font_sml, DKGREY, W // 2, H - 40)

    # ---- about ----
    def draw_about(self):
        self._overlay(215)
        text(screen, "about", font_big, PINK, W // 2, 70)
        pygame.draw.line(screen, DKGREY, (W // 2 - 200, 130), (W // 2 + 200, 130), 2)

        lines = [
            "cat's space invaders",
            "v0.1.1",
            "",
            "one file. no external assets.",
            "sound is generated on the fly",
            "with a tiny square-wave engine.",
            "",
            "made with python + pygame.",
        ]
        y = 175
        for line in lines:
            text(screen, line, font_sml, WHITE, W // 2, y)
            y += 30

        text(screen, "press any key to return", font_sml, DKGREY, W // 2, H - 40)

    # ---- settings ----
    def draw_settings(self):
        self._overlay(215)
        text(screen, "settings", font_big, YELLOW, W // 2, 90)
        pygame.draw.line(screen, DKGREY, (W // 2 - 200, 150), (W // 2 + 200, 150), 2)

        rows = [
            ("sound", "ON" if SOUND_ENABLED else "OFF"),
            ("fps", str(self.fps_target)),
            ("back", ""),
        ]
        top = 220
        line_h = 55
        for k, (name, value) in enumerate(rows):
            y = top + k * line_h
            selected = (k == self.settings_idx)
            cursor = ">" if selected else " "
            color = YELLOW if selected else GREY
            label = "%s %-10s" % (cursor, name)
            text(screen, label, font_med, color, W // 2 - 120, y, center=False)
            if value:
                text(screen, "< %s >" % value, font_med, CYAN, W // 2 + 120, y, center=False)

        text(screen, "left / right  change     enter  toggle",
             font_sml, DKGREY, W // 2, H - 80)
        text(screen, "esc  back", font_sml, DKGREY, W // 2, H - 45)

    # ---- game over ----
    def draw_gameover(self):
        self._overlay(170)
        text(screen, "GAME OVER", font_big, RED, W // 2, 170)
        text(screen, "SCORE  %d" % self.score, font_med, WHITE, W // 2, 260)
        text(screen, "WAVE   %d" % self.wave, font_med, CYAN, W // 2, 300)
        if self.score >= self.best and self.score > 0:
            text(screen, "NEW BEST!", font_med, YELLOW, W // 2, 350)
        else:
            text(screen, "BEST  %d" % self.best, font_sml, GREY, W // 2, 355)
        text(screen, "PRESS  Y  TO PLAY AGAIN", font_med, YELLOW, W // 2, 430)
        text(screen, "PRESS  N  TO QUIT", font_med, GREY, W // 2, 475)
        text(screen, "PRESS  M  FOR MAIN MENU", font_sml, GREY, W // 2, 520)


# ------------------------------------------------------------
#  MAIN LOOP
# ------------------------------------------------------------
def main():
    game = Game()
    running = True

    while running:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
                break

            if e.type != pygame.KEYDOWN:
                continue

            # global
            if e.key == pygame.K_ESCAPE:
                if game.state in ("help", "about", "settings"):
                    game.state = "menu"
                elif game.state == "play":
                    game.state = "menu"
                else:
                    running = False
                continue

            # ---- MENU ----
            if game.state == "menu":
                if e.key == pygame.K_UP:
                    game.menu_idx = (game.menu_idx - 1) % len(Game.MENU_ITEMS)
                    play('blip')
                elif e.key == pygame.K_DOWN:
                    game.menu_idx = (game.menu_idx + 1) % len(Game.MENU_ITEMS)
                    play('blip')
                elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                    if game.menu_select() == "quit":
                        running = False
                elif e.key == pygame.K_y:
                    game.new_game()
                    game.state = "play"
                    play('start')
                elif e.key == pygame.K_n:
                    running = False

            # ---- HELP / ABOUT (any key returns) ----
            elif game.state in ("help", "about"):
                game.state = "menu"
                play('blip')

            # ---- SETTINGS ----
            elif game.state == "settings":
                if e.key == pygame.K_UP:
                    game.settings_idx = (game.settings_idx - 1) % len(game.SETTINGS_ITEMS)
                    play('blip')
                elif e.key == pygame.K_DOWN:
                    game.settings_idx = (game.settings_idx + 1) % len(game.SETTINGS_ITEMS)
                    play('blip')
                elif e.key in (pygame.K_LEFT, pygame.K_a):
                    game.settings_adjust(-1)
                elif e.key in (pygame.K_RIGHT, pygame.K_d):
                    game.settings_adjust(1)
                elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                    game.settings_select()

            # ---- PLAY ----
            elif game.state == "play":
                if e.key == pygame.K_SPACE and game.player_bullet is None:
                    game.player_bullet = pygame.Rect(
                        int(game.px + PLAYER_W // 2 - 2),
                        game.py - 12, 4, 12)
                    play('shoot')

            # ---- GAME OVER ----
            elif game.state == "gameover":
                if e.key == pygame.K_y:
                    game.new_game()
                    game.state = "play"
                    play('start')
                elif e.key == pygame.K_n:
                    running = False
                elif e.key == pygame.K_m:
                    game.state = "menu"
                    game.menu_idx = 0
                    play('blip')

        game.update()
        game.draw()
        pygame.display.flip()
        clock.tick(game.fps_target)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()