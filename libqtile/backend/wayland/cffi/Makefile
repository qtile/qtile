# Paths
QW_PATH      := ../qw
QW_PROTO_OUT := ../qw/proto

# Compiler/linker
CC := gcc
CFLAGS := -O2 -fPIC \
          -DWLR_USE_UNSTABLE \
          -I$(QW_PATH) \
          -I$(QW_PROTO_OUT) \
          $(shell pkg-config --cflags wlroots-0.19 wayland-server cairo pixman-1 libdrm)

LDFLAGS := -shared $(shell pkg-config --libs wlroots-0.19 wayland-server cairo pixman-1 libdrm)

TARGET := ../libwayc.so

.PHONY: all
all: $(TARGET)

$(TARGET): $(wildcard $(QW_PATH)/*.c)
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)

.PHONY: clean
clean:
	rm -f $(OBJECTS) $(TARGET)

.PHONY: rebuild
rebuild: clean all

