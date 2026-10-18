/* Host adapter exposes the actual registered command handler; not a UART emulator. */
#ifndef TEST_LAB3_SHELL_H
#define TEST_LAB3_SHELL_H
#include <stddef.h>
struct shell { int unused; };
struct test_command {
    int (*handler)(const struct shell *, size_t, char **);
};
static inline void shell_error(const struct shell *s, const char *format, ...) {
    (void)s; (void)format;
}
#define shell_print shell_error
#define SHELL_CMD_ARG(name, sub, help, callback, required, optional) {callback}
#define SHELL_SUBCMD_SET_END {NULL}
#define SHELL_STATIC_SUBCMD_SET_CREATE(name, ...) static const struct test_command name[] = {__VA_ARGS__}
#define SHELL_CMD_REGISTER(name, sub, help, callback) const struct test_command *test_shell_##name = *(sub)
#endif
