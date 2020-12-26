# telegram-dice-bot
tg跑团用骰子机器人，开发中

使用前先新建`cfg.py`，并填入相应参数，具体见模板（还没写）

## 开发计划

* 制作人物卡，人物卡具有下列属性：

  ```json
{
      "id":int,
    "player":
      {
          "playerid":int,
          "formerplid":int
      },
      "group":
      {
          "groupid":int,
          "formergpid":int
      },
      "data":
      {
          "STR":int,
          "CON":int,
          "SIZ":int,
          "DEX":int,
          "APP":int,
          "INT":int,
          "POW":int,
          "EDU":int
      },
      "info":
      {
          "AGE":int,
          "name":str,
          "job":str,
          "sex":str,
          "birthplace":str
      },
      "derived":
      {
          
      },
      "skill":
      {
          "credit":int,
          "points":int,
          "otherskills":strs//etc.
      },
      "attr":
      {
          "maxlp":int,
          "lp":int,
          "SAN":int,
          "MAGIC":int,
          "dmgincrease":str,
          "physique":int,
          "MOV":int
      },
      "background":
      {
          "description":str,
          "faith":str,
          "vip":str,
          "exsigplace":str,
          "precious":str,
          "speciality":str,
          "dmg":str,
          "terror":str,
          "myth":str,
          "thirdencounter":str
      },
      "item":str,
      "assets":str,
      "type":str,
      "discard":bool
  }
  ```
  
  
  
  基础：`player:{playerid,playername}`,`group:{groupid,groupname}`,`data:{各项基础属性}`,`skill:{兴趣点}`,`attr:{maxlp, lp, SAN, MAGIC, dmgincrease, physique, MOV}`,
  
  以及：`background:{description, faith, vip, exsigplace, precious, speciality, dmg, terror, myth, thirdencounter}`,`item#string`,`assets#string`
  
  * 人物卡先生成基础属性。计算几个简单衍生属性。
  * 确定年龄，教育增强与基础属性修正。生成幸运，然后计算衍生属性（生命，魔法），决定移动速度
  * 决定职业，技能点，兴趣点(INT*2)，背景故事，姓名、性别、职业、工作地、出生地。（按钮实现）
  * 

## 流程（开发者自读）

* 启动。读取所有数据。将字典数据传入对象，防止游戏中途bot崩溃。对象应该是非易失数据。读取一个cfg文件。
  * 数据包含：
    * 卡数据
    * 群数据
      * 游戏是否进行中（T/F）
      * 用户数据
    * KP数据
  * 对象生成：
    * 卡
    * 群
    * 游戏（由前面定义的进行中的bool型来创建）

* 绑定群-KP，字典：`{groupid:kpid}`。
* PL群聊消息绑定群。
* PL私聊建立卡。卡需要包含的数据有`gpid, plid`，所以需要一个`getid()`获取群id。新建卡时传入一个`gpid`参数。
  * 在建立时即建立一个`pl-gp-card`的绑定。立刻存储数据至硬盘。
  * 新建卡返回一个字符串说明。即，生成了哪些属性，由哪些骰子得到该结果。用`/detail`显示，否则消息内容过于繁杂。
  * 立即提示可以`/discard`删除数值过低且未设定年龄的卡，如果存在多个群就需要指定到底删除的是哪个群的卡。先检查是否满足删卡条件，否则不允许随意删除卡。条件：3个基础数值小于50，或者综合小于xxx。具体以后再设定。
  * 可以在骰出90时选取一项进行一个1d10的奖励骰。如果KP不允许，则KP手动修改即可。
  * 提示PL使用`/age`指令添加年龄属性。然后立刻计算其他属性，之后不可删除卡。
  * **按钮**实现其它各项属性的添加。使用一个函数来判断是否已经完全创建完成以及还剩哪些参数没有获得，从而生成按钮类。
* 使用`/startgame`开启一个游戏，需要先定义KP，`/comfirm`来认证KP；通过获取已经绑定好的所有`pl-card`对来确认参与的PL。使用`/endgame`结束并删除当前群对应的对象。开始之后不可以写入`pl-gp-card`绑定。在开始之后不可以使用`/delkp`指令。
* 开启游戏。创建`Groupgame`对象。需要数据：
  * `kpid`，通过`gpid`获取。
  * PL-card对
* 玩家使用骰子。**复杂**
  * 调用时接受`gpid, plid, item`，用`gpid`决定进行的游戏，然后用`plid`决定使用的卡。`item`决定检定条目。
  * 先检查使用骰子的环境在哪个群（class）中。如果在群中，应该调用类方法而非外部方法。
  * 心理学等不可见结果的骰子需要将结果私聊至KP。除心理学的暗骰应该通过`/hide`。
  * KP设定`/hard`，临时生效一次。
  * 
* KP可以换目前使用的卡，私聊发送`switch`指令可以调整使用的卡。
* KP私聊可以修改卡的基础数值。
* 游戏结束的时候解除PL与群、卡的绑定。
* KP可以修改绝大多数设定，包括：
  * 卡的数值。接受参数`attrname:str, diff:int`，其中`diff`有正有负。PL不允许修改人物卡的数值。
  * 临时检定增加数值。例如：敏捷+50，这个设定应该考虑一个临时变量，在使用之后归0。在骰骰子时读取这个全局临时增量。如果有在本局游戏中持续生效的临时变量，应该写在人物卡的`temp`属性内，过骰子的时候检查`temp`里相应属性是否存在。

* `/deletecard`KP使用指令删除卡，`/confirm`进行二次确认，删除之后卡数据消失。**按钮**
* 没有权限进行的所有操作，都会被recall。