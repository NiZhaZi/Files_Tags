import json


class Convert:
    def __init__(self, file):
        self.file = file
        with open(file, 'r', encoding='utf-8') as f:
            self.js = json.load(f)

        js_company = self.movie2company()
        js_actor = self.movie2actor()
        with open('json_files/company.json', 'w', encoding='utf-8') as file1:
            json.dump(js_company, file1, ensure_ascii=False, indent=4)

        with open('json_files/actor.json', 'w', encoding='utf-8') as file2:
            json.dump(js_actor, file2, ensure_ascii=False, indent=4)

    def movie2company(self):
        company = {}

        for mv, inf in self.js.items():
            act = [i for i in inf['actors']]
            com = inf['company']
            company.update({com:{mv:act}})
        return company

    def movie2actor(self):
        actor = {}
        for mv, inf in self.js.items():
            com = inf['company']
            for act in inf['actors']:
                actor[act] = actor.get(act, {}) # 如果没有act这个键，则初始化为空字典
                actor[act]['companies'] = actor[act].get('companies',[])+[com]
                actor[act]['movies'] = actor[act].get('movies',[])+[mv]
        return  actor


if __name__ == '__main__':
    Convert("json_files/movie.json")