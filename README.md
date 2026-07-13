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
   * title 与 cntitle 不同：score += len(title)
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



---


在 backend/app/crud.py 中，search_and_create_media 函数负责根据种子信息 (TorrentInfo) 来查询对应的媒体库条目，如果没找到则进行搜索并创建。

总结来说，当满足以下逻辑路径时，条目会入库（创建新的 TdbMedia）：

1. 明确的 ID 匹配（未找到现有媒体时）
TMDb ID: 如果 torinfo 包含 tmdb_id 和 tmdb_cat，且本地数据库中找不到该 ID，系统会通过 TMDb 搜索获取详细信息并创建新条目。
IMDb ID: 如果 torinfo 包含 imdb_id (仅限电影)，且本地数据库找不到，系统会搜索 TMDb 获取信息并创建新条目。
2. 盲搜（Blind Search）成功且质量达标
如果上述本地匹配（通过名字、正则表达式等）均失败，系统会进入“盲搜”流程：

通过 TMDb 搜索: 系统会尝试搜索最佳匹配项，并填充 torinfo 的详细信息。
入库条件：
匹配到了正确的 TMDb 数据。
关键指标 id_score >= 19: 搜索结果的匹配得分（id_score）必须大于或等于 19。如果得分低于 19，系统会判定为不置信，此时不会入库（仅返回一个临时的内存对象用于后续处理，避免低质量数据污染数据库）。
补充说明：关于 override 参数
如果传入 override=True，函数会在搜索前强制删除所有与该 torinfo 的 clean_title 或 cntitle 匹配的现有媒体条目及其关联种子。这意味着即使之前存在匹配项，也会被先删后建，从而达到“刷新”或“重置”媒体信息的目的。

总结：什么情况“不会”入库？
已在库中: 如果直接通过 TMDb ID、IMDb ID、种子名称或正则表达式在本地库中找到了匹配项，系统只会创建一个新的“种子”关联（create_torrent），而不会重复创建媒体条目。
盲搜得分过低: 在盲搜过程中，如果 id_score < 19，认为匹配不够准确，拒绝入库。
完全搜索不到: 如果所有尝试（本地查询 + TMDb 远程搜索）都无法找到匹配项，返回 None。
正则表达式拦截: 如果通过 clean_title 找到了媒体，但该媒体配置了 torname_regex 且不匹配当前种子名称，也会被拦截并返回 None。

