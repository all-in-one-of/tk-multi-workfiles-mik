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

        if operation == "current_path":
            # return the current scene path
            return cmds.file(query=True, sceneName=True)
        elif operation == "open":
            # do new scene as Maya doesn't like opening
            # the scene it currently has open!
            cmds.file(new=True, force=True)
            cmds.file(file_path, open=True)
            self._check_mikinfo_node(context,"",file_path)
        elif operation == "save":
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
                                                 "Save your scene?",
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
            create_mikinfo_node(context)
        self._update_mikinfo_node(context,old_path,file_path)

    def _update_mikinfo_node(self,context,old_path,file_path):
        '''
        @summary: updates infonode in scene with new values
        @param context: current shotgun context
        '''
        mikinfo = cmds.select("mikInfo")

        tk = tank.sgtk_from_path(context.filesystem_locations[0])
        template = tk.template_from_path(file_path)
        fields = template.get_fields(file_path)
        sg = self.parent.engine.shotgun

        entity = context.entity
        user = context.user
        creation_time = datetime.datetime.now().strftime("%Y%m%d-%H%M")
        shot = entity['name']
        elementType = entity['type'].lower()
        versionPath = os.path.split(file_path)

        filters = [[ "id", "is", entity['id'] ]]
        asset_type = ""
        if elementType == "asset":
            field = ["sg_asset_type"]
            result = sg.find(entity['type'], filters, field)
            if len(result)>0:
                asset_type = result[0]["sg_asset_type"]

        # Applying render template to current field to obtain render path
        maya_wip = ""
        if elementType == "asset":
            maya_wip = tk.templates["maya_asset_render_mono_exr"]
        if elementType == "shot":
            maya_wip = tk.templates["maya_shot_render_mono_exr"]

        path = maya_wip.apply_fields(fields)
        cmds.setAttr("mikInfo.check","True",type="string")

        if old_path != "":
            cmds.setAttr("mikInfo.from",old_path,type="string")

        if path != "":
            cmds.setAttr("mikInfo.imagePath",path,type="string")

        cmds.setAttr("mikInfo.modifDate",creation_time,type="string")
        cmds.setAttr("mikInfo.nodeName",'mikInfo',type="string")
        cmds.setAttr("mikInfo.path",file_path,type="string")
        cmds.setAttr("mikInfo.versionPath",versionPath[0],type="string")
        cmds.setAttr("mikInfo.elementType",elementType,type="string")
        cmds.setAttr("mikInfo.department","maya",type="string")

        if "wip" in versionPath[0]:
            cmds.setAttr("mikInfo.location",'wip',type="string")
        else:
            cmds.setAttr("mikInfo.location",'publi',type="string")

        name_value = versionPath[1].replace(".ma","")
        if 'version' in fields:
            version_str = '-v%s'%str(fields['version']).zfill(3)
            name_value = name_value.replace(version_str,"")
        cmds.setAttr("mikInfo.name",name_value,type="string")

        if 'cs_publi_flag' in fields:
            cmds.setAttr("mikInfo.publishTag",'True',type="string")
        else:
            cmds.setAttr("mikInfo.publishTag",'False',type="string")

        if "cs_user_name" in fields:
            cmds.setAttr("mikInfo.savedBy",fields['cs_user_name'],type="string")

        if 'cs_step_short_name' in fields:
            cmds.setAttr("mikInfo.step",'maya',type="string")
            cmds.setAttr("mikInfo.task",fields['cs_step_short_name'],type="string")

        if 'name' in fields:
            cmds.setAttr("mikInfo.variant",fields['name'],type="string")
        else:
            cmds.setAttr("mikInfo.variant",'',type="string")

        if 'version' in fields:
            cmds.setAttr("mikInfo.version",'v%s'%str(fields['version']).zfill(3),type="string")

        if elementType == "shot":
            if "Sequence" in fields:
                cmds.setAttr("mikInfo.seq",fields['Sequence'],type="string")
            if "Shot" in fields:
                cmds.setAttr("mikInfo.shot",shot,type="string")
            cmds.setAttr("mikInfo.in",'-1',type="string")
            cmds.setAttr("mikInfo.out",'-1',type="string")
        if elementType == "asset":
            cmds.setAttr("mikInfo.type",asset_type,type="string")
            cmds.setAttr("mikInfo.asset",fields['Asset'],type="string")

# =======
#
# mikinfo
#
# =======

def createTextInput(name,value=""):
    '''
    @summary: create a string nuke knob with a name and a value
    @param name: knob name
    @param value: knob value
    @result: the new knob
    '''
    cmds.addAttr(longName=name,dt="string")


def create_mikinfo_node(context):
    '''
    @summary: create infonode with empty values
    @result: the infonode
    '''
    # create mikinfo node
    mikinfo = cmds.createNode("container",n="mikInfo")
    entity = context.entity
    elementType = entity['type'].lower()

    # add proper knobs
    createTextInput("check")
    createTextInput("from")
    createTextInput("imagePath")
    createTextInput("modifDate")
    createTextInput("nodeName")
    createTextInput("path")
    createTextInput("versionPath")
    createTextInput("comment")
    createTextInput("department")
    createTextInput("elementType")
    createTextInput("location")
    createTextInput("name")
    createTextInput("publishTag")
    createTextInput("savedBy")
    createTextInput("step")
    createTextInput("task")
    createTextInput("variant")
    createTextInput("version")
    if elementType == "asset":
        createTextInput("asset")
        createTextInput("type")
    if elementType == "shot":
        createTextInput("in")
        createTextInput("out")
        createTextInput("seq")
        createTextInput("shot")

