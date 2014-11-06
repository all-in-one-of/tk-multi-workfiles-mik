tk-multi-workfiles-mik
==================
This is a fork of tk-multi-workfiles from shotgun toolkit to replicate Mikros Image Vfx pipeline behavior
https://github.com/shotgunsoftware/tk-multi-workfiles

## Changes in behavior:
* changed default config to always start a new version number when creating (saving) a new variant.
* changed default behavior to always show all current work files for a given asset
* changed versionning to keep track of all work files across artists


##Changes in settings: info.yml:
+ added a wip_skip_fields to allow sniffing of multiple wip files through user-name based work folders

```yaml
wip_skip_fields:
    type: list
    description: keys to skip while looking for wips
    values:
        type: str
    allows_empty: True
    default_value: ["version"]
```