import json
from pathlib import Path


class Search:
    def __init__(self, string, mode):
        self.string = string
        self.js = self.read_json(mode)
        result = self.js.get(self.string, None)
        if result:
            print(result)
        else:
            print("没有找到数据")

    @staticmethod
    def read_json(mode):
        with open(Path('json_files')/ f'{mode}.json', 'r', encoding='utf-8') as file:
            js = json.load(file)
        return js

if __name__ == '__main__':
    string_ = input("请输入关键字：")
    # 输入三种搜索类型：影片，公司，演员
    # movie, company, actor
    mode_ = 'movie'
    Search(string_, mode_)