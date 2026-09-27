#include <zephyr/ztest.h>
/* Run main's existing production-controller contract unchanged on ARM/QEMU. */
#define main drive_contract_entry
#include "../../test_drive_control.c"
#undef main
ZTEST(motor_contracts, test_drive) { zassert_equal(drive_contract_entry(), 0); }
ZTEST_SUITE(motor_contracts, NULL, NULL, NULL, NULL, NULL);
