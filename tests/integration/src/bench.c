#include <zephyr/ztest.h>
#define main bench_contract_entry
#include "../../test_motor_bench.c"
#undef main
ZTEST(motor_contracts, test_bench_compatibility) { zassert_equal(bench_contract_entry(), 0); }
