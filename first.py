import requests
import os
from bs4 import BeautifulSoup
import time
from selenium import webdriver
import matplotlib.font_manager
import japanize_matplotlib
import urllib.request
import cv2
import numpy as np
from PIL import ImageFont, ImageDraw, Image
import pandas as pd
import math
import matplotlib.pyplot as plt

month = 0
day = 0


def gen_url(day):
    # ローテーションのグループ，決勝大会を選択
    res = requests.get("https://sv.j-cg.com/past-schedule")
    soup = BeautifulSoup(res.text, "html.parser")
    games = soup.find_all("a", attrs={"class": "schedule-link"})
    rotation = soup.find_all("div", attrs={"class": "schedule-title"})
    title_group = [day, "ローテーション大会", "グループ予選"]
    title_final = [day, "ローテーション大会", "決勝トーナメント"]
    group_url = "nasi"
    final_url = "nasi"
    for i, rota in enumerate(rotation):
        if all(t in str(rota) for t in title_group):
            group_url = games[i].get("href")
            print(group_url)
        if all(t in str(rota) for t in title_final):
            final_url = games[i].get("href")
            print(final_url)
    return group_url, final_url


def clan_distribution(url):  # urlの大会のクラス分布を取得
    url = url + "/entries"
    # ページ全体をスクロールして読み込む
    driver = webdriver.Chrome()
    driver.get(url)
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1.0)  # スクロールが終了するのを待つ
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height
    res_group = driver.page_source

    # ページのhtmlを取得
    soup_clan = BeautifulSoup(res_group, "html.parser")
    winners = soup_clan.find_all("div", attrs={"class": "entry winner"})
    # 予選/決勝クラス分布
    clan_map = [0, 0, 0, 0, 0, 0, 0, 0]
    clan_list = []
    # 各デッキのクラスを取得
    for winner in winners:
        decks = winner.find_all("div", attrs={"class": "deck-image"})
        for d in decks:
            img_item = d.find("img")
            if (".png" in str(img_item)):
                src_url = img_item.get("src")
                clan_num = src_url[-5]
                if (clan_num.isnumeric()):
                    clan_map[int(clan_num) - 1] += 1
                    clan_list.append(int(clan_num))
    return clan_map, clan_list


class winning_info():  # 入賞者の情報をまとめるクラス
    def __init__(self, final_url, m, d):
        self.url = final_url
        self.deck_urls = []
        self.deck_titles = ["優勝デッキリスト", "準優勝デッキリスト", "3位デッキリスト", "3位デッキリスト"]
        self.month = m
        self.day = d

    def deck_name_info(self):
        # 8個のデッキのどばすぽULRを取得し，画像をダウンロード，入賞者の名前を得る
        url = self.url + "/results"
        res = requests.get(url)
        soup = BeautifulSoup(res.text, "html.parser")
        name_elements = soup.find_all("div", attrs={"class": "result-name"})
        decks = soup.find_all("div", attrs={"class": "deck-image"})
        names = []
        for i, el in enumerate(name_elements):
            names.append(el.a.text.strip())
            self.deck_titles[i] = self.deck_titles[i] + "(" + names[i] + ")"
        for deck in decks:
            deck_a = deck.find("a")
            self.deck_urls.append(deck_a.get("href"))
        # デッキ画面のurlをRefererとして付与しないとDLできない
        for i, deck_url in enumerate(self.deck_urls):
            deck_url = str(deck_url)
            save_path = fr"decks\{self.month}-{self.day}\{i}.png"
            req = urllib.request.Request("https://shadowverse-portal.com/image/1?lang=ja")
            req.add_header('Referer', deck_url)
            opener = urllib.request.build_opener()
            response = opener.open(req)
            with open(save_path, "wb") as f:
                f.write(response.read())
            print('Image downloaded successfully!')

    def image_conbination(self):
        # フォント，タイトル，ファイル名の設定
        hozon = ["first_place.png", "second_place.png", "third_place1.png", "third_place2.png"]
        image_height = 50
        font_path = matplotlib.font_manager.findfont("MS Gothic")
        font = ImageFont.truetype(font_path, 32)
        position = (10, 10)
        self.deck_name_info()
        # 1~3位までの2デッキを組み合わせた画像を生成しタイトルをつける
        for i in range(4):
            # 画像を読み込む
            image1 = cv2.imread(fr"decks\{self.month}-{self.day}\{i*2}.png")
            image2 = cv2.imread(fr"decks\{self.month}-{self.day}\{i*2+1}.png")
            # 画像を結合する
            im_v = cv2.vconcat([image1, image2])
            # 結合した画像のサイズを計算し文字領域を生成
            height, width, _ = im_v.shape
            image_width = width
            image = np.ones((image_height, image_width, 3), dtype=np.uint8) * 255
            img_pil = Image.fromarray(image)
            draw = ImageDraw.Draw(img_pil)
            text = self.deck_titles[i]
            draw.text(position, text, font=font, fill="black")
            img = np.array(img_pil)
            img = cv2.vconcat([img, im_v])
            cv2.imwrite(fr"decks\{self.month}-{self.day}\{hozon[i]}", img)
        return self.deck_urls


class plot_map:  # 円グラフと表を生成するクラス
    clan_labels = ["エルフ", "ロイヤル", "ウィッチ", "ドラゴン", "ネクロマンサー", "ヴァンパイア", "ビショップ", "ネメシス"]
    colors = ["olivedrab", "gold", "blue", "orange", "darkviolet", "firebrick", "khaki", "darkturquoise"]
    title = ["予選クラス分布", "決勝クラス分布"]

    def __init__(self, clan, fig, i):  # グラフの表示領域と扱うクラス分布を指定
        self.ax_c = fig.add_subplot(2, 2, i + 1)
        self.ax_t = fig.add_subplot(2, 2, i + 3)
        self.i = i
        self.ax_c.axis("off")
        self.ax_t.axis("off")
        self.clan = clan

    def truncate_float(self, number, decimals=0):  # 指定した小数点以下の桁数で小数を切り捨てる
        multiplier = 10 ** decimals
        return math.trunc(number * multiplier) / multiplier

    def create_data(self):  # データが大きいクラス順にソート
        data_sorted = sorted(zip(self.clan, self.clan_labels, self.colors), reverse=True)
        clan_map_sorted, labels_sorted, colors_sorted = zip(*data_sorted)  # ソートしたデータから再度サイズ、ラベル、色を取得
        total = sum(clan_map_sorted)
        per = [self.truncate_float(x / total * 200, 2) for x in clan_map_sorted]  # クラス分布を割合で表示
        return clan_map_sorted, labels_sorted, colors_sorted, per

    def plot_data(self):  # クラス分布に対して表と円グラフをプロット 画像の保存は外部で行う
        group_map, group_label, group_color, group_per = self.create_data()
        # 円グラフを作成
        self.ax_c.pie(group_map, labels=group_label, colors=group_color, startangle=90, labeldistance=None, counterclock=False)
        self.ax_c.set_title(self.title[self.i])
        if (self.i == 0):  # 円グラフとクラスの対応を一度だけ凡例として表示
            self.ax_c.legend(loc="center", bbox_to_anchor=(1.3, -0.1), fontsize=7, ncol=4)
        # 表を作成し，デザインする
        data = {'クラス': group_label, 'デッキ数': group_map, "使用率": group_per}
        df = pd.DataFrame(data)
        tb = self.ax_t.table(cellText=df.values, colLabels=df.columns, loc="center")
        font_props = {'fontweight': 'bold'}
        for (i, j), cell in tb.get_celld().items():
            if (i == 0):
                cell.set_text_props(**font_props, color="w")
        tb[0, 0].set_facecolor('#363636')
        tb[0, 1].set_facecolor('#363636')
        tb[0, 2].set_facecolor('#363636')
        tb[3, 0].set_facecolor("pink")
        tb[2, 0].set_facecolor("hotpink")
        tb[1, 0].set_facecolor("magenta")


class plot_bo3:  # 円グラフと表を生成するクラス
    clan_labels = ["E", "R", "W", "D", "Nc", "V", "B", "Nm"]
    colors = ["olivedrab", "gold", "blue", "orange", "darkviolet", "firebrick", "khaki", "darkturquoise"]
    game = ["予選持ち込み分布", "決勝持ち込み分布"]

    def __init__(self, bo3, i, m, d):  # グラフの表示領域と扱うクラス分布を指定
        self.i = i
        self.bo3 = np.array(bo3) - 1
        self.deck_combo = np.zeros(64)
        self.fig = plt.figure()
        self.month = m
        self.day = d

    def reshape_data(self):
        self.bo3 = self.bo3.reshape(-1, 2)
        for k in self.bo3:
            k = np.sort(k)
            self.deck_combo[k[0] * 8 + k[1]] += 1

    def plot_decks(self):
        self.reshape_data()
        decks_index = np.nonzero(self.deck_combo)
        decks_num = self.deck_combo[decks_index]
        decks_name = []
        for k in decks_index[0]:
            first_deck = k // 8
            second_deck = k % 8
            decks_name.append(self.clan_labels[first_deck] + "," + self.clan_labels[second_deck])
        plt.bar(decks_name, decks_num)
        plt.title(f"{self.game[self.i]}")
        plt.xticks(rotation=90)
        plt.savefig(fr"decks\{self.month}-{self.day}\bo3{self.i}.png")


def main(m, d):
    today = str(m) + "月" + str(d) + "日"
    month = str(m)
    day = str(d)
    group_url, final_url = gen_url(today)  # ローテーション予選，決勝のurlを得る
    if (group_url == "nasi"):  # グループ大会，決勝が見つからなかったらbot.pyに状況を返す
        return "no_game"
    elif (group_url != "nasi" and final_url == "nasi"):
        return "on_game"
    # 以下，大会結果が見つかった時の処理
    folder_path = fr"decks\{month}-{day}"  # フォルダを作成
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        print("フォルダが作成されました")
    else:
        print("フォルダはすでに存在します")
    win = winning_info(final_url, month, day)  # 入賞者の情報を得る
    deck_urls = win.image_conbination()  # デッキのどばすぽurl
    group_clan, group_decks = clan_distribution(group_url)  # 予選のデッキ分布を計算
    final_clan, final_decks = clan_distribution(final_url)  # 決勝のデッキ分布を計算
    fig1, ax1 = plt.subplots()
    ax1.axis("off")
    group_plot = plot_map(group_clan, fig1, 0)  # 予選，決勝の円グラフと表をfigに表示
    group_plot.plot_data()
    final_plot = plot_map(final_clan, fig1, 1)
    final_plot.plot_data()
    fig1.savefig(fr"decks\{month}-{day}\data.png")  # グラフをdata.pngとして保存
    group_bo3 = plot_bo3(group_decks, 0, month, day)
    group_bo3.plot_decks()
    final_bo3 = plot_bo3(final_decks, 1, month, day)
    final_bo3.plot_decks()

    return deck_urls  # discordにどばすぽのリンクを返す


if __name__ == "__main__":
    main(4, 10)
