# SRL-Car-Controller
Controls 'Shell Racing Legends' RC cars on Windows via an controller.

![screenshot](https://raw.githubusercontent.com/whilefalse841/SRL-Car-Controller/refs/heads/main/screenshot.png)

Based on `control.py` found in https://github.com/mesailde/ShellRacingRemote.

### Improvements over the original
* Controller support (tested with Xinput)
* Works even when the window is not focused; controller slot is selectable (possible multiplayer, untested)
* Automatic Bluetooth scanning with filtering for supported car models
* Minor Bluetooth command optimizations

Controls are shown in the app.

## How to use

1. Enable Bluetooth.
2. Launch the `.exe`.
3. Wait for Bluetooth scanning to complete.
4. Select a detected car.
5. Wait for the connection to establish.
   
If something fails, retry or manually pair the car in Windows Bluetooth settings. The initial connection can be unreliable at times.



##### Disclaimer: The executable may trigger antivirus warnings due to how it listens for controller input and sends periodic Bluetooth messages, as well as the fact that it's a single-file exe made with PyInstaller. If you prefer full transparency and already have Python and the required libraries installed, you can run main.py instead. The app will be updated if a reliable way to reduce false positives is found.

### Supported models

| Internal Name       | Display Name                        | Bluetooth ID          |
|---------------------|-------------------------------------|-----------------------|
| 12CILINDRI          | 12Cilindri                          | `SL-12Cilindri`       |
| 296GT3              | 296 GT3                             | `SL-296 GT3`          |
| 296GTB              | 296 GTB                             | `SL-296 GTB`          |
| 330P                | 330 P 1965                          | `---`                 |
| 330P4               | 330 P4                              | `SL-330 P4(1967)`     |
| 488EVO              | 488 Challenge Evo                   | `SL-488 Challenge Evo`|
| 488GTE              | 488 GTE - AF Corse #51 2019         | `SL-488 GTE`          |
| 499P                | 499 P                               | `SL-499P`             |
| 499P(2024)          | 499P(2024)                          | `SL-499P N`           |
| 512S                | 512 S 1970                          | `---`                 |
| DaytonaSP3          | Daytona SP3                         | `SL-Daytona SP3`      |
| F175                | F1-75                               | `SL-F1-75`            |
| FXXK                | FXX-K EVO                           | `SL-FXX-K Evo`        |
| PUROSANGUE          | Purosangue                          | `SL-Purosangue`       |
| SF1000              | SF1000 - Tuscan GP - Ferrari 1000   | `SL-SF1000`           |
| SF23                | SF-23                               | `SL-SF-23`            |
| SF24                | SF-24                               | `SL-SF-24`            |
| SF90SPIDER          | SF90 Spider                         | `SL-SF90 Spider`      |
| SF90SPIDER(BLACK)   | SF90 Spider (Black)                 | `SL-SF90 Spider N`    |
| ShellCar            | *(string vazia)*                    | `SL-Shell Car`        |

##### Car list copied from https://github.com/mesailde/ShellRacingRemote.
