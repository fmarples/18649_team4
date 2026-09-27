#include "servo_core.h"
#include <string.h>
static bool pulse_valid(int pulse) { return pulse >= 500 && pulse <= 2500; }
void servo_reset(struct servo_control *s) { memset(s, 0, sizeof(*s)); }
bool servo_cal_valid(const struct servo_control *s)
{
 return s->marks == 7 && pulse_valid(s->left) && pulse_valid(s->center) &&
  pulse_valid(s->right) && ((s->left < s->center && s->center < s->right) ||
                          (s->left > s->center && s->center > s->right));
}
uint16_t servo_map(const struct servo_control *s, int32_t steer)
{
 if (!servo_cal_valid(s) || steer < -32768 || steer > 32767) return 0;
 int32_t endpoint = steer < 0 ? s->left : s->right;
 int32_t magnitude = steer < 0 ? -steer : steer;
 int32_t span = steer < 0 ? 32768 : 32767;
 return s->center + (int64_t)(endpoint - s->center) * magnitude / span;
}
bool servo_arm(struct servo_control *s, uint64_t now, bool self_test)
{
 if (self_test || s->mode != SERVO_OFF) return false;
 s->pulse = (s->marks & 2) ? s->center : 1500;
 s->heartbeat_ms = now;
 s->mode = SERVO_MANUAL;
 return true;
}
bool servo_step(struct servo_control *s, int delta)
{
 if (s->mode != SERVO_MANUAL ||
     !(delta == 25 || delta == -25 || delta == 5 || delta == -5) ||
     !pulse_valid(s->pulse + delta)) return false;
 s->pulse += delta;
 return true;
}
bool servo_mark(struct servo_control *s, unsigned mark)
{
 if (s->mode != SERVO_MANUAL) return false;
 if (mark == 1) s->left = s->pulse;
 else if (mark == 2) s->center = s->pulse;
 else if (mark == 4) s->right = s->pulse;
 else return false;
 s->marks |= mark;
 return true;
}
bool servo_live(struct servo_control *s, bool linked, bool self_test, int32_t steer)
{
 if (s->mode != SERVO_MANUAL || !servo_cal_valid(s) || !linked || self_test ||
     steer < -2000 || steer > 2000) return false;
 s->mode = SERVO_LIVE;
 s->pulse = servo_map(s, steer);
 return true;
}
void servo_tick(struct servo_control *s, uint64_t now, bool linked, bool self_test, int32_t steer)
{
 if (s->mode == SERVO_OFF) return;
 if (now - s->heartbeat_ms >= SERVO_LEASE_MS || self_test ||
     (s->mode == SERVO_LIVE && !linked)) {
  s->mode = SERVO_OFF; s->pulse = 0; return;
 }
 if (s->mode == SERVO_LIVE) {
  s->pulse = servo_map(s, steer);
  if (!s->pulse) s->mode = SERVO_OFF;
 }
}
