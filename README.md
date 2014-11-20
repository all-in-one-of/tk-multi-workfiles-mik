tk-multi-workfiles-mik
==================
This is a fork of tk-multi-workfiles from shotgun toolkit to replicate Mikros Image Vfx pipeline behavior
https://github.com/shotgunsoftware/tk-multi-workfiles

## Changes in behavior:
* changed default config to always start a new version number when creating (saving) a new variant.
* changed default behavior to always show all current work files for a given asset
* changed versionning to keep track of all work files across artists

## TO-DO, changelog:
https://github.com/tlhomme/tk-multi-workfiles-mik/wiki/TODO---Changelog

## Default config:
```yaml
tk-multi-workfiles-mik:
    allow_task_creation: false
    file_extensions: []
    hook_copy_file: default
    hook_filter_publishes: default
    hook_filter_work_files: default
    hook_scene_operation: default
    launch_at_startup: false
    launch_change_work_area_at_startup: false
    location: {path: 'https://github.com/tlhomme/tk-multi-workfiles-mik.git', type: git,
    version: v0.6.6.2} #MOST RECENT VERSION
    saveas_default_name: ''
    saveas_prefer_version_up: true
    sg_entity_type_extra_display_fields:
        Asset: {Type: sg_asset_type}
        Shot: {Sequence: sg_sequence.Sequence.code}
    sg_entity_type_filters: {}
    sg_entity_types: [Shot, Asset]
    sg_task_filters: []
    task_extra_display_fields: []
    template_publish: nuke_shot_publish #null or proper template name for the context
    template_publish_area: shot_publish_area_nuke #null or proper template name for the context
    template_work: nuke_shot_work #null or proper template name for the context
    template_work_area: shot_work_area_nuke #null or proper template name for the context
    version_compare_ignore_fields: [cs_user_name, cs_publi_flag]
```