# telegram-dice-bot
tg跑团用骰子机器人，开发中

使用前先新建`cfg.py`，并填入相应参数，具体见模板（还没写）

## 开发计划

* 制作人物卡，人物卡具有下列属性：

  基础：`player:{playerid,playername}`,`group:{groupid,groupname}`,`data:{各项基础属性}`,`skill:{兴趣点}`,`attr:{maxlp, lp, SAN, MAGIC, dmgincrease, physique, MOV}`,

  以及：`background:{description, faith, vip, exsigplace, precious, speciality, dmg, terror, myth, thirdencounter}`,`item#string`,`assets#string`

  * 人物卡先生成基础属性。计算几个简单衍生属性。
  * 确定年龄，教育增强与基础属性修正。生成幸运，然后计算衍生属性（生命，魔法），决定移动速度
  * 决定职业，技能点，兴趣点(INT*2)，背景故事，姓名、性别、职业、工作地、出生地。（按钮实现）
  * 