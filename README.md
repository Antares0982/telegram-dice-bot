# telegram-dice-bot
tg跑团用骰子机器人，目前版本`v1.3.0`

如果有任何意见或修改建议请提交issue或者联系[我](https://t.me/AntaresChr)。

## 使用说明

> 为了bot的正常使用，请不要删除这个README文件。

安装依赖包：

```
pip3 install -r requirements.txt
```

> 第一次使用前，如果不准备更改数据文件的位置，先执行一遍`cfg.py`，这时会执行失败并退出

重命名`sample_config.ini`为`config.ini`，并填入相应参数（`TOKEN`, `ADMIN_ID`）。如果有需要改变存储位置的话请手动修改。参数说明如下：

* 使用代理的话将`proxy`参数设为`true`，不需要则设为`false`。使用代理时，填写相应的代理地址和端口`proxy_url`，socks5与http都支持。

* `token`一项中填写你的tgbot token。

* `data_path`填写数据文件夹的位置。

* `admin_id`填写你的telegram id。如果不知道自己的ID可以先填0，启动之后对bot发送`/getid`来获得ID，修改后重启bot。

* `ignore_job_dict`是否可以设置职业表以外的职业（职业表位置：`/data/jobdict.json`），如果设为`false`则只能设置职业表内的职业。

* 可以在默认的`data/global`文件夹下找到职业表、技能表的JSON文件。如果有需要，可以自行添加技能和职业。

* `blacklistdatabase`黑名单数据库的路径。

* `startcommand`：设置启动脚本。如果不准备使用`/restart`指令，可以不管这一项。注意，该脚本必须能在成功启动bot后立即退出，否则会有两个bot进程。这一启动脚本用于在bot聊天窗口中使用`/restart`指令（从git仓库拉取并）重启bot。对于Linux用户，命令行中创建启动脚本的推荐方案如下：（注意自行修改`/path/to/dicebotFolder`，并确保原本在路径下没有`startup.sh`这一文件）

  ```bash
  cd ~
  echo "#\!/bin/bash" > startup.sh
  echo "cd /path/to/dicebotFolder && git pull" >> startup.sh # git pull 可选，如果不想获取到更新可以忽略'&& git pull'。有时更新新功能后会新增config项，需要手动更改才能正常运行。
  echo "nohup python3 -O main_dicebot.py > ~/dicebot.log &" >> startup.sh
  chmod +x startup.sh
  ```

  config中填写如下：

  ```
  startcommand = cd /home/tgbot && ./startup.sh &
  ```

然后运行`main_dicebot.py`即可。

## 指南

bot的所有指令帮助文档都在代码内可以查到。当bot正常运行时，向bot发送`/help <command>`可以查询到对应指令的帮助文档。

### KP

bot需要在群聊中进行游戏，如果要开始游戏，将bot拉入群。

在群内发送指令`/bindkp`，就可以将您自己设置为KP。这之后如果需要撤销自己的KP，发送指令`/unbindkp`。

管理员可以使用`/transferkp`强制转移KP权限。

查询更多内容，请向bot发送以下指令：

`/help bindkp`
`/help unbindkp`
`/help transferkp`

### 卡片

bot可以存储角色卡的数据。玩家使用`/newcard`创建新角色卡并绑定至群，或者使用`/addcard`直接添加一张卡片。卡片具有一个非负整数`id`作为唯一识别的标志。

卡片可以被转移至别的群`/changegroup`、别的玩家`/cardtransfer`，也可以更换喜欢的id`/changeid`。

可以用`/trynewcard`来尝试以下如何建卡，建立的卡会被绑定至一个无效群，无法使用并且随时可以删除。

玩家在一个群内最多只有一张卡，如果有多个群则每个群可以有一张卡。KP可以在一个群拥有多张角色卡（一般是NPC），可以用于与玩家对抗、合作等。

如果玩家或KP拥有多张卡，使用指令修改角色卡的属性时（例如姓名，背景故事，性别等），请先使用`/switch`切换操作中的卡。

`show`开头的系列指令用于显示卡片信息、技能表、职业表。

`/show`可以显示自己当前操作中（用`/switch`切换）的卡基本信息。`/show card`可以查看整张卡片。`/show STR`可以查看STR属性的值。`/showcard <id>`可以查看对应id的卡片的信息（如果有权限的话），`/showcard <id> (card)/(attr)`功能完全类似于`/show (card)/(attr)`。

其他`show`开头系列指令的详细说明请向bot发送`/help <command>`进行查阅。

发送`/createcardhelp`可以获得建立新卡流程的提示。

当游戏开始时，该群内所有卡片会被复制一份，这一副本被称为游戏内的卡，游戏中的修改只会作用在游戏内的卡上，这时若玩家修改姓名等属性，将只能修改到游戏外的卡上。当游戏暂停并继续时，这些游戏外修改的属性才会被写入游戏内。

当游戏正常结束，而不是被中途放弃时，游戏内的卡片会覆盖掉游戏外的对应卡片，并将控制权转移给KP。当游戏被中途放弃之时，游戏内的卡片将会被全部删除，游戏中造成的修改不会覆盖到游戏外的卡，也不会被转移控制权。

查询卡片相关的详细操作，请向bot发送以下指令：

`/help addcard`
`/help additem`
`/help addskill`
`/help cardtransfer`
`/help changegroup`
`/help changeid`
`/help choosedec`
`/help copygroup`
`/help delcard`
`/help discard`
`/help getid`
`/help newcard`
`/help randombkg`
`/help renewcard`
`/help setage`
`/help setasset`
`/help setbkg`
`/help setjob`
`/help setname`
`/help setsex`
`/help show`
`/help showcard`
`/help showids`
`/help showjoblist`
`/help showkp`
`/help showmycards`
`/help showskilllist`
`/help switch`
`/help switchgamecard`
`/help trynewcard`

### 游戏

KP可以使用`/setrule`设置游戏的部分规则，这个操作应该在第一名玩家车卡直接完成。可以使用`/showrule`查看规则。

KP使用`/startgame`开始游戏，这时会对群内玩家的卡片做一次检查，判断卡片是否缺少什么必填项。如果有缺失，则无法开始游戏。

如果想跳过这一检查，使用`/start ignore`。

`/startgame`执行成功后，群内即会产生角色卡的游戏内副本。

KP使用`/pausegame`暂停游戏，此时游戏会暂时被隐藏，无法进行sancheck，HP扣除等操作。使用`/continuegame`或者`/startgame`继续该游戏。

KP使用`/abortgame`放弃一场游戏，会导致所有游戏内的修改被丢弃。

KP使用`/endgame`正常结束游戏，游戏内的卡片会覆盖游戏外的卡片，且控制权会被转移给KP。

KP可以使用`/modify`修改群内任意卡片（包括游戏内、游戏外）的除群、id、玩家id以外的任何信息，具体如何使用，请向bot发送`/help modify`查询。

**进行游戏**

在游戏进行中时，可以使用`/roll`进行检定。

`/roll STR`：力量检定；`/roll 侦查`：侦查检定。不需要设置难度等级，会自动显示。

KP要使用NPC或怪物卡片过骰子时，需要先使用`/switchgamecard`在拥有的卡片之间切换。

如果需要给下一个骰子设置一个临时的检定修正，或者给玩家的某项检定设置持续生效的检定修正，请使用`/tempcheck`。

进行sancheck时，使用`/sancheck success/fail`。例如`/sancheck 0/1d6`即可进行一次成功减0，失败减1d6的sancheck。

KP使用`/hp`可以修改玩家的HP。`/hp +(1d3+1d2)`可以回复`(1d3+1d2)`点HP，`/hp 10`可以将HP设置为10。

KP使用`/kill`，`/mad`撕卡。`/recover`使角色从重伤状态恢复。

查询游戏相关的详细操作，请向bot发送以下指令：

`/help abortgame`
`/help continuegame`
`/help endgame`
`/help hp`
`/help kill`
`/help mad`
`/help modify`
`/help pausegame`
`/help recover`
`/help startgame`

### 管理

除了游戏的功能以外，bot还提供了一些方便的功能。

`/delmsg (number)`删除`/delmsg`这条指令上面的number条消息，并同时删除`/delmsg`这条消息。在私聊时可以用来清理对话框。在群聊时使用需要bot以及使用者都是管理员，可以清理多余的消息。删除速度会比较慢，请耐心等待，不要重复使用该指令。

`/getid`可以获取本群、本玩家的唯一识别id。

`/link`生成本群的邀请链接，并私聊发送给使用指令者（需要管理员权限）。

`/msgid`获取消息的message id，这是消息在群内的唯一识别id。

`/help delmsg`
`/help getid`
`/help link`
`/help msgid`

### BOT拥有者

作为拥有者，对bot有最高的管理权限。

`/reload` bot的拥有者可以使用，对应的人是`config.ini`中的`ADMIN_ID`。在bot出现非致命的数据问题时，可以重新读取全部数据。（如果发生了非数据损坏导致的无法解决的问题，请联系作者或者提交issue）

`/stop`终止python进程，请务必用这种方式终止bot。终止前会先进行文件写入保存数据。

`/restart`相当于`/reload`。

`/exec (r) <code>` **请谨慎使用**。将会执行一段python代码。如果代码前有参数`r`，则代码执行的返回值会输出给用户。没有参数`r`则只会提示执行成功与否。

