# Добавление NVMe DXE

Проверенный module имеет GUID `5BE3BDF4-53CF-46A3-A6A9-73C34A6E5EE3`, размер
`0x5160`, SHA-256 `0D77ACA7597795AB8C70A70770740DF4D6BFCF95464983E4AEF63ACDD2F64072`.
PE headers: X64 (`0x8664`), PE32+ (`0x20B`).

В профиле board dump `2K110919` модуль занимает `0x132F48–0x1380A7`.
До вставки диапазон должен быть полностью `FF`; всё вне него обязано остаться
неизменным. В официальном `2K111114` тот же диапазон занят, поэтому этот offset
нельзя переносить на него механически.

`build_nvme_mod.py` намеренно принимает только точные известные хэши. Это не
универсальный AMI modder. После сборки нужно независимо проверить весь image и
иметь аппаратный recovery path.

Исходный NVMe driver находится в
[TianoCore EDK2](https://github.com/tianocore/edk2/tree/master/MdeModulePkg/Bus/Pci/NvmExpressDxe),
а EDK2 публикует [BSD-2-Clause-Patent license](https://github.com/tianocore/edk2/blob/master/License.txt).
Проверенный `.ffs` встречается в community-репозитории
[NVMe_support_on_old_motherboard](https://github.com/cjtim/NVMe_support_on_old_motherboard),
но его точные build metadata и отдельное разрешение на redistribution там не
задокументированы достаточно однозначно. Поэтому бинарник не распространяется:
пользователь получает его самостоятельно и сверяет параметры выше.
