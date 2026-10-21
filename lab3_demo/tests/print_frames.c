/* Prints frames built by the production can_protocol.c for test_host.py to
 * compare against pi/can_protocol.py. Sequence nibbles stay zero here. */
#include "can_protocol.h"
#include <stdio.h>

static void show(const char *name, struct can_frame *f)
{
    lab3_seal(f);
    printf("%s %03x", name, (unsigned)f->id);
    for (unsigned i = 0; i < 8; ++i) printf(" %02x", f->data[i]);
    printf(" valid=%d\n", lab3_frame_valid(f));
}

int main(void)
{
    struct can_frame f;
    lab3_pack_heartbeat(&f, ID_HB_N3, STATE_OK, true, false);
    show("hb", &f);
    lab3_pack_fault(&f, ZONE_N1, FAULT_ZONE_LOST, ZONE_N2);
    show("fault", &f);
    lab3_pack_force(&f, -3);
    show("force", &f);
    /* Python-built CTRL bytes for steer -1200, throttle 100, brake 0, buttons 0x21. */
    struct can_frame ctrl = {.id = ID_CTRL, .dlc = 8, .data = {0x10, 0x50, 0xfb, 100, 0, 0x21, 0}};
    struct lab3_ctrl c;
    printf("ctrl_ok %d", lab3_ctrl_decode(&ctrl, &c));
    printf(" %d %u %u %u\n", c.steer, c.throttle, c.brake, c.buttons);
    ctrl.data[4] = 101;
    printf("ctrl_bad_brake %d\n", lab3_ctrl_decode(&ctrl, &c));
    ctrl.data[4] = 0; ctrl.data[0] = 0x00;
    printf("ctrl_bad_flags %d\n", lab3_ctrl_decode(&ctrl, &c));
    ctrl.flags = CAN_FRAME_RTR; ctrl.data[0] = 0x10; lab3_seal(&ctrl);
    printf("rtr_valid %d\n", lab3_frame_valid(&ctrl));
    printf("origin fault=%u blink=%u hb3=%u\n", lab3_frame_origin(&(struct can_frame){.id = ID_FAULT,
           .data = {0, 1, 4, 3}}), lab3_frame_origin(&(struct can_frame){.id = ID_BLINK}),
           lab3_frame_origin(&(struct can_frame){.id = ID_HB_N3}));
    return 0;
}
