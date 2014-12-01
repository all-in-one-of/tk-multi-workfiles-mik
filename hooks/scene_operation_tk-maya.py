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
        # log fields
        self.parent.log_debug(fields)

        entity = context.entity
        # log entity
        self.parent.log_debug(entity)

        user = context.user
        creation_time = datetime.datetime.now().strftime("%Y%m%d-%H%M")
        shot = entity['name']
        elementType = entity['type'].lower()
        versionPath = os.path.split(file_path)
        asset_type = ""
        if elementType == "asset":
        	asset_type = fields['cs_asset_type']

        #FIND CURRENT TASK
        sg = self.parent.engine.shotgun
        filters = [[ "sg_vfx_codes", "is", fields['cs_task_name']],
        ["entity","is",entity]]
        extra_fields = ["content"]
        result = sg.find('Task', filters,extra_fields)

        # Applying render template to current field to obtain render path
        maya_wip = ""
        if elementType == "asset":
            maya_wip = tk.templates["maya_asset_render_mono_exr"]
        if elementType == "shot":
            maya_wip = tk.templates["maya_shot_render_mono_exr"]

        # check
        cmds.setAttr("mikInfo.check","False",type="string")
        # from
        path = maya_wip.apply_fields(fields)
        if old_path != "":
            cmds.setAttr("mikInfo.from",old_path,type="string")
        # path
        if path != "":
            cmds.setAttr("mikInfo.imagePath",path,type="string")
        # modifDate
        cmds.setAttr("mikInfo.modifDate",creation_time,type="string")
        # nodeName
        cmds.setAttr("mikInfo.nodeName",'mikInfo',type="string")
        # path
        cmds.setAttr("mikInfo.path",file_path,type="string")
        # versionPath
        cmds.setAttr("mikInfo.versionPath",versionPath[0],type="string")
        # elementType
        cmds.setAttr("mikInfo._elementType",elementType,type="string")
        # _department
        cmds.setAttr("mikInfo._department","maya",type="string")
        # location
        if "wip" in versionPath[0]:
            cmds.setAttr("mikInfo._location",'wip',type="string")
        else:
            cmds.setAttr("mikInfo._location",'publi',type="string")
        # name
        name_value = versionPath[1].replace(".ma","")
        if 'version' in fields:
            version_str = '-v%s'%str(fields['version']).zfill(3)
            name_value = name_value.replace(version_str,"")
        cmds.setAttr("mikInfo._name",name_value,type="string")
        # publi_flag
        if 'cs_publi_flag' in fields:
            cmds.setAttr("mikInfo._publishTag",'True',type="string")
        else:
            cmds.setAttr("mikInfo._publishTag",'',type="string")
        # user_name
        if "cs_user_name" in fields:
            cmds.setAttr("mikInfo._savedBy",fields['cs_user_name'],type="string")
        # step
        cmds.setAttr("mikInfo._task",'maya',type="string")
        # task
        if len(result)>0:
            cmds.setAttr("mikInfo._step",result[0]['content'],type="string")

        if 'name' in fields:
            cmds.setAttr("mikInfo._variant",fields['name'],type="string")
        else:
            cmds.setAttr("mikInfo._variant",'',type="string")

        if 'version' in fields:
            cmds.setAttr("mikInfo._version",'v%s'%str(fields['version']).zfill(3),type="string")

        if elementType == "shot":
            if "Sequence" in fields:
                cmds.setAttr("mikInfo._seq",fields['Sequence'],type="string")
            if "Shot" in fields:
                cmds.setAttr("mikInfo._shot",shot,type="string")
            cmds.setAttr("mikInfo._in",'-1',type="string")
            cmds.setAttr("mikInfo._out",'-1',type="string")
        if elementType == "asset":
            cmds.setAttr("mikInfo._type",asset_type,type="string")
            cmds.setAttr("mikInfo._asset",fields['Asset'],type="string")

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
    createTextInput("_comment")
    createTextInput("_department")
    createTextInput("_elementType")
    createTextInput("_location")
    createTextInput("_name")
    createTextInput("_publishTag")
    createTextInput("_savedBy")
    createTextInput("_step")
    createTextInput("_task")
    createTextInput("_variant")
    createTextInput("_version")
    if elementType == "asset":
        createTextInput("_asset")
        createTextInput("_type")
    if elementType == "shot":
        createTextInput("_in")
        createTextInput("_out")
        createTextInput("_seq")
        createTextInput("_shot")

