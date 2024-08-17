# LB_repack
Русский | [English](README_en.md)

Проект предназначен для работы со скриптами PC-переиздания [Little Busters! English Edition](https://vndb.org/v5 "リトルバスターズ！")  (Luca System, 2017г).


## Мотивация
Основной проект для работы с ресурсами Luca System [LuckSystem](https://github.com/wetor/LuckSystem) не может перепаковывать все игровые скрипты LB_EN (по крайней мере, на момент написания README). Я попытался внести правки, но его код построен на пятиэтажных абстракциях, в которых легко потеряться. Это в итоге и произошло.

Было решено писать свою предельно прямолинейную вариацию.

## Состояние проекта
Основная цель — перевод новеллы на новый язык. Для этого всё готово. 

 - Полнофункциональные ассемблер и дизассемблер скриптов
 - Распаковщик и упаковщик .PAK-архивов

Важно понимать: дизассемблером *намеренно* поддерживается минимальный набор opcode'ов, связанных с текстом новеллы:
MESSAGE, SELECT, BATTLE, TASK, SAYAVOICETEXT и VARSTR_SET.

Если вы считаете, что я пропустил какой-то opcode, содержащий игровой текст, создайте issue — проверю.

Код местами грязный, но я не знаю, как его ощутимо улучшить. Если есть мысли — pull request'ы открыты, пишите.

## Использование
В репозитории есть оригинальный SCRIPT.PAK из steam-версии игры (build 1.2.4.0).
1. Распаковать `SCRIPT.PAK` и дизассемблировать полученные скрипты

    `python3 unpack.py`
    
    Появится две папки: `unpacked` с оригинальными скриптами из архива и `disassembled` с дизассемблированными.

2. Внести изменения в файлы из папке `disassembled`.

3. Скомпилировать скрипты и сгенерировать новый `SCRIPT.PAK`
	
    `python3 repack.py`

Для проверки работоспособности приложен `test.py`, который реассемблирует все скрипты и сверит получившиеся файлы с оригинальными. Они должны быть идентичны. 

## Известные проблемы
Отсутствует поддержка SEEN8500 и SEEN8501. Эти файлы содержат игровой текст, предположительно, названия предметов в бою.
Они не следуют стандартному «соглашению» о кодировании команд, в игровом движке для них предназначен отдельный обработчик. 

Постараюсь добавить поддержку в будущем, но пока даже непонятно, используются ли они на самом деле.


## Планы
Проект изначально предназначался для перевода новеллы на русский язык командой Team Энтузиасты. 
Сам перевод сейчас на достаточно ранней стадии, до релиза я надеюсь: 
 - Добавить поддержку версии для Nintendo Switch
 - Решить проблему с SEEN8500/SEEN8501
 - Хотя бы немного улучшить код


## Благодарности
1. [LuckSystem](https://github.com/wetor/LuckSystem) от [wetor](https://github.com/wetor) за общую идею и некоторую информацию о командах
2. [NXGameScripts](https://github.com/masagrator/NXGameScripts/tree/f0c6f0d847ea3bf7ca6f6b5b43101cdb003d52ea/Summer%20Pockets%20REFLECTION%20BLUE) от [masagrator](https://github.com/masagrator)

Код masagrator изначально был взят за основу проекта, но он него почти ничего не осталось.
