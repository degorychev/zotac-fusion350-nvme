# Установка PBS на NVMe

Этот проект не заменяет документацию Proxmox. Проверенный порядок был таким:

1. Установить PBS на GPT-размеченный NVMe.
2. Проверить fallback loader `\EFI\BOOT\BOOTX64.EFI` из UEFI Shell.
3. После восстановления NVRAM создать native entry через `efibootmgr`.
4. Проверить `BootOrder`, затем выполнить обычный reboot без Shell/USB.

Публикуемый пример намеренно не содержит GPT partition GUID конкретного диска.
Перед изменением boot variables сохраните обезличенный диагностический вывод.

