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
import maya.cmds as cmds
import datetime

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
        if operation == "current_path":
            # return the current scene path
            return cmds.file(query=True, sceneName=True)
        elif operation == "open":
            # do new scene as Maya doesn't like opening
            # the scene it currently has open!
            cmds.file(new=True, force=True)
            cmds.file(file_path, open=True)
        elif operation == "save":
            self._check_mikinfo_node(context,"",file_path)
            # save the current scene:
            cmds.file(save=True)
        elif operation == "save_as":
            old_path = cmds.file(query=True, sceneName=True)
            # first rename the scene as file_path:
            cmds.file(rename=file_path)

            # Maya can choose the wrong file type so
            # we should set it here explicitely based
            # on the extension
            maya_file_type = None
            if file_path.lower().endswith(".ma"):
                maya_file_type = "mayaAscii"
            elif file_path.lower().endswith(".mb"):
                maya_file_type = "mayaBinary"

            self._check_mikinfo_node(context,old_path,file_path)

            # save the scene:
            if maya_file_type:
                cmds.file(save=True, force=True, type=maya_file_type)
            else:
                cmds.file(save=True, force=True)

        elif operation == "reset":
            """
            Reset the scene to an empty state
            """
            while cmds.file(query=True, modified=True):
                # changes have been made to the scene
                res = QtGui.QMessageBox.question(None,
                                                 "Save your scenfile_pathe?",
                                                 "Your scene has unsaved changes. Save before proceeding?",
                                                 QtGui.QMessageBox.Yes|QtGui.QMessageBox.No|QtGui.QMessageBox.Cancel)

                if res == QtGui.QMessageBox.Cancel:
                    return False
                elif res == QtGui.QMessageBox.No:
                    break
                else:
                    scene_name = cmds.file(query=True, sn=True)
                    if not scene_name:
                        cmds.SaveSceneAs()
                    else:
                        cmds.file(save=True)

            # do new file:
            cmds.file(newFile=True, force=True)
            return True


    def _check_mikinfo_node(self,context,old_path,file_path):
        '''
        @summary: check if info node exists, create it not and then update it
        @param context: current shotgun context
        '''
        mikinfo = None
        exists = []
        try:
            cmds.select("mikInfo")
            exists = cmds.ls(sl=True)
        except Exception, e:
            print "not Found"
        if len(exists)>0:
            self.parent.log_debug("Found mikinfo node .. ")
        else:
            self.parent.log_debug("Creating mikinfo node .. ")
            self.infoNodeLib.maya_create_mikinfo_node(context)
        self.infoNodeLib.maya_update_mikinfo_node(context,old_path,file_path)
        self.infoNodeLib.maya_check_info_node()


