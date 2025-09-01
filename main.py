import pygame
import sys
import time
import random
import math

pygame.init()

# Fullscreen setup
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
screen_width, screen_height = screen.get_size()
pygame.display.set_caption("Pygame-Survival-Shooter")
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 55)
small_font = pygame.font.SysFont(None, 35)

# Game states
START, PLAYING, GAME_OVER, WIN = "start", "playing", "game_over", "win"
state = START


# Player class
class Player:
    def __init__(self):
        self.rect = pygame.Rect(screen_width // 2, screen_height // 2, 50, 50)
        self.color = (0, 150, 255)  # Blue
        self.speed = 5

    def handle_keys(self):
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT] and self.rect.x > 0:
            self.rect.x -= self.speed
        if keys[pygame.K_RIGHT] and self.rect.x < screen_width - 50:
            self.rect.x += self.speed
        if keys[pygame.K_UP] and self.rect.y > 0:
            self.rect.y -= self.speed
        if keys[pygame.K_DOWN] and self.rect.y < screen_height - 50:
            self.rect.y += self.speed

    def draw(self, surface):
        pygame.draw.rect(surface, self.color, self.rect)


# Bullet class
class Bullet:
    def __init__(self, x, y, target_x, target_y):
        self.rect = pygame.Rect(x + 20, y + 20, 10, 10)
        self.color = (255, 255, 0)  # Yellow
        self.speed = 12

        # Calculate normalized direction vector toward mouse
        dx = target_x - (x + 20)
        dy = target_y - (y + 20)
        distance = math.hypot(dx, dy)
        if distance == 0:
            distance = 1
        self.dx = dx / distance
        self.dy = dy / distance

    def move(self):
        self.rect.x += int(self.dx * self.speed)
        self.rect.y += int(self.dy * self.speed)

    def draw(self, surface):
        pygame.draw.rect(surface, self.color, self.rect)


# Enemy class
class Enemy:
    def __init__(self, speed_boost=0):
        x = random.randint(0, screen_width - 50)
        y = random.randint(0, screen_height - 50)
        self.rect = pygame.Rect(x, y, 50, 50)
        self.color = (255, 50, 50)  # Red
        self.base_speed = 1 + speed_boost
        self.speed = self.base_speed

    def follow(self, target):
        if self.rect.x < target.rect.x:
            self.rect.x += self.speed
        if self.rect.x > target.rect.x:
            self.rect.x -= self.speed
        if self.rect.y < target.rect.y:
            self.rect.y += self.speed
        if self.rect.y > target.rect.y:
            self.rect.y -= self.speed

    def draw(self, surface):
        pygame.draw.rect(surface, self.color, self.rect)

    def collision(self, target):
        return self.rect.colliderect(target.rect)


# Functions for screens
def draw_text_center(text, font, color, y):
    render = font.render(text, True, color)
    rect = render.get_rect(center=(screen_width // 2, y))
    screen.blit(render, rect)


def start_screen():
    screen.fill((30, 30, 30))
    draw_text_center("CHASE GAME", font, (255, 255, 255), screen_height // 3)
    draw_text_center(
        "Arrow Keys = Move", small_font, (200, 200, 200), screen_height // 2 - 40
    )
    draw_text_center(
        "Mouse Click = Shoot", small_font, (200, 200, 200), screen_height // 2
    )
    draw_text_center(
        "Survive 2 waves to WIN!", small_font, (200, 200, 200), screen_height // 2 + 40
    )
    draw_text_center(
        "Press any key to start", small_font, (200, 200, 200), screen_height // 2 + 100
    )
    pygame.display.flip()


def game_over_screen(score):
    screen.fill((30, 30, 30))
    draw_text_center("GAME OVER", font, (255, 0, 0), screen_height // 3)
    draw_text_center(
        f"Survived: {score} seconds", small_font, (255, 255, 255), screen_height // 2
    )
    draw_text_center(
        "Press R to Restart or Q to Quit",
        small_font,
        (200, 200, 200),
        screen_height // 2 + 60,
    )
    pygame.display.flip()


def win_screen(score):
    screen.fill((0, 100, 0))
    draw_text_center("YOU WIN! 🎉", font, (255, 255, 0), screen_height // 3)
    draw_text_center(
        f"Final Score: {score} seconds", small_font, (255, 255, 255), screen_height // 2
    )
    draw_text_center(
        "Press R to Play Again or Q to Quit",
        small_font,
        (200, 200, 200),
        screen_height // 2 + 60,
    )
    pygame.display.flip()


# Game loop
running = True
player = Player()
enemies = []
bullets = []
start_time = 0
score = 0
wave = 1

while running:
    if state == START:
        start_screen()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                player = Player()
                enemies = [Enemy() for _ in range(3)]
                bullets = []
                start_time = time.time()
                wave = 1
                state = PLAYING

    elif state == PLAYING:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left mouse click
                    mx, my = pygame.mouse.get_pos()
                    bullets.append(Bullet(player.rect.x, player.rect.y, mx, my))

        player.handle_keys()
        elapsed_time = int(time.time() - start_time)

        # Wave system
        if wave == 1 and elapsed_time >= 10:  # After 10 seconds → wave 2
            wave = 2
            enemies = [Enemy(speed_boost=1) for _ in range(5)]
        elif wave == 2 and elapsed_time >= 20:  # Survive wave 2
            score = elapsed_time
            state = WIN

        # Update enemies
        for enemy in enemies:
            enemy.follow(player)
            if enemy.collision(player):
                score = elapsed_time
                state = GAME_OVER

        # Update bullets
        for bullet in bullets[:]:
            bullet.move()
            if (
                bullet.rect.x < 0
                or bullet.rect.x > screen_width
                or bullet.rect.y < 0
                or bullet.rect.y > screen_height
            ):
                bullets.remove(bullet)
                continue

            for enemy in enemies[:]:
                if bullet.rect.colliderect(enemy.rect):
                    bullets.remove(bullet)
                    enemies.remove(enemy)
                    break

        # Draw everything
        screen.fill((30, 30, 30))
        player.draw(screen)
        for enemy in enemies:
            enemy.draw(screen)
        for bullet in bullets:
            bullet.draw(screen)

        timer_text = small_font.render(
            f"Time: {elapsed_time}  Wave: {wave}", True, (255, 255, 255)
        )
        screen.blit(timer_text, (10, 10))
        pygame.display.flip()
        clock.tick(60)

    elif state == GAME_OVER:
        game_over_screen(score)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    player = Player()
                    enemies = [Enemy() for _ in range(3)]
                    bullets = []
                    start_time = time.time()
                    wave = 1
                    state = PLAYING
                elif event.key == pygame.K_q:
                    running = False

    elif state == WIN:
        win_screen(score)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    player = Player()
                    enemies = [Enemy() for _ in range(3)]
                    bullets = []
                    start_time = time.time()
                    wave = 1
                    state = PLAYING
                elif event.key == pygame.K_q:
                    running = False

pygame.quit()
sys.exit()
