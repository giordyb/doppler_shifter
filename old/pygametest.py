import pygame
import os

os.putenv("SDL_FBDEV", "/dev/fb1")
os.putenv("SDL_MOUSEDRV", "TSLIB")
os.putenv("SDL_MOUSEDEV", "/dev/input/touchscreen")
pygame.init()

SCREEN_WIDTH = 480
SCREEN_HEIGHT = 320

lcd = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.mouse.set_visible(True)
lcd.fill((255, 0, 0))
pygame.display.update()


while True:
    for event in pygame.event.get():
        if event.type == pygame.MOUSEMOTION and pygame.mouse.get_pressed()[0]:
            print(pygame.mouse.get_pos())
