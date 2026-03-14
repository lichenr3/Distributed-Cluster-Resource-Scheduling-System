import uvicorn

from master.core.config import MASTER_HOST, MASTER_PORT

if __name__ == "__main__":
    uvicorn.run("master.main:app", host=MASTER_HOST, port=MASTER_PORT, reload=False)
