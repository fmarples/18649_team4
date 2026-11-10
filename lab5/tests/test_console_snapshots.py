"""Run the production console handlers with lock/output probes on the host.

This tests snapshot boundaries and lock ownership, not Zephyr scheduling or
UART latency. The handler source is extracted so the test cannot silently use
a second implementation of the export loop.
"""

import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

HARNESS = r'''
#include "lab5.h"
#include "store.h"
#include <assert.h>
#include <errno.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define ARG_UNUSED(x) (void)(x)
#define K_FOREVER -1
struct shell { int unused; };
static struct l5_raft raft;
static struct l5_store store;
static int raft_lock, held, growing, fail_at, reads, lines, errors;
static struct shell uart_shell;
#define SHELL_NORMAL 0
static const struct shell *shell_backend_uart_get_ptr(void) { return &uart_shell; }
static bool shell_ready(const struct shell *s) { assert(s == &uart_shell); return true; }
static unsigned max_read, end_seen;
static char first_line[256], last_line[256];
static void k_mutex_lock(int *lock, int timeout) {
    (void)timeout;
    assert(lock == &raft_lock && !held); held = 1;
}
static void k_mutex_unlock(int *lock) {
    assert(lock == &raft_lock && held); held = 0;
}
bool l5_store_read(void *s, uint16_t i, struct l5_entry *e) {
    assert(s == &store && held);
    reads++; max_read = i;
    if (i == fail_at) return false;
    e->term = 513; e->event = L5_NOOP;
    return true;
}
const char *l5_event_name(uint8_t event) {
    assert(event == L5_NOOP); return "NOOP";
}
static void vprintk(const char *format, va_list ap) {
    (void)format; (void)ap;
    assert(0 && "Active shell must own all application output");
}
static void shell_vfprintf(const struct shell *sh, int color, const char *format, va_list ap) {
    /* Simulate a protocol task becoming runnable during slow UART output. */
    assert(!held && sh == &uart_shell && color == SHELL_NORMAL);
    vsnprintf(last_line, sizeof(last_line), format, ap);
    last_line[strcspn(last_line, "\n")] = 0;
    if (!lines++) strcpy(first_line, last_line);
    if (!strncmp(last_line, "LOG_END", 7)) end_seen++;
    if (!strncmp(last_line, "LOG_ERROR", 9)) errors++;
    if (growing) raft.commit++;
}
'''

MAIN = r'''
int main(int argc, char **argv) {
    assert(argc == 2);
    struct shell shell = {0};
    raft.id = 2; raft.leader = 2; raft.term = 513; raft.commit = 1801;
    raft.graph = (struct l5_graph){.nodes = 7, .links = 63, .cockpit_ok = false};
    int mode = atoi(argv[1]);
    if (mode == 0) {
        growing = 1;
        assert(network_cmd(&shell, 0, NULL) == 0);
        assert(!strcmp(first_line, "NETWORK node=2 term=513 leader=2 commit=1801 nodes=0x7 links=0x3f cockpit_ok=0"));
        assert(raft.commit == 1802 && !held);
    } else {
        if (mode == 2) growing = 1;
        if (mode == 3) fail_at = 20;
        int result = log_cmd(&shell, 0, NULL);
        assert(!held);
        if (mode == 3) {
            assert(result == -EIO && errors == 1 && end_seen == 0);
            assert(reads == 20 && max_read == 20);
        } else {
            assert(result == 0 && errors == 0 && end_seen == 1);
            assert(reads == 1801 && max_read == 1801 && lines == 1803);
            assert(!strcmp(first_line, "LOG_BEGIN node=2 through_index=1801"));
            assert(!strcmp(last_line, "LOG_END node=2 through_index=1801 entries=1801"));
            if (growing) assert(raft.commit == 3604);
        }
    }
    return 0;
}
'''


class ConsoleSnapshotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        directory = Path(cls.temp.name)
        source = (ROOT / "stm32_zephyr/src/lab5_runtime.c").read_text()
        console = source[source.index("void lab5_console_print("):
                         source.index("K_SEM_DEFINE(ready")]
        handlers = source[source.index("static int network_cmd("):
                          source.index("static int event_cmd(")]
        test_c = directory / "console.c"
        test_c.write_text(HARNESS + console + handlers + MAIN)
        cls.program = directory / ("console.exe" if os.name == "nt" else "console")
        compiler = shlex.split(os.environ.get("CC", "gcc"))
        if not shutil.which(compiler[0]):
            compiler = [sys.executable, "-m", "ziglang", "cc"]
        subprocess.run(compiler + ["-std=c11", "-Wall", "-Wextra", "-Werror",
                                  f"-I{ROOT / 'core'}", str(test_c),
                                  "-o", str(cls.program)],
                       check=True, capture_output=True, text=True)

    def run_case(self, mode):
        subprocess.run([str(self.program), str(mode)], check=True,
                       capture_output=True, text=True, timeout=10)

    def test_network_output_does_not_hold_protocol_lock(self):
        self.run_case(0)

    def test_long_log_releases_lock_before_every_output(self):
        self.run_case(1)

    def test_concurrent_append_does_not_move_export_end(self):
        self.run_case(2)

    def test_read_failure_reports_incomplete_export(self):
        self.run_case(3)


if __name__ == "__main__":
    unittest.main()
