#ifndef BENCH_ENCODERS_H
#define BENCH_ENCODERS_H

#include <stdint.h>

/* Indices: 0=left, 1=right. Raw x4 counts, same convention as encoder_test.
 * Hand-turn calibration: vehicle-forward decreases left, increases right.
 * This module observes movement only; it does not provide stall protection. */
struct bench_encoder_sample {
    int64_t time_ms;
    int32_t counts[2];
    uint32_t invalid[2];
    uint32_t errors;
    int ab[2];
};

int bench_encoders_init(void);
/* Snapshot both counters under one lock; negative return on GPIO read errors. */
int bench_encoders_read(struct bench_encoder_sample *sample);

#endif
