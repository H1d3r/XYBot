import json

import aiohttp
import yaml
from loguru import logger
from prettytable import PrettyTable

import pywxdll
from utils.plugin_interface import PluginInterface


class get_contact_list(PluginInterface):
    def __init__(self):
        config_path = "plugins/get_contact_list.yml"
        with open(config_path, "r", encoding="utf-8") as f:  # 读取设置
            config = yaml.safe_load(f.read())

        self.information_post_url = config[
            "information_post_url"
        ]  # 获取信息发送api的url (非微信)

        main_config_path = "main_config.yml"
        with open(main_config_path, "r", encoding="utf-8") as f:  # 读取设置
            main_config = yaml.safe_load(f.read())

        self.ip = main_config["ip"]  # 机器人ip
        self.port = main_config["port"]  # 机器人端口
        self.bot = pywxdll.Pywxdll(self.ip, self.port)  # 机器人api

        self.admin_list = main_config["admins"]  # 获取管理员列表

    async def run(self, recv):
        if recv['id1']:
            admin_wxid = recv['id1']
        else:
            admin_wxid = recv['wxid']

        if admin_wxid in self.admin_list:  # 判断操作人是否在管理员列表内
            heading = ["名字", "类型", "微信号(机器人用)", "微信号(加好友用)"]

            chart = PrettyTable(heading)  # 创建表格

            # pywxdll 0.2
            data = self.bot.get_contact_list()

            for i in data:  # 在通讯录数据中for
                name = i["name"]  # 获取昵称
                wxcode = i["wxcode"]  # 获取微信号(机器人用)
                wxid = i["wxid"]  # 获取微信号(加好友用)
                if wxid[:5] == "wxid_":  # 判断是好友 群 还是其他（如文件传输助手）
                    id_type = "好友"
                elif wxid[-9:] == "@chatroom":
                    id_type = "群"
                else:
                    id_type = "其他"
                chart.add_row([name, id_type, wxid, wxcode])  # 加入表格

            chart.align = "l"
            # 不传直接发微信是因为微信一行实在太少了，不同设备还不一样，用pywxdll发excel文件会报错
            json_data = json.dumps(
                {"content": chart.get_string()}
            )  # 转成json格式 用于发到api
            url = self.information_post_url + "/texts"  # 创建url
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.87 Safari/537.36",
            }

            conn_ssl = aiohttp.TCPConnector(verify_ssl=False)
            async with aiohttp.request(
                    "POST", url=url, data=json_data, headers=headers, connector=conn_ssl
            ) as req:
                reqeust = await req.json()
            await conn_ssl.close()

            fetch_code = reqeust["fetch_code"]  # 从api获取提取码
            date_expire = reqeust["date_expire"]  # 从api获取过期时间

            fetch_link = f"{self.information_post_url}/r/{fetch_code}"  # 创建获取链接
            out_message = f"-----XYBot-----\n🤖️机器人的通讯录：\n{fetch_link}\n过期时间：{date_expire}"  # 组建输出信息

            self.bot.send_txt_msg(recv["wxid"], out_message)
            logger.info(f'[发送信息]{out_message}| [发送到] {recv["wxid"]}')  # 发送

        else:  # 用户不是管理员
            out_message = "-----XYBot-----\n❌你配用这个指令吗？"
            logger.info(f'[发送信息]{out_message}| [发送到] {recv["wxid"]}')
            self.bot.send_txt_msg(recv["wxid"], out_message)
