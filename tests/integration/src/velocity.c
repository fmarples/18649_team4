#include <zephyr/ztest.h>
#define main velocity_contract_entry
#include "../../test_velocity_control.c"
#undef main
ZTEST(motor_contracts, test_velocity) { zassert_equal(velocity_contract_entry(), 0); }
