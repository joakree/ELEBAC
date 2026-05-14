ELEBAC

Firmware and hardware files for the sensor and camera system developed for the Phoenix 2 rocket within UiS Aerospace.

Repository Structure

```text
ELEBAC/
├── Camera_System/
│   └── Firmware for the camera system
│
├── Sensor_System_PCB_Design/
│   └── Altium schematic and PCB design files for:
│       - Sensor Central PCB
│       - Strain Gauge Node PCB
│       - Thermocouple Node PCB
│
├── Sensor_System/
│   ├── Strain_Gauge/
│   │   ├── Prototype firmware for development and testing
│   │   └── Test_Results/
│   │       └── CSV files and MATLAB plot scripts
│   │
│   ├── Thermocouple/
│   │   ├── Prototype firmware for development and testing
│   │   └── Test_Results/
│   │       └── CSV files and MATLAB plot scripts
│   │
│   └── Thermocouple_PCB/
│       └── Firmware for the final PCB design
│           (not yet tested on physical hardware)



## Opening the Project Files

- STM32 firmware projects can be opened in STM32CubeIDE.
- PCB schematic and layout files were developed in Altium Designer.
- MATLAB scripts (.m) can be opened and executed in MATLAB.
- Python scripts can be executed using Python 3.
- CSV files contain logged test data used for analysis and plotting.




