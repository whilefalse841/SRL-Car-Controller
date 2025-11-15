# SRL-Car-Controller
Allows to connect to and remotely control "Shell Racing Legends" RC cars on Windows using a controller.

![screenshot](https://raw.githubusercontent.com/whilefalse841/SRL-Car-Controller/refs/heads/main/screenshot.png)

Based on `control.py` found in https://github.com/mesailde/ShellRacingRemote. Changes include:
- controller support (tested with Xinput controllers)
- controlling the car when the window isn't in focus, ability to pick used controller slot (should allow for multiplayer, not tested yet)
- automatically scanning for available Bluetooth devices and filtering for device names of known supported models
- possible optimization in the way the Bluetooth commands are sent over

Controls are as displayed in the app.

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
