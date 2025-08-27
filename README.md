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
1. 初始分：输入title, cntitle, extitle;
   * 初始 score: 4 + len(title)
   * 有 cntitle: score += 8, 有extitle且与cntitle不同 score += 8
   * 有 year score += 10
2. 搜索
   * 搜索过程没有用 multi 的: score += 5
   * 搜出的 tmdb_title == cntitle 的: score += 20
   * 搜出的 LCS(tmdb_title, cntitle) 与 len(tmdb_title) 相差 < 3: score += 10
  
3. score < 19 不计入规则


