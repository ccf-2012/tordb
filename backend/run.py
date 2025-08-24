import uvicorn
import os

if __name__ == "__main__":
    # 从环境变量获取端口，或使用默认值 6006
    port = int(os.environ.get("PORT", 6009))

    print(f"Starting Uvicorn server on 0.0.0.0:{port}")

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        workers=1
    )