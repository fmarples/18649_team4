#include "status.h"
#include "protocol.h"
#include "uart_link.h"
void status_send(uint8_t state, uint16_t m1, uint16_t m2, uint16_t servo) {
    status_frame_t s = { .type=FRAME_STATUS, .sequence=0, .motor1_current=m1,
                         .motor2_current=m2, .servo_current=servo, .state=state };
    uart_link_send_status(&s);
}
