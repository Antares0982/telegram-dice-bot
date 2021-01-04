# telegram-dice-bot
tg跑团用骰子机器人，目前版本v1.0.0

## 使用说明

需要安装的包：

```
pip3 install numpy
pip3 install python-telegram-bot
pip3 install logging
pip3 install pysocks
```

使用前先重命名`sample_config.ini`到`config.ini`，并填入相应参数（TOKEN, USERID, DATA_PATH）。参数说明如下：

* 使用代理的话将`PROXY`参数设为`true`，不需要则设为`false`。使用代理时，填写相应的代理地址`PROXY_URL`。
* `TOKEN`一项中填写你的tgbot token。
* `DATA_PATH`填写数据文件夹的位置，在末尾需要`/`，如果是win系统则是`\`
* `USERID`填写你的telegram id。如果不知道自己的ID可以先填0，启动之后对bot发送`/getid`来获得ID，修改后重启bot。
* `HELP`是使用时给使用者的提示。
* `IGNORE_JOB_DICT`是否可以设置职业表以外的职业（职业表位置：`/data/jobdict.json`），如果设为`false`则只能设置职业表内的职业。

## 指令

建议KP熟读以下指令信息。PL只需要了解`/newcard`，`/setage`，`/setstrdec `，`/setcondec `，`/setjob`，`/addskill`，`/setname`，`/setsex`，`/setbkground`，`/randombackground`，`/roll`，`/sancheck`。

KP进行游戏引导时，可以在指令前输入文字+空格（使该指令无效），并提示PL长按指令将指令加入输入框中。例如：

**“长按 /roll 使用骰子。”**

* `/start`显示帮助信息。

* (group) `/addkp` 将本群kp设置为自己。

* (group) `/delkp` 自己是kp时，撤销kp设置。

* `/reload` 重新读取数据文件。

* `/showuserlist` 查看全部用户信息。

* `/getid` 获取本群或用户id。

* (private) `/newcard <groupid>` 生成新的角色卡基础数据，绑定至一个群。

* (private) `/discard` 满足某些条件时，删除生成的角色卡。

* `/details` 显示详细信息。

* (private) `/setage <AGE>` 设置新角色卡的年龄。设置后不可删除角色卡。

* (private) `/setstrdec <STRDEC>` 设置因为年龄设定导致的STR属性下降。

* (private) `/setcondec <CONDEC>` 设置因为年龄设定导致的CON属性下降。

* (private) `/setjob (<jobname>)` 设置职业。

* (private) `/addskill (<skillname>) (<point>) (main/interest)` 增加/修改一项技能的点数。可以将技能列表中的任意一个技能加入自己的角色卡

* `/setname <name:List[str]>` 设定角色姓名，中间可以有空格。多个空格、制表符与换行会被替换为单个空格。如果已经设定过，则会被替换为新设定的内容。

* `/randombackground` 随机生成角色背景。如果已经设定过，则会被替换为新设定的内容。建议结合`/show background`来查看并修改背景。

* `/setbkground <bkgroundname> <bkgroudinfo:List[str]>` 例如：

  * `/setbkground description 李华是一个不会写英语作文的高中生。` 

  * `/setbkground vip 父亲 母亲 前妻`

  * ```
    /setbkground faith 坚信外星人存在。
    狂热地想被外星人绑架。
    经常和友人说自己和外星人握过手。
    ```

  多个空格、制表符与换行会被替换为单个空格。建议在游戏开始前使用`/setbkground description <bkgroundinfo>` 详细填写背景故事。如果已经设定过，则会被替换为新设定的内容。建议结合`/show background`来查看并修改背景。backgroundname的快速参考：

  * description：描述。即背景故事。
  * faith：信仰。
  * vip：重要之人。
  * exsigplace：重要之地。
  * precious：珍贵之物。
  * speciality：特质。
  * dmg：曾受过的伤。
  * terror：恐惧之物。
  * myth：神秘学背景。
  * thirdencounter：第三类接触。

* `/setsex <SEX>` 设置性别，可以设置男女以外的性别。

* `/startgame` KP使用该指令开启跑团。使用后人物卡属性会被复制一份，并且`/roll`指令进行检定开始生效。

* `/abortgame` 中止游戏，将删去所有在游戏内人物卡属性的修改。

* `/endgame` 结束游戏，游戏中人物卡会覆盖原本的人物卡信息，并且删除`playerid`等属性。

* `/roll (<dice>)` 默认1d100，支持的参数dice有

  * 技能名：`/roll 闪避`则会对当前操控的角色所持有的“闪避”技能进行检定。
  * 骰子： `/roll 2d6+3d10+6`则会骰2d6与3d10，并将结果与6相加。
  * 暗骰：`/roll 心理学`以及`/roll 暗骰`都会将骰子结果私聊给KP。`/roll 暗骰80`可以将暗骰检定值设置为80，不设置的话默认50。

* `/sancheck <checkpass>/<checkfail>` 例如，`/sancheck 1/1d6` 进行一次san check，成功减1失败减1d6。

* `/show (<attr>)` 群聊时发送则仅限游戏内显示整张卡信息，或者显示某项具体数值。私聊时显示自己的角色卡信息。例如`/show STR`会显示人物卡STR属性的值。还有以下几种用法：

  * (private) `/show group <groupid>` 显示某个具体群的所有（游戏外）角色卡信息
  * (private) `/show kp` 显示目前用户作为KP控制的所有（游戏外）卡信息
  * (private) `/show game`显示KP所主持的游戏中所有卡信息

* (private) `/showids (kp)` 不带kp参数时，如果在主持游戏，将会显示游戏内所有卡的id。如果不是在主持游戏，显示所有相关卡的id。带kp参数时，显示kp控制的卡的顺序号而非id，仅用于`/switchcard`指令配合使用。

* (group)`/tempcheck <tempcheckvalue> (<cardid> <checkname>)` 只有游戏中可以使用。临时加/减一次检定，或者对某张卡写入一个长期生效的检定。

  * 只生效一次的+10检定可以写为`/tempcheck 10`，那么下次进行检定时，无论是什么检定都会在原有值上+10，只生效一次。

  * 如果对某张卡写入游戏中长期生效的加/减检定，例如，用`/tempcheck -10 0 STR`可以对id为0的卡写入一个-10的STR检定下降。如果要去掉这个设置，则使用`/tempcheck 0 0 STR`即可。

* `/switchcard <cardID>`  按照kp在游戏中控制的卡的顺序号而非真实id，切换kp控制的卡。顺序号用`/showids kp`来查看。

* `modify <cardID> <attrname> <value>` 修改角色卡信息，请谨慎使用该指令。发送者需是kp。如果在主持游戏，则修改的是游戏中的属性，且id参数也是游戏中的卡id。如果不在游戏中，则修改的是游戏外角色卡信息，id参数是游戏外卡片id。