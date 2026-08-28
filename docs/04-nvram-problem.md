# Диагностика переполненного NVRAM

UEFI Shell видел NVMe и запускал fallback loader, но `efibootmgr` не мог создать
`Boot####`. `QueryVariableInfo()` для non-volatile variables вернул:

| Параметр | Значение |
|---|---:|
| MaximumVariableStorageSize | 65536 |
| RemainingVariableStorageSize | 1310 |
| Linux EFI_MIN_RESERVE | 5120 |

Поэтому Linux отказывался от операции до полного исчерпания store. Статический
разбор показал 529 records в первом bank и 600 во втором, преимущественно `Link`,
при малом free tail. Это указывает на накопленную append-only историю. Причина,
по которой firmware не выполнила reclaim автоматически, не доказана.

Скрипты в `tools/query_efi_variables/` только читают сведения и не меняют EFI
variables. Не публикуйте сырой efivarfs dump: он может содержать уникальные
идентификаторы и сведения о загрузке конкретной машины.

