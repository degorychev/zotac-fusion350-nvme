# Публичная сводка сравнения official 2K111114

Официальный `A1114IZT..rom` имеет размер 4194304 байта и SHA-256
`C14AC80DF372EBFC97B91E553DFE8FD67DFE66EA76378B289DACF1FA7522E48F`.
Он идентифицирован как AMI Aptio IV той же hardware/firmware family, что и
проверенный board dump `2K110919`.

## Firmware volumes и modules

Структура `0x020000–0x3FFFFF`, карта основных FV, архитектура и GUID ключевых
PEI/DXE совместимы. Наблюдаемые изменения затрагивают более поздние варианты
Setup/AMITSE и platform modules и согласуются с release notes, но не доказывают
поддержку другой PCB revision. Официальный image не является побайтным клоном
board dump, поэтому модификации по offsets нельзя переносить без проверки.

Сравнение Setup, AMITSE, CSMCORE, AGESA, SATA/AHCI, PATA, RAID, PXE, ACPI,
SMBIOS/DMI, Option ROM и Volume Top File не обнаружило признака другой основной
платформы. При этом различия в platform initialization делают замену всего body
менее консервативной, чем перенос только canonical NVAR template.

Полный исходный аналитический отчёт не публикуется, поскольку он содержит
низкоуровневые извлечения и machine-specific material, не необходимые для
воспроизведения вывода.

## NVAR comparison

| Образ | Bank 0 | Bank 1 |
|---|---|---|
| official | clean FV; `StdDefaults`; большой free tail | полностью `FF` |
| used dump | 529 records; 91 free byte | 600 records; 4780 free bytes |

В официальном template не было `Boot####`, `BootOrder` или старой Link/Data
history. Анализ не выявил MAC, UUID, board serial, SPD cache/training material
или иной уникальный идентификатор, который требовалось бы сохранить из него.
Это позволяет классифицировать official first 128 KiB как пригодный clean NVAR
template для строго проверенной firmware family.

## Вывод

Для проверенного workflow перенос exact `0x000000–0x01FFFF` из official image с
сохранением body рабочего NVMe image был оценён как безопаснее реконструкции
закрытого формата AMI вручную. Runtime после прошивки подтвердил восстановление
записи variables. Вывод ограничен одним экземпляром платы и точными хэшами.

