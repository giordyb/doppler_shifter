import sys, pygame
from tkinter import Button
import os
from pygame.locals import *
import pygame

import pygame_widgets
from pygame_widgets.button import Button

os.putenv("SDL_FBDEV", "/dev/fb1")


class Text:
    def __init__(self, text, pos, **options):
        self.text = text
        self.pos = pos
        self.fontname = None
        self.fontsize = 72
        self.fontcolor = Color("black")
        self.set_font()
        self.render()

    def set_font(self):
        """Set the Font object from name and size."""
        self.font = pygame.font.Font(self.fontname, self.fontsize)

    def render(self):
        """Render the text into an image."""
        self.img = self.font.render(self.text, True, self.fontcolor)
        self.rect = self.img.get_rect()
        self.rect.topleft = self.pos

    def draw(self):
        """Draw the text image to the screen."""
        App.screen.blit(self.img, self.rect)


class Scene1:
    id = 0
    bg = Color("gray")

    def __init__(self, *args, **kwargs):
        # Append the new scene and make it the current scene
        App.scenes.append(self)
        App.scene = self

    def draw(self):
        """Draw all objects in the scene."""
        App.screen.fill(self.bg)
        for node in self.nodes:
            node.draw()
        pygame.display.flip()

    def __str__(self):
        return "Scene {}".format(self.id)


class App:
    def __init__(self):
        pygame.init()
        flags = RESIZABLE
        App.screen = pygame.display.set_mode((480, 320), flags)
        App.t = Text("Pygame App", pos=(20, 20))

        App.running = True

    def run(self):
        while App.running:
            events = pygame.event.get()
            for event in events:
                if event.type == QUIT:
                    App.running = False
            App.screen.fill(Color("gray"))
            App.t.draw()
            pygame_widgets.update(events)
            pygame.display.update()
            App.scene = App.scenes[0]

        pygame.quit()


if __name__ == "__main__":
    App().run()
