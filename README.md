# StrawberryFruitNinja

Computer vision-guided automated strawberry decalyxing prototype developed for the Arkansas Food Innovation Center at the Market Center of the Ozarks (AFIC @ MCO).

This project integrates OpenCV-based strawberry detection, dynamic cut-height prediction, conveyor coordination, and linear actuator control on an NVIDIA Jetson platform to automate strawberry calyx removal.

---

## Overview

Manual strawberry decalyxing is repetitive, labor-intensive, and inconsistent for small-scale food processors. This prototype demonstrates a low-cost automation approach capable of adapting to varying strawberry geometries using real-time computer vision and actuator positioning.

The system uses:

- OpenCV color segmentation for strawberry and calyx detection
- Real-time cut-line prediction
- A vertically adjustable rotary blade
- Conveyor synchronization logic
- GPIO-based operator controls
- A Jetson Nano / Jetson Orin Nano embedded platform

---

## Features

- Real-time strawberry detection using HSV color segmentation
- Dynamic cut-height positioning
- Queue-based conveyor timing logic
- Linear actuator control using Sysfs PWM
- Start/stop operator control panel
- OpenCV visualization overlays
- Adjustable mask visualization for debugging
- Safety-oriented control structure

---

## Hardware Requirements

### Embedded System

- NVIDIA Jetson Nano or Jetson Orin Nano
- Ubuntu 22.04 recommended

### Sensors & Actuation

- USB camera (`/dev/video0`)
- Linear actuator
- PWM motor driver
- Rotary cutting tool (Dremel-style)
- Conveyor system
- Physical start/stop pushbuttons

### Electrical

GPIO wiring for:

- Start button
- Stop button
- Relay outputs
- PWM actuator control

---

## Software Dependencies

Install Python dependencies:

```bash
pip install opencv-python numpy Jetson.GPIO
```

Required system components:

- Python 3
- OpenCV 4.x
- GStreamer support enabled
- Jetson.GPIO

---

## Repository Structure

```text
.
├── main.py                # Main entry point
├── vision.py              # OpenCV detection and visualization
├── actuator.py            # Linear actuator + PWM control
├── button.py              # Operator button panel handling
├── statecontroller.py     # Main machine state logic
├── states.py              # State machine definitions
└── .gitignore
```

---

## Running the System

Launch the main program:

```bash
python3 main.py
```

---

## Keyboard Controls

| Key | Action |
|---|---|
| `1` | Start system |
| `2` | Stop system |
| `m` | Toggle mask visualization |
| `h` | Show help menu |
| `q` or `ESC` | Exit program |

---

## Vision Pipeline

The computer vision subsystem performs:

1. Region-of-interest cropping
2. HSV conversion
3. Red strawberry segmentation
4. Green calyx segmentation
5. Morphological filtering
6. Contour extraction
7. Cut-line estimation

The resulting cut coordinate is transmitted to the actuator subsystem for dynamic blade positioning.

---

## State Machine

The system operates using the following machine states:

- `IDLE`
- `RUNNING`
- `STOPPED`
- `ERROR`

The controller coordinates communication between:

- Vision subsystem
- Actuator subsystem
- Conveyor timing logic
- Operator controls

---

## Safety Notes

This repository is intended for educational and research purposes.

The physical prototype uses rotating cutting hardware and moving mechanical systems. Proper electrical safeguards, emergency stop systems, and operator supervision are required before operating any real hardware.

---

## Project Context

This project was developed as part of:

- BENG 48203 Senior Biological Engineering Design II
- University of Arkansas
- Client: Arkansas Food Innovation Center at the Market Center of the Ozarks (AFIC @ MCO)

---

## Authors

Samuel Vinson, Jabe Lovett, Alex Salonen, Kayla King  
Biological & Agricultural Engineering  
University of Arkansas

---

## Future Improvements

Potential future enhancements include:

- Deep learning-based strawberry segmentation
- Improved cut-line prediction
- Multi-fruit tracking
- Throughput optimization
- Closed-loop actuator feedback
- Industrial safety integration
- Automated fruit unloading

---

## License

This project is provided for educational and research use.
