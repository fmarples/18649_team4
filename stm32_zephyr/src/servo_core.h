#ifndef SERVO_CORE_H
#define SERVO_CORE_H
#include <stdbool.h>
#include <stdint.h>
#define SERVO_PERIOD_US 20000U
#define SERVO_LEASE_MS 500U
enum servo_mode { SERVO_OFF, SERVO_MANUAL, SERVO_LIVE };
struct servo_control {
 enum servo_mode mode;
 uint16_t pulse, left, center, right;
 uint8_t marks;
 uint64_t heartbeat_ms;
};
void servo_reset(struct servo_control *s);
bool servo_cal_valid(const struct servo_control *s);
uint16_t servo_map(const struct servo_control *s, int32_t steer);
bool servo_arm(struct servo_control *s, uint64_t now, bool self_test);
bool servo_step(struct servo_control *s, int delta);
bool servo_mark(struct servo_control *s, unsigned mark);
bool servo_live(struct servo_control *s, bool linked, bool self_test, int32_t steer);
void servo_tick(struct servo_control *s, uint64_t now, bool linked, bool self_test, int32_t steer);
#endif
