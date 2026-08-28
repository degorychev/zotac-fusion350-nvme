# Анализ firmware

Исходный dump платы содержит AMI Aptio IV 4.6.4, build `2K110919`. Официальный
образ `A1114IZT..rom`, package `2K111114`, имеет тот же размер 4 MiB и совместимую
карту firmware volumes, ключевые GUID и архитектуру DXE. Основное firmware body
начинается с `0x020000`; первые 128 KiB отведены под два NVAR banks.

Статически подтверждено, что официальный образ относится к той же firmware
family. Отличия Setup/AMITSE, platform initialization и части драйверов
соответствуют более позднему build, поэтому официальный образ нельзя считать
побайтным replacement для dump без отдельной проверки ревизии платы.

Сводка без machine-specific данных находится в
[публичном отчёте](../reports/official_2K111114_comparison.md).

