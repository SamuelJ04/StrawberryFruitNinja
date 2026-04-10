# -------------------------------------------------------------
# main.py
# Name: Sam Vinson
# Course: BENG 48203 Senior Biological Engineering Design II
# Date: 03/31/2026
# Purpose: Main program for Fruit Ninja strawberry decalyxing
# -------------------------------------------------------------
import time

from vision import VisionSystem
from actuator import LinearActuator
from button import ButtonPanel
from statecontroller import StrawberryMachineController


def main():
    vision = None
    actuator = None
    buttons = None

    try:
        vision = VisionSystem()
        actuator = LinearActuator()
        buttons = ButtonPanel(start_pin=22, stop_pin=24)

        controller = StrawberryMachineController(
            vision=vision,
            actuator=actuator,
            buttons=buttons
        )

        print("Vision actuator, buttons, controller all successfully loaded!")
        print("Press 'h' for a help menu of keyboard inputs!")

        while True:
            controller.update()
            time.sleep(0.03)

    except KeyboardInterrupt:
        print("Exiting on keyboard interrupt")

    finally:
        if vision is not None:
            vision.release()
        if actuator is not None:
            actuator.cleanup()
        if buttons is not None:
            buttons.cleanup()


if __name__ == "__main__":
    main()