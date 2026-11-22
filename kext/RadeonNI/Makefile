# Builds RadeonNI.kext inside the Tiger guest with Apple's gcc 4.0.1.
# Run through scripts/kext.sh from the host; not meant for the host itself.
#
# The hardware library in ../../hw is compiled into the kext unchanged.

KEXT     = RadeonNI
CC       = gcc
CXX      = g++
NM       = nm
ARCHFLAGS ?= -arch ppc
SDKFLAGS ?=
LONG_BRANCH_FLAG ?= -mlong-branch
KERNEL_CFLAGS_EXTRA ?=
KERNEL_CXXFLAGS_EXTRA ?=
KEXT_LIBS ?= -lkmodc++ -lkmod -lcc_kext
KROOT    = /System/Library/Frameworks/Kernel.framework
HW       = ../../hw
# make LEOPARD=1: the same sources, plus leopard.s, for Mac OS X 10.5
# (see scripts/leopard.sh). Built apart, so that the Tiger kext is not touched.
CAYMAN_SMC ?= 0
NATIVE_KMOD_RUNTIME ?= 0
TIGER_COMPAT ?= 0
SLEEP_LINK_EXPERIMENT ?= 0
SLEEP_INDEX_PROBE ?= 0
CPPFLAGS_EXTRA = -DRDN_CAYMAN_SMC=$(CAYMAN_SMC) -DRDN_NATIVE_KMOD_RUNTIME=$(NATIVE_KMOD_RUNTIME)
ifeq ($(SLEEP_INDEX_PROBE),1)
CPPFLAGS_EXTRA += -DRDN_SLEEP_INDEX_PROBE=1
ifeq ($(SLEEP_LINK_EXPERIMENT),1)
$(error SLEEP_INDEX_PROBE and SLEEP_LINK_EXPERIMENT cannot be combined)
endif
HW_SRCS_EXTRA += rdn_snapshot_plan.c rdn_live_plan.c rdn_live_image.c
endif
LEOPARD  = 0
ifeq ($(LEOPARD),1)
BUILD    = build-leopard
else
BUILD    = build
endif
BUNDLE   = $(BUILD)/$(KEXT).kext

CPPFLAGS = $(SDKFLAGS) $(CPPFLAGS_EXTRA) -DKERNEL -DKERNEL_PRIVATE -DDRIVER_PRIVATE -DAPPLE -DNeXT \
	-nostdinc -Icompat -I$(KROOT)/PrivateHeaders -I$(KROOT)/Headers -I$(HW)
CFLAGS   = $(ARCHFLAGS) -Os -Wall -fno-builtin -fno-common -static \
	$(LONG_BRANCH_FLAG) -force_cpusubtype_ALL $(KERNEL_CFLAGS_EXTRA)
CXXFLAGS = $(CFLAGS) -fno-exceptions -fno-rtti -fapple-kext -fcheck-new $(KERNEL_CXXFLAGS_EXTRA)
# Files taken from Linux do not pass -Wall cleanly with this compiler.
HWCFLAGS = $(CFLAGS) -std=gnu99 -Wno-unused -Wno-sign-compare

HW_SRCS  = rdn_quiesce.c rdn_snapshot.c rdn_fan.c rdn_cayman_gating.c rdn_cayman_memory.c rdn_dma.c rdn_uvd.c rdn_gart.c rdn_mc.c rdn_watermark.c rdn_cayman_dpm.c rdn_smc.c rdn_pm.c rdn_cursor.c rdn_mem.c rdn_gpu.c rdn_cp.c rdn_blit.c rdn_selftest.c rdn_post.c rdn_atom.c rdn_i2c.c rdn_mode.c rdn_dmt.c rdn_modeset.c rdn_dp.c \
	rdn_pattern.c atom/atom.c
HW_SRCS += $(HW_SRCS_EXTRA)
HW_OBJS  = $(addprefix $(BUILD)/hw/,$(HW_SRCS:.c=.o))
HW_OBJS += $(BUILD)/hw/rdn_cayman.o $(BUILD)/hw/rdn_mc_layout.o $(BUILD)/hw/rdn_uvd_h264.o $(BUILD)/hw/rdn_cp_dma_readback.o
OBJS     = $(BUILD)/RadeonNI.o $(BUILD)/RadeonNIAccel.o $(BUILD)/RadeonNISurface.o $(BUILD)/kmod_info.o $(HW_OBJS)
OBJS    += $(BUILD)/RadeonNIFence.o $(BUILD)/RadeonNITelemetry.o $(BUILD)/RadeonNIManaged.o
OBJS    += $(BUILD)/RadeonNIVideo.o $(BUILD)/RadeonNIVideoMemory.o $(BUILD)/RadeonNIUvdSession.o
OBJS    += $(BUILD)/RadeonNIUvdFixture.o $(BUILD)/uvd_decode_fixture.o
ifeq ($(SLEEP_INDEX_PROBE),1)
OBJS += $(BUILD)/RadeonNITigerPhysicalProbe.o
endif
ifeq ($(SLEEP_LINK_EXPERIMENT),1)
ifeq ($(LEOPARD),1)
$(error SLEEP_LINK_EXPERIMENT is Tiger link-only)
endif
ifneq ($(TIGER_COMPAT),1)
$(error SLEEP_LINK_EXPERIMENT requires TIGER_COMPAT=1)
endif
CPPFLAGS_EXTRA += -DRDN_SLEEP_INTERNAL_EXPERIMENT=1
HW_SRCS += rdn_snapshot_plan.c rdn_snapshot_transfer.c rdn_sleep_staging.c rdn_sleep_copy.c \
           rdn_sleep_dma.c rdn_sleep_private.c rdn_sleep_guarded.c rdn_sleep_sequence.c \
           rdn_sleep_sequence_bridge.c rdn_sleep_runtime.c rdn_sleep_transaction.c rdn_sleep_owner.c
OBJS += $(BUILD)/RadeonNITigerSleepStage.o $(BUILD)/RadeonNITigerSleepBuffer.o $(BUILD)/RadeonNITigerSleepOwner.o
endif
ifeq ($(TIGER_COMPAT),1)
ifeq ($(LEOPARD),1)
$(error TIGER_COMPAT cannot be combined with LEOPARD)
endif
OBJS    += $(BUILD)/tiger-compat.o
endif
ifeq ($(LEOPARD),1)
OBJS    += $(BUILD)/leopard.o
CPPFLAGS += -DRDN_LEOPARD
endif

all: $(BUNDLE)/Contents/MacOS/$(KEXT)

$(BUILD)/tiger-compat.o: tiger-compat.s
	@mkdir -p $(dir $@)
	$(CC) $(SDKFLAGS) -arch ppc -c -o $@ $<

$(BUILD)/leopard.o: leopard.s
	@mkdir -p $(dir $@)
	$(CC) $(SDKFLAGS) -arch ppc -c -o $@ $<

$(BUILD)/%.o: %.cpp RadeonNI.h RadeonNIAccel.h RadeonNISurface.h RadeonNIVideo.h RadeonNIVideoMemory.h $(wildcard $(HW)/*.h $(HW)/atom/*.h)
	@mkdir -p $(dir $@)
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -c -o $@ $<

$(BUILD)/%.o: %.c
	@mkdir -p $(dir $@)
	$(CC) $(CPPFLAGS) $(CFLAGS) -c -o $@ $<

$(BUILD)/hw/%.o: $(HW)/%.c $(wildcard $(HW)/*.h $(HW)/atom/*.h)
	@mkdir -p $(dir $@)
	$(CC) $(CPPFLAGS) $(HWCFLAGS) -c -o $@ $<

$(BUILD)/uvd_decode_fixture.o: ../../tests/uvd_decode_fixture.c ../../tests/uvd_decode_fixture.h
	@mkdir -p $(dir $@)
	$(CC) $(CPPFLAGS) $(HWCFLAGS) -c -o $@ $<

$(BUILD)/RadeonNIUvdFixture.o: ../../tests/uvd_decode_fixture.h

# Objects first: kld needs the symbols libkmodc++ defines for them.
$(BUNDLE)/Contents/MacOS/$(KEXT): $(OBJS) Info.plist
	@mkdir -p $(BUNDLE)/Contents/MacOS
	$(CXX) $(SDKFLAGS) -arch ppc -static -nostdlib -r $(OBJS) $(KEXT_LIBS) \
		-o $(BUNDLE)/Contents/MacOS/$(KEXT).new
	$(NM) -u $(BUNDLE)/Contents/MacOS/$(KEXT).new > /dev/null
	mv $(BUNDLE)/Contents/MacOS/$(KEXT).new $(BUNDLE)/Contents/MacOS/$(KEXT)
	cp Info.plist $(BUNDLE)/Contents/Info.plist
ifeq ($(LEOPARD),1)
	perl -0777 -pi -e 's/com\.apple\.kernel\.(iokit|libkern|mach)/com.apple.kpi.$$1/g; s/<string>6\.0<\/string>/<string>9.0.0<\/string>/g; s{(<key>OSBundleLibraries</key>\s*<dict>)}{$$1\n\t\t<key>com.apple.kpi.bsd</key>\n\t\t<string>9.0.0</string>\n\t\t<key>com.apple.kpi.unsupported</key>\n\t\t<string>9.0.0</string>}' $(BUNDLE)/Contents/Info.plist
endif

clean:
	rm -rf $(BUILD)

.PHONY: all clean
