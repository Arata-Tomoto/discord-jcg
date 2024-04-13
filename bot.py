import discord
from discord.ext import commands
import first
import asyncio
import datetime
import os
bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())


# 起動したときに起こるイベント
@bot.event
async def on_ready():
    print("準備完了")
    await execute_function()


async def execute_function():  # 大会を一定時間ごとに調べる関数
    while True:
        today = datetime.datetime.now()
        print(today.hour, today.minute)
        tmp = await jcg(today.month, today.day)
        while (tmp == "no_game"):  # グループ予選が見つからなかったとき1時間待つ
            print("cannnot find group match. wait for 1 hour")
            await asyncio.sleep(60 * 60)
            now = datetime.datetime.now()
            if (now.date != today.day):  # 日が変わっても見つからなければ終了
                tmp = "end"
            else:  # 日が変わっていなければ探索を続行
                tmp == await jcg(today.month, today.day)
        while (tmp == "on_game"):  # 決勝進行中なら10分に一度調べる
            print("game is in progress. wait for 10 minutes")
            await asyncio.sleep(60 * 10)
            tmp == await jcg(today.month, today.day)
        print("cannot find today's game or end sending data. wait for 15 hours")
        await asyncio.sleep(60 * 60 * 15)  # 送信終了or今日の大会がないとき15時間待って再開


async def jcg(month, day):  # 情報を取得し，チャンネルに送信する関数
    ctx = bot.get_channel(CHANNEL_NUM)) #メッセージ送信チャンネルID
    try:
        deck_urls = first.main(month, day)  # デッキのダウンロード，統計の処理
        if (deck_urls == "no_game"):  # グループ予選が見つからなかったら終了
            return "no_game"
        elif (deck_urls == "on_game"):  # 決勝進行中
            return "on_game"
        else:  # データの処理が完了したらディスコードに送信
            await ctx.send(str(month) + "月" + str(day) + "日" + "のJCGの結果を送信します")
            await ctx.send("------------------------------")
            clan_map = [fr"decks\{month}-{day}\data.png", fr"decks\{month}-{day}\bo30.png",
                        fr"decks\{month}-{day}\bo31.png"]  # まず統計画像だけ送信
            for c in clan_map:
                with open(c, "rb") as file:
                    image_data = discord.File(file)
                await ctx.send(file=image_data)
            image_files = [fr"decks\{month}-{day}\first_place.png", fr"decks\{month}-{day}\second_place.png",
                           fr"decks\{month}-{day}\third_place1.png", fr"decks\{month}-{day}\third_place2.png"]
            for nu, image_file in enumerate(image_files):  # デッキリストとまとめ画像をまとめて送信
                with open(image_file, "rb") as file:
                    image_data = discord.File(file)
                await ctx.send(file=image_data)
                await ctx.send(f"デッキ1url:{deck_urls[nu*2]}")
                await ctx.send(f"デッキ2url:{deck_urls[nu*2+1]}")
            await ctx.send("------------------------------")
            await ctx.send("送信が終了しました")
    except Exception as e:
        await ctx.send(f"エラーが発生しました:{e}")
    return "end"


bot.run(os.environ.get("DISCORD_TOKEN"))  # 環境変数としてトークンを使用
