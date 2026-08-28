# QueryVariableInfo

Оба варианта только читают состояние UEFI variable services через Linux `efi_test`.
Модуль ядра должен быть доступен как `/dev/efi_test`.

```bash
sudo modprobe efi_test
sudo python3 query_variable_info.py
gcc -O2 -Wall query_variable_info.c -o query-variable-info
sudo ./query-variable-info
```

Код не создаёт, не удаляет и не меняет EFI variables. Значения следует сохранять
в обезличенном виде: вывод окружения может содержать сведения о конкретной машине.

