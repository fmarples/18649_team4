CC = gcc
CFLAGS = -O2 -Wall -Wextra -std=c11

TARGET = pi_uart_bridge
SOURCES = main.c udp_receiver.c uart.c

all:
	$(CC) $(CFLAGS) -o $(TARGET) $(SOURCES)

clean:
	rm -f $(TARGET)
