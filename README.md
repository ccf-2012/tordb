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

