// SPDX-License-Identifier: MIT
// Read-only QueryVariableInfo() diagnostic via Linux efi_test.
#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <linux/ioctl.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/ioctl.h>
#include <unistd.h>

#pragma pack(push, 1)
struct efi_queryvariableinfo {
    uint32_t attributes;
    uint64_t *maximum_storage, *remaining_storage, *maximum_variable;
    unsigned long *status;
};
#pragma pack(pop)
#define EFI_RUNTIME_QUERY_VARIABLEINFO _IOR('p', 0x08, struct efi_queryvariableinfo)

int main(void) {
    int fd = open("/dev/efi_test", O_RDONLY | O_CLOEXEC);
    if (fd < 0) { fprintf(stderr, "open: %s\n", strerror(errno)); return 1; }
    puts("attrs ioctl EFI_STATUS maximum_storage remaining maximum_variable");
    for (uint32_t attr = 1; attr <= 7; ++attr) {
        uint64_t maximum = 0, remaining = 0, variable = 0;
        unsigned long status = ~0UL;
        struct efi_queryvariableinfo q = {attr, &maximum, &remaining, &variable, &status};
        int rc = ioctl(fd, EFI_RUNTIME_QUERY_VARIABLEINFO, &q);
        printf("0x%08" PRIx32 " %5d 0x%016lx %" PRIu64 " %" PRIu64 " %" PRIu64 "\n",
               attr, rc, status, maximum, remaining, variable);
    }
    close(fd);
    return 0;
}

