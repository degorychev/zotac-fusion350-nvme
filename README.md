# NVMe boot и восстановление NVRAM на ZOTAC FUSION350-B-E / E350ITX-B-E

Это документированное исследование AMI Aptio IV на плате ZOTAC с AMD E-350 и
Hudson-M1. Целью было превратить компактную старую плату в Proxmox Backup
Server/NAS: оставить все четыре SATA-порта дискам, а систему разместить на NVMe
через mini-PCIe.

> **[Полная история исследования: от первого SPI dump до native NVMe boot](docs/FULL_STORY_RU.md)** — основной подробный материал проекта с хронологией, диагностикой и итогами.

Результат подтверждён на конкретном экземпляре платы: X64 NVMe DXE дал UEFI
доступ к накопителю, очистка переполненного NVAR восстановила запись `Boot####`,
и обычный reboot загрузил PBS с NVMe. Репозиторий не содержит готовых BIOS.

## Аппаратная платформа

- ZOTAC FUSION350-B-E / E350ITX-B-E, mini-ITX;
- AMD E-350, chipset Hudson-M1;
- четыре SATA и mini-PCIe;
- съёмная SPI flash Winbond W25Q32, 4 MiB, DIP-8;
- CH341A использовался как аппаратный recovery mechanism.

Перед работой с CH341A проверьте реальное напряжение на выводах: у ряда дешёвых
чёрных плат программатора известны нежелательные уровни 5 V. Не подключайте SPI
flash, пока схема и питание не проверены измерением.

## Две разные проблемы

Исходный AMI Aptio IV 4.6.4, build `2K110919`, не имел NVMe DXE. После добавления
`NvmExpressDxe_4` UEFI Shell увидел NVMe filesystem и успешно запускал
`\EFI\BOOT\BOOTX64.EFI`. Однако `efibootmgr` отвечал:

```text
Could not prepare Boot variable: Cannot allocate memory
```

Это была не нехватка RAM и не поломка NVMe. `QueryVariableInfo()` показал NV
store размером 65536 байт и только 1310 байт остатка. Linux сохраняет
`EFI_MIN_RESERVE = 5120`, поэтому создание новой variable завершалось
`EFI_OUT_OF_RESOURCES`. Удаление отдельных `Boot####` иногда помещалось в
оставшееся место, тогда как append новой `BootOrder` — уже нет.

## Урок об архитектуре DXE

Возраст платы мог подтолкнуть к ошибочному выбору IA32. Проверка PE headers
показала X64: `Machine = 0x8664`, формат `PE32+ = 0x20B`. Архитектуру firmware
module нужно определять по PE, а не по возрасту CPU или платы.

## Что было в NVAR

Статический разбор двух 64-KiB областей обнаружил сотни записей `Link`, историю
`Data` и устаревшие записи при небольшом числе логически живых variables. Это
согласуется с append-only поведением AMI NVAR: обновление оставляет историю, а
освобождение физического места зависит от reclaim/garbage collection.

Точная семантика всех внутренних типов не доказана исходным кодом AMI. В этом
репозитории `Full`, `Link` и `Data` — наблюдаемые категории анализатора, а вывод
о не сработавшем reclaim — наиболее согласующаяся с runtime и статикой гипотеза.

```text
official 2K111114:
  0x000000–0x00FFFF  factory-clean NVAR FV со StdDefaults
  0x010000–0x01FFFF  erased FF bank

used board dump:
  0x000000–0x00FFFF  heavily used NVAR
  0x010000–0x01FFFF  heavily used NVAR
```

Официальный `A1114IZT..rom` (`2K111114`, 4 MiB, SHA-256 приведён в
[таблице хэшей](hashes/known-images.txt)) относится к той же firmware family.
Release notes указывают на сентябрьский production release, октябрьские правки
CMOS defaults/CPU temperature и ноябрьские правки обновления пароля, memory beep,
автовхода в Setup, клавиатуры и USB mouse. Структурное сравнение не показало
доказательств нового механизма reclaim; чистое состояние NVAR объясняется тем,
что официальный update image является factory template.

## Восстановление NVAR и результат

В экспериментальном образе первые 128 KiB были взяты из проверенного
официального factory template, а `0x020000–0x3FFFFF` оставлен побайтно идентичным
рабочему NVMe BIOS. Никакие live variables старого экземпляра не переносились.
После прошивки firmware самостоятельно создал runtime variables из defaults:

```text
efivarfs: 65536 total, 5292 used, 55124 available
Boot0000* PBS HD(2,GPT,...)/File(\EFI\BOOT\BOOTX64.EFI)
BootOrder: 0000,0001
```

Затем PBS загрузился с NVMe при обычном reboot без USB и Shell. Это runtime
подтверждение для одной платы, а не гарантия для другой ревизии.

## Воспроизводимый workflow

Нужны локально полученные пользователем файлы. Все builders fail closed,
проверяют точные известные хэши, не меняют inputs и отказываются перезаписывать
существующий output.

```bash
python3 tools/verify_rom.py /path/to/local-image

python3 tools/build_nvme_mod.py \
  --base /path/to/verified-board-dump \
  --nvme /path/to/NvmExpressDxe_4.ffs \
  --output /path/to/new-nvme-image

python3 tools/build_clean_nvar_mod.py \
  --working /path/to/verified-nvme-image \
  --official /path/to/official-update-image \
  --output /path/to/new-clean-nvar-image
```

Важно: проверенный insert profile относится к реальному dump `2K110919`.
Применять его напрямую к официальному `2K111114` нельзя: этот диапазон там занят.
Конкретная community-сборка `NvmExpressDxe_4.ffs` также не включена: хотя исходный
EDK2 NVMe driver имеет permissive license, точные provenance/build metadata этой
сборки не установлены достаточно однозначно для её перераспространения.

Подробнее: [анализ firmware](docs/02-firmware-analysis.md),
[NVMe mod](docs/03-nvme-mod.md), [диагностика NVRAM](docs/04-nvram-problem.md),
[recovery](docs/07-recovery-with-ch341a.md) и [технические параметры](docs/technical-details.md).

## Безопасность

Не экспериментируйте с BIOS mod без проверенного аппаратного recovery path.
Сначала прочитайте [DISCLAIMER.md](DISCLAIMER.md). Этот проект не официальный,
не распространяет proprietary firmware и не обещает совместимость с другими
revision платы.

Основная документация — русская. Краткое английское описание: [README_EN.md](README_EN.md).
