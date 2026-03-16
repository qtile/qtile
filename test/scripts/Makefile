CC = clang
SDK = $(shell xcrun --sdk macosx --show-sdk-path)
FRAMEWORKS = -framework Cocoa

all: macos_window

macos_window: macos_window.m
	$(CC) -isysroot $(SDK) $(FRAMEWORKS) -o $@ $<

clean:
	rm -f macos_window
