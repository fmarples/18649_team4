#include "uart.h"

#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <termios.h>
#include <unistd.h>

static int uart_fd = -1;

static void put_u16_le(uint8_t *p, uint16_t value)
{
    p[0] = (uint8_t)(value & 0xFFu);
    p[1] = (uint8_t)((value >> 8) & 0xFFu);
}

static void put_i16_le(uint8_t *p, int32_t value)
{
    /*
     * The Pi->STM32 protocol uses int16 values.
     * The STM32 will reject values outside its agreed range.
     *
     * IMPORTANT: Replace this with scaling/clamping logic once the team
     * has decided whether to transmit raw wheel values or normalized values.
     */
    int16_t v = (int16_t)value;
    put_u16_le(p, (uint16_t)v);
}

int uart_open(const char *device)
{
    struct termios tty;

    uart_fd = open(device, O_RDWR | O_NOCTTY | O_SYNC);
    if (uart_fd < 0) {
        perror("open UART");
        return -1;
    }

    if (tcgetattr(uart_fd, &tty) != 0) {
        perror("tcgetattr");
        close(uart_fd);
        uart_fd = -1;
        return -1;
    }

    cfsetospeed(&tty, B115200);
    cfsetispeed(&tty, B115200);

    tty.c_cflag = (tty.c_cflag & ~CSIZE) | CS8;
    tty.c_cflag |= CLOCAL | CREAD;
    tty.c_cflag &= ~(PARENB | PARODD);
    tty.c_cflag &= ~CSTOPB;
    tty.c_cflag &= ~CRTSCTS;

    tty.c_iflag &= ~(IXON | IXOFF | IXANY);
    tty.c_lflag = 0;
    tty.c_oflag = 0;

    tty.c_cc[VMIN] = 0;
    tty.c_cc[VTIME] = 1; /* 100 ms */

    if (tcsetattr(uart_fd, TCSANOW, &tty) != 0) {
        perror("tcsetattr");
        close(uart_fd);
        uart_fd = -1;
        return -1;
    }

    printf("UART opened on %s at 115200 8N1\n", device);
    return 0;
}

int uart_send_command(const wheel_state_t *state, uint16_t sequence)
{
    uint8_t frame[UART_COMMAND_LEN];
    ssize_t written;

    if (uart_fd < 0 || state == NULL) {
        return -1;
    }

    frame[0] = UART_SYNC;
    frame[1] = UART_FRAME_COMMAND;
    put_u16_le(&frame[2], sequence);
    put_i16_le(&frame[4], state->steering_raw);
    put_i16_le(&frame[6], state->throttle_raw);
    put_i16_le(&frame[8], state->brake_raw);

    frame[10] = (uint8_t)(state->buttons & 0xFFu);
    frame[11] = (uint8_t)((state->buttons >> 8) & 0xFFu);
    frame[12] = (uint8_t)((state->buttons >> 16) & 0xFFu);
    frame[13] = (uint8_t)((state->buttons >> 24) & 0xFFu);

    frame[14] = protocol_checksum(frame, UART_COMMAND_LEN - 1);

    written = write(uart_fd, frame, sizeof(frame));
    if (written != (ssize_t)sizeof(frame)) {
        perror("UART command write");
        return -1;
    }

    return 0;
}

int uart_receive_status(uint8_t *frame, uint8_t max_len)
{
    if (uart_fd < 0 || frame == NULL || max_len == 0) {
        return -1;
    }

    /*
     * This function is intentionally simple for the starter project.
     * For the final design, add a byte-by-byte status parser with:
     *   - sync recovery
     *   - frame type checking
     *   - checksum validation
     *   - truncated-frame handling
     */
    return (int)read(uart_fd, frame, max_len);
}

void uart_close(void)
{
    if (uart_fd >= 0) {
        close(uart_fd);
        uart_fd = -1;
    }
}
