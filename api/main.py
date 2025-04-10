import uvicorn
from app.application import application
from app.configs.configs import SERVER_PORT

if __name__ == "__main__":
    uvicorn.run(application, host="0.0.0.0", port=SERVER_PORT)
