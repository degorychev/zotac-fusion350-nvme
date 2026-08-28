# Сводка диагностики NVRAM

До восстановления:

```text
MaximumVariableStorageSize:   65536
RemainingVariableStorageSize: 1310
efibootmgr: Cannot allocate memory
```

Статически: оба 64-KiB bank использованы, обнаружены сотни Link/history records.
Это указывает на физическое заполнение append-only store при небольшом числе
актуальных variables. Автоматический reclaim фактически не освободил достаточно
места; точная внутренняя причина в закрытом AMI driver не установлена.

После clean-NVAR recovery:

```text
efivarfs total:     65536
efivarfs used:       5292
efivarfs available: 55124
BootOrder: 0000,0001
```

Runtime подтвердил создание `Boot0000` и автономную загрузку PBS с NVMe после
обычного reboot. Вывод обезличен; raw efivars и GPT identifiers не публикуются.

