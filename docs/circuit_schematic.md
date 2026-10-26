# Circuit Schematic & Hardware Pinout

## Overview
The embedded game server is deployed on the **UCT STM32F051 Development Board** (designed by James Gowans). The system interfaces with a host PC through the onboard ST-Link V2 Virtual COM Port (VCP) and communicates physically through GPIO-driven status LEDs and a push button.

---

## 1. Pin Mapping Summary Table

| Peripheral | STM32 Pin | GPIO Mode | Active State | Description / Function |
| :--- | :---: | :---: | :---: | :--- |
| **USART1_TX** | `PA9` | Alternate Function 1 (`AF1`) | High (Idle) | Transmit line to ST-Link VCP RX (115200 8N1) |
| **USART1_RX** | `PA10` | Alternate Function 1 (`AF1`) | High (Idle) | Receive line from ST-Link VCP TX (115200 8N1) |
| **Button SW0** | `PA0` | Input with Internal Pull-up | Active-Low | Hardware game reset button (Debounced 50 ms) |
| **Status Red LED** | `PB10` | Output Push-Pull | Active-High | Player X turn indicator / Victory blinker |
| **Status Green LED** | `PB11` | Output Push-Pull | Active-High | Player O turn indicator / Victory blinker |
| **Data LED (D0)** | `PB0` | Output Push-Pull | Active-High | RX/TX serial traffic activity monitor |

---

## 2. Circuit Diagram (Schematic Representation)

> [!TIP]
> A publication-quality vector schematic is available at [**`docs/circuit_schematic.svg`**](file:///c:/Users/NEMUKULA%20VHUGALA/OneDrive%20-%20University%20of%20Cape%20Town/Desktop/3rd%20year/EEE3095S/EEE3096S_Project/docs/circuit_schematic.svg). You can import this directly into your IEEE report Word or LaTeX document without pixelation.

```text
                             +------------------------+
                             |    STM32F051C8T6       |
                             |    (LQFP-48 Package)   |
                             |                        |
     +3.3V (VDD)             |                        |
        |                    |                        |
     [ 40k internal pull-up ]|                        |
        |                    |                        |
        +------------------->| PA0 (SW0 Button)       |
        |                    |                        |
      [SW0] (Push Button)    |                        |
        |                    |                        |
       GND                   |                        |
                             |                        |
                             | PA9 (USART1_TX) -------> ST-Link VCP (RX Pin) ---> USB to PC
                             | PA10 (USART1_RX) <------ ST-Link VCP (TX Pin) <--- USB to PC
                             |                        |
                             | PB10 (Red Status) ---->[ 330R ]---> (Red LED) ----> GND
                             | PB11 (Green Status) ->[ 330R ]---> (Green LED) --> GND
                             | PB0  (Data LED D0) --->[ 330R ]---> (Blue/Yel LED)-> GND
                             |                        |
                             +------------------------+
```

---

## 3. Circuit Subsystem Analysis

### A. Power Supply Subsystem
* **Input Voltage:** $5.0\text{ V}$ from host USB connector via ST-Link.
* **Onboard Regulation:** Fixed $+3.3\text{ V}$ Low-Dropout (LDO) regulator supplying $V_{DD}$ and $V_{DDA}$.
* **Decoupling Capacitors:** Multiple $0.1\ \mu\text{F}$ ceramic surface-mount capacitors placed adjacent to each $V_{DD}/V_{SS}$ pin pair to suppress high-frequency switching noise.

### B. Serial Communication Subsystem (USART1)
* **Lines:** Full-Duplex UART over pins `PA9` (TX) and `PA10` (RX).
* **Baud Rate:** $115{,}200\text{ bps}$.
* **Format:** 8 Data Bits, No Parity, 1 Stop Bit (8N1).
* **Signal Conditioning:** Direct digital logic ($0\text{--}3.3\text{ V}$) connected to the onboard ST-Link STM32F103 chip, which translates serial frames into USB CDC packets for the host PC virtual COM port.

### C. Status LED Drivers (PB10, PB11, PB0)
* **Configuration:** GPIO Output Push-Pull, Low-Speed.
* **Current-Limiting Resistors:** $330\ \Omega$ surface-mount resistors in series with each LED.
* **Current Calculation:**
  $$I_{LED} = \frac{V_{DD} - V_{F}}{R} = \frac{3.3\text{ V} - 2.0\text{ V}}{330\ \Omega} \approx 3.94\text{ mA}$$
  This safely conforms within the maximum GPIO source limit ($25\text{ mA}$ per pin) and microcontroller total package rating ($120\text{ mA}$).

### D. User Button Interface (SW0 on PA0)
* **Configuration:** GPIO Input with internal pull-up enabled ($\approx 40\ \text{k}\Omega$).
* **Mechanism:** When idle (unpressed), pin PA0 reads logic `HIGH` ($3.3\text{ V}$). When pressed, the mechanical contacts close to `GND`, driving PA0 to logic `LOW` ($0\text{ V}$).
* **Contact Bounce Protection:** Handled in firmware by a non-blocking 50 ms debounce accumulator in `hardware.c`.
