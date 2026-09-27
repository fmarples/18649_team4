#include "current_sense.h"
#include <errno.h>
/* Part 3.5 has not been completed. Replace this backend only after identifying
 * the ACS712 variant, ADC-safe conditioning and measured conversion constants.
 * This implementation never configures ADC pins or fabricates measurements. */
int current_backend_read(int32_t ma[3], uint32_t *valid_mask)
{
    for (unsigned i = 0; i < CURRENT_CHANNELS; i++) ma[i] = CURRENT_UNAVAILABLE;
    *valid_mask = 0;
    return -ENOSYS;
}
