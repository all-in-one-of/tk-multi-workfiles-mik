# Copyright (c) 2013 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import os
import nuke
import datetime
import getpass

import tank
from tank import Hook
from tank import TankError
from tank.platform.qt import QtGui

import sys

LINUX_PATH = "/s/apps/common/python/luigi/infonodelib"
WINDOWS_PATH = "V:\\apps\\common\\python\\luigi\\infonodelib"
info_lib_path = {"linux2": LINUX_PATH,
              "win32":  WINDOWS_PATH,
              "darwin": "" }

sys.path.append(info_lib_path[sys.platform])

from infonodelib import InfoNodeLib

class SceneOperation(Hook):
    """
    Hook called to perform an operation with the
    current scene
    """

    def execute(self, operation, file_path, context, parent_action, file_version, read_only, **kwargs):
        '''
        @summary:
        @param operation:
        @param file_path:
        @param context:
        @param parent_action:
        @param file_version:
        @param read_only:
        @param **kwargs:
        @result:
        '''
        """
        Main hook entry point

        :param operation:       String
                                Scene operation to perform

        :param file_path:       String
                                File path to use if the operation
                                requires it (e.g. open)

        :param context:         Context
                                The context the file operation is being
                                performed in.

        :param parent_action:   This is the action that this scene operation is
                                being executed for.  This can be one of:
                                - open_file
                                - new_file
                                - save_file_as
                                - version_up

        :param file_version:    The version/revision of the file to be opened.  If this is 'None'
                                then the latest version should be opened.

        :param read_only:       Specifies if the file should be opened read-only or not

        :returns:               Depends on operation:
                                'current_path' - Return the current scene
                                                 file path as a String
                                'reset'        - True if scene was reset to an empty
                                                 state, otherwise False
                                all others     - None
        """
        self.infoNodeLib = InfoNodeLib(self.parent)
        self.parent.log_debug("Operation: %s"%operation)

        if file_path:
            file_path = file_path.replace("/", os.path.sep)

        if operation == "current_path":
            # return the current script path
            return nuke.root().name().replace("/", os.path.sep)

        elif operation == "open":
            # open the specified script
            nuke.scriptOpen(file_path)
            self.infoNodeLib.nuke_check_mikinfo_node(context,"",file_path)
            self.infoNodeLib.nuke_check_write_nodes()

            # reset any write node render paths:
            if self._reset_write_node_render_paths():
                # something changed so make sure to save the script again:
                nuke.scriptSave()

        elif operation == "save":
            # save the current script:

            nuke.scriptSave()

        elif operation == "save_as":
            old_path = nuke.root()["name"].value()
            try:
                # rename script:
                nuke.root()["name"].setValue(file_path)

                # reset all write nodes:
                self._reset_write_node_render_paths()

                self.infoNodeLib.nuke_check_mikinfo_node(context,old_path,file_path)
                self.infoNodeLib.nuke_check_write_nodes()

                
                # save script:
                nuke.scriptSaveAs(file_path, -1)

            except Exception, e:
                # something went wrong so reset to old path:
                nuke.root()["name"].setValue(old_path)
                raise TankError("Failed to save scene %s", e)

        elif operation == "reset":
            """
            Reset the scene to an empty state
            """
            while nuke.root().modified():
                # changes have been made to the scene
                res = QtGui.QMessageBox.question(None,
                                                 "Save your script?",
                                                 "Your script has unsaved changes. Save before proceeding?",
                                                 QtGui.QMessageBox.Yes|QtGui.QMessageBox.No|QtGui.QMessageBox.Cancel)

                if res == QtGui.QMessageBox.Cancel:
                    return False
                elif res == QtGui.QMessageBox.No:
                    break
                else:
                    nuke.scriptSave()

            # now clear the script:
            nuke.scriptClear()

            return True

        elif operation == "prepare_new":
            """
            Create proper mikinfo node and write nodes
            """
            self.infoNodeLib.nuke_check_mikinfo_node(context,"",file_path, create_only=True)
            self.infoNodeLib.nuke_check_write_nodes()

        if file_path:
            self.set_pf_settings(file_path)

    def _reset_write_node_render_paths(self):
        """
        Use the tk-nuke-writenode app interface to find and reset
        the render path of any Tank write nodes in the current script
        """
        write_node_app = self.parent.engine.apps.get("tk-nuke-writenode")
        if not write_node_app:
            return False

        # only need to forceably reset the write node render paths if the app version
        # is less than or equal to v0.1.11
        from distutils.version import LooseVersion
        if (write_node_app.version == "Undefined"
            or LooseVersion(write_node_app.version) > LooseVersion("v0.1.11")):
            return False

        write_nodes = write_node_app.get_write_nodes()
        for write_node in write_nodes:
            write_node_app.reset_node_render_path(write_node)

        return len(write_nodes) > 0

    def set_pf_settings(self,file_path):
        self.parent.log_debug("Settings pj settings")
        sg = self.parent.shotgun
        self.parent.log_debug(sg)
        tk = self.parent.sgtk
        self.parent.log_debug(tk)
        ctx = tk.context_from_path(file_path)
        self.parent.log_debug(ctx)
        if ctx.project:
            pj_id = ctx.project.get("id")
            fields = ["sg_frame_rate","sg_color_space"]
            filters = [['id','is',pj_id]]
            result = sg.find_one("Project", filters, fields)
            self.set_frame_rate(result)
            self.set_writes_colorspace(result)

    def _update_frame_range_form_shotgun(self):
        """
        Use the tk-nuke-writenode app interface to find and reset
        the render path of any Tank write nodes in the current script
        """
        write_node_app = self.parent.engine.apps.get("tk-nuke-writenode")
        if not write_node_app:
            return False

        # only need to forceably reset the write node render paths if the app version
        # is less than or equal to v0.1.11
        from distutils.version import LooseVersion
        if (write_node_app.version == "Undefined"
            or LooseVersion(write_node_app.version) > LooseVersion("v0.1.11")):
            return False

        write_nodes = write_node_app.get_write_nodes()
        for write_node in write_nodes:
            write_node_app.reset_node_render_path(write_node)

        return len(write_nodes) > 0

    def set_frame_rate(self,result):
        if "sg_frame_rate" in result:
            self.parent.log_debug("Settings frame rate")
            new_rate =float( result.get("sg_frame_rate"))
            nuke.root().knobs()['fps'].setValue(new_rate)

    def set_writes_colorspace(self,result):
        if "sg_color_space" in result:
            colorspace = result.get("sg_color_space")
            for node in nuke.allNodes('WriteTank'):
                if  "DEF" in node.name():
                    print "switching", node.name(), "to %s"%colorspace
                    node.knobs()['tk_profile_list'].setValue('Write WIP')
                    node.knobs()['tk_profile_list'].setValue('Write DEF')
                if  "WIP" in node.name():
                    print "switching", node.name(), "to %s"%colorspace
                    node.knobs()['tk_profile_list'].setValue('Write DEF')
                    node.knobs()['tk_profile_list'].setValue('Write WIP')