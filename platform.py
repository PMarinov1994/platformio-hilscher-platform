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

import json
import os
import sys
import re

from pprint import pprint
from platformio.managers.platform import PlatformBase


IS_WINDOWS = sys.platform.startswith("win")

class HilscherPlatform(PlatformBase):

    def configure_default_packages(self, variables, targets):
        board = variables.get("board")
        board_config = self.board_config(board)
        frameworks = variables.get("pioframework", [])

        if "cmsis" in frameworks:
            device_package = "framework-cmsis-netx"
            if device_package in self.packages:
                self.packages[device_package]["optional"] = False

        # configure J-LINK tool
        jlink_conds = [
            "jlink" in variables.get(option, "")
            for option in ("upload_protocol", "debug_tool")
        ]
        if board:
            jlink_conds.extend([
                "jlink" in board_config.get(key, "")
                for key in ("debug.default_tools", "upload.protocol")
            ])
        jlink_pkgname = "tool-jlink"
        if not any(jlink_conds) and jlink_pkgname in self.packages:
            del self.packages[jlink_pkgname]

        return PlatformBase.configure_default_packages(self, variables,
                                                       targets)


    def get_boards(self, id_=None):
        result = PlatformBase.get_boards(self, id_)
        if not result:
            return result
        if id_:
            return self._add_default_debug_tools(result)
        else:
            for key, value in result.items():
                result[key] = self._add_default_debug_tools(result[key])
        return result


    def _add_default_debug_tools(self, board):        
        debug = board.manifest.get("debug", {})        
        upload_protocols = board.manifest.get("upload", {}).get(
            "protocols", [])
        if "tools" not in debug:
            debug["tools"] = {}
        
        # J-Link, hilscher
        for link in ("jlink", "hilscher"):
            if link not in upload_protocols or link in debug["tools"]:
                continue
            if link == "jlink":
                assert debug.get("jlink_device"), (
                    "Missed J-Link Device ID for %s" % board.id)
                debug["tools"][link] = {
                    "server": {
                        "package": "tool-jlink",
                        "arguments": [
                            "-singlerun",
                            "-if", "SWD",
                            "-select", "USB",
                            "-device", debug.get("jlink_device"),
                            "-port", "2331"
                        ],
                        "executable": ("JLinkGDBServerCL.exe"
                                       if IS_WINDOWS else
                                       "JLinkGDBServer")
                    }
                }
            if link == "hilscher":
                server_args = ["-s", "$PACKAGE_DIR/scripts"]
                server_args.extend([
                    # "-c", "debug_level 3",
                    "-c", "set MODE RUN",
                    "-c", "set JTAG_SPEED 1000",
                    "-f", "interface/%s.cfg" % debug["openocd_interface"],
                    "-f", "board/%s.cfg" % debug["openocd_board"],
                    "-c", "gdb_breakpoint_override hard",
                    "-c", "puts gdb-server-ready"
                ])

                debug["tools"][link] = {
                    "server": {
                        "package": "tool-openocd",
                        "executable": "bin/openocd",
                        "arguments": server_args
                    },
                    "init_cmds": [
                        # "set debug remote 1",
                        # "set remotetimeout 20",
                        "target extended-remote $DEBUG_PORT",
                        "set remote hardware-breakpoint-limit 6",
                        "set $sp = *(int*)&__Vectors",
                        "set $pc = *((int*)&__Vectors+1)",
                        "set {int}0xE000ED08 = &__Vectors"
                    ],
                    "extra_cmds": [
                    ],
                    "init_break": "",
                    # "load_cmd": "preload", # Will invoke the donwload command
                    "load_mode": "manual",
                    "server_ready_pattern": "gdb-server-ready",
                    "onboard": link in debug.get("onboard_tools", []),
                    "default": link == debug.get("default_tool"),
                }                

        board.manifest["debug"] = debug
        return board
    
    
    def configure_debug_session(self, debug_config):
        board = PlatformBase.get_boards(self, debug_config.env_options["board"])

        if "debug_svd_path"not in debug_config.env_options:        
            debug_config.env_options["debug_svd_path"] = os.path.join(PlatformBase.get_dir(self), "misc", board.manifest["debug"]["svd"])
        
        if debug_config.env_options["debug_tool"] == "hilscher":        
            port = ":3333"
            if 'debug_port' not in debug_config.env_options:
                debug_config.env_options["debug_port"] = port
            else:
                port = debug_config.env_options["debug_port"]
            
            match = re.match(r'.*:(\d+)', port)
            port_number = match.group(1)
            
            debug_config.server["arguments"].insert(0, "-c")
            debug_config.server["arguments"].insert(1, "gdb_port %s" % port_number)

        from pprint import pprint
        print("====================")
        pprint(vars(debug_config))
        print("====================")