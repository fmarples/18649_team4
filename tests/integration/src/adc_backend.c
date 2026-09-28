#include <zephyr/ztest.h>
int adc_contract_0_entry(void);
int adc_contract_5_entry(void);
int adc_contract_7_entry(void);
ZTEST(adc_backend, test_disabled) { zassert_equal(adc_contract_0_entry(), 0); }
ZTEST(adc_backend, test_left_and_servo) { zassert_equal(adc_contract_5_entry(), 0); }
ZTEST(adc_backend, test_all_and_faults) { zassert_equal(adc_contract_7_entry(), 0); }
ZTEST_SUITE(adc_backend, NULL, NULL, NULL, NULL, NULL);
