## Documentation
This is a fork of tk-multi-workfiles from shotgun toolkit to replicate Mikros Image Behaviour
https://github.com/shotgunsoftware/tk-multi-workfiles


##Change in settings:
*added a wip_skip_fields to allow sniffing of multiple wip files through user-name based work folders

>    wip_skip_fields:
>       type: list
>        description: keys to skip while looking for wips
>        values:
>            type: str
>        allows_empty: True
>        default_value: ["version"]