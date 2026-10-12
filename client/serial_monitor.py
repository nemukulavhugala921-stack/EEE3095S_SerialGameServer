import sys
import serial
import serial.tools.list_ports

def find_stm32_port():
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if "STLink" in port.description or "STM" in port.description:
            return port.device
    # fallback to COM9 if detected earlier or first port
    for port in ports:
        if port.device == "COM9":
            return "COM9"
    if ports:
        return ports[0].device
    return "COM9"

def main():
    port = sys.argv[1] if len(sys.argv) > 1 else find_stm32_port()
    baud = 115200
    print(f"--- Opening Serial Monitor on {port} @ {baud} baud ---")
    print("--- (Press Ctrl+C to exit) ---")
    print("--- Now press the Black Reset Button on your STM32 board ---\n")

    try:
        with serial.Serial(port, baud, timeout=0.1) as ser:
            while True:
                data = ser.read(1024)
                if data:
                    sys.stdout.write(data.decode(errors='replace'))
                    sys.stdout.flush()
    except KeyboardInterrupt:
        print("\n--- Monitor closed ---")
    except Exception as e:
        print(f"\n[Error] {e}")

if __name__ == "__main__":
    main()
