# NVMe-загрузка и восстановление NVRAM на ZOTAC FUSION350-B-E / E350ITX-B-E

> Практический разбор модернизации старой платы на AMD E-350: добавление NVMe DXE в AMI Aptio IV, диагностика ошибки `efibootmgr: Cannot allocate memory`, восстановление переполненного AMI NVAR и успешная загрузка Proxmox Backup Server напрямую с NVMe.

## Кратко

Исходная цель была простой: превратить старую mini-ITX плату ZOTAC FUSION350-B-E на AMD E-350 в компактный сервер Proxmox Backup Server, оставив все четыре SATA-порта под HDD. Для системного диска хотелось использовать NVMe через освободившийся mini-PCIe слот.

Плата была выпущена задолго до массового появления NVMe и штатной поддержки NVMe в UEFI не имела. После добавления `NvmExpressDxe_4` NVMe действительно появился в UEFI и с него стало возможно вручную запускать `BOOTX64.EFI`, но нормальная автоматическая UEFI-загрузка всё равно не работала.

Причина оказалась неожиданной: не NVMe, не GRUB и не архитектура DXE, а практически исчерпанный 64-KiB AMI NVAR store. Linux видел только 1310 байт свободного NVRAM, при этом для безопасной записи EFI variables сохранял резерв 5120 байт и возвращал `EFI_OUT_OF_RESOURCES`.

Позже был найден официальный BIOS Zotac `2K111114` (`A1114IZT..rom`). Его NVAR оказался заводски чистым: первый 64-KiB bank содержал только `StdDefaults`, второй bank был полностью стёрт (`FF`). Этот clean template был перенесён в уже рабочий NVMe-модифицированный BIOS без изменения firmware body.

После прошивки:

```text
efivarfs:
65536 total
5292 used
55124 available
```

`efibootmgr` успешно создал обычную UEFI-запись на NVMe, и после перезагрузки PBS самостоятельно загрузился без USB, UEFI Shell или другого bootstrap-носителя.

---

## 1. Аппаратная платформа

Плата:

- ZOTAC FUSION350-B-E / семейство E350ITX-B;
- AMD E-350 APU, 2 ядра, 1.6 GHz;
- AMD Hudson-M1 / M1 platform;
- mini-ITX;
- 4 SATA;
- mini-PCIe;
- PCIe x4;
- DDR3 SO-DIMM;
- встроенная графика Radeon HD 6310;
- AMI Aptio IV UEFI/CSM firmware.

SPI flash:

- Winbond `W25Q32BVAIG`;
- 32 Mbit = 4 MiB;
- 3.3 V SPI NOR;
- DIP-8, съёмная микросхема.

Именно съёмный DIP-8 сильно упростил эксперимент: полный recovery был возможен обычным программатором CH341A.

### Важное замечание по CH341A

Дешёвые чёрные CH341A исторически известны тем, что некоторые ревизии могут подавать нежелательные 5 V уровни на сигнальные линии при работе с 3.3 V flash. Перед использованием программатора разумно проверить реальные напряжения своей конкретной платы.

---

## 2. Исходная задача

Планировалось использовать плату как выделенный Proxmox Backup Server.

Основная идея:

- 4 SATA-порта оставить под HDD datastore;
- mini-PCIe Wi-Fi больше не нужен;
- вместо Wi-Fi установить mini-PCIe → NVMe адаптер;
- PBS разместить на NVMe;
- HDD использовать только для backup datastore.

Проблема: BIOS 2011 года ничего не знает о NVMe.

---

## 3. Снятие и верификация исходного BIOS

BIOS был считан аппаратным программатором несколько раз.

Три независимых чтения дали абсолютно одинаковый 4-MiB файл.

Проверенный исходный образ:

```text
bios_original_verified.bin

Size:
4194304 bytes

SHA-256:
833EFD7CB5A1D77C1F8B6E5D5B2701BDD75F08D806A20E762BB40A2FE61F5BE5

SHA-1:
F1923FF3A1DF8280FAEB29AED44B542529E1DFA2

MD5:
A2645B66B9A29E69A5D47511A551AABB
```

Это важный этап. BIOS-модификация без проверенного оригинального dump и recovery path — плохая идея.

---

## 4. Структура исходной прошивки

Прошивка оказалась AMI Aptio IV 4.6.4, UEFI/legacy hybrid.

Основная карта flash:

```text
0x000000–0x00FFFF   AMI NVAR
0x010000–0x01FFFF   второй NVAR/reclaim bank
0x020000–0x39FFFF   основной DXE/CSM/Option ROM FV
0x3A0000–0x3FFFFF   PEI/AGESA/recovery/boot block/VTF
```

Критически важный boot block расположен в последнем FV. Его модифицировать не требовалось.

Reset vector в конце ROM:

```text
offset 0x3FFFF0:

E9 0D E0 FF FF 00 00 10 00 00 78 56 00 00 FA FF
```

Основной DXE FV имел огромный свободный участок:

```text
0x132F48–0x39FFFF
size 0x26D0B8
= 2,543,800 bytes
```

То есть увеличивать flash с W25Q32 до W25Q64 не было никакого смысла: места внутри штатного DXE FV было более чем достаточно.

---

## 5. Ошибка, которую важно не повторять: IA32 или X64

По возрасту платы легко было предположить, что DXE firmware IA32.

Это предположение оказалось неверным.

Проверка PE headers ключевых модулей (`CORE_DXE`, `PciBus`, `AHCI`, `AhciSmm`) показала:

```text
Machine: 0x8664
Optional Header: 0x20B
```

То есть DXE — x86-64 / PE32+.

Поэтому нужен именно X64 `NvmExpressDxe_4`.

Урок здесь универсальный:

> Архитектуру UEFI-модуля нужно определять по PE header существующих DXE, а не по возрасту платы или CPU.

---

## 6. Добавление NVMe DXE

Был выбран модуль:

```text
Name:
NvmExpressDxe_4

GUID:
5BE3BDF4-53CF-46A3-A6A9-73C34A6E5EE3

Size:
20832 bytes
0x5160

Machine:
0x8664

Optional Header:
0x20B

Subsystem:
EFI boot-service driver

SHA-256:
0D77ACA7597795AB8C70A70770740DF4D6BFCF95464983E4AEF63ACDD2F64072
```

Модуль был добавлен прямо в настоящий свободный участок DXE FV, без перепаковки всего firmware volume:

```text
start: 0x132F48
end:   0x1380A7
```

После вставки:

- размер BIOS остался 4 MiB;
- все различия находились только в области нового FFS;
- NVRAM не менялся;
- PEI/boot FV не менялся;
- reset vector не менялся;
- UEFIExtract разбирал образ без ошибок.

Полученный образ:

```text
bios_nvme_mod.bin

SHA-256:
40E425C1D0597C1D5BE42DFB82E2790E1BE9FC833C2FF7EC02167DA35783CB72
```

---

## 7. Первый успех: NVMe действительно заработал

После прошивки модифицированного BIOS плата нормально проходила POST.

С установленным NVMe в Boot Manager появилась запись, отображаемая как:

```text
PATA:
```

Важно: это не означало, что NVMe внезапно стал PATA-устройством. AMI TSE/CSM просто классифицировал новый storage device в legacy BBS UI как generic hard drive.

Попытка загрузиться через эту запись заканчивалась:

```text
Reboot and select proper boot device
```

Но в UEFI Shell NVMe появился как filesystem, например:

```text
FS1:
```

И команда:

```text
FS1:\EFI\BOOT\BOOTX64.EFI
```

успешно загрузила Proxmox Backup Server.

Это было ключевое доказательство:

- NVMe DXE исполняется;
- NVMe controller enumerates;
- namespace читается;
- GPT читается;
- EFI System Partition читается;
- FAT читается;
- `BOOTX64.EFI` работает;
- Linux/PBS загружается.

После этого проблема уже не могла быть «NVMe не поддерживается».

Оставалось понять, почему firmware не создаёт нормальный UEFI Boot####.

---

## 8. Почему установка PBS всё равно падала

PBS installer запускался в UEFI mode:

```text
/sys/firmware/efi
```

существовал.

Но на финальном шаге установки bootloader появлялась ошибка примерно такого вида:

```text
efi_set_variable ... failed: Cannot allocate memory
failed to register the EFI boot entry
```

Позже уже из загруженного PBS:

```bash
efibootmgr -c \
  -d /dev/nvme0n1 \
  -p 2 \
  -L PBS \
  -l '\EFI\BOOT\BOOTX64.EFI'
```

давал:

```text
Could not prepare Boot variable: Cannot allocate memory
```

Это стало главным направлением расследования.

---

## 9. CSM оказался не основной проблемой

Был разобран Setup IFR.

Отдельного нормального переключателя:

- Launch CSM;
- CSM Support;
- UEFI only;
- Legacy only;
- Boot Mode;
- Boot Option Filter;

в прошивке не оказалось.

CSMCORE является постоянной частью firmware.

При этом были отдельные параметры вроде:

```text
PCI ROM Priority
Launch PXE OpROM
Launch Storage OpROM
```

Но глобально выключить CSM обычным Setup было нельзя.

Это объясняло странное отображение NVMe как `PATA:` в legacy BBS, но не объясняло невозможность создания UEFI Boot####.

---

## 10. Подозрение на NVRAM

Статический анализ NVAR показал крайне подозрительную картину.

Первый 64-KiB store:

```text
free tail ≈ 91 bytes
```

Второй:

```text
free tail ≈ 4780 bytes
```

Внутри находились сотни исторических записей:

- `MonotonicCounter`;
- `MemoryS3SaveNv`;
- `MemoryS3SaveVol`;
- `AllLegacyDevChecksum`;
- `LegacyDevOrder`;
- `BootOrder`;
- `LegacyDevChecksum`;
- `ConIn`;
- другие Link/Data chains.

При этом в firmware была найдена строка:

```text
Reached TSE Maximum supported variables
```

Это ещё не доказывало конкретную причину, но очень хорошо согласовывалось с проблемой variable store.

---

## 11. Странное поведение удаления Boot####

До очистки состояние выглядело примерно так:

```text
BootOrder: 0004,0003

Boot0003  Network Card  BBS(Network,,0x0)

Boot0004* Hard Drive    BBS(HD,,0x0)
                       PATA:
```

Удаление:

```bash
efibootmgr -b 0003 -B
```

возвращало:

```text
Could not delete variable: Cannot allocate memory
```

Но после этого `Boot0003` фактически исчез.

`BootOrder` при этом оставался:

```text
0004,0003
```

То же произошло с `Boot0004`.

Это очень важное наблюдение.

Вероятная последовательность:

1. `SetVariable(..., DataSize=0)` удаляет `Boot0003` — это проходит;
2. `efibootmgr` пытается записать новый `BootOrder`;
3. ненулевая NV-запись блокируется из-за нехватки variable storage;
4. пользователь видит `Cannot allocate memory`.

То есть операция была частично успешной.

---

## 12. Runtime-диагностика: причина подтверждена

Из работающего PBS был снят полный snapshot efivarfs.

На тот момент:

```text
live variables: 51
non-volatile: 34
volatile: 17
```

Суммарный логический NV payload составлял всего около:

```text
2530 bytes
```

То есть десятки килобайт физического store были заняты не текущими переменными, а историей append-only записей.

### QueryVariableInfo

Через Linux `efi_test` / `EFI_RUNTIME_QUERY_VARIABLEINFO` были получены реальные параметры firmware variable storage.

Для `NV|BS|RT`:

```text
MaximumVariableStorageSize:   65536
RemainingVariableStorageSize: 1310
MaximumVariableSize:          0
```

`MaximumVariableSize=0` при SUCCESS выглядит как дефект старой реализации AMI, но ключевой параметр здесь — `RemainingVariableStorageSize`.

Через efivarfs это же выглядело так:

```text
type=efivarfs
blocks=65536
free_blocks=1310
available=0
```

Linux x86 сохраняет минимальный EFI storage reserve:

```text
EFI_MIN_RESERVE = 5120 bytes
```

Если remaining storage ниже этого порога, kernel пытается спровоцировать firmware garbage collection, повторяет запрос и, если места не стало больше, возвращает:

```text
EFI_OUT_OF_RESOURCES
```

На уровне `efibootmgr` это проявляется как:

```text
Cannot allocate memory
```

То есть это **не RAM**.

Причина была установлена достаточно уверенно:

> 64-KiB non-volatile AMI variable store практически исчерпан физически, несмотря на небольшой объём реально живых переменных.

---

## 13. Почему обычное удаление variables не лечит ситуацию

AMI NVAR в этой прошивке ведёт себя как log-structured / append-oriented store.

Удаление variable не обязательно означает немедленное освобождение её старых physical records.

В store оставались сотни Link/Data/history records.

Поэтому «удалить побольше Boot####» — потенциально плохая стратегия:

- удаление может добавить новый tombstone/state record;
- физический tail может стать ещё меньше;
- без работающего reclaim/GC свободное место не возвращается.

Нужна была либо штатная реинициализация NVRAM, либо factory-clean template.

---

## 14. Поиск официального BIOS

Старая плата уже плохо находится на современном сайте Zotac.

Через старые страницы и Internet Archive удалось подтвердить модель:

```text
FUSION350-B-E
```

и старую download category:

```text
Fusion350-B
```

Позже был найден BIOS package `2K111114`.

ROM:

```text
A1114IZT..rom
```

Размер:

```text
4194304 bytes
```

Release note:

```text
AMD M1 Chipset (Fusion), DDR3, mITX Motherboard
AMI BIOS

A1114IZT.ROM BIOS for M1 Fusion, DDR3
* With STR
* With Hardware Monitor
* With LAN on board
* With HD Audio
* Zotac Full Screen Powerup Logo

32Mbit Flash
2011/Sept built core
Initial mass production release

2011/Oct update
CMOS Default - COM Port Enabled
Corrected CPU Temperature Reading in CMOS

2011/Nov update
Fixed CMOS Password cleared after BIOS update issue
Added Beep Sound for Memory Detection Failure
Changed Auto-Enter CMOS when no Boot Device in the system
Fixed can't enter CMOS from Del (Numeric Keypad)
Fixed waiting issue with Steel Series USB mouse
```

Хэш official ROM:

```text
SHA-256:
C14AC80DF372EBFC97B91E553DFE8FD67DFE66EA76378B289DACF1FA7522E48F
```

---

## 15. Сравнение official 2K111114 с BIOS платы

Результат оказался очень хорошим.

Official:

```text
BIOS-I-32M(2K111114)
AMI 4.6.4
AGESA OntaroPI V1.1.0.0
```

Board dump:

```text
BIOS-I-32M(2K110919)
AMI 4.6.4
AGESA OntaroPI V1.1.0.0
```

Все 89 уникальных FFS GUID из исходного firmware присутствовали и в official.

FV boundaries совпали:

```text
0x020000–0x39FFFF  DXE/CSM
0x3A0000–0x3FFFFF  PEI/boot
```

Ключевые:

- `CORE_DXE`;
- `Runtime`;
- `PciBus`;
- `AHCI`;
- `CSMCORE`;
- `AMITSE`;
- `Setup`;
- SATA/PATA;
- AGESA;
- Option ROM;

принадлежали одной firmware family.

Official действительно выглядел как более свежая ревизия той же платы/семейства, а не BIOS от случайно похожей motherboard.

---

## 16. Самое ценное в official ROM: factory-clean NVAR

Вот здесь нашёлся настоящий ключ к ремонту.

### Official `0x000000–0x00FFFF`

Первый NVAR FV:

```text
Physical records: 9
Full:             9
Link:             0
Data:             0
Invalid:          0
```

На верхнем уровне существовал только один live record:

```text
StdDefaults
```

Внутри него находились factory default records:

- `Setup`;
- `PlatformLang`;
- `Timeout`;
- `AMITSESetup`;
- `UsbSupport`;
- `AmiAgesaSetup`;
- `PNP0501_0_NV`;
- второй небольшой `Setup`.

Свободный tail:

```text
~64.5 KiB
```

### Official `0x010000–0x01FFFF`

Весь регион:

```text
FF FF FF FF ...
```

ровно 65536 байт.

Ни FV header, ни NVAR records.

Это характерное состояние factory-distribution image:

```text
bank 0 = clean initialized NVAR
bank 1 = erased reclaim/reserve area
```

---

## 17. Сравнение с забитым NVAR платы

В dump платы:

```text
store 0:
529 physical records
486 Link
free tail 91 bytes

store 1:
600 physical records
536 Link
free tail 4780 bytes
```

Всего:

```text
1129 physical records
1022 Link records
```

Сильнейший churn приходился на:

```text
MonotonicCounter
MemoryS3SaveNv
AllLegacyDevChecksum
MemoryS3SaveVol
LegacyDevOrder
BootOrder
LegacyDevChecksum
ConIn
```

Это были не сотни одновременно живых EFI variables, а накопленная история обновлений.

---

## 18. Уникальные данные платы

Перед заменой NVAR важно было понять, нет ли там identity конкретного экземпляра.

В первых 128 KiB не было найдено подтверждённых:

- motherboard MAC;
- system UUID;
- board serial;
- manufacturing identity;
- calibration blob.

Были machine/configuration-specific данные другого типа:

- SPD cache установленных DIMM;
- memory/S3 state;
- runtime addresses;
- BootOrder;
- Boot####;
- legacy device order;
- loader variables;
- monotonic counter.

Они не должны переноситься в clean store.

MAC, по всей видимости, хранится не в этом NVAR диапазоне.

---

## 19. Создание clean-NVAR NVMe BIOS

Базой оставили уже проверенный рабочий:

```text
bios_nvme_mod.bin
```

Из official ROM взяли только первые 128 KiB:

```text
0x000000–0x00FFFF   official clean NVAR FV
0x010000–0x01FFFF   official erased FF bank
```

А всё остальное:

```text
0x020000–0x3FFFFF
```

оставили побайтно из рабочего NVMe BIOS.

Новый образ:

```text
bios_nvme_clean_nvar.bin

Size:
4194304 bytes

SHA-256:
4678C13C79EFB5715B1D0A47787FCDCE52D4FA7D6B4849AA19DF5CFE7BDB4F28
```

### Проверки

Различия с `bios_nvme_mod.bin`:

```text
только 0x000000–0x01FFFF
```

За пределами первых 128 KiB:

```text
0 differing bytes
```

NVMe FFS остался:

```text
GUID:
5BE3BDF4-53CF-46A3-A6A9-73C34A6E5EE3

SHA-256:
0D77ACA7597795AB8C70A70770740DF4D6BFCF95464983E4AEF63ACDD2F64072
```

UEFIExtract:

```text
report: exit 0
guids:  exit 0
all:    exit 0
```

FV header checksums были корректны.

---

## 20. Первый boot после NVAR recovery

После прошивки clean-NVAR ROM система прошла POST.

Firmware заново создала runtime variables.

Из загруженного PBS:

```bash
df -B1 /sys/firmware/efi/efivars
```

получено:

```text
Filesystem     1B-blocks  Used Available Use%
efivarfs           65536  5292     55124   9%
```

Сравнение:

```text
до:
Remaining ≈ 1310 bytes
Available = 0

после:
Available = 55124 bytes
```

Это окончательно подтвердило диагноз.

---

## 21. Создание нормальной UEFI Boot entry

После восстановления NVRAM:

```bash
efibootmgr -v
```

показывал только автоматически созданный legacy hard drive entry:

```text
BootOrder: 0001
Boot0001* Hard Drive BBS(HD,,0x0)
```

Создание PBS entry:

```bash
efibootmgr -c \
  -d /dev/nvme0n1 \
  -p 2 \
  -L PBS \
  -l '\EFI\BOOT\BOOTX64.EFI'
```

впервые завершилось успешно:

```text
BootOrder: 0000,0001

Boot0000* PBS
HD(2,GPT,...,0x800,0x200000)
/File(\EFI\BOOT\BOOTX64.EFI)
```

Exit status:

```text
0
```

После:

```bash
sync
reboot
```

PBS загрузился самостоятельно с NVMe.

Без:

- USB boot drive;
- `startup.nsh`;
- отдельного `/boot` на флешке;
- постоянного UEFI Shell;
- legacy chainloader.

---

## 22. Итоговая причинно-следственная цепочка

Вся проблема в итоге выглядела так:

```text
старый Aptio IV
        |
        v
нет NVMe DXE
        |
        v
добавлен NvmExpressDxe_4
        |
        v
NVMe доступен UEFI
        |
        v
BOOTX64.EFI вручную работает
        |
        v
но Boot#### не создаётся
        |
        v
efibootmgr:
Cannot allocate memory
        |
        v
QueryVariableInfo:
65536 total / 1310 remaining
        |
        v
AMI NVAR забит append-only history
        |
        v
runtime GC не возвращает достаточно места
        |
        v
найден official factory BIOS
        |
        v
clean NVAR + erased reclaim bank
        |
        v
NVAR заменён, firmware body сохранён
        |
        v
55124 bytes available
        |
        v
Boot0000 PBS создаётся
        |
        v
native NVMe UEFI boot работает
```

---

## 23. Что здесь было действительно важно

### 23.1. Не путать `Cannot allocate memory` с RAM

В контексте `efibootmgr` это может быть `EFI_OUT_OF_RESOURCES` из firmware variable service.

Проверять нужно `QueryVariableInfo`, а не свободную оперативную память.

### 23.2. UEFI Shell — отличный диагностический инструмент

Если firmware shell может открыть NVMe filesystem и выполнить `BOOTX64.EFI`, то:

- NVMe DXE уже работает;
- filesystem stack работает;
- bootloader работает.

Это резко сужает область поиска.

### 23.3. Не доверять названию `PATA:` в старом AMI UI

Это может быть лишь legacy BBS classification нового storage device.

### 23.4. Не удалять variables вслепую при полном NVAR

В append-oriented variable store delete не обязательно возвращает physical space.

### 23.5. Factory ROM полезен не только как firmware update

Даже если не планируется шить официальный BIOS целиком, factory ROM может быть эталоном:

- NVAR layout;
- default variable schema;
- erased reclaim bank;
- firmware volume boundaries.

### 23.6. Recovery path меняет допустимый уровень риска

Съёмный W25Q32 + CH341A позволили экспериментировать гораздо увереннее, чем на плате с припаянным flash без внешнего programmer recovery.

---

## 24. Что не стоит выкладывать в публичный репозиторий

Этот проект можно документировать публично, но лучше не распространять:

- официальный Zotac ROM;
- полный дамп своей SPI flash;
- готовый модифицированный ROM;
- извлечённые большие AMI/Zotac firmware blobs.

Вместо этого достаточно публиковать:

- SHA-256;
- offsets;
- GUID;
- размеры;
- методику;
- анализ;
- build/verification scripts.

Пользователь должен самостоятельно получить оригинальный firmware image.

---

## 25. Известные хэши

### Исходный dump платы

```text
bios_original_verified.bin
4194304 bytes

SHA-256
833EFD7CB5A1D77C1F8B6E5D5B2701BDD75F08D806A20E762BB40A2FE61F5BE5
```

### Первый рабочий NVMe mod

```text
bios_nvme_mod.bin
4194304 bytes

SHA-256
40E425C1D0597C1D5BE42DFB82E2790E1BE9FC833C2FF7EC02167DA35783CB72
```

### Official Zotac 2K111114

```text
A1114IZT..rom
4194304 bytes

SHA-256
C14AC80DF372EBFC97B91E553DFE8FD67DFE66EA76378B289DACF1FA7522E48F
```

### Clean-NVAR NVMe mod

```text
bios_nvme_clean_nvar.bin
4194304 bytes

SHA-256
4678C13C79EFB5715B1D0A47787FCDCE52D4FA7D6B4849AA19DF5CFE7BDB4F28
```

### NvmExpressDxe_4 FFS

```text
GUID
5BE3BDF4-53CF-46A3-A6A9-73C34A6E5EE3

Size
0x5160
20832 bytes

SHA-256
0D77ACA7597795AB8C70A70770740DF4D6BFCF95464983E4AEF63ACDD2F64072
```

---

## 26. Команды диагностики, которые оказались полезны

### Проверка текущих EFI boot entries

```bash
efibootmgr -v
```

### Проверка efivarfs

```bash
df -B1 /sys/firmware/efi/efivars
```

### Количество variables

```bash
find /sys/firmware/efi/efivars -maxdepth 1 -type f | wc -l
```

### Безопасное чтение efivarfs

Обычный `cp` на некоторых AMI variables может получить:

```text
Illegal seek
```

Надёжнее последовательное чтение:

```bash
mkdir -p ./efi-vars-backup

for f in /sys/firmware/efi/efivars/*; do
    [ -f "$f" ] || continue
    cat "$f" > "./efi-vars-backup/$(basename "$f")"
done
```

### Создание UEFI boot entry

```bash
efibootmgr -c \
  -d /dev/nvme0n1 \
  -p 2 \
  -L PBS \
  -l '\EFI\BOOT\BOOTX64.EFI'
```

---

## 27. Проверенная конфигурация

Успешный результат был получен на:

```text
Motherboard:
ZOTAC FUSION350-B-E / E350ITX-B family

Platform:
AMD E-350 / Hudson-M1

Firmware:
AMI Aptio IV 4.6.4

Base board BIOS dump:
2K110919

NVMe driver:
NvmExpressDxe_4 X64

System:
Proxmox Backup Server

Boot:
native UEFI Boot#### from NVMe
```

Это **не означает**, что тот же binary mod безопасен для любой платы с E-350 или любой ревизии Zotac Fusion350.

---

## 28. Возможное дальнейшее развитие

Интересный следующий эксперимент — не только clean-NVAR версия старого `2K110919`, но и аккуратная интеграция NVMe DXE уже непосредственно в более свежий официальный `2K111114`.

При этом нельзя использовать старый offset `0x132F48`: в `2K111114` DXE layout изменён и свободное место начинается позже.

Такой вариант потенциально даст:

- более свежую official firmware revision;
- factory-clean NVAR;
- native NVMe support.

Но это отдельная модификация и должна валидироваться заново.

---

## 29. Заключение

Эта история начиналась как обычный «добавим NVMe DXE в старый BIOS», но в итоге оказалась намного интереснее.

Сам NVMe mod заработал почти сразу. Настоящая проблема была глубже: старый AMI Aptio IV годами накапливал NVAR history, пока 64-KiB variable store практически не закончился. Из-за этого Linux больше не позволял создавать новые non-volatile EFI variables, и установка bootloader выглядела сломанной.

Комбинация нескольких методов дала полный ответ:

- аппаратный SPI dump;
- структурный анализ Aptio IV;
- PE architecture verification;
- UEFI Shell;
- runtime efivarfs;
- `efibootmgr`;
- `QueryVariableInfo`;
- сравнение с official factory ROM;
- clean NVAR reconstruction;
- аппаратный recovery path.

Финальный результат — полноценная автоматическая UEFI-загрузка PBS с NVMe на плате 2011 года без внешнего boot-носителя.

---

## English summary

This project documents how native NVMe UEFI boot was added to a ZOTAC FUSION350-B-E / E350ITX-B family motherboard based on AMD E-350 and AMI Aptio IV.

Adding an x64 `NvmExpressDxe_4` driver successfully exposed the NVMe SSD to UEFI, and `\EFI\BOOT\BOOTX64.EFI` could be launched manually from UEFI Shell. However, creating a persistent EFI `Boot####` entry failed with:

```text
Could not prepare Boot variable: Cannot allocate memory
```

Runtime diagnostics showed that the firmware exposed a 64-KiB non-volatile variable store with only 1310 bytes remaining. Linux therefore returned `EFI_OUT_OF_RESOURCES` because the remaining space was below its EFI safety reserve.

Static analysis revealed heavy AMI NVAR append-only history with more than a thousand physical records, mostly obsolete Link chains.

An official Zotac `2K111114` BIOS was later found. Its NVAR area contained a canonical factory-clean first bank and a completely erased second reclaim bank. These first 128 KiB were used as a clean template while preserving the already working NVMe-modified firmware body.

After flashing the reconstructed image, efivarfs reported:

```text
65536 total
5292 used
55124 available
```

A standard UEFI `Boot####` entry pointing to the NVMe ESP was then created successfully, and Proxmox Backup Server booted directly from NVMe after a normal reboot.

No USB bootstrap or permanent UEFI Shell workaround was required.

---

См. также [инструменты и безопасный workflow](../README.md),
[известные хэши](../hashes/known-images.txt) и [отказ от гарантий](../DISCLAIMER.md).
