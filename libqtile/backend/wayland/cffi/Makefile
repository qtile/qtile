.POSIX:

include libconfig.mk

BUILD_DIR := .build
SRC := $(wildcard $(QW_PATH)/*.c)
OBJS := $(patsubst $(QW_PATH)/%.c,$(BUILD_DIR)/%.o,$(SRC))

.PHONY: all
all: $(TARGET)

$(BUILD_DIR)/%.o: $(QW_PATH)/%.c
	@mkdir -p $(dir $@)
	$(CC) -O2 -fPIC -DWLR_USE_UNSTABLE -Wall -Wextra $(CFLAGS) $(INCLUDES) -c $< -o $@

$(TARGET): $(OBJS)
	$(LINK.c) -shared $(LDFLAGS) -shared -o $@ $^ $(LDLIBS)

.PHONY: clean
clean:
	$(RM) $(OBJS) $(TARGET)

