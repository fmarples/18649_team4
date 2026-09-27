#include <zephyr/ztest.h>
#define main throttle_contract_entry
#include "../../test_throttle_mapping.c"
#undef main
ZTEST(motor_contracts, test_throttle) { zassert_equal(throttle_contract_entry(), 0); }
