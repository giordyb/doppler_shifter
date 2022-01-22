from logging import PlaceHolder
import pygame
import pygame_widgets

from pygame_widgets.button import Button
from pygame_widgets.textbox import TextBox
import datetime

import os
from pygame.locals import *

os.putenv("SDL_FBDEV", "/dev/fb1")


class SceneBase:
    def __init__(self):
        self.next = self

    def ProcessInput(self, events, pressed_keys):
        print("uh-oh, you didn't override this in the child class")

    def Update(self):
        print("uh-oh, you didn't override this in the child class")

    def Render(self, screen):
        print("uh-oh, you didn't override this in the child class")

    def SwitchToScene(self, next_scene):
        self.next = next_scene

    def Terminate(self):
        self.SwitchToScene(None)


def run_app(width, height, fps, starting_scene):
    pygame.init()
    screen = pygame.display.set_mode((width, height))
    clock = pygame.time.Clock()

    active_scene = starting_scene

    while active_scene != None:
        pressed_keys = pygame.key.get_pressed()

        # Event filtering
        filtered_events = []
        for event in pygame.event.get():
            quit_attempt = False
            if event.type == pygame.QUIT:
                quit_attempt = True
            elif event.type == pygame.KEYDOWN:
                alt_pressed = pressed_keys[pygame.K_LALT] or pressed_keys[pygame.K_RALT]
                if event.key == pygame.K_ESCAPE:
                    quit_attempt = True
                elif event.key == pygame.K_F4 and alt_pressed:
                    quit_attempt = True

            if quit_attempt:
                active_scene.Terminate()
            else:
                filtered_events.append(event)

        active_scene.ProcessInput(filtered_events, pressed_keys)
        active_scene.Update()
        active_scene.Render(screen)

        active_scene = active_scene.next

        pygame.display.flip()
        clock.tick(fps)


# The rest is code where you implement your game using the Scenes model


class Scene1(SceneBase):
    def __init__(self):
        SceneBase.__init__(self)

    def ProcessInput(self, events, pressed_keys):
        for event in events:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                # Move to the next scene when the user pressed Enter
                print("pressed")  # self.SwitchToScene(GameScene())
        pygame_widgets.update(events)

    def Update(self):
        pass

    def Render(self, screen):
        # For the sake of brevity, the title scene is a blank red screen
        button2 = Button(
            screen,
            0,
            0,
            100,
            100,
            text="Hello",  # Text to display
            fontSize=50,  # Size of font
            margin=20,
            onClick=lambda: self.SwitchToScene(Scene2()),
        )

        pygame.display.update()


class Scene2(SceneBase):
    def __init__(self):
        SceneBase.__init__(self)

    def ProcessInput(self, events, pressed_keys):
        pygame_widgets.update(events)

    def Update(self):
        pass

    def Render(self, screen):
        button3 = Button(
            screen,
            0,
            200,
            100,
            100,
            text="Quit",  # Text to display
            fontSize=50,  # Size of font
            margin=20,
            onClick=lambda: pygame.event.post(pygame.event.Event(pygame.QUIT)),
        )
        textbox = TextBox(screen, 0, 150, 800, 80, fontSize=30)
        textbox.setText(datetime.datetime.now())
        pygame.display.flip()


run_app(480, 320, 60, Scene1())
