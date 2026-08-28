# Технические параметры

| Объект | Значение |
|---|---|
| ROM size | `0x400000` |
| NVAR bank 0 | `0x000000–0x00FFFF` |
| NVAR bank 1 | `0x010000–0x01FFFF` |
| Firmware body | `0x020000–0x3FFFFF` |
| NVMe FFS range | `0x132F48–0x1380A7` |
| NVMe FFS size | `0x5160` |
| NVMe architecture | X64, PE32+ |

Clean official bank 0: один верхнеуровневый `StdDefaults`, 9 наблюдаемых `Full`
records с учётом embedded defaults, без `Link`, `Data` и `Invalid`; free tail
`0x3A9–0xFFEF` (`0xFC47`). Bank 1 — 65536 байт `FF`.

Used dump: bank 0 — 529 records (`39 Full`, `486 Link`, `4 Data`), 91 free byte;
bank 1 — 600 records (`37 Full`, `536 Link`, `9 Data`, `15 Invalid`,
`3 InvalidLink`), 4780 free bytes. Категории отражают результат конкретного
парсера и не претендуют на полную спецификацию закрытого формата AMI.

