# Torrent Media Db

This is a web application to manage a database of media entries and their associated torrents, with a smart search feature powered by TMDb.

## Project Structure

- `backend/`: Contains the Python FastAPI application.
- `frontend/`: Contains the React single-page application.

## Getting Started
### 安装
- 前端 
```sh
cd frontend; npm install; npm run build; cd ..
```
- 后端 
```sh
cd backend
python -m venv venv; source venv/bin/activate
python -m ensurepip
python -m pip -r requirements.txt`
```

### 启动
- 前端
```sh
cd frontend; npm start; cd ..
```

- 后湍
```sh
cd backend; source venv/bin/activate
uvicorn app.main:app --port 5009 --reload
```

## 接口文档
* `/docs`, `/redoc` 
* 主要查询接口为： `/api/query`

## 规则自动生成算法
* 规则是在种子查询过程中自动生成的，这样的自动生成存在不可信，因此需要一种方式排除一些不可信的信息变成规则
  
1. 初始分：输入title, cntitle, extitle;
   * 初始 score: 
   * 有 cntitle: score += len(cntitle) * 2
   * title 与 cntitle 不同：score += len(cntitle)
   * 有 extitle 且与 cntitle不同 score += 8
   * 有 year score += 10
2. 搜索
   * 搜索过程没有用 multi 的: score += 5
   * 搜到全匹配：sccore += 10 + len(cntitle)
   * 有差异时，计算 LCS : score += 2 * LCS(tmdb_title, cntitle)
  
3. score < 19 不计入规则

```
 例1: "银翼杀手.mkv", 有中文名但没年份，初始 8，一次搜索到 +5, 结果全匹配，+10+4，总分 27
 例2: "Sullivan's.Travels.1941.1080p.Criterion.Bluray.DTS.x264-Grp", 解出来 title为 "Sullivan s Travels", 无中文名，有year, 初始 18+10=28，一次搜到 +5, 结果是中文因而没有LCS加分，总分 33
 例3: "乱世佳人.Gone.with.the.Wind.1939.BluRay.1080p.x265.10bit.9..."，解出来 len('Gone with the Wind')=18, len('乱世佳人')=4，有年份，初始18+4*2+10=36，搜索+5, 完全匹配 +10+8，总分 59
 例4: "花絮”，搜到"猎魔人：血源制作花絮", 初始2中字 4, 搜索 +5，结果LCS匹配2字符 +4, 得分 13 , 不计入规则
```
> TL;DR 中文名长度大于4的片名搜索很稳了，带年份的也稳了，纯英文需要点长度，中文短词乱匹配的尽量排除掉



