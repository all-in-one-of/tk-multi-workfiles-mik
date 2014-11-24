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

        if file_path:
            file_path = file_path.replace("/", os.path.sep)

        if operation == "current_path":
            # return the current script path
            return nuke.root().name().replace("/", os.path.sep)

        elif operation == "open":
            # open the specified script
            nuke.scriptOpen(file_path)
            self._check_mikinfo_node(context,"",file_path)
            self._check_write_nodes()

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

                self._check_mikinfo_node(context,old_path,file_path)
                self._check_write_nodes()

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

    def _check_mikinfo_node(self,context,old_path,file_path):
        '''
        @summary: check if info node exists, create it not and then update it
        @param context: current shotgun context
        '''
        mikinfo = nuke.toNode("mikInfo")
        if mikinfo:
            self.parent.log_debug("Found mikinfo node .. ")
        else:
            self.parent.log_debug("Creating mikinfo node .. ")
            mikinfo = create_mikinfo_node()
        update_mikinfo_node(context,old_path,file_path)

    def _check_write_nodes(self):
        '''
        @summary: check if mikros write nodes existrs otherwise create them
        '''
        x , y = None, None
        mikinfo = nuke.toNode("mikInfo")
        if mikinfo:
            x = mikinfo.xpos()
            y = mikinfo.ypos()
        deselectAll()
        wipwrite = nuke.toNode("WriteWIP")
        if not wipwrite:
            self.parent.log_debug("Creating WriteWIP .. ")
            wipwrite =nuke.createNode("WriteTank",inpanel = False)
            wipwrite.setName('WriteWIP')
            wipwrite.knobs()['tk_profile_list'].setValue('Write WIP')
            wipwrite.setXpos(x+150)
            wipwrite.setYpos(y)
            deselectAll()

        defwrite = nuke.toNode("WriteDEF")
        if not defwrite:
            self.parent.log_debug("Creating WriteDEF .. ")
            defwrite =nuke.createNode("WriteTank",inpanel = False)
            defwrite.setName('WriteDEF')
            defwrite.knobs()['tk_profile_list'].setValue('Write DEF')
            defwrite.setXpos(x+300)
            defwrite.setYpos(y)
            deselectAll()

# =======
#
# mikinfo
#
# =======
def deselectAll():
    for node in nuke.allNodes():
        node['selected'].setValue(0)

def createTextInput(name,value=""):
    '''
    @summary: create a string nuke knob with a name and a value
    @param name: knob name
    @param value: knob value
    @result: the new knob
    '''
    label = name.split('-')[1]
    new_knob = nuke.String_Knob(name,label)
    new_knob.setValue(value)
    return new_knob


def create_mikinfo_node():
    '''
    @summary: create infonode with empty values
    @result: the infonode
    '''
    # create mikinfo node
    mikinfo = nuke.createNode('NoOp', inpanel=False)
    mikinfo.setName("mikInfo")
    # add proper knobs
    mikinfo.addKnob(createTextInput("mik-check"))
    mikinfo.addKnob(createTextInput("mik-from"))
    mikinfo.addKnob(createTextInput("mik-imagePath"))
    mikinfo.addKnob(createTextInput("mik-in"))
    mikinfo.addKnob(createTextInput("mik-maya"))
    mikinfo.addKnob(createTextInput("mik-modifDate"))
    mikinfo.addKnob(createTextInput("mik-nodeName"))
    mikinfo.addKnob(createTextInput("mik-out"))
    mikinfo.addKnob(createTextInput("mik-path"))
    mikinfo.addKnob(createTextInput("mik-versionPath"))
    mikinfo.addKnob(createTextInput("mik-x"))
    mikinfo.addKnob(createTextInput("mik-y"))
    mikinfo.addKnob(createTextInput("_mik-comment"))
    mikinfo.addKnob(createTextInput("_mik-department"))
    mikinfo.addKnob(createTextInput("_mik-elementType"))
    mikinfo.addKnob(createTextInput("_mik-in"))
    mikinfo.addKnob(createTextInput("_mik-location"))
    mikinfo.addKnob(createTextInput("_mik-name"))
    mikinfo.addKnob(createTextInput("_mik-out"))
    mikinfo.addKnob(createTextInput("_mik-pass"))
    mikinfo.addKnob(createTextInput("_mik-publishTag"))
    mikinfo.addKnob(createTextInput("_mik-savedBy"))
    mikinfo.addKnob(createTextInput("_mik-seq"))
    mikinfo.addKnob(createTextInput("_mik-shot"))
    mikinfo.addKnob(createTextInput("_mik-step"))
    mikinfo.addKnob(createTextInput("_mik-task"))
    mikinfo.addKnob(createTextInput("_mik-variant"))
    mikinfo.addKnob(createTextInput("_mik-version"))

    return mikinfo

def update_mikinfo_node(context,old_path,file_path):
    '''
    @summary: updates infonode in scene with new values
    @param context: current shotgun context
    '''
    mikinfo = nuke.toNode("mikInfo")
    if mikinfo:
        tk = tank.sgtk_from_path(context.filesystem_locations[0])
        template = tk.template_from_path(file_path)
        fields = template.get_fields(file_path)
        entity = context.entity
        user = context.user
        creation_time = datetime.datetime.now().strftime("%Y%m%d-%H%M")
        shot = entity['name']
        elementType = entity['type'].lower()
        versionPath = os.path.split(file_path)


        # Applying render template to current field to obtain render path
        nuke_render_wip = tk.templates["nuke_shot_render_mono_dpx"]
        path = nuke_render_wip.apply_fields(fields)

        x = str(mikinfo.xpos())
        y = str(mikinfo.ypos())

        mikinfo.knobs()["mik-check"].setValue("True")

        if old_path != "":
            mikinfo.knobs()["mik-from"].setValue(old_path)

        if path != "":
            mikinfo.knobs()["mik-imagePath"].setValue(path)

        mikinfo.knobs()["mik-in"].setValue('-1')

        mikinfo.knobs()["mik-maya"].setValue('None')

        mikinfo.knobs()["mik-modifDate"].setValue(creation_time)

        mikinfo.knobs()["mik-nodeName"].setValue('mikInfo')

        mikinfo.knobs()["mik-out"].setValue('-1')

        mikinfo.knobs()["mik-path"].setValue(file_path)

        mikinfo.knobs()["mik-versionPath"].setValue(versionPath[0])

        mikinfo.knobs()["mik-x"].setValue(x)

        mikinfo.knobs()["mik-y"].setValue(y)

        # mikinfo.knobs()["_mik-comment"].setValue('')
        #
        mikinfo.knobs()["_mik-department"].setValue('compo')

        mikinfo.knobs()["_mik-elementType"].setValue(elementType)

        mikinfo.knobs()["_mik-in"].setValue('-1')

        if "wip" in versionPath[0]:
            mikinfo.knobs()["_mik-location"].setValue('wip')
        else:
            mikinfo.knobs()["_mik-location"].setValue('publi')

        name_value = versionPath[1].replace(".nk","")
        if 'version' in fields:
            version_str = '-v%s'%str(fields['version']).zfill(3)
            name_value = name_value.replace(version_str,"")
        mikinfo.knobs()["_mik-name"].setValue(name_value)

        mikinfo.knobs()["_mik-out"].setValue('-1')

        # mikinfo.knobs()["_mik-pass"].setValue('')
        #
        if 'cs_publi_flag' in fields:
            mikinfo.knobs()["_mik-publishTag"].setValue('True')
        else:
            mikinfo.knobs()["_mik-publishTag"].setValue('False')

        if "cs_user_name" in fields:
            mikinfo.knobs()["_mik-savedBy"].setValue(fields['cs_user_name'])

        if "Sequence" in fields:
            mikinfo.knobs()["_mik-seq"].setValue(fields['Sequence'])

        mikinfo.knobs()["_mik-shot"].setValue(shot)

        if 'cs_step_short_name' in fields:
            mikinfo.knobs()["_mik-step"].setValue(fields['cs_step_short_name'])
            mikinfo.knobs()["_mik-task"].setValue(fields['cs_step_short_name'])

        if 'name' in fields:
            mikinfo.knobs()["_mik-variant"].setValue(fields['name'])
        else:
            mikinfo.knobs()["_mik-variant"].setValue('')

        if 'version' in fields:
            mikinfo.knobs()["_mik-version"].setValue('v%s'%str(fields['version']).zfill(3))
