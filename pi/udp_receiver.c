#include "udp_receiver.h"

#include <arpa/inet.h>
#include <errno.h>
#include <stdio.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

/*
 * The handout says the UDP packet is:
 *   4-byte little-endian counter + 272-byte DIJOYSTATE2.
 *
 * IMPORTANT:
 * These offsets should be checked against the state.h supplied with the
 * course's wheel proxy. Do not assume a different struct layout.
 *
 * DIJOYSTATE2 fields used by the lab:
 *   lX       -> steering
 *   lY       -> throttle
 *   lRz      -> brake
 *   rgbButtons[128]
 *
 * The offsets below are the standard DirectInput layout. If your supplied
 * state.h/proxy uses different offsets, EDIT THESE CONSTANTS.
 */
#define OFFSET_COUNTER       0
#define OFFSET_STATE         4
#define OFFSET_LX            (OFFSET_STATE + 0)
#define OFFSET_LY            (OFFSET_STATE + 4)
#define OFFSET_LRZ           (OFFSET_STATE + 20)
#define OFFSET_BUTTONS       (OFFSET_STATE + 48)

static int sockfd = -1;

static int32_t read_i32_le(const uint8_t *p)
{
    uint32_t u = ((uint32_t)p[0]) |
                 ((uint32_t)p[1] << 8) |
                 ((uint32_t)p[2] << 16) |
                 ((uint32_t)p[3] << 24);
    return (int32_t)u;
}

static uint32_t read_u32_le(const uint8_t *p)
{
    return ((uint32_t)p[0]) |
           ((uint32_t)p[1] << 8) |
           ((uint32_t)p[2] << 16) |
           ((uint32_t)p[3] << 24);
}

int udp_receiver_open(void)
{
    struct sockaddr_in addr;

    sockfd = socket(AF_INET, SOCK_DGRAM, 0);
    if (sockfd < 0) {
        perror("socket");
        return -1;
    }

    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_port = htons(UDP_PORT);
    addr.sin_addr.s_addr = htonl(INADDR_ANY);

    if (bind(sockfd, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        perror("bind");
        close(sockfd);
        sockfd = -1;
        return -1;
    }

    printf("UDP receiver listening on port %d\n", UDP_PORT);
    return 0;
}

int udp_receiver_receive(wheel_state_t *state)
{
    uint8_t packet[WHEEL_PACKET_LEN];
    ssize_t n;

    if (sockfd < 0 || state == NULL) {
        return -1;
    }

    n = recvfrom(sockfd, packet, sizeof(packet), 0, NULL, NULL);

    if (n < 0) {
        if (errno == EINTR) {
            return 0;
        }
        perror("recvfrom");
        return -1;
    }

    if (n != WHEEL_PACKET_LEN) {
        fprintf(stderr, "Ignoring UDP packet of %zd bytes; expected %d\n",
                n, WHEEL_PACKET_LEN);
        return 0;
    }

    state->counter = read_u32_le(packet + OFFSET_COUNTER);
    state->steering_raw = read_i32_le(packet + OFFSET_LX);
    state->throttle_raw = read_i32_le(packet + OFFSET_LY);
    state->brake_raw = read_i32_le(packet + OFFSET_LRZ);

    /*
     * Convert the 128-byte DirectInput button array into a 32-bit mask.
     *
     * Only button indices 0..31 fit in this command protocol.
     * If your chosen wheel buttons have larger raw indices, change the
     * protocol to carry a larger button field.
     */
    state->buttons = 0;
    for (int i = 0; i < 32; ++i) {
        if (packet[OFFSET_BUTTONS + i] != 0) {
            state->buttons |= (1u << i);
        }
    }

    return 1;
}

void udp_receiver_close(void)
{
    if (sockfd >= 0) {
        close(sockfd);
        sockfd = -1;
    }
}
