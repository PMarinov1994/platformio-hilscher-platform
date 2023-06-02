# Copyright 2014-present PlatformIO <contact@platformio.org>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

#
# Default flags for bare-metal programming (without any framework layers)
#

from SCons.Script import DefaultEnvironment

env = DefaultEnvironment()

cpu = env.BoardConfig().get("build.cpu").lower()
warninglevel1_Enabled = env.BoardConfig().get("build.warninglevel1").lower() == "true"
# buildMode = env. BoardConfig().get("build.buildMode").lower()

common_flags = [
    # NETX Platform
    "-D_NETX_",
    # "-march=armv5te",
    # "-msoft-float",
    # "-mfpu=vfp",
    "-mfloat-abi=soft",
    # "-mthumb-interwork",
    # "-fshort-enums",
    
    # ???
    "-ffunction-sections",
    "-fdata-sections",
    "-fno-common",
]

commonASM_flags = [
    "-Wall",
    "-Wredundant-decls",
    "-Wno-inline"
]

commonC_flags = [item for item in common_flags]
commonC_flags += [
    "-Wall",
    "-Wredundant-decls",
    "-Wno-inline",
    "-Winit-self",
    "-std=gnu99"
]

commonLinker_flags = [item for item in common_flags]
commonLinker_flags += [
    # "-mthumb-interwork",
    "-Wl,-gc-sections",
    "-nostdlib",
    "-mthumb",
    "-march=armv7e-m",
    "-mfloat-abi=soft",
]

commonDefines = []
cpu_extra_flags = []
if cpu == "netx90":
    cpu_extra_flags = [
        "-D_NETX_",
        "-D__NETX90",
        "-march=armv7e-m",
        "-mfloat-abi=soft",
        "-mthumb"
    ]

commonC_flags += cpu_extra_flags
# commonLinker_flags += cpu_extra_flags

# if buildMode == "debug":
#     commonASM_flags += [ "-Wa,-gdwarf2" ]
#     commonC_flags += [
#         "-O0",
#         "-g",
#         "-gdwarf-2"
#     ]
    
# elif buildMode == "debugrel":
#     commonASM_flags += [ "-Wa,-gdwarf2" ]
#     commonC_flags += [
#         "-Os",
#         "-g",
#         "-gdwarf-2"
#     ]

# elif buildMode == "release":
#     commonC_flags += [
#         "-Os"
#     ]

# else:
#     assert False, "Invalid 'buildMode' configuration value. Supported values are 'debug', 'debugrel' and 'release'"

commonCPP_flags = [item for item in commonC_flags]


commonDefines = [
        ("__STACK_SIZE", env.BoardConfig().get("build.__STACK_SIZE")),
        ("__HEAP_SIZE", env.BoardConfig().get("build.__HEAP_SIZE")),
        "__STARTUP_CLEAR_BSS",
        ("__START", env.BoardConfig().get("build.__START")),
    ]
print(commonDefines)

if warninglevel1_Enabled:
    compiler_extra_warnings = [
        "-Wsystem-headers",
        "-Wsign-compare",
        "-Wswitch-default",
        "-Wpointer-arith"
    ]
    
    commonC_flags += compiler_extra_warnings + ["-Wbad-function-cast", "-Wstrict-prototypes",]
    commonCPP_flags += compiler_extra_warnings


print("Adding gcc flags from _bare.py")
env.Append(
    ASFLAGS=commonASM_flags,
    ASPPFLAGS=commonASM_flags,
    CCFLAGS=commonC_flags,
    CXXFLAGS=commonCPP_flags,
    LINKFLAGS=commonLinker_flags,
    CPPDEFINES=commonDefines
)