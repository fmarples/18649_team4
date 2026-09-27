#ifndef LAB_CURRENT_SENSE_H
#define LAB_CURRENT_SENSE_H
#include "current_cache.h"
/* Backend runs only in the priority-3 dedicated sampling workqueue. Return 0 on successful
 * acquisition, negative errno on failure. Set bits only for calibrated,
 * physically acquired channels. Signed mA are permitted; INT32_MIN is reserved.
 * Do ADC waits outside shared locks. No motor output or fault policy here. */
int current_backend_read(int32_t ma[3], uint32_t *valid_mask);
void current_sense_start(void); /* Main calls once; schedules the first work item. */
struct current_sample current_sense_snapshot(void);
#endif
