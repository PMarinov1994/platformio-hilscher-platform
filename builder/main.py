"""
    Build script for test.py
    test-builder.py
"""

import sys
from platform import system
from os import makedirs
from os.path import basename, isdir, join

from SCons.Script import (ARGUMENTS, COMMAND_LINE_TARGETS, AlwaysBuild,
                          Builder, Default, DefaultEnvironment)

from platformio.public import list_serial_ports

env = DefaultEnvironment()
platform = env.PioPlatform()
board = env.BoardConfig()

# A full list with the available variables
# http://www.scons.org/doc/production/HTML/scons-user.html#app-variables
env.Replace(
    AR="arm-none-eabi-gcc-ar",
    AS="arm-none-eabi-as",
    CC="arm-none-eabi-gcc",
    CXX="arm-none-eabi-g++",
    GDB="arm-none-eabi-gdb",
    OBJCOPY="arm-none-eabi-objcopy",
    RANLIB="arm-none-eabi-gcc-ranlib",
    SIZETOOL="arm-none-eabi-size",

    ARFLAGS=["rc"],

    SIZEPROGREGEXP=r"^(?:\.text|\.data|\.rodata|\.text.align|\.ARM.exidx)\s+(\d+).*",
    SIZEDATAREGEXP=r"^(?:\.data|\.bss|\.noinit)\s+(\d+).*",
    SIZECHECKCMD="$SIZETOOL -A -d $SOURCES",
    SIZEPRINTCMD='$SIZETOOL -B -d $SOURCES',

    PROGSUFFIX=".elf"
)

# Allow user to override via pre:script
if env.get("PROGNAME", "program") == "program":
    env.Replace(PROGNAME="firmware")

cpu = env.BoardConfig().get("build.cpu").lower()

fmw_extension = ".bin"
if cpu == "netx90":
    fmw_extension = ".nai"

hboot_image_compiler = platform.get_package_dir("tool-hil_nxt_hboot_image_compiler")

env.Append(
    BUILDERS=dict(
        ElfToBin=Builder(
            action=env.VerboseAction(" ".join([
                "$OBJCOPY",
                "-O",
                "binary",
                "--only-section=.text.nai_header",
                "--only-section=.text.pagereader",
                "--only-section=.text.pageflasher",
                "--only-section=.text",
                "--only-section=.data",
                "$SOURCES",
                "$TARGET"
            ]), "Building $TARGET"),
            suffix=fmw_extension
        ),
        ElfToNai=Builder(
            action=env.VerboseAction(" ".join([
                join(hboot_image_compiler, "hboot_image_compiler_app", "hboot_image_compiler_app"),
                "-t", "nai",
                "-A", "tElf=$SOURCES",
                "-A", 'segments_intflash=""',
                "-nt", cpu,
                "$TARGET"
            ]), "Building $TARGET")
        )
    )
)
    
    
if not env.get("PIOFRAMEWORK"):
    env.SConscript("frameworks/_bare.py")


#
# Target: Build executable and linkable firmware
#

target_elf = None
if "nobuild" in COMMAND_LINE_TARGETS:
    target_elf = join("$BUILD_DIR", "${PROGNAME}.elf")
    target_firm = join("$BUILD_DIR", "${PROGNAME}.nai")
else:
    target_elf = env.BuildProgram()
    target_firm = env.ElfToNai(join("$BUILD_DIR", "${PROGNAME}.nai"), target_elf)
    env.Depends(target_firm, "checkprogsize")

AlwaysBuild(env.Alias("nobuild", target_elf))
target_buildprog = env.Alias("buildprog", target_firm, target_firm)

#
# Target: Print binary size
#

target_size = env.Alias(
    "size", target_elf,
    env.VerboseAction("$SIZEPRINTCMD", "Calculating size $SOURCE"))
AlwaysBuild(target_size)

#
# Target: Upload firmware
#

upload_protocol = env.subst("$UPLOAD_PROTOCOL")
debug_tools = board.get("debug.tools", {})
upload_source = target_elf
upload_actions = []

if upload_protocol.startswith("jlink"):

    def _jlink_cmd_script(env, source):
        build_dir = env.subst("$BUILD_DIR")
        if not isdir(build_dir):
            makedirs(build_dir)
        script_path = join(build_dir, "upload.jlink")
        commands = [
            "h",
            "loadbin %s, %s" % (source, board.get(
                "upload.offset_address", "0x00000000")),
            "r",
            "q"
        ]
        with open(script_path, "w") as fp:
            fp.write("\n".join(commands))
        return script_path

    env.Replace(
        __jlink_cmd_script=_jlink_cmd_script,
        UPLOADER="JLink.exe" if system() == "Windows" else "JLinkExe",
        UPLOADERFLAGS=[
            "-device", board.get("debug", {}).get("jlink_device"),
            "-speed", env.GetProjectOption("debug_speed", "4000"),
            "-if", ("jtag" if upload_protocol == "jlink-jtag" else "swd"),
            "-autoconnect", "1",
            "-NoGui", "1"
        ],
        UPLOADCMD='$UPLOADER $UPLOADERFLAGS -CommanderScript "${__jlink_cmd_script(__env__, SOURCE)}"'
    )
    upload_actions = [env.VerboseAction("$UPLOADCMD", "Uploading $SOURCE")]
elif upload_protocol == "hilscher":
    print("Uploading via Hilscher CLI Flasher...")
    cli_flasher_dir = platform.get_package_dir("tool-hilscher-cli-flasher")
    
    cli_flasher_args = [
        "cli_flash.lua",
        "flash",
        "-b", "2",
        "-u", "2",
        "-cs", "0",
        "-s", "0x0",
        join("$BUILD_DIR", "${PROGNAME}.nai"),
    ]
    
    print(cli_flasher_args)

    env.Replace(
        WORKING_DIR='"%s"' % join(cli_flasher_dir, "1.8.1"),
        UPLOADER="lua5.1.exe",
        UPLOADERFLAGS=cli_flasher_args,
        UPLOADCMD="$UPLOADER $UPLOADERFLAGS")

    upload_actions = [
        # env.VerboseAction('cd "%s"' % join(cli_flasher_dir, "1.8.1"), "Change directory to CLI Flasher tool..."),
        env.VerboseAction("cd $WORKING_DIR && $UPLOADCMD", "Uploading $SOURCE")
    ]

AlwaysBuild(env.Alias("upload", upload_source, upload_actions))

#
# Default targets
#

Default([target_buildprog, target_size])